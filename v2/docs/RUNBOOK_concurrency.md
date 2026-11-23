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

1. Find the latest Google record of the row: the newest AuditLog with that `details.solicitacao_id` among
   `PUBLISH_GCAL_REQUESTED`, `RESYNC_GCAL_REQUESTED`, `CANCEL_GCAL_REQUESTED`, `CANCELAR_NA_AGENDA_REQUESTED`,
   `PUBLISH_GCAL`, `CANCEL_GCAL`, `CANCELAR_NA_AGENDA` and `PUBLISH_GCAL_ERROR`. It works for rows marked by any version, before or after DEF-32, with three pre-DEF-32 limits listed in
   [gcal.spec.md](specs/backend/gcal.spec.md) ("Linha parada em `PENDING`"). Three cases do not count,
   because they can be written after a cancel request while the row is still `PENDING`: the preview
   (`details.dry_run` true), the circuit-breaker retry error (`details.operation` = `retry`; the retry only acts
   on `ERROR` rows, and its `GCAL_RETRY_SUCCESS` is not in the list) and a `PUBLISH_GCAL` with
   `details.action` = `SKIP`, which the version before DEF-32 wrote without taking the row out of `PENDING`.
   Google copy, approval and edit records do not count either. Batches write no `*_REQUESTED`, so a stuck batch
   request may leave no record at all. Read-only, in `python manage.py shell`, with the row id in `ID`:
   ```python
   from apps.core.models import AuditLog, Solicitacao
   ID = int(ID)
   s = Solicitacao.objects.get(pk=ID)
   print(s.gcal_status, bool(s.external_event_id), s.cancelado_na_agenda)
   assert s.gcal_status == "PENDING", "a linha não está em PENDING: conferir o ID"
   ACOES = ["PUBLISH_GCAL_REQUESTED", "RESYNC_GCAL_REQUESTED", "CANCEL_GCAL_REQUESTED",
            "CANCELAR_NA_AGENDA_REQUESTED", "PUBLISH_GCAL", "CANCEL_GCAL", "CANCELAR_NA_AGENDA",
            "PUBLISH_GCAL_ERROR"]
   conta = lambda r: not r.details.get("dry_run") and r.details.get("operation") != "retry" and not (
       r.action == "PUBLISH_GCAL" and r.details.get("action") == "SKIP")
   regs = AuditLog.objects.filter(details__solicitacao_id=ID, action__in=ACOES).order_by("-created_at", "-id")
   ultimo = next((r for r in regs if conta(r)), None)
   print(ultimo.action if ultimo else "nenhum registro")
   ```
   The `int()` and the row check come first on purpose: the JSON filter also compares the type, and an id as
   text (`"123"`) does not match the stored number. Without them, a text or wrong id would print
   "nenhum registro", which sends you to resend. With them, a wrong id stops with an error (`DoesNotExist` or the
   row not in `PENDING`). "nenhum registro" only counts once the row is confirmed `PENDING`. The three cases are
   filtered in Python: `exclude()` on a JSON key would also drop the rows without that key.
2. Check the executions for that `solicitacao_id`, for both tasks (publish and cancel):
   ```bash
   docker compose logs --tail=5000 worker | grep -E "task_publish_solicitacao_to_gcal|task_cancel_solicitacao_from_gcal|task_cancelar_na_agenda" | grep "<ID>"
   ```
   More than one execution is fine as long as only one acted; the others log `pedido superado ou já concluído`.
3. A row stuck in `PENDING`. The request never commits `PENDING` without a queued task (if the queue refuses
   the task, the transaction rolls back and the API answers 503 `fila_indisponivel`), but the task may never
   reach an outcome:
   - host crash with the task in flight: the message comes back after the Redis `visibility_timeout` (up to 1 h);
   - database down when a delivery starts (first delivery, redelivery after 1 h, requeue after the worker
     process died): the `STARTED` write fails before the task body, Celery acks the message without running it,
     and the row stays `PENDING`. Celery only runs the task again (`autoretry_for`, 180 s later, up to 3 times)
     when the `ERROR` mark itself fails with a Django `OperationalError` or `InterfaceError` (in practice a
     connection drop or the 30 s production statement timeout; a deadlock is rare). A short database drop
     mid-task needs no retry: the mark opens a new connection and writes `ERROR`. The row also stays `PENDING`
     when the attempts run out, or when the mark fails with another database error (`IntegrityError`,
     `DataError`, `ProgrammingError`);
   - hard crash of VM01 with the task inside the row lock: PostgreSQL keeps the lock until it notices the dead
     client (about 2 h with Linux defaults). Meanwhile a resend answers 409 `linha_ocupada`, and the returned
     message may run out of `autoretry_for` attempts.

   To find them: `PENDING` for more than 15 min by `gcal_last_sync_at`, and nothing in `unacked` or in the queue
   on the broker Redis (DB 1, `ZCARD unacked_index` and `LLEN celery` at 0; counts only, never print the content).
4. Recover, by the latest record found in step 1:
   - the row has `cancelado_na_agenda` (printed `True`), or the latest record is `CANCELAR_NA_AGENDA_REQUESTED`, or
     a `PUBLISH_GCAL_ERROR` with `details.operation` = `cancelar_na_agenda`: a stuck cancel-in-calendar (CON-08).
     Redo it with `POST /api/solicitacoes/{id}/cancelar-na-agenda/`, which accepts a `PENDING` row with
     `external_event_id` and does not repeat the marker if the title already has it. A row cancelled in the
     calendar is **never** resent nor removed from Google: both refuse it;
   - `CANCEL_GCAL_REQUESTED`: a stuck cancel, from any version. **Never** resend or reapply. That undoes the
     removal and may bring back an event Google already deleted (the Google delete is a soft delete, and the
     UPDATE sends `status: confirmed`). Waiting only helps while the message is still in `unacked` or in the
     queue (`LLEN celery` above 0), up to about 1 h. A row found by the filter above has no message to come back:
     redo the cancel now with `POST /api/solicitacoes/{id}/cancel-gcal/`, which accepts a `PENDING` row with
     `external_event_id` (the screen has no button for a `PENDING` row). If someone batch-resent on top of the
     cancel while it was still running, the batch left no record and the rule reads the cancel: it keeps the side
     that does not put back in Google what someone asked to remove;
   - anything else, including no record at all: the stuck request is a publish, resend or reapply. Resend it from
     the Pré-agenda: resend accepts `PENDING` rows, the new request supersedes the old one, and the old message
     returns `SKIP` when it arrives. It forces the UPDATE and, with `GCAL_SEND_UPDATES` other than `none`,
     e-mails external guests even with no change. Reapply does not help here: it refuses a `PENDING` row
     (`operacao_em_andamento`);
   - Event already over: resend and reapply refuse it (`evento_passado`). A stuck cancel still goes through
     `cancel-gcal`, which ignores the date, if the row has `external_event_id`. Otherwise check in Google whether
     the event exists (by `external_event_id` or by the id `asv2{id}`) and set the row to `ERROR` in the admin,
     where `gcal_status` is editable (`external_event_id` is read-only). The stuck row has no retry queued.

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
