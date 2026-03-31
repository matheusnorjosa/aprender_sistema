# ADR-007: Upgrade para Django 5.2 LTS

**Status:** Accepted
**Date:** 2026-03-31
**Decider:** Matheus Norjosa

## Context

Django 5.1 sai de suporte em dezembro 2026 (zero patches de segurança após). Django 5.2 é LTS com suporte até abril 2028 (3 anos). Codebase auditado — nenhum dos 10 vetores de breaking change do 5.2 encontrado.

## Decision

Upgrade em 4 waves sequenciais:

- **Wave 0**: Fix deprecation warnings + remover pacotes mortos (nplusone, db-connection-pool, pytz→zoneinfo, CheckConstraint check→condition)
- **Wave 1**: Django 5.1.15 → 5.2.1 + celery-beat 2.7→2.9
- **Wave 2**: DRF 3.15.2 → 3.16.1 + drf-spectacular 0.27.2→0.29.0
- **Wave 3**: 7 pacotes secundários (debug-toolbar 5.1, extensions 4.1, environ 0.13, etc.)

Alternativas rejeitadas:
- **Big bang upgrade**: Risco alto de regressão indetectável
- **Manter 5.1**: Sem patches de segurança após dez/2026
- **Migrar psycopg2→psycopg3**: Escopo separado (habilita native pooling)

## Consequences

- 3 anos de suporte de segurança garantidos
- Habilita futuras features: CompositePrimaryKey, native connection pooling
- Zero mudanças de código no upgrade (Wave 0 preparou tudo)
- 1942 testes passam em todas as waves

## References

- Epic #980, Issues #981-#985
- PRs #1010, #1012, #1020, #1021, #1022
- `thoughts/shared/plans/PLAN-django-5.2-upgrade.md`
