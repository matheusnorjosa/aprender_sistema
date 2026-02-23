# Phase 06 — Métricas/Dashboards/Relatórios/Mapa (v2)

Data: 2026-02-04
Escopo: métricas de equipe, dashboards executivos, mapa do Brasil, relatórios analíticos. (GCal dashboard já coberto na fase 04.)

## Status
Concluído.

## Notas de Execução (Alto Nível)
1. Cruzei a documentação do mapa e a referência de API com a implementação atual.
2. Auditei views de métricas e relatórios, incluindo permissões, parâmetros e estrutura de resposta.
3. Auditei páginas de dashboards e mapa no frontend e comparei com o backend.
4. Rodei testes focados em métricas e relatórios.

## Explorado (Log Alto Nível)
Read: `v2/docs/BACKLOG_MAPA_BRASIL.md`
Read: `v2/docs/API_REFERENCE.md`
Read: `v2/docs/OBSERVABILITY.md`
Read: `v2/backend/apps/core/views_metrics.py`
Read: `v2/backend/apps/core/views/metrics/map_metrics.py`
Read: `v2/backend/apps/core/views/metrics/dashboard_metrics.py`
Read: `v2/backend/apps/core/views/metrics/formador_metrics.py`
Read: `v2/backend/apps/core/views_reports.py`
Read: `v2/backend/apps/core/views_dashboard.py`
Read: `v2/backend/apps/core/permissions.py`
Read: `v2/backend/apps/core/models/organizacao.py`
Read: `v2/backend/apps/core/tests/test_metrics_map.py`
Read: `v2/backend/apps/core/tests/test_metrics_api.py`
Read: `v2/backend/apps/core/tests/test_reports.py`
Read: `v2/frontend/src/App.tsx`
Read: `v2/frontend/src/pages/Dashboards/DashboardsPage.tsx`
Read: `v2/frontend/src/pages/Dashboards/EquipeDashboardPage.tsx`
Read: `v2/frontend/src/pages/MapaBrasil/MapaBrasilPage.tsx`

## Implementação vs Documentação (Resumo)
1. `BACKLOG_MAPA_BRASIL.md` está desatualizado: o backend já agrega por município e `Municipio` possui lat/long.
2. `API_REFERENCE.md` está desatualizado em métricas: permissões, rotas e nomes dos endpoints não batem.
3. `/api/metrics/map/summary/` e `/api/metrics/coordinators/` não existem, mas constam no doc.
4. Endpoints `/api/metrics/team/*` e `/api/reports/*` não aparecem na documentação pública.

## Backend — Métricas e Relatórios

### Mapa do Brasil (metrics/map)
Endpoint: `GET /api/metrics/map/` em `v2/backend/apps/core/views/metrics/map_metrics.py`.
Permissão: `IsControleOrDAT`.
Parâmetros: `status`, `projeto_id`, `uf`, `limit` (default 50, max 100).
Retorno: `by_municipio` com `latitude`, `longitude`, `eventos`, `projetos`, `coordenadores`.
Observações:
- Ignora municípios sem coordenadas.
- `coordenadores` é agregado por nome do município (risco de colisão de nomes iguais em UFs diferentes).

### Coordenadores por UF (metrics/map/coordinators)
Endpoint: `GET /api/metrics/map/coordinators/` em `map_metrics.py`.
Permissão: `IsControleOrDAT`.
Parâmetro obrigatório: `uf`.
Retorno: lista detalhada de coordenadores, projetos e municípios.

### Métricas de Equipe (metrics/team)
Endpoints:
- `/api/metrics/team/productivity/`
- `/api/metrics/team/formadores/`
- `/api/metrics/team/quality/`
Permissão: `IsControle | IsGerencia`.
Cálculos: taxa de aprovação, error rate GCal, ranking de formadores, qualidade (rework/conflict/rejection).

### Dashboard Overview
Endpoint: `GET /api/dashboard/overview/` em `v2/backend/apps/core/views_dashboard.py`.
Permissão: `IsAuthenticated`.
KPIs: `eventos_futuros`, `eventos_aprovados`, `total_formadores`, `aprovacoes_pendentes`.
Observações:
- `total_formadores` é `Participation.count()` (todas as roles), não distinto.

### Relatórios Analíticos
Endpoints:
- `/api/reports/status-counts/`
- `/api/reports/top-projects/`
- `/api/reports/weekly-approved/`
- `/api/reports/by-uf/`
Permissão: `IsControleOrDAT`.
Retorno: estruturado via `APIResponse`.

## Frontend — Dashboards e Mapa

### DashboardsPage
Endpoint consumido: `/api/dashboard/overview/`.
RBAC UI: `canDashboards` (Diretoria/DAT/superuser).
Gap: backend permite qualquer autenticado, mas UI restringe. Controle/Gerência não conseguem acessar UI.

### EquipeDashboardPage
Endpoints consumidos: `/api/metrics/team/*`.
RBAC esperado: Controle/Gerência (conforme comentário da página).
Gap: UI usa `canDashboards` (Diretoria/DAT/superuser), causando 403 para DAT/Diretoria e bloqueando Controle/Gerência no frontend.

### MapaBrasilPage
Endpoints consumidos:
- `/api/metrics/map/`
- `/api/metrics/map/coordinators/`
- `/api/projetos/`
Gaps:
- UI envia `data_inicio/data_fim`, mas backend não aceita esses filtros.
- `metrics_map` possui `limit=50` por default; UI não passa limite e agrega estados sobre lista truncada.
- RBAC: UI libera para Diretoria/DAT, backend exige Controle/DAT (Diretoria recebe 403; Controle não vê a página).

## Achados (Prioritizados)
1. [Alto] RBAC desalinhado entre frontend e backend em dashboards e mapa.
Impacto: usuários permitidos no backend não têm acesso na UI e vice‑versa; Diretoria recebe 403 em métricas de equipe e mapa.
Recomendação: alinhar `canDashboards` com `IsControle|IsGerencia` para equipe e `IsControleOrDAT` para mapa, ou ajustar permissões no backend.

2. [Médio] Filtros de data no MapaBrasil não funcionam.
Evidência: frontend envia `data_inicio/data_fim`, backend não filtra por datas.
Impacto: UI indica filtro aplicado, mas dados permanecem globais.
Recomendação: implementar filtros por data no `metrics_map` ou remover do frontend.

3. [Médio] `metrics_map` usa `limit` com default 50; UI agrega estados com dataset truncado.
Impacto: estados e contagens ficam incorretos quando há mais de 50 municípios.
Recomendação: remover/elevar limite por default, ou fornecer agregação por UF no backend para a UI.

4. [Médio] Contagem de coordenadores por município usa apenas nome.
Impacto: municípios com mesmo nome em UFs diferentes podem colidir.
Recomendação: usar `municipio_id` como chave ou combinar `nome+uf`.

5. [Baixo] KPI `total_formadores` é count de participações (não distinto) e inclui todas as roles.
Impacto: “Total Participantes” no dashboard pode estar inflado.
Recomendação: decidir se o KPI é participações ou participantes distintos e ajustar label/cálculo.

6. [Baixo] Documentação de métricas/relatórios está desatualizada.
Impacto: confusão operacional e divergência de permissões/rotas.
Recomendação: atualizar `API_REFERENCE.md` e `BACKLOG_MAPA_BRASIL.md` com endpoints atuais.

## Testes Executados
Comando:
```
docker compose -f v2/infra/docker-compose.yml exec -T web pytest \
  apps/core/tests/test_metrics_api.py \
  apps/core/tests/test_metrics_map.py \
  apps/core/tests/test_reports.py \
  apps/core/tests/test_views_metrics_coverage.py -q
```
Resultado: 72 passed, 88 warnings.

## Próximos Passos Sugeridos
1. Corrigir RBAC de dashboards e mapa (UI x backend).
2. Implementar filtro por data no `metrics_map` ou remover filtros da UI.
3. Ajustar `metrics_map` para não truncar dados críticos (ou expor agregação por UF).
4. Corrigir contagem de coordenadores por município (usar id).
5. Revisar KPI `total_formadores` (distinct + role).
6. Atualizar documentação de métricas/relatórios.
