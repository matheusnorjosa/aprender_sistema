# Phase 04 — Google Calendar (Sync, OAuth, Dashboards)

Date: 2026-02-04
Scope: v2 only
Status: Completed

## Explored
- v2/docs/GUIDE_GCAL.md
- v2/docs/API_REFERENCE.md
- v2/docs/API_EXAMPLES.md
- v2/backend/apps/core/services/gcal/__init__.py
- v2/backend/apps/core/services/gcal/utils.py
- v2/backend/apps/core/services/gcal/payload.py
- v2/backend/apps/core/services/gcal/sync.py
- v2/backend/apps/core/services/gcal/validation.py
- v2/backend/apps/core/services/gcal/client.py
- v2/backend/apps/core/services/gcal/circuit_breaker.py
- v2/backend/apps/core/services/gcal_google_client.py
- v2/backend/apps/core/services/gcal_oauth_client.py
- v2/backend/apps/core/services/gcal_fake_client.py
- v2/backend/apps/core/services/gcal_client_factory.py
- v2/backend/apps/core/services/solicitacao_publish.py
- v2/backend/apps/core/views_gcal/gcal.py
- v2/backend/apps/core/views_gcal/summary.py
- v2/backend/apps/core/views_gcal/detail.py
- v2/backend/apps/core/views_gcal/insights.py
- v2/backend/apps/core/views_gcal/batch.py
- v2/backend/apps/core/views_gcal/helpers.py
- v2/backend/apps/core/views_solicitacao.py (preview/publish/resync/cancel)
- v2/backend/apps/core/views_preagenda.py
- v2/backend/apps/core/views_oauth.py
- v2/backend/apps/core/tasks.py
- v2/backend/apps/core/management/commands/preagenda_to_gcal.py
- v2/backend/apps/core/models/solicitacao.py
- v2/backend/apps/core/models/integracao.py
- v2/backend/apps/core/serializers/solicitacao.py
- v2/backend/apps/core/permissions.py
- v2/backend/apps/core/urls.py
- v2/backend/apps/core/views_health.py
- v2/backend/apps/core/tests/test_gcal_*.py
- v2/frontend/src/pages/PreAgenda/PreAgendaPage.tsx
- v2/frontend/src/pages/Dashboards/GCalDashboardPage.tsx
- v2/frontend/src/api/solicitacoes.ts
- v2/frontend/src/api/gcal.ts
- v2/frontend/src/hooks/useGoogleIntegration.ts
- v2/frontend/src/hooks/useGoogleGuard.tsx
- v2/frontend/src/components/google/GoogleIntegrationCard.tsx
- v2/frontend/src/components/MeetLink.tsx
- v2/frontend/src/types/solicitacao.ts
- v2/frontend/src/types/gcal.ts
- v2/frontend/src/App.tsx

## What Was Implemented
- Serviço modular de sync GCal com payload padronizado, eventId determinístico, retries e idempotência.
- Clientes GCal para Service Account e OAuth, com lista de calendários e health check.
- Preview/publish/resync/cancel via endpoints de solicitação, com AuditLog e Celery tasks.
- Operações em lote (publish, reapply, resync) no dashboard GCal.
- Dashboards de métricas, eventos, export CSV/JSON, insights e alertas.
- Fluxo OAuth por usuário com criptografia de tokens, seleção de calendário e UI dedicada.
- PreAgenda e MeetLink integrados no frontend (preview, publish, resync, cancel).

## Findings (Ordered by Severity)
High
- Nenhum achado crítico nesta fase.

Medium
- Cancelamento em modo OAuth usa service account (não o OAuth do operador). Em ambientes OAuth, isso tende a falhar ao excluir eventos publicados na conta do usuário e pode deixar `gcal_status` em PENDING indefinidamente. Arquivos: v2/backend/apps/core/services/solicitacao_publish.py, v2/backend/apps/core/tasks.py, v2/backend/apps/core/services/gcal/sync.py
- Endpoints `/api/gcal/calendars/` e `/api/gcal/health/` permitem qualquer usuário autenticado, enquanto a documentação indica IsControleOrSuper. Isso pode expor calendários/estado de saúde da integração. Arquivos: v2/backend/apps/core/views_gcal/gcal.py, v2/docs/API_REFERENCE.md
- Hash de drift em eventos online tende a divergir: `gcal_payload_hash` é calculado com `conferenceData` (requestId aleatório), mas o drift usa `compute_payload_hash` sem conferenceData. Isso gera falsos positivos no endpoint de drift para eventos online. Arquivos: v2/backend/apps/core/services/gcal/payload.py, v2/backend/apps/core/services/gcal/sync.py, v2/backend/apps/core/views_gcal/detail.py

Low
- Documentação de endpoints GCal está desatualizada (ex.: `/api/gcal/preview`, `/api/gcal/publish`, `/api/gcal/dashboard/*` antigos, e exemplos `api/v1`). Arquivos: v2/docs/API_REFERENCE.md, v2/docs/API_EXAMPLES.md
- Frontend possui endpoints GCal não implementados (`/gcal/approved/`, `/gcal/unpublish-batch/`, `/gcal/sync-blocked/`). Arquivo: v2/frontend/src/api/gcal.ts
- Tipagens e payloads divergentes no frontend: `GCalStatus` inclui `NOT_SYNCED`/`CANCELLED` (backend usa `NONE`), e o dashboard espera `gcal_payload_hash` embora o serializer o remova. Arquivos: v2/frontend/src/types/solicitacao.ts, v2/frontend/src/pages/Dashboards/GCalDashboardPage.tsx, v2/backend/apps/core/serializers/solicitacao.py
- Hash de payload documentado como SHA256, mas a implementação usa SHA1. Arquivos: v2/backend/apps/core/types.py, v2/backend/apps/core/services/gcal/utils.py
- Circuit breaker existe mas não está integrado nas operações principais de sync (usa-se apenas retry). Arquivos: v2/backend/apps/core/services/gcal/utils.py, v2/backend/apps/core/services/gcal/sync.py, v2/backend/apps/core/services/gcal/circuit_breaker.py
- GCal Dashboard é visível para Diretoria/DAT no frontend, mas APIs exigem Controle/Super; isso gera UX de “acesso negado” para esses perfis. Arquivo: v2/frontend/src/App.tsx

## Tests
- Executado em Docker:
  - `docker compose -f v2/infra/docker-compose.yml exec -T web pytest apps/core/tests -k gcal -q`
  - Resultado: 259 passed, 1 skipped, 959 deselected, 154 warnings (35.92s)

## Notes (Execution Thoughts)
- Cruzei o GUIDE_GCAL com a implementação de serviços, views e tasks.
- Validei fluxos OAuth (start/status/calendar select) e sua integração no frontend.
- Rodei a suíte de testes GCal em Docker para confirmar comportamento real.

## Summary
- A integração GCal está ampla e bem testada (publicação, batch, dashboards, OAuth).
- Os principais riscos estão em cancelamento OAuth e drift de eventos online.
- Há dívida de documentação e pequenas divergências de frontend/contrato.

## Next Phase
- Phase 05: Configurações/DAT/Importações e Admin (cadastros, config API, ETL/imports)
