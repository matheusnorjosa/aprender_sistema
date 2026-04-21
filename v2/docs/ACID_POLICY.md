# ACID Policy — Aprender Sistema v2

Formal transactional policy for the critical flows. Tracks issue [#866](https://github.com/matheusnorjosa/aprender_sistema/issues/866) (ASQ-016, part of epic [#845](https://github.com/matheusnorjosa/aprender_sistema/issues/845)).

## Goals

- Every critical flow has an explicit, documented transaction boundary.
- Lock acquisition order is consistent across services, so two concurrent callers cannot deadlock over the same resources in different orders.
- Transient PostgreSQL concurrency errors (serialization failure, deadlock detected) are retried automatically inside the service layer — callers see the operation succeed, not an opaque 500.
- Concurrency behavior is covered by regression tests in CI.

## Database configuration (recap)

| Setting | Value | Note |
|---------|------:|------|
| `ATOMIC_REQUESTS` | *unset* | Services own transaction boundaries; DO NOT set this globally. |
| `CONN_MAX_AGE` | 60 | Persistent connections, health-checked. |
| `statement_timeout` | 30s (prod) | Kills runaway queries before they block others. |
| Isolation level | `READ COMMITTED` (PostgreSQL default) | Row locks via `SELECT ... FOR UPDATE` give serializability where it matters. |

## ACID matrix — critical flows

| Flow | Entry point | TX boundary | Lock strategy | Idempotency | Retry on deadlock |
|------|------|------|---|---|---|
| **Approve (single)** | `services/solicitacao_approval.py :: approve_solicitacao` | Function body (`transaction.atomic`) | `Solicitacao.objects.select_for_update().get(pk=...)`, re-fetched inside tx | Status check (`status == 'pendente'`) after lock | ✅ `@retry_on_deadlock("solicitacao.approve")` |
| **Reject (single)** | `services/solicitacao_approval.py :: reject_solicitacao` | Same | Same, rejected instead of approved | Same | ✅ `@retry_on_deadlock("solicitacao.reject")` |
| **Approve (batch)** | `services/solicitacao_approval.py :: batch_approve_solicitacoes` | Function body | `select_for_update(skip_locked=True).order_by('id')` so concurrent batches never deadlock | `skip_locked` drops already-locked rows; concurrent duplicate batches approve 0 | ✅ `@retry_on_deadlock("solicitacao.batch_approve")` |
| **Reject (batch)** | `services/solicitacao_approval.py :: batch_reject_solicitacoes` | Same | Same | Same | ✅ `@retry_on_deadlock("solicitacao.batch_reject")` |
| **OAuth refresh** | `services/oauth/token_manager.py :: refresh_access_token_safe` | Function body | `GoogleOAuthCredential.objects.select_for_update().get(id=...)` + double-check `token_expiry` after lock | Second caller short-circuits if token is still valid | ✅ `@retry_on_deadlock("oauth.refresh_access_token")` |
| **GCal publish (entry point)** | `services/gcal/sync.py :: apply_one_solicitacao` | Function body wraps DB writes via `s.mark_gcal` / `s.save`; HTTP call to Google happens outside the tx | Caller (Celery task / management command) is responsible for `select_for_update` on the batch; single-item callers use `@retry_on_deadlock` as the safety net | Deterministic event id + payload hash on `Solicitacao`; duplicate dispatches collapse via `client.get(...)` existence check | ✅ `@retry_on_deadlock("gcal.apply_one_solicitacao")` |
| **GCal low-level upsert** | `services/gcal/sync.py :: upsert_one` | Each `s.save(update_fields=...)` is atomic on its own; HTTP call happens between saves | Caller contract: wrap in `transaction.atomic()` + `select_for_update` for batch sync | Same — event id + hash | Inherits retry via `apply_one_solicitacao`; circuit breaker at HTTP layer (#779) |
| **Import/ETL** — all 10 services | `services/*_import.py` (`bloqueios`, `colecoes`, `controle_acoes`, `dat_cadastros`, `deslocamentos`, `equipe_gerencia`, `eventos`, `municipios`, `produtos`, `usuarios`) | Outer `transaction.atomic` for dry-run rollback + **savepoint-per-row** via nested `transaction.atomic` | No explicit row locks — idempotency via unique constraints + `external_hash` | One bad row only aborts itself (savepoint); dry-run still discards the whole batch | ❌ Not yet — imports run offline. |

## Lock ordering convention

When a flow needs to lock more than one row across tables, acquire locks in this order:

1. `Usuario`
2. `Solicitacao`
3. `AvailabilityBlock`
4. `GoogleOAuthCredential`
5. `AuditLog` (always INSERT-only, last)

All multi-row locks in a single transaction must use `ORDER BY id ASC` to prevent the "lock rows in different orders" class of deadlock — this is already how the batch approval paths work.

## Deadlock retry contract

The helper lives at `apps/core/services/db_retry.py`:

```python
from apps.core.services.db_retry import retry_on_deadlock

@retry_on_deadlock(operation="solicitacao.approve")
def approve_solicitacao(...):
    with transaction.atomic():
        ...
```

- **Retryable PostgreSQL SQLSTATEs**: `40001` (serialization failure), `40P01` (deadlock detected). Everything else (IntegrityError, ProgrammingError, DataError) propagates immediately — those are programmer bugs, not transient.
- **Max attempts**: 3 (default). On exhaustion the last exception is raised and a warning is logged with `event=db_retry_exhausted`.
- **Backoff**: jittered exponential, `rand(0, min(1.0s, 100ms * 2^(attempt-1)))`. Small by design — serialization failures are resolved on retry in < 100 ms most of the time.
- **Non-negotiable**: the decorated callable must open its own `transaction.atomic()`. Retrying inside an already-open outer transaction does nothing useful — the outer tx is still poisoned.

## Observability

Prometheus counter `as_db_transaction_retries_total{operation, pgcode, attempt}` is incremented on every retry attempt (not just on final failure). A sustained non-zero rate on any `operation` is the signal to investigate lock contention; a burst followed by a `db_retry_exhausted` log line is the signal that a caller surfaced the failure to the user.

Structured log events:
- `db_retry_scheduled` — one per retry attempt, includes `operation`, `pgcode`, `attempt`, `next_delay_seconds`.
- `db_retry_exhausted` — logged at WARNING when retries are exhausted, with the same fields plus `max_attempts`.

## Gaps tracked for follow-up PRs

Phase 2 (#866) closed the following:

- ✅ **GCal publish retry** — `apply_one_solicitacao` carries `@retry_on_deadlock`; the caller contract for `upsert_one` is documented.
- ✅ **Savepoint-per-row in imports** — rolled out to all 10 import services (bloqueios, colecoes, controle_acoes, dat_cadastros, deslocamentos, equipe_gerencia, eventos, municipios, produtos, usuarios).
- ✅ **Concurrency regression tests** — race coverage added for OAuth refresh, GCal publish, and import savepoint behavior in `test_concurrency_regressions_asq016.py`.
- ✅ **Runbook** — see [`RUNBOOK_concurrency.md`](RUNBOOK_concurrency.md).

Still open, deliberately out of scope:

- **"Count only transient errors" filter** on the GCal circuit breaker (tracked in #779 notes).
- **Distributed tracing span** for each retry attempt — today we have structured logs but no trace context.

## Related

- Epic [#845 — Testing Maturity](https://github.com/matheusnorjosa/aprender_sistema/issues/845)
- [#866 — ASQ-016 ACID policy](https://github.com/matheusnorjosa/aprender_sistema/issues/866)
- [#779 — ASQ-006 GCal circuit breaker](https://github.com/matheusnorjosa/aprender_sistema/issues/779) (already wired)
- Test reference: `apps/core/tests/test_solicitacao_approval_concurrency.py`
