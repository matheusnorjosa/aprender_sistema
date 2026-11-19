# Runbook — Concurrency Incidents

Companion to [`ACID_POLICY.md`](ACID_POLICY.md). Tracks how to diagnose and respond to the concurrency failure modes the policy defends against.

> ⚠️ **Não existe Loki nem Grafana em produção.** A stack de coleta/painéis
> (Prometheus + Grafana) é **local e opcional** (`make up-obs`, arquivos gitignored) e
> **não roda em prod** — ver [OBSERVABILITY.md](./OBSERVABILITY.md). Não há **nenhuma**
> referência a Loki no repositório fora deste runbook. Em produção, a fonte de sinal é o
> **stdout dos containers** (`docker compose logs`, driver `json-file`, `max-size: 50m` /
> `max-file: 10`), e o `/metrics` do Django, que é gated (staff / IP interno) e depende de
> scraping externo. As queries LogQL/PromQL abaixo servem para o ambiente local com
> `make up-obs`; em prod, traduza para `docker compose logs … | grep`.

## Signals to watch

| Signal | Where (prod) | What it means |
|---|---|---|
| **Prometheus counter** `as_db_transaction_retries_total` (`apps/core/services/db_retry.py`) | `/metrics` do serviço `web` (gated). Sem scraper externo configurado, só dá para ler pontualmente | A retry fired. A low, bursty rate is normal; a sustained non-zero rate means a hotspot. |
| **Log event** `db_retry_exhausted` | `docker compose logs worker web \| grep db_retry_exhausted` | A user actually hit the ceiling on `max_attempts`. A single burst after a deploy can be noise; sustained events are a bug. |
| **Log event** `solicitacao_batch_approved` over **10 s** | `docker compose logs web \| grep solicitacao_batch_approved` | Batch approvals normally complete in < 1 s. Slowness usually means `skip_locked` is hitting contention somewhere upstream. |
| **Circuit breaker `state=open`** | `GET /api/gcal/circuit-breaker/` (`apps/core/urls.py`) — autenticado | Google Calendar is rejecting us. Not strictly a concurrency issue, but related: approvals no longer publish, so the retry task **`apps.core.tasks.queue_gcal_sync_retry`** (`apps/core/tasks.py`) deve estar re-agendando (`max_retries=10`, `default_retry_delay=300`). Ela é **enfileirada por evento**, não pelo beat — não há entrada dela em `config/celery.py`. |

## Triage — "deadlock_detected in production"

1. **Grab the event** (`db_retry_scheduled` é emitido em `retry_on_deadlock`, `services/db_retry.py`):
   ```bash
   # Produção (sem Loki): stdout dos containers
   docker compose logs --tail=2000 web worker | grep db_retry_scheduled | grep 40P01
   ```
   Com a stack local de observabilidade (`make up-obs`), o equivalente LogQL seria
   `{event="db_retry_scheduled"} | operation=~"solicitacao.*" | pgcode="40P01"`.
2. **Check recent activity**: was there a bulk import or migration running? A deploy in the last 10 min?
3. **Identify the two transactions** in Postgres logs (`log_lock_waits=on` must be enabled):
   ```sql
   SELECT pid, now() - xact_start AS running_for, query, wait_event_type, wait_event
   FROM pg_stat_activity
   WHERE state <> 'idle'
   ORDER BY xact_start
   LIMIT 20;
   ```
4. **If the same operation appears twice** (two `solicitacao.approve` at once on the same row): expected — the retry helper and `select_for_update` will resolve it. If `db_retry_exhausted` fires for the same `operation` more than once per minute, escalate.
5. **If two different operations appear** (e.g. `solicitacao.approve` and an unrelated write): we have a lock-ordering violation. Compare the query acquisition order against the documented convention in `ACID_POLICY.md` — the newer code path is almost always the offender.

## Triage — "serialization failure"

Rare under `READ COMMITTED`. If you see it:
1. Look for places where code reads data outside `select_for_update`, decides something, and then writes — that's the classic "lost update" shape.
2. Check if anyone recently changed the isolation level for a specific call (`transaction.atomic(using=..., savepoint=...)` does **not** change isolation; `SET TRANSACTION ISOLATION LEVEL SERIALIZABLE` does).
3. Fix: add `select_for_update` on the row being read or move the decision inside the existing lock scope.

## Triage — "concurrent GCal publish left external_event_id in weird state"

Symptoms: `Solicitacao.gcal_status = PUBLISHED` but `external_event_id = NULL`, two different `last_sync_action` values flipping, or a row that stays in `PENDING`.

Since DEF-32 (2026-11-19) every publish, resend, reapply and cancel request writes a request id on the row
(`Solicitacao.gcal_pedido`) under the row lock, in the same transaction that enqueues the task
(`pedir_operacao_gcal`). The task only acts if the id it carries is still the one on the row and the row is
still `PENDING` (`ERROR` for the circuit-breaker retry). A superseded request, a request whose transaction was
rolled back and a message delivered again after the task finished all return `SKIP`: no Calendar call and no
write on the row. In OAuth mode the task builds the operator's client before the guard, and that may refresh
the token (a `GOOGLE_REFRESH_TOKEN` AuditLog). Duplicate deliveries are expected: the publish and cancel tasks
run with `acks_late` + `reject_on_worker_lost`, so the message comes back when the worker process dies mid-task
(at once) or when the whole host goes down (after the Redis `visibility_timeout`, 1 h). A redelivery after a
death between the Google write and the commit finds the row still `PENDING` with the same id and writes again
(UPDATE or ADOPT of the same event, or a DELETE that gets 404/410): the event is not duplicated, but with
`GCAL_SEND_UPDATES` other than `none` the e-mail may go out again.

1. Find the latest request: `Solicitacao.gcal_pedido` holds it; look for the AuditLog rows whose `details.pedido`
   equals it. The three `*_REQUESTED` rows carry it, and so do the outcomes (`PUBLISH_GCAL`, `CANCEL_GCAL`,
   `PUBLISH_GCAL_ERROR`, `GCAL_RETRY_SUCCESS`). Batches write no `*_REQUESTED`: an id with no `*_REQUESTED` row
   came from a batch (publish, reapply or resend), and it is also in `TaskResult.task_kwargs` (kept 1 day).
2. Check the executions for that `solicitacao_id`, for both tasks (publish and cancel):
   ```bash
   docker compose logs --tail=5000 worker | grep -E "task_publish_solicitacao_to_gcal|task_cancel_solicitacao_from_gcal" | grep "<ID>"
   ```
   More than one execution is fine as long as only one acted; the others log `pedido superado ou já concluído`.
3. A row stuck in `PENDING`. The request never commits `PENDING` without a queued task (if the queue refuses
   the task, the transaction rolls back and the API answers 503 `fila_indisponivel`), but the task may never
   reach an outcome:
   - host crash with the task in flight: the message comes back after the Redis `visibility_timeout` (up to 1 h);
   - database down when a delivery starts (first delivery, redelivery after 1 h, requeue after the worker
     process died): the `STARTED` write fails before the task body, Celery acks the message without running it,
     and the row stays `PENDING`. The same happens when the `autoretry_for` attempts run out (3, 180 s apart) or
     the database error is not a connection error: the retry only covers a connection drop mid-task with the
     database back before the next run;
   - hard crash of VM01 with the task inside the row lock: PostgreSQL keeps the lock until it notices the dead
     client (about 2 h with Linux defaults). Meanwhile a resend answers 409 `linha_ocupada`, and the returned
     message may run out of `autoretry_for` attempts.

   To find them: `PENDING` for more than 15 min by `gcal_last_sync_at`, and nothing in `unacked` on the broker
   Redis (DB 1, `ZCARD unacked_index`; counts only, never print the content).
4. Recover, by the latest request found in step 1:
   - `CANCEL_GCAL_REQUESTED`: **never** resend or reapply. That undoes the removal and may bring back an event
     Google already deleted (the Google delete is a soft delete, and the UPDATE sends `status: confirmed`). Wait
     for the message (up to about 1 h) or redo the cancel with `POST /api/solicitacoes/{id}/cancel-gcal/`, which
     accepts a `PENDING` row with `external_event_id` (the screen has no button for a `PENDING` row);
   - `PUBLISH_GCAL_REQUESTED` or `RESYNC_GCAL_REQUESTED` (a single-row publish or resend), or no `*_REQUESTED`
     row with that id (a batch request): batch resend from the Pré-agenda is safe. It accepts `PENDING` rows, the
     new request supersedes the old one, and the old message returns `SKIP` when it arrives. Reapply does not
     help here: it refuses a `PENDING` row (`operacao_em_andamento`).

## Triage — "import took 30 min and then only some rows were saved"

All 10 import services now use **savepoint-per-row**, so a single bad row
aborts its own insert/update only — the outer `transaction.atomic()` still
commits the valid rows (or rolls the whole file back if `dry_run=True`).
If you see an import finish with fewer rows persisted than expected:
1. The rejected rows are reported in `pendencias.*` sections of the response
   (`usuarios`, `dates`, `outros`, etc.). Each entry carries `linha` and
   `erro`.
2. Fix the offending rows in the source file and re-run — re-importing the
   same valid rows is idempotent (unique constraints / `external_hash`
   dedupe).
3. If you see an IntegrityError *inside* the savepoint that looks like a
   constraint change (e.g. a new `NOT NULL` after a migration), that is a
   schema regression, not a data issue — open an incident.

## Escalation

- **Repeated `db_retry_exhausted` on the same operation** for > 5 min → page the on-call backend engineer.
- **Circuit breaker stays open** (`GET /api/gcal/circuit-breaker/` returns `state=open` for > 10 min) → page OAuth owner to investigate Google API status.
- **`pg_stat_activity` shows > 50 connections in `idle in transaction`** → open DB incident; kill the longest-running transactions with `SELECT pg_terminate_backend(pid)` after confirming it is a request, not a migration.

## Known gaps this runbook does not yet cover

- Tracing a deadlock back to the specific Python call stack (we have structured logs but not a distributed tracing span name yet — tracked in the `#845` epic).
- Per-tenant lock metrics (we count by `operation`, not by `solicitacao_id` or `user_id` — intentional, since high-cardinality labels blow up Prometheus storage).

## Related

- [`ACID_POLICY.md`](ACID_POLICY.md) — policy spec, lock ordering, decorator contract.
- [`COVERAGE_POLICY.md`](analysis/COVERAGE_POLICY.md) — test bar for the services this runbook protects.
- Issue [#866](https://github.com/matheusnorjosa/aprender_sistema/issues/866) — ASQ-016 tracking.
