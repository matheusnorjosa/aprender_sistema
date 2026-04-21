# Runbook — Concurrency Incidents

Companion to [`ACID_POLICY.md`](ACID_POLICY.md). Tracks how to diagnose and respond to the concurrency failure modes the policy defends against.

## Signals to watch

| Signal | Where | What it means |
|---|---|---|
| **Prometheus counter rate** `rate(as_db_transaction_retries_total[5m]) > 0` | Grafana `aprender-db-concurrency` board | A retry fired in the last 5 minutes. A low, bursty rate is normal; a sustained non-zero rate means a hotspot. |
| **Log event** `db_retry_exhausted` | Loki / stdout | A user actually hit the ceiling on `max_attempts`. A single burst after a deploy can be noise; sustained events are a bug. |
| **Log event** `solicitacao_batch_approved` over **10 s** | Loki | Batch approvals normally complete in < 1 s. Slowness usually means `skip_locked` is hitting contention somewhere upstream. |
| **Circuit breaker `state=open`** | `GET /api/gcal/circuit-breaker/` | Google Calendar is rejecting us. Not strictly a concurrency issue, but related: approvals no longer publish, so the task retry task (`task_retry_gcal_sync_when_breaker_closes`) should be firing. |

## Triage — "deadlock_detected in production"

1. **Grab the event** from Loki:
   ```
   {event="db_retry_scheduled"} | operation=~"solicitacao.*" | pgcode="40P01"
   ```
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

Symptoms: `Solicitacao.gcal_status = PUBLISHED` but `external_event_id = NULL`, or two different `last_sync_action` values flipping.

1. Check for duplicate Celery task enqueues for the same `solicitacao_id`:
   ```
   {event="task_publish_solicitacao_to_gcal"} | solicitation_id=<ID>
   ```
2. If count > 1 in < 30 s, the upstream dispatcher is double-queuing — fix the dispatcher, not the task.
3. As a safety net, `apply_one_solicitacao` is decorated with `@retry_on_deadlock`. A torn state should not be possible from a single dispatch — it requires two parallel dispatches.
4. Recover: either wait for the circuit-breaker retry task to re-sync, or manually re-apply via the Django admin action.

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
