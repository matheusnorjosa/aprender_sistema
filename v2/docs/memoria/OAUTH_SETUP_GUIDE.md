# 🔐 Guia de Configuração OAuth - Google Calendar

## 📋 Prompt 2: Configuração de Variáveis OAuth

### 1️⃣ Adicionar Variáveis ao `.env`

Abra o arquivo `v2/infra/.env` e adicione as seguintes variáveis:

```bash
# ============================================================================
# GOOGLE OAUTH CONFIGURATION (Issue #95 - Batch Operations)
# ============================================================================

# OAuth Client Credentials (obter no Google Cloud Console)
GCAL_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GCAL_OAUTH_CLIENT_SECRET=your-client-secret

# OAuth Redirect URI (deve estar registrado no Google Cloud Console)
GCAL_OAUTH_REDIRECT_URI=http://localhost:8002/api/oauth/google/callback/

# Encryption Key para tokens (Fernet key gerada abaixo)
GCAL_ENCRYPTION_KEY=puo0c1u0EJLTGI-fMntHGIjPM1LPjd2Qf_SjFCUXAPc=

# OAuth Scopes (separados por espaço)
GCAL_OAUTH_SCOPES=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events

# OAuth Auth Mode (service_account ou oauth)
GCAL_AUTH_MODE=oauth
```

---

### 2️⃣ Obter Credenciais OAuth no Google Cloud Console

#### Passo 1: Acessar Google Cloud Console
1. Acesse: https://console.cloud.google.com/
2. Selecione o projeto **Aprender Sistema** (ou crie um novo)

#### Passo 2: Habilitar Google Calendar API
1. Menu → **APIs & Services** → **Library**
2. Buscar: **Google Calendar API**
3. Clicar **Enable**

#### Passo 3: Criar OAuth 2.0 Credentials
1. Menu → **APIs & Services** → **Credentials**
2. Clicar **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Application type: **Web application**
4. Name: **Aprender Sistema - OAuth Client**
5. **Authorized redirect URIs**:
   - `http://localhost:8002/api/oauth/google/callback/`
   - `http://127.0.0.1:8002/api/oauth/google/callback/`
6. Clicar **CREATE**

#### Passo 4: Copiar Credenciais
Após criar, copiar:
- **Client ID**: `123456789-abc...apps.googleusercontent.com`
- **Client Secret**: `GOCSPX-...`

Colar no `.env`:
```bash
GCAL_OAUTH_CLIENT_ID=<Client ID copiado>
GCAL_OAUTH_CLIENT_SECRET=<Client Secret copiado>
```

---

### 3️⃣ Atualizar `.env.example`

Abra `v2/infra/.env.example` e adicione os placeholders:

```bash
# ============================================================================
# GOOGLE OAUTH CONFIGURATION
# ============================================================================
GCAL_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GCAL_OAUTH_CLIENT_SECRET=your-client-secret
GCAL_OAUTH_REDIRECT_URI=http://localhost:8002/api/oauth/google/callback/
GCAL_ENCRYPTION_KEY=<generate-with-Fernet.generate_key()>
GCAL_OAUTH_SCOPES=https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events
GCAL_AUTH_MODE=oauth
```

---

### 4️⃣ Rebuild e Reiniciar Containers

```bash
cd v2/infra

# Rebuild (se necessário rebuild de imagens)
docker compose build

# Restart services
docker compose restart web worker beat

# Verificar logs
docker compose logs -f web
```

**Nota**: Se não houver mudanças no Dockerfile, apenas `docker compose restart` é suficiente. As variáveis `.env` são carregadas no restart.

---

### 5️⃣ Validação Manual do Fluxo OAuth

#### Teste 1: Verificar Status (Desconectado)
```bash
curl -X GET http://localhost:8002/api/integrations/google/status/ \
  -H "Cookie: sessionid=<seu-session-id>" \
  -b cookies.txt

# Esperado: {"connected": false}
```

#### Teste 2: Iniciar Fluxo OAuth
1. Acessar frontend: http://localhost:5173/pre-agenda
2. Clicar **"Conectar conta Google"** (no card ou ao tentar batch operation)
3. **Verificar redirecionamento**:
   - URL: `https://accounts.google.com/o/oauth2/v2/auth?...`
   - Parâmetros: `client_id`, `redirect_uri`, `scope`, `state`

#### Teste 3: Concluir Consent
1. Selecionar conta Google corporativa (@aprendereditora.com.br)
2. Aceitar permissões:
   - "Ver e gerenciar eventos do Google Calendar"
3. **Verificar redirect**:
   - URL: `http://localhost:8002/api/oauth/google/callback/?code=...&state=...`
   - Frontend redirect: `http://localhost:5173/pre-agenda?google=connected`

#### Teste 4: Verificar Status (Conectado)
```bash
curl -X GET http://localhost:8002/api/integrations/google/status/ \
  -H "Cookie: sessionid=<seu-session-id>" \
  -b cookies.txt

# Esperado:
# {
#   "connected": true,
#   "google_email": "usuario@aprendereditora.com.br",
#   "token_expiry": "2025-11-10T14:30:00Z",
#   "default_calendar_id": "primary"
# }
```

#### Teste 5: Executar Batch Operation
1. Na página `/pre-agenda`, selecionar 2-3 eventos
2. Clicar **"Reapply Selecionados"** ou **"Resync Selecionados"**
3. **Verificar**:
   - ✅ Não deve mostrar modal "Conectar conta Google"
   - ✅ Deve executar operação e exibir `{queued: N}` eventos
   - ✅ Verificar logs: `operator_user_id` propagado na task

---

### 6️⃣ Troubleshooting

#### Erro: "redirect_uri_mismatch"
**Causa**: Redirect URI no `.env` não está registrado no Google Cloud Console

**Solução**:
1. Google Cloud Console → **APIs & Services** → **Credentials**
2. Editar OAuth Client
3. Adicionar exatamente: `http://localhost:8002/api/oauth/google/callback/`

#### Erro: "Invalid encryption key"
**Causa**: `GCAL_ENCRYPTION_KEY` inválido ou não definido

**Solução**: Gerar nova chave:
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Erro: "GoogleOAuthCredential matching query does not exist"
**Causa**: Usuário não completou fluxo OAuth

**Solução**: Clicar "Conectar conta Google" e completar consent flow

#### Erro: "Token expired"
**Causa**: Token OAuth expirado (1 hora de validade padrão)

**Solução**: Sistema deve renovar automaticamente com `refresh_token`. Se falhar, desconectar e reconectar.

---

### 7️⃣ Validação de Segurança

✅ **Checklist de Segurança OAuth**:
- [ ] `GCAL_ENCRYPTION_KEY` com 32+ caracteres (Fernet key)
- [ ] Client Secret **NÃO** commitado no git (.env em .gitignore)
- [ ] Redirect URI whitelist no Google Cloud Console
- [ ] OAuth scopes mínimos necessários (calendar.events)
- [ ] Token expiry validado (1 hora default, auto-refresh)
- [ ] HTTPS em produção (localhost OK para dev)

---

### 8️⃣ Diagrama do Fluxo OAuth

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │         │   Backend    │         │   Google    │
│ (PreAgenda) │         │ (Django/DRF) │         │   OAuth     │
└──────┬──────┘         └──────┬───────┘         └──────┬──────┘
       │                       │                        │
       │ 1. Clicar "Conectar"  │                        │
       ├──────────────────────>│                        │
       │                       │                        │
       │ 2. Redirect to Google │                        │
       │<──────────────────────┤                        │
       │                       │                        │
       │ 3. Consent Screen     │                        │
       ├───────────────────────┼───────────────────────>│
       │                       │                        │
       │ 4. Redirect + code    │                        │
       │<──────────────────────┼────────────────────────┤
       │                       │                        │
       │ 5. Exchange code      │                        │
       ├──────────────────────>│                        │
       │                       │ 6. Get tokens          │
       │                       ├───────────────────────>│
       │                       │                        │
       │                       │ 7. Access + Refresh    │
       │                       │<───────────────────────┤
       │                       │                        │
       │                       │ 8. Encrypt + Store DB  │
       │                       │ (GoogleOAuthCredential)│
       │                       │                        │
       │ 9. Redirect success   │                        │
       │<──────────────────────┤                        │
       │                       │                        │
```

---

### 9️⃣ Comandos Úteis

```bash
# Gerar nova encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Verificar variáveis carregadas no container
docker compose exec web python manage.py shell -c "
from django.conf import settings
print('GCAL_AUTH_MODE:', settings.GCAL_AUTH_MODE)
print('GCAL_OAUTH_CLIENT_ID:', settings.GCAL_OAUTH_CLIENT_ID[:20] + '...' if settings.GCAL_OAUTH_CLIENT_ID else None)
print('GCAL_ENCRYPTION_KEY:', 'SET' if settings.GCAL_ENCRYPTION_KEY else 'NOT SET')
"

# Ver logs do OAuth flow
docker compose logs -f web | grep -i oauth

# Limpar credenciais OAuth (reset)
docker compose exec web python manage.py shell -c "
from apps.core.models import GoogleOAuthCredential
GoogleOAuthCredential.objects.filter(user__username='seu_usuario').delete()
print('Credentials deleted')
"
```

---

### 🎯 Resultado Esperado

Após seguir este guia:

✅ Variáveis OAuth configuradas no `.env`
✅ Credenciais obtidas do Google Cloud Console
✅ Containers reiniciados com novas variáveis
✅ Fluxo OAuth completo funcionando
✅ Status endpoint retorna `connected: true`
✅ Batch operations executam sem modal "Conectar Google"
✅ `operator_user_id` propagado nas tasks

---

**Próxima etapa**: Testar manualmente ações em massa com múltiplos eventos! 🚀
