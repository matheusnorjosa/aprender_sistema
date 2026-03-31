# ADR-005: Single Source of Truth em PostgreSQL

**Status:** Accepted
**Date:** 2025-10-01
**Decider:** Matheus Norjosa

## Context

O sistema original operava sobre 4+ planilhas Google/Excel com 82.389 fórmulas cruzadas (IMPORTRANGE, VLOOKUP). Dados duplicados entre planilhas causavam inconsistências frequentes — nomes divergentes, emails inválidos, dessincronia de agenda.

## Decision

PostgreSQL é a única fonte de verdade (SSOT) para todos os dados. Planilhas são read-only ou eliminadas.

- Cada entidade tem uma única tabela autoritativa
- ForeignKeys garantem integridade referencial
- Constraints validam dados na entrada (CHECK, UNIQUE, NOT NULL)
- ON DELETE PROTECT para entidades críticas (Usuario, Formador)
- ON DELETE CASCADE para entidades dependentes (Evento, Aprovação)

## Consequences

- Zero duplicação de dados entre tabelas
- FKs impedem referências a registros inexistentes
- Properties calculadas (`@property`) em vez de campos duplicados
- Planilhas substituídas por formulários web + API REST
- ETL importa dados legados uma vez, depois sistema é fonte única

## References

- `v2/docs/SINGLE_SOURCE_OF_TRUTH.md`
- `v2/backend/apps/core/models/`
