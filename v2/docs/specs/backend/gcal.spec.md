---
title: Integração Google Calendar + Meet
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/services/gcal_client_factory.py
  - v2/backend/apps/core/services/gcal_google_client.py
  - v2/backend/apps/core/services/gcal_oauth_client.py
  - v2/backend/apps/core/services/gcal_fake_client.py
  - v2/backend/apps/core/services/gcal_sync_service.py
  - v2/backend/apps/core/services/gcal/sync.py
  - v2/backend/apps/core/services/gcal/payload.py
  - v2/backend/apps/core/services/gcal/client.py
  - v2/backend/apps/core/services/oauth/oauth_flow.py
  - v2/backend/apps/core/services/oauth/token_manager.py
  - v2/backend/apps/core/services/google_oauth.py
  - v2/backend/apps/core/services/solicitacao_publish.py
  - v2/backend/apps/core/tasks.py
  - v2/backend/apps/core/views_solicitacao.py
  - v2/backend/apps/core/views_oauth.py
  - v2/backend/apps/core/urls.py
  - v2/backend/apps/core/models/integracao.py
  - v2/backend/apps/core/models/auditoria.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/management/commands/preagenda_to_gcal.py
  - v2/backend/apps/core/management/commands/rotate_gcal_encryption_key.py
owner: backend
supersedes:
  - v2/docs/GUIDE_GCAL.md
related:
  - v2/docs/specs/backend/rbac.spec.md
  - v2/docs/RBAC_NAMING.md
  - v2/docs/rbac_authorization_matrix.md
---

# Integração Google Calendar + Meet

## Propósito

Publica eventos de formações aprovadas no Google Calendar e gera links Google Meet para eventos online (RF05/RF06). A integração é acionada a partir da Pré-agenda: quando uma `Solicitacao` está `aprovado`, um operador de Controle/Superintendência publica, re-sincroniza ou cancela o evento correspondente no Calendar. O `meet_link` resultante é persistido e exposto na API/UI.

O módulo isola o acesso à Google Calendar API atrás de um adaptador único (`CalendarClientAdapter`), com três implementações intercambiáveis selecionadas por configuração: `fake` (in-memory, default seguro), `google` via Service Account e `google` via OAuth 2.0 por usuário. Toda escrita real no Calendar passa por idempotência (event id derivado da solicitação), retry com backoff e auditoria.

## Fonte de verdade no código

- Guia operacional detalhado (setup Google Cloud, troubleshooting): [`v2/docs/GUIDE_GCAL.md`](../../GUIDE_GCAL.md). Esta spec é o índice/contrato; o guia mantém os passos de configuração.
- Seleção de cliente: [`gcal_client_factory.py`](../../../backend/apps/core/services/gcal_client_factory.py) — `get_gcal_client_and_calendar_id()` (service account / fake) e `get_oauth_client_for_user(user)` (OAuth).
- Clientes (implementam o adaptador [`gcal/client.py`](../../../backend/apps/core/services/gcal/client.py)):
  - [`gcal_google_client.py`](../../../backend/apps/core/services/gcal_google_client.py) — Service Account.
  - [`gcal_oauth_client.py`](../../../backend/apps/core/services/gcal_oauth_client.py) — OAuth por usuário.
  - [`gcal_fake_client.py`](../../../backend/apps/core/services/gcal_fake_client.py) — fake in-memory.
- Sincronização (pacote modular): [`gcal/sync.py`](../../../backend/apps/core/services/gcal/sync.py) (`apply_one_solicitacao`, `upsert_one`, `resync_solicitacao`, `cancel_solicitacao`) e [`gcal/payload.py`](../../../backend/apps/core/services/gcal/payload.py) (`build_event_payload`, `build_preview_for_solicitacao`). O módulo legado [`gcal_sync_service.py`](../../../backend/apps/core/services/gcal_sync_service.py) é apenas um *re-export facade* para o pacote `gcal/`.
- Camada de serviço dos endpoints: [`solicitacao_publish.py`](../../../backend/apps/core/services/solicitacao_publish.py) (`publish_to_gcal`, `preview_gcal`, `resync_to_gcal`, `cancel_from_gcal`, `_check_google_oauth`).
- Tasks Celery: [`tasks.py`](../../../backend/apps/core/tasks.py) — `task_publish_solicitacao_to_gcal`, `task_cancel_solicitacao_from_gcal`, `preview_then_apply_gcal` (beat).
- OAuth 2.0 (fluxo + tokens): [`oauth/oauth_flow.py`](../../../backend/apps/core/services/oauth/oauth_flow.py) e [`oauth/token_manager.py`](../../../backend/apps/core/services/oauth/token_manager.py), re-exportados por [`google_oauth.py`](../../../backend/apps/core/services/google_oauth.py). Modelo: [`models/integracao.py`](../../../backend/apps/core/models/integracao.py) (`GoogleOAuthCredential`).
- Endpoints: [`views_solicitacao.py`](../../../backend/apps/core/views_solicitacao.py) (ações GCal) e [`views_oauth.py`](../../../backend/apps/core/views_oauth.py) (fluxo OAuth) — roteados em [`urls.py`](../../../backend/apps/core/urls.py).

## Contratos e invariantes

- **Modo de cliente vs modo de auth são variáveis distintas**: `GCAL_CLIENT` ∈ `{fake, google}` decide cliente real vs in-memory; `GCAL_AUTH_MODE` ∈ `{service_account, oauth}` decide a autenticação no modo real. **Não existe `GCAL_CLIENT_MODE`.** Default: `GCAL_CLIENT=fake`, `GCAL_AUTH_MODE=service_account`.
- **Governança de escrita real**: publicação real só ocorre com `GCAL_CLIENT=google`. Com `GCAL_CLIENT != "google"`, `apply_blocked=false` e `dry_run=false`, o serviço retorna **409 Conflict** (`code=gcal_client_not_configured`) e não persiste nada. `apply_blocked=true` força via cliente fake (somente testes).
- **Pré-condição de publicação**: apenas `Solicitacao.status == "aprovado"` pode publicar/re-sincronizar (`code=not_approved` caso contrário).
- **OAuth obrigatório por usuário**: em `GCAL_AUTH_MODE=oauth`, o operador precisa de `GoogleOAuthCredential`. Sem credencial, publish/resync/cancel retornam **403 Forbidden** (`code=google_not_connected`); com credencial, a task recebe `operator_user_id` e a resposta é **202 Accepted**.
- **Domínio restrito (OAuth)**: o callback só aceita contas `@{GCAL_ALLOWED_DOMAIN}` (default `aprendereditora.com.br`); outras levantam erro na troca de código.
- **Idempotência**: o event id é derivado da solicitação; `insert`/`update`/`delete` são idempotentes. `delete`/`cancel` tratam **404 como sucesso** (evento já removido). `cancel_solicitacao` exige evento publicado, senão `ValueError` (→ **409** no endpoint).
- **Modalidade (`is_online`)**: `conferenceData`/`requestId` (`conferenceSolutionKey=hangoutsMeet`) só é incluído quando `is_online=true`; `conferenceDataVersion=1` é obrigatório no `insert`/`patch` para o Meet ser criado. Eventos presenciais nunca geram nem persistem `meet_link`.
- **Persistência de `meet_link` apenas em APPLY real**: preview, `dry_run=true` e o caminho bloqueado (409) **não** persistem `meet_link`/`external_event_id`/`gcal_payload_hash`.
- **`GCAL_SEND_UPDATES`** ∈ `{none, all, externalOnly}` (default `none`) é validado *fail-fast* no boot (`sys.exit(1)` em valor inválido) e repassado como `sendUpdates` em insert/update/delete.
- **Tokens OAuth criptografados em repouso** (Fernet, AES-128-CBC + HMAC-SHA256) via `GCAL_ENCRYPTION_KEY`. Em produção a chave é **obrigatória** (ausência → `ValueError`); em dev/staging há fallback derivado de `SECRET_KEY` com warning. Refresh é thread-safe (`select_for_update` + double-check). `invalid_grant` no refresh remove a credencial e exige reconexão.
- **RBAC**: todas as ações GCal usam `permission_classes=[CanUseGcal]` (Policy `use_gcal` = `operate_preagenda | approve_solicitation`, ou seja Controle + Superintendência). Nenhum acesso a grupo direto (banido por `scripts/rbac_lint.py`). Endpoints OAuth também exigem autenticação + RBAC e têm rate limit (`UserRateThrottle`, ~10/h no start).
- **Auditoria obrigatória (PA-05)**: cada operação grava `AuditLog` — ações `PREVIEW_GCAL`, `PUBLISH_GCAL_REQUESTED`/`PUBLISH_GCAL`/`PUBLISH_GCAL_ERROR`, `RESYNC_GCAL_REQUESTED`, `CANCEL_GCAL_REQUESTED`/`CANCEL_GCAL`, `GCAL_ENCRYPTION_KEY_ROTATION`, `GOOGLE_CONNECT`/`GOOGLE_DISCONNECT`/`GOOGLE_REFRESH_TOKEN`.

## API / Interface

Ações sobre `Solicitacao` (DRF `@action`, todas `CanUseGcal`):

- `POST /api/solicitacoes/{id}/preview-gcal/` → payload simulado, sem persistir (200).
- `POST /api/solicitacoes/{id}/publish/` — corpo `{dry_run?, apply_blocked?}` → enfileira `task_publish_solicitacao_to_gcal` (202 `task_id`); 409 se bloqueado; 403 se OAuth sem conexão.
- `POST /api/solicitacoes/{id}/resync-gcal/` → força UPDATE (reseta `gcal_payload_hash`), enfileira publish (202).
- `POST /api/solicitacoes/{id}/cancel-gcal/` → enfileira `task_cancel_solicitacao_from_gcal`; deleta evento e limpa campos (202); 409 se não publicado.
- `meet_link` é exposto nos serializers de detalhe e lista de `Solicitacao`.

Fluxo OAuth (em [`urls.py`](../../../backend/apps/core/urls.py), sob prefixo `/api/`):

- `GET /api/oauth/google/start/?return_to=…` → redireciona para o consent do Google (state CSRF em cache, TTL 10min).
- `GET /api/oauth/google/callback/` → troca código por tokens, cria `GoogleOAuthCredential`.
- `GET /api/integrations/google/status/`, `POST .../disconnect/`, `GET .../calendars/`, `POST .../select-calendar/`, `GET .../events/`.

Comandos de gestão:

- `python manage.py preagenda_to_gcal [--dry-run] [--client=fake|google] [--ids …] [--since/--until …]` — sync em lote da Pré-agenda (substitui a referência stale a `sync_calendar` no guia).
- `python manage.py rotate_gcal_encryption_key --old-key … --new-key …` — rotação zero-downtime da chave Fernet.

Beat automático: `preview_then_apply_gcal` (CELERY_BEAT_SCHEDULE, quando habilitado).

## Fluxos principais

1. **Publicação (service account)**: solicitação aprovada → `POST /publish/` → `publish_to_gcal` valida status/governança → marca `gcal_status=PENDING` → `task_publish_solicitacao_to_gcal.delay()` → `apply_one_solicitacao` monta payload (com `conferenceData` se `is_online`), faz upsert via factory (`fake`/`google`), persiste `external_event_id`/`meet_link`/hash e marca `PUBLISHED`. Erro → `ERROR` + `PUBLISH_GCAL_ERROR`.
2. **Publicação (OAuth)**: idêntico, mas `_check_google_oauth` injeta `operator_user_id`; a task instancia `OAuthCalendarClient` via `get_oauth_client_for_user` (refresh de token se expirado) e usa o calendário preferido do usuário. Sem credencial → 403 antes de enfileirar.
3. **Resync**: `resync-gcal` zera `gcal_payload_hash` para forçar UPDATE e reutiliza o caminho de publish.
4. **Cancel**: `cancel-gcal` valida publicação → `task_cancel_solicitacao_from_gcal` → `client.delete` (404 = sucesso) → limpa `external_event_id`/`meet_link`/`gcal_payload_hash`, marca `gcal_status=NONE`, `last_sync_action=DELETE`.
5. **Preview**: `preview-gcal` sempre permitido; retorna payload e (se online) `meet_link` simulado, sem persistir.
6. **Conexão OAuth**: `start` → consent Google → `callback` valida state/domínio, troca código, criptografa e salva tokens; `disconnect` revoga no Google e remove a credencial.

## Decisões relacionadas (ADRs)

- SEC-011 — criptografia de tokens OAuth (Fernet + `GCAL_ENCRYPTION_KEY`, rotação zero-downtime). Detalhes na seção 8 de [`GUIDE_GCAL.md`](../../GUIDE_GCAL.md).
- Epic #459 (§1/§7) — extração da camada de serviço de publicação e modularização OAuth (`oauth/oauth_flow.py`, `oauth/token_manager.py`).
- Issue #1233 (Epic 4.2.a) — operações GCal encapsuladas na Policy `use_gcal` (`CanUseGcal`); ver [`rbac.spec`](rbac.spec.md).

## Testes que cobrem

- [`test_gcal_publish_apply_blocked.py`](../../../backend/apps/core/tests/test_gcal_publish_apply_blocked.py) — matriz governança (409 vs publish; preview sempre permitido).
- [`test_gcal_meet_link_persist.py`](../../../backend/apps/core/tests/test_gcal_meet_link_persist.py) / [`test_gcal_meet_link_by_mode.py`](../../../backend/apps/core/tests/test_gcal_meet_link_by_mode.py) — persistência de `meet_link` só em apply real e por modo.
- [`test_gcal_conference_version.py`](../../../backend/apps/core/tests/test_gcal_conference_version.py) — `conferenceDataVersion=1` + `conferenceData` condicionado a `is_online`.
- [`test_gcal_send_updates.py`](../../../backend/apps/core/tests/test_gcal_send_updates.py) — `sendUpdates` em insert/update/delete.
- [`test_gcal_retry_backoff.py`](../../../backend/apps/core/tests/test_gcal_retry_backoff.py) / [`test_gcal_retry_audit.py`](../../../backend/apps/core/tests/test_gcal_retry_audit.py) — retry 429/5xx e auditoria.
- [`test_gcal_cancel_resync.py`](../../../backend/apps/core/tests/test_gcal_cancel_resync.py) / [`test_gcal_publish_resync.py`](../../../backend/apps/core/tests/test_gcal_publish_resync.py) — resync/cancel (helpers, tasks, endpoints; 404 idempotente; 403/409).
- [`test_gcal_oauth_mode.py`](../../../backend/apps/core/tests/test_gcal_oauth_mode.py) — roteamento OAuth (403 sem credencial, 202 com).
- [`test_google_oauth.py`](../../../backend/apps/core/tests/test_google_oauth.py), [`test_pr_security_oauth_hardening.py`](../../../backend/apps/core/tests/test_pr_security_oauth_hardening.py), [`test_pr_security_oauth_authorize_url.py`](../../../backend/apps/core/tests/test_pr_security_oauth_authorize_url.py) — encrypt/decrypt/rotation, open-redirect, rate limit, HTTPS, validação de domínio/state.
- [`test_gcal_google_client.py`](../../../backend/apps/core/tests/test_gcal_google_client.py), [`test_gcal_sync_dryrun.py`](../../../backend/apps/core/tests/test_gcal_sync_dryrun.py), [`test_gcal_hash_drift.py`](../../../backend/apps/core/tests/test_gcal_hash_drift.py), [`test_gcal_endpoints.py`](../../../backend/apps/core/tests/test_gcal_endpoints.py).

## Pontos de atenção / dívidas conhecidas

- **Doc canônico com referência stale**: a seção 5 de [`GUIDE_GCAL.md`](../../GUIDE_GCAL.md) cita `manage.py sync_calendar`, mas o comando real é `preagenda_to_gcal`. Atualizar o guia.
- **Nome de módulo na seção OAuth do guia**: a seção 1 sugere que `gcal_oauth_client` lê tokens via `oauth/token_manager`; no código o cliente importa de [`google_oauth.py`](../../../backend/apps/core/services/google_oauth.py) (que re-exporta `oauth/token_manager`). Mesmo destino, caminho indireto.
- **Mismatch `GCAL_CLIENT` configurado vs valor**: `apply_one_solicitacao` libera escrita quando `settings.GCAL_CLIENT is not None` (qualquer valor), mas a factory só instancia cliente real com `=="google"`. Com `GCAL_CLIENT=fake` a guarda passa e cai no fake client — comportamento intencional para testes, porém a governança 409 fica concentrada em `publish_to_gcal`/`apply_blocked`, não no `apply_one`. Atenção ao chamar `apply_one_solicitacao` fora do fluxo de endpoint.
- **Fallback de chave em dev/staging**: tokens cifrados com chave derivada de `SECRET_KEY` ficam ilegíveis se `SECRET_KEY` mudar; em produção `GCAL_ENCRYPTION_KEY` é mandatória. Rotação exige restart dos containers (web, worker, beat).
- **TOCTOU brando no cancel**: validação de "publicado" no endpoint e o `delete` na task são separados; concorrência é mitigada por idempotência (404 = sucesso), não por lock.
