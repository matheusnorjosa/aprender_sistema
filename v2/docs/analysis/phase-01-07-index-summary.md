# Índice + Consolidação — Fases 01 a 07 (v2)

**Data**: 2026-02-05

## Índice

### Consolidado
- `v2/docs/analysis/phase-01-07-summary.md`

### Fases
1. `v2/docs/analysis/phase-01-auth-rbac-sessions.md`
2. `v2/docs/analysis/phase-02-solicitacoes-aprovacoes.md`
3. `v2/docs/analysis/phase-03-disponibilidade-bloqueios-grade.md`
4. `v2/docs/analysis/phase-04-gcal.md`
5. `v2/docs/analysis/phase-05-config-dat-import-etl-admin.md`
6. `v2/docs/analysis/phase-06-metrics-dashboards-reports-map.md`
7. `v2/docs/analysis/phase-07-infra-observability-backup-dr.md`

### Atalhos por tema
- Auth/RBAC/Sessions: `v2/docs/analysis/phase-01-auth-rbac-sessions.md`
- Solicitações/Aprovações: `v2/docs/analysis/phase-02-solicitacoes-aprovacoes.md`
- Disponibilidade/Grade/Bloqueios: `v2/docs/analysis/phase-03-disponibilidade-bloqueios-grade.md`
- Google Calendar/OAuth/Dashboards: `v2/docs/analysis/phase-04-gcal.md`
- Config/DAT/Import/ETL/Admin: `v2/docs/analysis/phase-05-config-dat-import-etl-admin.md`
- Métricas/Relatórios/Mapa: `v2/docs/analysis/phase-06-metrics-dashboards-reports-map.md`
- Infra/Observability/Backup/DR/Deploy/Scaling: `v2/docs/analysis/phase-07-infra-observability-backup-dr.md`

## Consolidação — Fases 01 a 07

### Documentos criados
- `v2/docs/analysis/phase-01-auth-rbac-sessions.md`
- `v2/docs/analysis/phase-02-solicitacoes-aprovacoes.md`
- `v2/docs/analysis/phase-03-disponibilidade-bloqueios-grade.md`
- `v2/docs/analysis/phase-04-gcal.md`
- `v2/docs/analysis/phase-05-config-dat-import-etl-admin.md`
- `v2/docs/analysis/phase-06-metrics-dashboards-reports-map.md`
- `v2/docs/analysis/phase-07-infra-observability-backup-dr.md`

### Fase 01 — Auth/RBAC/Sessions
**Documento**: `v2/docs/analysis/phase-01-auth-rbac-sessions.md`

**Escopo**: autenticação, sessões e RBAC (Setor/Função), alinhamento backend vs frontend.

**O que foi feito**
- Validado login/logout/ping, CSRF HttpOnly e sessões em Redis.
- Auditado RBAC Setor/Função e flags de permissão no `/api/me/`.
- Cruzado gates do frontend com permissões do backend (dashboards, approvals, disponibilidade).

**Achados principais (resumo)**
- Dashboard overview exposto com `IsAuthenticated` (métricas agregadas amplas).
- RBAC desalinhado: UI libera Diretoria/DAT enquanto backend exige Controle/Gerência em métricas.
- Grupo “Diretoria” não é criado via migration/seed.

**Testes**
- Tentativa de `pytest` falhou por ausência de módulo no ambiente.

### Fase 02 — Solicitações/Aprovações (PA)
**Documento**: `v2/docs/analysis/phase-02-solicitacoes-aprovacoes.md`

**Escopo**: fluxo SUPER/NAO_SUPER, aprovação, publicação e edição de solicitações.

**O que foi feito**
- Validado fluxo de criação, aprovação/reprovação individual e batch.
- Cruzado regras de edição/publicação com backend e UI.
- Verificada documentação e permissões de aprovação.

**Achados principais (resumo)**
- Backend não aplica `check_conflicts` na criação, permitindo eventos conflitantes.
- Aprovação/reprovação aceita transições fora de “pendente”.
- Divergências entre documentação, UI e permissões do backend.

**Testes**
- Não executados (ambiente sem pip/pytest na época).

### Fase 03 — Disponibilidade/Bloqueios/Grade
**Documento**: `v2/docs/analysis/phase-03-disponibilidade-bloqueios-grade.md`

**Escopo**: RD-01..RD-05, bloqueios, grade mensal.

**O que foi feito**
- Revisado `availability_service` e grade mensal.
- Auditadas permissões e importação de bloqueios.
- Cruzado regras RD com documentação.

**Achados principais (resumo)**
- Usuários podem editar/excluir bloqueios de terceiros da mesma gerência.
- Grade mensal pode retornar dados SUPER sem `gerencia_id` (exposição ampla).
- Divergências menores entre docs e implementação (ex.: código de conflito).

**Testes**
- Não executados (ambiente sem pip/pytest na época).

### Fase 04 — Google Calendar (Sync/OAuth/Dashboards)
**Documento**: `v2/docs/analysis/phase-04-gcal.md`

**Escopo**: integração GCal, OAuth, preagenda, dashboards e batch.

**O que foi feito**
- Validado pipeline de sync/publish/preview/resync/cancel.
- Revisada integração OAuth e flows de UI.
- Cruzado docs com serviços e views.

**Achados principais (resumo)**
- Cancelamento em modo OAuth usa service account (risco de falha e status preso).
- Endpoints `/api/gcal/calendars/` e `/api/gcal/health/` abertos a qualquer autenticado.
- Drift de eventos online pode gerar falso positivo por hash inconsistente.

**Testes**
- Executado: `pytest -k gcal -q` via Docker.
- Resultado: `259 passed, 1 skipped, 959 deselected, 154 warnings`.

### Fase 05 — Config/DAT/Import/ETL/Admin
**Documento**: `v2/docs/analysis/phase-05-config-dat-import-etl-admin.md`

**Escopo**: config do sistema, Admin DAT, DAT Module, importações, ETL.

**O que foi feito**
- Mapeadas docs e código de config, admin e módulos DAT.
- Cruzado frontend e backend (payloads, RBAC, rotas).
- Auditada observabilidade de ETL e importações.

**Achados principais (resumo)**
- `assign_groups` ignora whitelist e auto-modificação de grupos (risco RBAC).
- ImportCompras sem validação de upload (tamanho/MIME).
- `CadastrosPage` envia campos não suportados pelo serializer.
- RBAC e rotas de ETL Reports desalinhados (UI vs backend).

**Testes**
- Executado suite focada em admin/config/DAT/import/ETL.
- Resultado: `232 passed, 2 skipped, 148 warnings`.

### Fase 06 — Métricas/Dashboards/Relatórios/Mapa
**Documento**: `v2/docs/analysis/phase-06-metrics-dashboards-reports-map.md`

**Escopo**: métricas de equipe, dashboards, mapa e relatórios.

**O que foi feito**
- Auditadas views de métricas e relatórios.
- Cruzadas permissões backend vs gates de UI.
- Verificados filtros e estrutura de resposta.

**Achados principais (resumo)**
- RBAC desalinhado: UI libera perfis diferentes do backend (403 ou bloqueios indevidos).
- Filtros de data no mapa não funcionam (backend ignora).
- `metrics_map` truncado por `limit=50` afeta agregações por UF.

**Testes**
- Executado suite de métricas/relatórios.
- Resultado: `72 passed, 88 warnings`.

### Fase 07 — Infra/Observability/Logging/Backup/DR/Deploy/Scaling
**Documento**: `v2/docs/analysis/phase-07-infra-observability-backup-dr.md`

**Escopo**: observabilidade, logging, Sentry, SLOs, scaling, backup/DR, deploy/runbook.

**O que foi feito**
- Validado stack Prom/Grafana, settings de métricas e logging estruturado.
- Cruzados scripts e rotinas de backup/DR com documentação.
- Verificados runbooks e configs de infra (Nginx, systemd, compose).

**Achados principais (resumo)**
- Backups via Celery quebrados no Docker (script ausente no worker + host/paths errados).
- Health check de backup sempre degrada por naming incompatível.
- `/metrics` não é exposto no Nginx de produção.

**Testes**
- Executado suite de readiness/logging/sentry/SLOs.
- Resultado: `29 passed, 35 warnings`.
