# ADR-003: Regras de Disponibilidade e Timezone (RD-01 a RD-08)

**Status:** Accepted
**Date:** 2025-10-15
**Decider:** Matheus Norjosa

## Context

Formadores atendem múltiplos municípios em diferentes horários. O sistema original usava fórmulas Excel para detectar conflitos de agenda, com falhas frequentes em bordas de timezone (eventos próximos da meia-noite apareciam no dia errado).

## Decision

Implementar 8 regras de disponibilidade com timezone-aware comparison:

- **RD-01**: Não-sobreposição (overlap ≥1min = conflito)
- **RD-02**: Bloqueio total (T) impede qualquer evento
- **RD-03**: Bloqueio parcial (P) impede no subintervalo
- **RD-04**: Buffer de deslocamento (D) entre municípios diferentes (configurável, default 120min). municipio=None tratado como cidade diferente.
- **RD-05**: Capacidade diária (M) por formador (configurável)
- **RD-06**: Armazenamento em UTC, comparação em America/Fortaleza
- **RD-07**: Prioridade: Bloqueios → Conflitos → Buffer → Limite
- **RD-08**: Mensagens com código/tipo/detalhe para cada conflito

## Consequences

- Timezone: `zoneinfo.ZoneInfo("America/Fortaleza")` (stdlib, sem pytz)
- Todos os datetime são stored em UTC no PostgreSQL
- Comparações de disponibilidade usam `to_local()` para converter
- 6 códigos de conflito: E (evento), M (capacidade), D (deslocamento), P (parcial), T (total), X (outro)

## References

- CP-03 (Cláusula Pétrea)
- `v2/backend/apps/core/services/availability_service.py`
- `v2/backend/apps/core/tests/test_availability_service.py`
- `docs/business-rules/regras-disponibilidade.md`
