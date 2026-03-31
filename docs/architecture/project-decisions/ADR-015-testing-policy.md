# ADR-015: Política de Testes

**Status:** Accepted
**Date:** 2026-02-24
**Decider:** Matheus Norjosa

## Context

Suite com 1942+ testes precisa de regras claras para manter CI previsível. Testes flacos em xdist (paralelo) e inconsistências entre ambiente local e CI causavam falsos negativos.

## Decision

Regras obrigatórias:

- **Security-first**: Validar permissão ANTES de parâmetros (403 → 400 → 200)
- **Fake GCal em CI**: `GCAL_CLIENT=fake`, `GCAL_SEND_UPDATES=none`
- **Sem CELERY_ALWAYS_EAGER**: Causa divergências em testes de segurança
- **OAuth tokens criptografados**: Usar `_get_fernet_key()` (mesma derivação do serviço)
- **Paths robustos**: `Path(settings.BASE_DIR)`, nunca `/app` hardcoded
- **Fixtures idempotentes**: `get_or_create()` para evitar cross-pollution
- **xdist-safe**: CPFs/usernames com uuid, sem `AuditLog.objects.all().delete()`, counts filtrados
- **Nunca pular testes** por conveniência — ajustar teste OU código

Baseline CI: 1942 passed, 28 skipped, 0 failed.

## Consequences

- CI reproduzível em qualquer runner
- Testes paralelos (xdist) não interferem entre si
- Fixtures explícitas por teste (não globais)
- Coverage threshold: 85% (Phase 1), target 90% (Phase 2)

## References

- `v2/docs/TESTING_POLICY.md`
- `v2/backend/conftest.py`
- `v2/backend/pytest.ini`
- PR #1030 (xdist isolation fixes)
