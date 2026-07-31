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
| **Approve (single)** | `services/solicitacao_approval.py :: approve_solicitacao` | Function body (`transaction.atomic`) | `Solicitacao.objects.select_for_update().get(pk=...)`, re-fetched inside tx (`:128-129`) | Status check (`status == 'pendente'`) after lock **+ revalidação de disponibilidade dentro do lock** (`enforce_solicitacao_availability`, `:136` — #1452) | ✅ `@retry_on_deadlock("solicitacao.approve")` |
| **Reject (single)** | `services/solicitacao_approval.py :: reject_solicitacao` | Same | Same, rejected instead of approved | Same | ✅ `@retry_on_deadlock("solicitacao.reject")` |
| **Approve (batch)** | `services/solicitacao_approval.py :: batch_approve_solicitacoes` | Function body | `select_for_update(skip_locked=True).order_by('id')` so concurrent batches never deadlock | `skip_locked` drops already-locked rows; concurrent duplicate batches approve 0 | ✅ `@retry_on_deadlock("solicitacao.batch_approve")` |
| **Reject (batch)** | `services/solicitacao_approval.py :: batch_reject_solicitacoes` | Same | Same | Same | ✅ `@retry_on_deadlock("solicitacao.batch_reject")` |
| **OAuth refresh** | `services/oauth/token_manager.py :: refresh_access_token_safe` | Function body | `GoogleOAuthCredential.objects.select_for_update().get(id=...)` + double-check `token_expiry` after lock | Second caller short-circuits if token is still valid | ✅ `@retry_on_deadlock("oauth.refresh_access_token")` |
| **GCal publish (entry point)** | `services/gcal/sync.py :: apply_one_solicitacao` | ⚠️ **NONE — see "Known gaps" below.** The function has no `transaction.atomic()`; each `s.mark_gcal` / `s.save` commits on its own. HTTP call to Google happens outside any tx | Caller (Celery task / management command) is responsible for `select_for_update` on the batch | Deterministic event id + payload hash on `Solicitacao`; duplicate dispatches collapse via `client.get(...)` existence check | ⚠️ Decorator applied (`sync.py:30`) but **ineffective** — see gaps |
| **GCal low-level upsert** | `services/gcal/sync.py :: upsert_one` (`sync.py:143`) | Each `s.save(update_fields=...)` is atomic on its own; HTTP call happens between saves | Caller contract: wrap in `transaction.atomic()` + `select_for_update` for batch sync | Same — event id + hash | Circuit breaker at HTTP layer (`services/gcal/circuit_breaker.py`, #779) |
| **GCal publish (DRF entry point)** | `services/solicitacao_publish.py :: publish_to_gcal` (`:168`) | ⚠️ **NONE.** `mark_gcal` (`:229`) e `AuditLog.objects.create` (`:253`) são escritas independentes | — | — | ❌ **Ausente** — zero ocorrências de `transaction.atomic` ou `retry_on_deadlock` no arquivo |
| **Imports** — 10 services de planilha | `services/*_import.py` (`bloqueios`, `colecoes`, `controle_acoes`, `dat_cadastros`, `deslocamentos`, `equipe_gerencia`, `eventos`, `municipios`, `produtos`, `usuarios`) | Outer `transaction.atomic` for dry-run rollback + **savepoint-per-row** via nested `transaction.atomic` | No explicit row locks — idempotency via unique constraints + `external_hash` | One bad row only aborts itself (savepoint); dry-run still discards the whole batch | ❌ Not yet — imports run offline. |
| **Import canônico** (`import_export_contract`) | `services/export_contract_importer.py` | ⚠️ Um único `transaction.atomic()` grosso (`:355`) — **sem savepoint-per-row** | Sem locks | `external_hash` / chaves naturais | ❌ Não |

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

## Known gaps (verified 2026-07-24)

The matrix above described the intended design. These three rows were corrected against the code
and are **open gaps**, not documentation errors to be re-closed silently:

1. **`apply_one_solicitacao` viola a regra "non-negotiable" acima.**
   O decorator `@retry_on_deadlock(operation="gcal.apply_one_solicitacao")` está aplicado
   (`services/gcal/sync.py:30`), mas o corpo da função (`:30-140`) **não abre
   `transaction.atomic()`**. A única ocorrência da string `transaction.atomic` no arquivo inteiro é
   um **comentário** (`sync.py:184`). Consequência: em caso de `40001`/`40P01`, o retry re-executa
   a função a partir do zero — inclusive a chamada HTTP ao Google — sem rollback de escritas já
   commitadas. Ou seja, o retry existe no papel e não dá a garantia que o contrato promete.

2. **`solicitacao_publish.py` não tem fronteira transacional nem retry.**
   É o service que atende os endpoints DRF de publish/resync/cancel. `publish_to_gcal` (`:168`)
   faz duas escritas — `mark_gcal` (`:229`) e `AuditLog.objects.create` (`:253`) — sem
   `transaction.atomic` e sem `retry_on_deadlock` (zero ocorrências no arquivo). Uma falha entre
   as duas deixa o estado do GCal marcado **sem** o registro de auditoria correspondente.

3. **O importador canônico não tem savepoint-per-row.**
   `services/export_contract_importer.py:355` usa um único `transaction.atomic()` para o lote
   inteiro. Uma linha ruim aborta o lote — comportamento diferente dos 10 services de planilha,
   que seguem o padrão ASQ-016. Como `import_export_contract` é hoje o caminho canônico de import,
   vale decidir se ele deve adotar o mesmo padrão.

Nenhum dos três está coberto por teste de concorrência
(`apps/core/tests/test_concurrency_regressions_asq016.py` cobre OAuth `:65`, GCal publish `:199` e
savepoint de import `:245`, mas não os casos acima).

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
