# ADR-013: Pin Axios + Plano de Migração para Fetch API

**Status:** Accepted
**Date:** 2026-03-31
**Decider:** Matheus Norjosa

## Context

Em 31/03/2026, a conta npm do axios foi comprometida. Versões 1.14.1 e 0.30.4 contêm malware. O projeto usa axios 1.13.5 (seguro), mas o caret (`^`) no package.json permitiria upgrade automático para versão maliciosa.

## Decision

**Imediato**: Pinar axios em versão exata `1.13.5` (remover caret `^`).

**Planejado**: Migrar para Fetch API nativa (issue #782):
1. Criar wrapper `httpClient.ts` (~50 linhas) sobre `fetch()`
2. Migrar `src/api.ts` (instância central)
3. Migrar 5 API clients (adminDAT, acoesNotificacao, datModule, availability, errors)
4. `npm uninstall axios`

Alternativas rejeitadas:
- **Manter caret e monitorar**: Risco de upgrade acidental em CI/deploy
- **Migrar para got/ky/ofetch**: Troca dependência por outra (mesmo risco supply chain)
- **Manter axios indefinidamente**: Biblioteca com histórico de vulnerabilidades

## Consequences

- Zero risco de upgrade para versão comprometida (pin exato)
- Migração para Fetch elimina dependência permanentemente (-40KB bundle)
- Fetch é nativa do browser — zero supply chain risk
- Interceptors (CSRF, error handling) reimplementados em wrapper fino

## References

- CVE-2025-27152
- github.com/axios/axios/issues/10604
- PR #1031 (pin)
- Issue #782 (migração Fetch)
