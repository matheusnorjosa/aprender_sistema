# Phase 03 — Disponibilidade, Bloqueios e Grade Mensal

Date: 2026-02-04
Scope: v2 only
Status: Completed

## Explored
- docs/business-rules/regras-disponibilidade.md
- v2/docs/GUIDE_AVAILABILITY.md
- v2/backend/apps/core/services/availability_service.py
- v2/backend/apps/core/views_availability.py
- v2/backend/apps/core/views_availability_monthly.py
- v2/backend/apps/core/services/monthly_grid_service.py
- v2/backend/apps/core/models/agenda.py
- v2/backend/apps/core/models/workflow.py
- v2/backend/apps/core/serializers/agenda.py
- v2/backend/apps/core/views_import_bloqueios.py
- v2/backend/apps/core/tests/test_multi_sector_permissions.py
- v2/frontend/src/pages/Disponibilidade.tsx
- v2/frontend/src/pages/Disponibilidade/MonthlyPage.tsx
- v2/frontend/src/pages/Disponibilidade/FiltersBar.tsx
- v2/frontend/src/pages/Disponibilidade/Grid.tsx
- v2/frontend/src/pages/Disponibilidade/DetailsDrawer.tsx
- v2/frontend/src/api/availability.ts

## What Was Implemented
- RD-01 a RD-05 em availability_service (overlap, bloqueios, buffer, capacidade diária).
- Grade mensal multi-setor com cache e detalhes por célula.
- Bloqueios auto-aprovados e importação CSV/XLSX (Controle/Super).
- Permissão HasSectorAccess e filtros por gerência via EquipeGerencia.

## Findings (Ordered by Severity)
High
- Usuários não-privilegiados podem editar ou excluir bloqueios de terceiros da mesma gerência. O queryset permite listar blocos de outros usuários e não há permissão por objeto para update/delete. Arquivo: v2/backend/apps/core/views_availability.py

Medium
- Sem gerencia_id, a grade mensal retorna dados SUPER para qualquer usuário autenticado (exceto Controle). Isso expõe dados de um setor sensível por padrão. O comportamento está documentado, mas é risco de acesso amplo. Arquivos: v2/backend/apps/core/permissions.py, v2/backend/apps/core/views_availability_monthly.py, v2/backend/apps/core/tests/test_multi_sector_permissions.py

Low
- check_conflicts declara tratar municipio=None como cidade diferente, mas se ambos forem None não exige buffer. Pode sub-detectar conflito de deslocamento. Arquivo: v2/backend/apps/core/services/availability_service.py
- RD-08 documenta código “E” para evento existente, mas o serviço usa “X” para overlap. Documentação divergente. Arquivos: docs/business-rules/regras-disponibilidade.md, v2/backend/apps/core/services/availability_service.py
- daily limit soma duração total do novo intervalo no dia do início, mesmo se o evento atravessar dias. Pode superestimar carga diária em eventos longos. Arquivo: v2/backend/apps/core/services/availability_service.py
- AvailabilityCheckManyView tem checagem de “não privilegiado” redundante (não alcançável com IsControleOrSuper). Arquivo: v2/backend/apps/core/views_availability.py

## Tests
- Existem testes para permissões multi-setor e grade mensal.
- Não foi possível executar pytest (ambiente sem pip/pytest).

## Notes (Execution Thoughts)
- Validei os fluxos de disponibilidade no serviço e comparei com o guia RD.
- Cruzei permissões da grade com o comportamento do frontend e com testes existentes.
- Foquei em controle de acesso de bloqueios, por ser dado sensível e mutável.

## Summary
- A lógica principal de disponibilidade está implementada e coerente.
- O principal risco é controle de acesso de bloqueios (update/delete indevido).
- A grade mensal expõe dados SUPER por padrão; o comportamento é conhecido mas arriscado.

## Next Phase
- Phase 04: Google Calendar (Publicação, Sync, OAuth, Dashboards)
