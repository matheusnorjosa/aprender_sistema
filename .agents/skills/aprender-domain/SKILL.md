---
name: aprender-domain
description: Business-rules reference for Aprender Sistema v2 — RF (functional requirements), RD (availability rules), PA (approval policy), CP (immutable clauses), and core domain models. Use when implementing a feature, validating a requirement, or writing a compliance test against any RF/RD/PA/CP rule.
---

# Aprender Sistema v2 — Business Domain

Reference for the stable domain contracts (RF / RD / PA / CP) and core models.

> **SSOT dos contratos vivos**: `v2/docs/specs/domain/*.spec.md` (modelo SDD, ADR-017).
> Cada spec tem `status` + `last_verified` + `sources_of_truth`. Não duplicar métricas
> datadas aqui; este skill resume a regra e aponta para a spec viva.

## CP (Cláusulas Pétreas) — IMMUTABLE

SSOT: `v2/docs/specs/domain/clausulas-petreas.spec.md` (CP-01..CP-08).

- **CP-01**: v2 roda APENAS em Docker (`cd v2 && make up`). Validação `REQUIRE_DOCKER` em `config/settings.py`.
- **CP-02**: PA-01..PA-07 — aprovação manual obrigatória (ver PA abaixo).
- **CP-03**: RD-01..RD-08 — disponibilidade com timezone Fortaleza (ver RD abaixo).
- **CP-04**: Workflow Entender → Planejar → Implementar → Testar. Nunca pular etapas.
- **CP-05** a **CP-08**: v1 congelado; conventional commits; nunca push direto na main (hook); `INCLUDE_DEV_TOOLS=false` em produção.

## RD (Regras de Disponibilidade) — Availability Rules

SSOT: `v2/docs/specs/domain/regras-disponibilidade.spec.md`.
Implementação: `apps/core/services/availability_service.py:check_conflicts()`.
Testes: `apps/core/tests/test_availability_service.py`.

- **RD-01 — Non-overlapping**: formador não pode ter dois eventos que se sobreponham (≥1 min). `end == start` é adjacente, NÃO é conflito.
- **RD-02 — Bloqueio total (T)**: bloqueio marcado `T` impede QUALQUER evento no intervalo. Código `X`.
- **RD-03 — Bloqueio parcial (P)**: bloqueio `P` impede eventos só dentro do subintervalo; fora é permitido.
- **RD-04 — Deslocamento (D)**: entre municípios diferentes exige tempo mínimo de viagem (configurável). Mesmo município pode ser zero.
- **RD-05 — Capacidade diária (M)**: limite de N horas de evento por dia (configurável).
- **RD-06 — Timezone**: comparações timezone-aware em `America/Fortaleza`; armazenamento em UTC.
- **RD-07 — Ordem dos checks**: (1) blocos T/P → (2) conflitos de eventos aprovados → (3) deslocamento D → (4) limite diário M.
- **RD-08 — Mensagens de conflito**: cada conflito lista formador(es), data+intervalo (HH:MM dd/mm) e tipo (E, M, D, P, T, X).

```json
{ "code": "T", "title": "Bloqueio total", "detail": "Maria Silva - 15/01/2025 09:00-12:00", "ref_id": 123 }
```

## PA (Política de Aprovação) — Approval Policy

SSOT: `v2/docs/specs/domain/politica-aprovacao.spec.md`.
Testes: `apps/core/tests/test_approval_policy_PA.py`.

- **PA-01 — No auto-approval (SUPER)**: `Solicitacao` com `projeto.fluxo == 'SUPER'` NUNCA vira "aprovado" automaticamente, mesmo sem conflito. Em `Solicitacao.save()`.
- **PA-02 — Perfil exigido**: só superuser OU (Gerente + Superintendência) aprova/rejeita. Idioma canônico `permission_classes = [HasPerm("codename")]` (`from apps.core.rbac import HasPerm`; políticas em `apps/core/rbac/`).
- **PA-03 — Triggers pós-aprovação**: integrações externas (GCal, RF05/RF06) só executam APÓS a aprovação manual; a task de publicação não é chamada em `save()`.
- **PA-04 — Estado inicial**: SUPER começa em `status = 'pendente'`. NAO_SUPER é auto-aprovado na criação (exceção a PA-01).
- **PA-05 — Auditoria**: registra usuário, data/hora e justificativa em `Aprovacao` + `AuditLog`. Actions: `APPROVE`, `REJECT`, `PREVIEW_GCAL`, `PUBLISH_GCAL_REQUESTED`, `PUBLISH_GCAL`.
- **PA-06 — UI/UX**: telas de requester/coordenador mostram status e escondem botões sem permissão. `ApprovalsPage.tsx` renderiza Approve/Reject só se `status === 'pendente' && canApprove`.
- **PA-07 — Testes obrigatórios**: `test_never_auto_approves_on_clean_or_save`, `test_only_superintendencia_can_approve_or_reject`, `test_calendar_integration_not_called_before_approval`, `test_approval_flow_records_audit_log`, `test_non_privileged_user_gets_403_on_approval_endpoint`. Rodar `pytest apps/core/tests/test_approval_policy_PA.py -v`.

## RF (Requisitos Funcionais) — Functional Requirements

SSOT: `v2/docs/specs/domain/requisitos-funcionais.spec.md`.

- **RF01 — Import de dados**: ETL legado (`apps.dat_ingest`) REMOVIDO. Import atual = command `import_export_contract` (dry-run por padrão; `--apply` exige allowlist) + endpoints DRF (`POST /api/controle/import-compras/`, `/api/controle/import-acoes/`, `/api/dat/import-cadastros/`). Idempotência via `external_hash` (SHA1/SHA256). Spec: `v2/docs/specs/backend/imports.spec.md`.
- **RF02 — Solicitação de evento**: wizard Ant Design (3 passos: projeto/município/tipo → data/horários → participantes/observação/online). Coordenador cria → sistema checa conflitos (RF03) → NAO_SUPER auto-aprova, SUPER fica pendente (PA-01..PA-07).
- **RF03 — Verificação de conflitos**: `availability_service.py:check_conflicts()` retorna `AvailabilityResult` com lista de `ConflictDetail` (regras RD-01..RD-08). Endpoints `GET /api/availability/check/` e `POST /api/availability/check-many/`. Frontend `NewSolicitacaoPage.tsx` com feedback visual por tipo (X/T bloqueio, P/D atenção, M aviso).
- **RF04 — Fluxo de aprovação**: política PA acima. `POST /api/solicitacoes/{id}/approve/` (AuditLog APPROVE) e `/reject/` (REJECT). Frontend `ApprovalsPage.tsx`.
- **RF05 — Google Calendar**: factory `gcal_client_factory.py` (fake vs google). Idempotência `eventId=asv2-{id}` + `gcal_payload_hash` (SHA256). Retry 3x (1s/2s/4s) para 429/5xx. Preview (`/preview-gcal/`) gera payload sem persistir; Publish (`/publish/`) enfileira Celery e retorna 202. Vars: `GCAL_CLIENT`, `GCAL_CALENDAR_ID`, `GOOGLE_SERVICE_ACCOUNT_FILE`, `GCAL_SEND_UPDATES`.
- **RF06 — Google Meet**: campo `meet_link` (read-only no serializer). `is_online=false` (default) → presencial, sem `conferenceData`; `is_online=true` → online com `conferenceData`, gera link. Persiste o `hangoutLink` SÓ no apply real (não em preview/dry_run/409). Componente `MeetLink.tsx`.
- **RF07 — Auditoria**: model `AuditLog` (usuario, action, model_name, details JSON, created_at). Actions: APPROVE, REJECT, PREVIEW_GCAL, PUBLISH_GCAL_REQUESTED, PUBLISH_GCAL, RESYNC_GCAL_REQUESTED, CANCEL_GCAL_REQUESTED, CANCEL_GCAL.
- **RF08 — Mapa mensal**: página `/disponibilidade`, 2 grids (Formadores / Coordenadores), filtros ano/mês/setor/q, linhas virtualizadas, export CSV, cache Redis 5 min. Códigos por célula: E (1 evento), 2 (2+), P/T (bloqueios), X (evento+bloqueio), D/D1 (deslocamento). API `GET /api/availability/monthly/?year=&month=&role=&sector=&q=`.

## Módulos de domínio (REFERENCE)

Fatos consultados sob demanda (modelos, campos, workflows) — abrir só quando precisar:

- **DAT** (ações, registros, cadastros, coordenadores): `reference/dat-module.md`
- **PlanoFormacoes** (planos anuais, formações, acompanhamentos, provas): `reference/plano-formacoes.md`
- **Compras** (Compra histórico, DATCompra operacional, Produto): `reference/compras.md`
- **Key Models** (Usuario, Municipio, Projeto, Solicitacao, AvailabilityBlock, AuditLog): `reference/key-models.md`

## Related Skills

- **`django-patterns`** — padrões de implementação (models, views, serializers).
- **`create_plan`** / **`implement_plan`** — arquitetura e planejamento.
- Imports/data-loading: `v2/docs/specs/backend/imports.spec.md` (skill `etl-guidelines` DEPRECADA — ETL legado removido).

## Quick Reference Commands

```bash
# RD-01..RD-08 (conflitos)
pytest apps/core/tests/test_availability_service.py -v

# PA-01..PA-07 (aprovação)
pytest apps/core/tests/test_approval_policy_PA.py -v

# Google Calendar
pytest apps/core/tests/test_gcal*.py -v

# Import export-contract (dry-run por padrão; --apply exige allowlist)
docker compose exec web python manage.py import_export_contract

# Imports via API DRF (dry-run)
make import-compras-dry FILE=...
make import-acoes-dry FILE=...
make import-cadastros-dry FILE=...
```
