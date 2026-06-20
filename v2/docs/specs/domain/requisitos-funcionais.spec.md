---
title: Requisitos Funcionais (RF01..RF08)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/management/commands/import_export_contract.py
  - v2/backend/apps/core/services/export_contract_importer.py
  - v2/backend/apps/core/services/solicitacao_create.py
  - v2/backend/apps/core/services/availability_service.py
  - v2/backend/apps/core/services/solicitacao_approval.py
  - v2/backend/apps/core/services/solicitacao_publish.py
  - v2/backend/apps/core/services/gcal_client_factory.py
  - v2/backend/apps/core/services/gcal_sync_service.py
  - v2/backend/apps/core/services/monthly_grid_service.py
  - v2/backend/apps/core/models/auditoria.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/views_availability.py
  - v2/backend/apps/core/views_availability_monthly.py
  - v2/backend/apps/core/urls.py
owner: domain
supersedes:
  - docs/business-rules/requisitos-funcionais.md
related:
  - v2/docs/specs/INDEX_SDD.md
  - v2/docs/specs/domain/README.md
  - v2/docs/GUIDE_AVAILABILITY.md
  - v2/docs/GUIDE_GCAL.md
  - v2/docs/RBAC_NAMING.md
  - docs/business-rules/regras-disponibilidade.md
  - docs/business-rules/politica-aprovacao.md
---

# Requisitos Funcionais (RF01..RF08)

## Propósito

Os Requisitos Funcionais RF01..RF08 descrevem **o que** o Aprender Sistema v2 entrega ao negócio: importar dados, abrir e validar solicitações de evento, conferir conflitos de disponibilidade, aprovar manualmente, publicar no Google Calendar (com Meet quando online), auditar tudo e exibir o mapa mensal de disponibilidade. São o contrato de produto que substitui as planilhas (objetivo: eliminar as 82.389 fórmulas Excel).

Esta spec é um **índice** (SSOT do conjunto RF) e não duplica os guias/specs detalhados: cada RF aponta para o serviço/arquivo que o implementa hoje e para a spec/guia canônico do tópico. As regras numéricas (RD-01..RD-08 de disponibilidade, PA-01..PA-07 de aprovação) vivem nas specs de domínio dedicadas — aqui ficam apenas os contratos de alto nível.

## Fonte de verdade no código

| RF | O que faz | Implementação atual |
|---|---|---|
| **RF01** Importação | Carga de dados a partir do export-contract (Sheets → Sistema), dry-run-first | [`management/commands/import_export_contract.py`](../../../backend/apps/core/management/commands/import_export_contract.py) + [`services/export_contract_importer.py`](../../../backend/apps/core/services/export_contract_importer.py); importers DRF por entidade em `views_imports.py` e `views_import_*.py` |
| **RF02** Solicitação | Criação de pré-agenda, decide status inicial por `projeto.fluxo` | [`services/solicitacao_create.py`](../../../backend/apps/core/services/solicitacao_create.py) (`decide_initial_status`); `SolicitacaoViewSet` em [`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) |
| **RF03** Conflitos | Checagem de disponibilidade (RD-01..RD-08) | [`services/availability_service.py`](../../../backend/apps/core/services/availability_service.py) (`check_conflicts`); views em [`views_availability.py`](../../../backend/apps/core/views_availability.py) |
| **RF04** Aprovação | Aprovar/reprovar (PA-01..PA-07), individual e em lote | [`services/solicitacao_approval.py`](../../../backend/apps/core/services/solicitacao_approval.py); ações `approve`/`reject` no `SolicitacaoViewSet` |
| **RF05** Google Calendar | Preview e publish do evento no GCal (fake vs google) | [`services/gcal_client_factory.py`](../../../backend/apps/core/services/gcal_client_factory.py), [`services/gcal_sync_service.py`](../../../backend/apps/core/services/gcal_sync_service.py), [`services/solicitacao_publish.py`](../../../backend/apps/core/services/solicitacao_publish.py) (`preview_gcal`, `publish_to_gcal`) |
| **RF06** Google Meet | Link Meet gerado só quando `is_online=True`, no apply real | Campo `meet_link` em [`models/solicitacao.py`](../../../backend/apps/core/models/solicitacao.py); `conferenceData` montado no publish (`solicitacao_publish.py` / `gcal_sync_service.py`) |
| **RF07** Auditoria | Trilha completa de ações sensíveis | [`models/auditoria.py`](../../../backend/apps/core/models/auditoria.py) (`AuditLog` + `AuditLog.Action`) |
| **RF08** Mapa mensal | Grade mensal de disponibilidade por papel/setor | [`services/monthly_grid_service.py`](../../../backend/apps/core/services/monthly_grid_service.py) (`build_monthly_grid`); view em [`views_availability_monthly.py`](../../../backend/apps/core/views_availability_monthly.py) |

> Correção histórica (RF01): o **ETL legado foi removido** (app `dat_ingest` deletado). O caminho de importação real é o **`import_export_contract`** + os endpoints DRF de import; comandos `etl_upsert_*` antigos não são mais a fonte de verdade.

## Contratos e invariantes

- **RF01 — dry-run-first / never-overwrite**: sem `--apply` o comando apenas classifica; `--apply` **exige** `--allow-entity` (allowlist) e roda em modo create-only; campos protegidos (`Solicitacao.status`, `Formacao.data_formacao`, `Acompanhamento`) nunca são sobrescritos. Idempotência por hash externo (`external_hash`). **Nenhum import real foi executado** — não importar dados de verdade até um `--apply` dry-run passar verde + autorização.
- **RF02 / PA-04**: solicitação de projeto `fluxo == SUPER` nasce `pendente`; projeto `NAO_SUPER` é auto-aprovado na criação. Datas são timezone-aware em `America/Fortaleza` (armazenadas em UTC).
- **RF03 / RD-01..RD-08**: precedência de checagens é Bloqueios (T/P) → Conflitos → Deslocamento (D) → Capacidade (M); `fim == inicio` **não** é conflito (adjacência permitida). Detalhe em [`regras-disponibilidade.spec.md`](./regras-disponibilidade.spec.md) / [GUIDE_AVAILABILITY](../../GUIDE_AVAILABILITY.md).
- **RF04 / PA-01..PA-07 (CP-02)**: SUPER **nunca** auto-aprova; aprovar/reprovar exige autorização (`CanAccessSolicitationApprovals`); lote limitado a 100 ids, com `select_for_update(skip_locked=True)` para evitar dupla aprovação. Idioma RBAC: `permission_classes=[HasPerm("codename")]` (grupos diretos banidos por `scripts/rbac_lint.py`).
- **RF05 / PA-03**: integração GCal só ocorre **após** aprovação manual; `preview` nunca persiste; idempotência por `external_event_id = asv2-{id}` + `gcal_payload_hash` (SHA256); retry/backoff para 429/5xx. Cliente selecionado por `GCAL_CLIENT=fake|google`.
- **RF06**: `meet_link` é read-only no serializer; só é gerado/persistido em apply real com `is_online=True` (nunca em preview, dry-run ou 409). `is_online=False` (default) → sem `conferenceData`.
- **RF07 / PA-05**: toda ação sensível grava `AuditLog` (usuario, action, model_name, details JSON com `solicitacao_id`, `prev_status`, `new_status`, `ip_address`, `user_agent`). Ações: `APPROVE`, `REJECT`, `PREVIEW_GCAL`, `PUBLISH_GCAL_REQUESTED`, `PUBLISH_GCAL`, `PUBLISH_GCAL_ERROR`, `RESYNC_GCAL_REQUESTED`, `CANCEL_GCAL_REQUESTED`, `CANCEL_GCAL`.
- **RF08**: grade mensal usa precedência de código `X > D1 > 2 > E > T/P > D`; cacheada em Redis (~5 min); ranking denso por carga horária do mês.

## API / Interface

Rotas registradas em [`urls.py`](../../../backend/apps/core/urls.py) (prefixo `/api/`). Contrato detalhado em [`v2/docs/API_REFERENCE.md`](../../API_REFERENCE.md).

- **RF02**: `SolicitacaoViewSet` (router `solicitacoes`); `POST /api/solicitacoes/validate/`.
- **RF03**: `GET /api/availability/check/` (individual) · `POST /api/availability/check-many/` (lote).
- **RF04**: `PATCH /api/solicitacoes/{id}/approve/` · `PATCH /api/solicitacoes/{id}/reject/` (+ ações de lote no viewset).
- **RF05/RF06**: `POST /api/solicitacoes/{id}/preview-gcal/` · `POST /api/solicitacoes/{id}/publish/` (202 Accepted, Celery) · `POST /api/solicitacoes/{id}/resync-gcal/` · `POST /api/gcal/publish-batch/`. Permissão `CanUseGcal` (Controle + Superintendência).
- **RF08**: `GET /api/availability/monthly/?year=&month=&role=§or=&q=`.
- **RF01**: comando `python manage.py import_export_contract --path ... [--apply --allow-entity <entidade>] [--json]`; importers DRF sob `/api/.../import/`.

## Fluxos principais

1. **Importação (RF01)**: operador roda `import_export_contract` em dry-run → revisa classificação → (com autorização) `--apply --allow-entity X` → writes create-only idempotentes; campos protegidos preservados.
2. **Solicitação → publicação (RF02→RF05/RF06)**: coordenador cria solicitação → sistema checa conflitos (RF03) → `NAO_SUPER` auto-aprova; `SUPER` fica `pendente` → Superintendência/DAT aprova (RF04, grava AuditLog) → Controle/Super faz `preview-gcal` (não persiste) → `publish` enfileira Celery → evento criado no GCal; se `is_online=True`, `meet_link` extraído de `hangoutLink` e persistido (RF06).
3. **Mapa mensal (RF08)**: front pede `availability/monthly/` por ano/mês/papel/setor → `build_monthly_grid` agrega eventos, bloqueios e deslocamentos em códigos por dia/pessoa → resposta cacheada; clique abre detalhe do dia.

- **Erros relevantes**: aprovar item não-`pendente` → `ValidationAPIError` (`already_approved`/`already_rejected`/`invalid_status`); lote > 100 → `batch_limit_exceeded`; `--apply` sem allowlist → bloqueado, nada escrito; publish com `apply_blocked=True` → respeitado (não escreve no GCal).

## Decisões relacionadas (ADRs)

- [ADR-001 Docker-only](../../../../docs/architecture/project-decisions/ADR-001-docker-only-deployment.md) (CP-01)
- [ADR-002 Aprovação manual](../../../../docs/architecture/project-decisions/ADR-002-approval-policy-manual.md) (RF04/PA)
- [ADR-003 Regras de disponibilidade + timezone](../../../../docs/architecture/project-decisions/ADR-003-availability-rules-timezone.md) (RF03/RD)
- [ADR-005 SSOT PostgreSQL](../../../../docs/architecture/project-decisions/ADR-005-ssot-postgresql.md) (RF01)
- [ADR-008 GCal requestId determinístico](../../../../docs/architecture/project-decisions/ADR-008-gcal-deterministic-requestid.md) (RF05/RF06)
- [ADR-011 Polling sobre WebSocket](../../../../docs/architecture/project-decisions/ADR-011-polling-over-websocket.md)
- [ADR-017 Documentação spec-driven](../../../../docs/architecture/project-decisions/ADR-017-spec-driven-documentation.md)

## Testes que cobrem

- **RF03**: [`tests/test_availability_service.py`](../../../backend/apps/core/tests/test_availability_service.py); [`tests/test_monthly_with_deslocamento.py`](../../../backend/apps/core/tests/test_monthly_with_deslocamento.py).
- **RF04 / PA**: [`tests/test_approval_policy_PA.py`](../../../backend/apps/core/tests/test_approval_policy_PA.py) (5 testes obrigatórios); [`tests/test_solicitacao_approval_concurrency.py`](../../../backend/apps/core/tests/test_solicitacao_approval_concurrency.py).
- **RF02**: [`tests/test_solicitacao_create_service.py`](../../../backend/apps/core/tests/test_solicitacao_create_service.py); [`tests/test_solicitacao_fluxo.py`](../../../backend/apps/core/tests/test_solicitacao_fluxo.py); [`tests/test_solicitacao_online_mode.py`](../../../backend/apps/core/tests/test_solicitacao_online_mode.py).
- **RF05/RF06**: `tests/test_gcal_*.py` (ex.: [`test_gcal_endpoints.py`](../../../backend/apps/core/tests/test_gcal_endpoints.py), [`test_gcal_publish_apply_blocked.py`](../../../backend/apps/core/tests/test_gcal_publish_apply_blocked.py), [`test_gcal_meet_link_persist.py`](../../../backend/apps/core/tests/test_gcal_meet_link_persist.py), [`test_gcal_retry_backoff.py`](../../../backend/apps/core/tests/test_gcal_retry_backoff.py)).
- **RF07**: coberto indiretamente por `test_approval_policy_PA.py::test_approval_flow_records_audit_log` e pelos testes de retry/audit GCal ([`test_gcal_retry_audit.py`](../../../backend/apps/core/tests/test_gcal_retry_audit.py)).
- **RF01**: [`tests/test_export_contract_importer.py`](../../../backend/apps/core/tests/test_export_contract_importer.py); [`tests/test_export_contract_projeto_resolver.py`](../../../backend/apps/core/tests/test_export_contract_projeto_resolver.py).

## Pontos de atenção / dívidas conhecidas

- **RF01 não foi executado em produção**: o pipeline export-contract está em dry-run; `--apply` segue bloqueado sem allowlist. Re-import cego sobrescreveria data-fixes manuais (D2/C3-A/C4.4) — exige `--apply` dry-run verde + autorização.
- **RF05/RF06 em prod**: GCal depende de `GCAL_CLIENT`, `GCAL_CALENDAR_ID`/`GCAL_AUTH_MODE` e `GCAL_ENCRYPTION_KEY` no Portainer; eventos vazios geralmente são config de ambiente, não código. Celery já teve broker quebrado em prod (#1089) — publish é assíncrono e depende do worker.
- **TOCTOU de aprovação**: aprovação individual e em lote usam `select_for_update` para fechar a janela de corrida, mas a checagem de conflito (RF03) e a aprovação (RF04) são passos separados — alteração de disponibilidade entre eles não revalida automaticamente.
- **PA-01 no importer de eventos**: corrigido para SUPER nunca auto-aprovar mesmo em evento passado (#1370); manter coberto ao evoluir RF01.
- **Specs irmãs ainda planejadas**: `regras-disponibilidade.spec.md` e `politica-aprovacao.spec.md` referenciadas aqui podem estar como esqueleto; até serem escritas, a fonte canônica é `docs/business-rules/` + ADRs.
