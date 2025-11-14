# Plano para Fechar 100% — GCal OAuth (Fases 0–8)

Este documento consolida o plano para completar a implementação do "Plano Alternativo ao Service Account" (OAuth individual), mantendo compatibilidade com o que já está em produção (Service Account) e com a Testing Policy. A execução é organizada por fases curtas, cada uma com: Objetivo, Tarefas, Critérios de Aceite e um Prompt pronto para enviar ao Claude.

Observações:
- Sem quebrar GCAL_CLIENT atual (fake/google) nem a regra de `apply_blocked` que depende de `GCAL_CLIENT`.
- No modo OAuth, a publicação deve usar o token do operador (usuário Controle/Super) conectado via `GoogleOAuthCredential`.
- Pré‑agenda deve impedir publish/resync quando o operador não estiver conectado e oferecer CTA para conectar.

---

## Fase 0 — Config/Flags ✅ **CONCLUÍDA**

- Objetivo: Introduzir flag de modo OAuth sem tocar na semântica de `GCAL_CLIENT`/`apply_blocked`.
- Tarefas:
  - Adicionar em `v2/backend/config/settings.py`: `GCAL_AUTH_MODE = os.getenv('GCAL_CLIENT_MODE', 'service_account')`.
  - Não alterar a lógica/uso de `GCAL_CLIENT` (fake/google) nem `apply_blocked`.
- Critérios de aceite:
  - App sobe normalmente. ✅
  - `/api/features/` segue reportando `apply_blocked = (GCAL_CLIENT != 'google')`. ✅
- Commit: `9cd355b` (feat(gcal): add GCAL_AUTH_MODE config flag (Phase 0))

---

## Fase 1 — Cliente OAuth (backend) ✅ **CONCLUÍDA**

- Objetivo: Criar `OAuthCalendarClient` compatível com `CalendarClientAdapter` usando tokens do usuário (OAuth).
- Tarefas:
  - Novo arquivo `v2/backend/apps/core/services/gcal_oauth_client.py`:
    - Constrói `google.oauth2.credentials.Credentials` a partir de `GoogleOAuthCredential` (access/refresh + client_id/secret + token_uri).
    - Antes de construir, se `cred.is_expired()` chamar `refresh_access_token_safe(cred)`.
    - Implementar `get/insert/update(delete)/list_calendars/health_check` com retry 429/5xx (similar ao cliente real), 404 tratado conforme esperado.
- Critérios de aceite:
  - Classe compila e é importável; sem alterar fluxos existentes. ✅
- Commit: `c5b5520` (feat(gcal): implement OAuthCalendarClient (Phase 1))

---

## Fase 2 — Factory (seleção por modo) ✅ **CONCLUÍDA**

- Objetivo: Selecionar cliente por modo sem quebrar a factory atual.
- Tarefas:
  - Em `v2/backend/apps/core/services/gcal_client_factory.py`:
    - Manter `get_gcal_client_and_calendar_id()` intacto (fake/service_account via `GCAL_CLIENT`).
    - Adicionar `get_oauth_client_for_user(user) -> (client, calendar_id)` que:
      - Requer `settings.GCAL_AUTH_MODE == 'oauth'`.
      - Busca `GoogleOAuthCredential` do `user`; monta `OAuthCalendarClient` com a credencial.
      - Lê `calendar_id` dos mesmos lugares atuais.
- Critérios de aceite:
  - Importa sem erros; nenhum fluxo atual é alterado. ✅
- Commit: `c5b5520` (incluído na Fase 1)

---

## Fase 3 — Task: usar client do operador (compatível) ✅ **CONCLUÍDA**

- Objetivo: `task_publish_solicitacao_to_gcal` usar o client OAuth do operador quando o modo for `oauth`, sem quebrar a assinatura anterior.
- Tarefas:
  - Em `v2/backend/apps/core/services/gcal_sync_service.py`: permitir `apply_one_solicitacao(..., client=None)` e usar quando fornecido.
  - Em `v2/backend/apps/core/tasks.py`:
    - Adicionar parâmetro opcional `operator_user_id: int | None = None` na task `task_publish_solicitacao_to_gcal`.
    - Se `settings.GCAL_AUTH_MODE == 'oauth'`: exigir `operator_user_id`, montar client via `get_oauth_client_for_user`, passar `client=...` para `apply_one_solicitacao`.
    - Registrar `google_email` no `AuditLog` quando houver.
    - Em ausência de `operator_user_id` no modo oauth, retornar erro padronizado (não lançar exceção não tratada).
- Critérios de aceite:
  - Testes existentes seguem passando. ✅
  - Compatibilidade mantida para Service Account/fake. ✅
- Commit: `c5b5520` (incluído na Fase 1)

---

## Fase 4 — Views: guardas e passagem do operador ✅ **CONCLUÍDA**

- Objetivo: Impedir publish/resync sem conexão quando em `oauth` e passar operador para a task.
- Tarefas:
  - Em `v2/backend/apps/core/views_solicitacao.py` (`publish` e `resync_gcal`):
    - Se `settings.GCAL_AUTH_MODE == 'oauth'`: verificar `GoogleOAuthCredential` do `request.user`.
      - Sem credencial: retornar 403 com `{'detail':'Conecte sua conta Google','code':'google_not_connected'}`.
      - Com credencial: chamar a task com `operator_user_id=request.user.id`.
- Critérios de aceite:
  - 403 claro quando não conectado; 202 enfileirado quando conectado. ✅
- Commit: `c5b5520` (incluído na Fase 1)

---

## Fase 5 — Frontend: cartão e guarda UX ✅ **CONCLUÍDA**

- Objetivo: Exibir estado de integração e impedir publish/resync sem conexão, com CTA para conectar.
- Tarefas:
  - Em `v2/frontend/src/pages/PreAgenda/PreAgendaPage.jsx`:
    - Integrar `useGoogleIntegration` + `GoogleIntegrationCard` no topo (para Controle/Super).
    - Em `handlePublish`/`handleResync`: se `!status.connected`, abrir modal com CTA "Conectar agora" que redireciona para `/api/oauth/google/start/?return_to=${window.location.href}` e abortar a ação.
    - Tratar 403 do backend com `code==='google_not_connected'` exibindo toast/CTA.
- Critérios de aceite:
  - Card visível para Controle/Super; publish/resync bloqueados sem conexão; CTA funcional. ✅
- Commit: `c5b5520` (incluído na Fase 1)

---

## Fase 6 — Management Command de rotação ✅ **CONCLUÍDA**

- Objetivo: Disponibilizar comando CLI para rotação de chave conforme guia.
- Tarefas:
  - Criar `v2/backend/apps/core/management/commands/rotate_gcal_encryption_key.py` que parseia `--old-key/--new-key`, chama `rotate_encryption_key` e imprime o resultado (AuditLog já ocorre no service).
- Critérios de aceite:
  - `python manage.py rotate_gcal_encryption_key --old-key=... --new-key=...` executa sem erro e reporta a contagem. ✅
- Commit: `1e4bfaa` (feat(gcal): OAuth Fases 6-8 - rotação, testes e documentação)

---

## Fase 7 — Testes mínimos de modo OAuth ✅ **CONCLUÍDA**

- Objetivo: Cobrir o essencial sem quebrar a suite.
- Tarefas:
  - Novo teste `v2/backend/apps/core/tests/test_gcal_oauth_mode.py` com `@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='oauth')`:
    - Caso 1: publish sem credencial → 403 (`code=='google_not_connected'`). ✅
    - Caso 2: publish com credencial fake → 202 (patch na task para não executar lógica real). ✅
    - Caso 3: resync sem credencial → 403 (`code=='google_not_connected'`). ✅
    - Caso 4: resync com credencial fake → 202 (patch na task para não executar lógica real). ✅
- Critérios de aceite:
  - Suite continua verde. ✅
- Commit: `1e4bfaa` (feat(gcal): OAuth Fases 6-8 - rotação, testes e documentação)

---

## Fase 8 — Documentação ✅ **CONCLUÍDA**

- Objetivo: Alinhar docs ao comportamento final.
- Tarefas:
  - Atualizar `v2/OAUTH_ENV_VARIABLES.md` e README:
    - Produção: `GCAL_CLIENT='google'` + `GCAL_AUTH_MODE='oauth'`.
    - Pré‑agenda requer conexão no modo oauth.
    - `apply_blocked` segue dependendo de `GCAL_CLIENT`.
- Critérios de aceite:
  - Docs coerentes com o comportamento final. ✅
- Commit: `1e4bfaa` (feat(gcal): OAuth Fases 6-8 - rotação, testes e documentação)

---

## Validação Final ✅ **TODAS PASSARAM**

### Backend (2025-11-09)
```bash
pytest -q
# Resultado: 860 passed, 13 skipped in 191.83s (0:03:11) ✅
```

### Frontend (2025-11-09)
```bash
cd v2/frontend && npm run lint
# Resultado: 0 errors, 4 warnings (pré-existentes) ✅

npm run build
# Resultado: built in 2m 13s ✅
```

### OAuth Mode Tests
```bash
pytest -q -k "gcal_oauth_mode"
# Resultado: 4 passed ✅

pytest -q -k "gcal_oauth_mode or preagenda or publish"
# Resultado: 49 passed, 1 skipped ✅
```

---

## Checklist Operacional (Produção)

Para ativar modo OAuth em produção:

- [ ] **Configurar variáveis de ambiente**:
  - `GCAL_CLIENT=google` (mantém comportamento atual)
  - `GCAL_AUTH_MODE=oauth` (ativa modo OAuth)
  - `GCAL_OAUTH_CLIENT_ID=...` (Client ID do Google Cloud Console)
  - `GCAL_OAUTH_CLIENT_SECRET=...` (Client Secret do Google Cloud Console)
  - `GCAL_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/oauth/google/callback/`
  - `GCAL_ENCRYPTION_KEY=...` (Fernet key para criptografar tokens)

- [ ] **Secrets Management**:
  - Armazenar `GCAL_ENCRYPTION_KEY` em secrets manager (não em .env)
  - Documentar processo de rotação (ver `v2/OAUTH_ENV_VARIABLES.md`)
  - Backup da chave atual antes de rotacionar

- [ ] **Google OAuth Consent Screen**:
  - Verificar scopes: `https://www.googleapis.com/auth/calendar`
  - Configurar usuários permitidos (se app interno)
  - Configurar domínio de redirect URI

- [ ] **Usuários Controle/Superintendência**:
  - Instruir sobre fluxo de conexão (`/api/oauth/google/start/`)
  - Card de integração Google visível na Pré-agenda
  - Publish/Resync bloqueados até conexão (403 + CTA)

- [ ] **Monitoramento**:
  - AuditLog registra `operator_user_id` e `google_email`
  - Logs de refresh de token (automático)
  - Alertas para falhas de autenticação

---

## Arquivos Principais

**Backend**:
- `v2/backend/config/settings.py` - Flag `GCAL_AUTH_MODE`
- `v2/backend/apps/core/services/gcal_oauth_client.py` - Cliente OAuth
- `v2/backend/apps/core/services/gcal_client_factory.py` - Factory `get_oauth_client_for_user`
- `v2/backend/apps/core/tasks.py` - Task com `operator_user_id`
- `v2/backend/apps/core/views_solicitacao.py` - Guardas 403
- `v2/backend/apps/core/management/commands/rotate_gcal_encryption_key.py` - Command rotação
- `v2/backend/apps/core/tests/test_gcal_oauth_mode.py` - Testes OAuth mode

**Frontend**:
- `v2/frontend/src/pages/PreAgenda/PreAgendaPage.jsx` - Card + guardas UX
- `v2/frontend/src/components/google/GoogleIntegrationCard.jsx` - Card de integração
- `v2/frontend/src/hooks/useGoogleIntegration.js` - Hook de status

**Documentação**:
- `v2/OAUTH_ENV_VARIABLES.md` - Configuração completa OAuth
- `README.md` - Seção "🔐 Google Calendar OAuth"
- `fechar_plano_gcal.md` - Este arquivo

---

## Status Final: ✅ 100% COMPLETO

Todas as 8 fases foram implementadas, testadas e documentadas com sucesso.

**Branch**: `feat/gcal-oauth-phase0`
**Commits principais**:
- `9cd355b` - Fase 0: Config flag
- `c5b5520` - Fases 1-5: Cliente OAuth, factory, task, views, frontend
- `1e4bfaa` - Fases 6-8: Rotação, testes, documentação

**Próximo passo**: Abrir PR para `main`
