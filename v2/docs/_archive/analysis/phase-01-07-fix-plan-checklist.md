# Checklist Operacional — Plano de Correções (Fases 01–07)

**Data**: 2026-02-05

## P0 — Segurança e integridade operacional
- [x] Corrigir `assign_groups` (whitelist + self‑mod) `v2/backend/apps/core/views/admin.py`
- [x] Corrigir pipeline de backup no Docker (scripts/compose/settings/naming)
- [x] Corrigir acesso indevido em bloqueios (update/delete)

## P1 — RBAC e consistência backend/UI
- [ ] Alinhar RBAC de dashboards/métricas/mapa (UI x backend)
- [ ] Bloquear transições inválidas em aprovações (PA)
- [ ] Aplicar `check_conflicts` na criação de solicitação
- [ ] Criar grupo “Diretoria” via migration/seed + UI

## P2 — Observabilidade, logs e infraestrutura
- [ ] Expor `/metrics` no Nginx
- [ ] Corrigir `RequestIDMiddleware` (thread‑local por request)
- [ ] Alinhar scheduler de backups no systemd (DatabaseScheduler)

## P3 — Documentação e divergências
- [ ] Unificar docs de backup/DR/SLO
- [ ] Atualizar `API_REFERENCE.md` e `RBAC_COMPLETO.md`
- [ ] Ajustes menores: `LOGGING.md` (logger.ts) + alerts do Prometheus

## P4 — Bugs funcionais e UX
- [ ] Corrigir payload de `CadastrosPage`
- [ ] Validar upload em `ImportComprasView`
- [ ] Corrigir rotas e download de ETL reports
- [ ] Ajustes no Mapa do Brasil (filtros/limit/colisão)

## P5 — GCal e contratos
- [ ] Cancelamento OAuth usando credencial correta
- [ ] Corrigir drift hash online (conferenceData)
- [ ] RBAC de `/api/gcal/calendars/` e `/api/gcal/health/`

## Regressão
- [ ] Rodar suíte de testes indicada no plano
