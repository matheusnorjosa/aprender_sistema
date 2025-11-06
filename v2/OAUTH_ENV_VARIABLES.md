# OAuth 2.0 Environment Variables

**Arquivo**: `.env` (adicione ao `.env.example` existente)

## Variáveis Obrigatórias (Sprint 1 - Issue #1)

```bash
# ============================================================================
# GOOGLE OAUTH 2.0 (Sprint 1 - Issue #1)
# ============================================================================

# Client ID do Google Cloud OAuth 2.0 Client
# Obter em: https://console.cloud.google.com/apis/credentials
# Formato: 123456789012-abcdefghijklmnopqrstuvwxyz123456.apps.googleusercontent.com
GCAL_OAUTH_CLIENT_ID=

# Client Secret do Google Cloud OAuth 2.0 Client
# Obter em: https://console.cloud.google.com/apis/credentials
# Formato: GOCSPX-abcdefghijklmnopqrstuvwxyz
GCAL_OAUTH_CLIENT_SECRET=

# Redirect URI autorizada (deve estar configurada no Google Cloud Console)
# Desenvolvimento: http://localhost:8002/api/oauth/google/callback/
# Staging: https://staging.aprender.com/api/oauth/google/callback/
# Produção: https://sistema.aprender.com/api/oauth/google/callback/
GCAL_OAUTH_REDIRECT_URI=http://localhost:8002/api/oauth/google/callback/

# Domínio permitido para contas Google (validação de segurança)
# Apenas contas com email @GCAL_ALLOWED_DOMAIN serão aceitas
GCAL_ALLOWED_DOMAIN=aprendereditora.com.br

# Chave de criptografia dedicada para tokens OAuth (GAP-2)
# OBRIGATÓRIA EM PRODUÇÃO. Gere com:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Formato: 32 bytes base64-encoded (ex: "abcdefghijklmnopqrstuvwxyz012345678901234=")
# IMPORTANTE: Guarde esta chave em local seguro (ex: Vault, AWS Secrets Manager)
GCAL_ENCRYPTION_KEY=

# Modo do cliente Google Calendar
# Valores: "oauth" (usar credenciais OAuth individuais) ou "service_account" (fallback)
# Staging/Produção: "oauth"
# Desenvolvimento: "fake" (para testes sem Google API)
GCAL_CLIENT_MODE=oauth

# ID do calendário padrão (usado se usuário não especificar)
# Obter em: Google Calendar Settings > Integrate calendar
# Formato: "primary" ou "abc123@group.calendar.google.com"
GCAL_CALENDAR_ID=primary
```

---

## Configuração no Google Cloud Console

### 1. Criar OAuth 2.0 Client ID

1. Acesse: https://console.cloud.google.com/apis/credentials
2. Clique em **"+ CREATE CREDENTIALS"** → **"OAuth 2.0 Client ID"**
3. **Application type**: Web application
4. **Name**: Aprender Sistema v2 - OAuth (ou nome descritivo)
5. **Authorized redirect URIs**:
   - Desenvolvimento: `http://localhost:8002/api/oauth/google/callback/`
   - Staging: `https://staging.aprender.com/api/oauth/google/callback/`
   - Produção: `https://sistema.aprender.com/api/oauth/google/callback/`
6. Clique em **"CREATE"**
7. Copie **Client ID** e **Client Secret**

### 2. Configurar OAuth Consent Screen

1. Acesse: https://console.cloud.google.com/apis/credentials/consent
2. **User Type**: Internal (apenas @aprendereditora.com.br)
3. **App name**: Aprender Sistema v2
4. **User support email**: operacional1@aprendereditora.com.br
5. **Developer contact**: operacional1@aprendereditora.com.br
6. **Scopes**:
   - `https://www.googleapis.com/auth/calendar` (gerenciar eventos de calendário)
7. **Test users** (se necessário em dev):
   - `operacional1@aprendereditora.com.br`
   - `operacional3@aprendereditora.com.br`
8. Clique em **"SAVE AND CONTINUE"**

### 3. Habilitar Google Calendar API

1. Acesse: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
2. Clique em **"ENABLE"**

---

## Gerar Chave de Criptografia (GAP-2)

```bash
# Gerar nova chave Fernet (32 bytes)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Exemplo de saída:
# 1234567890abcdefghijklmnopqrstuvwxyzABCDEF==

# Adicionar ao .env:
GCAL_ENCRYPTION_KEY=1234567890abcdefghijklmnopqrstuvwxyzABCDEF==
```

**⚠️ IMPORTANTE:**
- **NÃO** commitar chave no Git
- Usar gerenciador de secrets (Vault, AWS Secrets Manager, etc.) em produção
- Rotacionar chave periodicamente (ver `python manage.py rotate_gcal_encryption_key`)

---

## Teste de Configuração

### 1. Verificar variáveis:

```bash
cd v2/backend
python manage.py shell

# No shell Python:
import os
print("CLIENT_ID:", os.getenv("GCAL_OAUTH_CLIENT_ID")[:20], "...")
print("CLIENT_SECRET:", "✅ configurado" if os.getenv("GCAL_OAUTH_CLIENT_SECRET") else "❌ ausente")
print("REDIRECT_URI:", os.getenv("GCAL_OAUTH_REDIRECT_URI"))
print("ENCRYPTION_KEY:", "✅ configurado" if os.getenv("GCAL_ENCRYPTION_KEY") else "❌ ausente")
```

### 2. Testar fluxo OAuth:

```bash
# Aplicar migration
docker compose exec web python manage.py migrate

# Criar usuário de teste Controle (se não existir)
docker compose exec web python manage.py shell
>>> from django.contrib.auth.models import Group
>>> from apps.core.models import Usuario
>>> controle_group = Group.objects.get(name="Controle")
>>> user = Usuario.objects.create_user(
...     username="teste_oauth",
...     email="teste@aprendereditora.com.br",
...     password="senha123",
...     cpf="12345678901"
... )
>>> user.groups.add(controle_group)
>>> exit()

# Acessar frontend
# 1. Login com usuario teste_oauth
# 2. Acessar /pre-agenda
# 3. Clicar "Conectar conta Google"
# 4. Autorizar permissões
# 5. Verificar card verde "Conectado"
```

---

## Troubleshooting

### Erro: "redirect_uri_mismatch"

**Causa**: Redirect URI no .env não está configurado no Google Cloud Console

**Solução**:
1. Verificar GCAL_OAUTH_REDIRECT_URI no .env
2. Adicionar exatamente a mesma URI em: https://console.cloud.google.com/apis/credentials → OAuth 2.0 Client → "Authorized redirect URIs"

### Erro: "invalid_grant"

**Causa**: Usuário revogou permissões ou refresh_token expirou

**Solução**:
- Usuário deve reconectar conta via `/pre-agenda` → "Conectar conta Google"

### Erro: "Domínio não permitido"

**Causa**: Email da conta Google não é @aprendereditora.com.br

**Solução**:
- Usar apenas contas corporativas @aprendereditora.com.br
- Ou atualizar GCAL_ALLOWED_DOMAIN no .env

### Erro: "GCAL_ENCRYPTION_KEY obrigatória"

**Causa**: GCAL_ENCRYPTION_KEY não definida no .env

**Solução**:
```bash
# Gerar chave
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Adicionar ao .env
echo 'GCAL_ENCRYPTION_KEY=<chave-gerada>' >> .env
```

---

## Segurança (Produção)

### Checklist:

- [ ] `GCAL_ENCRYPTION_KEY` gerada e armazenada em Vault/Secrets Manager
- [ ] `GCAL_OAUTH_CLIENT_SECRET` armazenado em Secrets Manager (não em plaintext)
- [ ] `GCAL_ALLOWED_DOMAIN` configurado corretamente
- [ ] OAuth Consent Screen configurado como "Internal"
- [ ] HTTPS obrigatório (`request.is_secure()` validado no callback)
- [ ] Rate limiting ativo (10 req/h por usuário)
- [ ] AuditLog monitorado (Sentry alertas para `invalid_grant`)
- [ ] Rotation de chave documentada e testada

---

## Refs:

- Sprint 1 (Issue #1): Core OAuth - Backend + Frontend
- GAP-2: Encryption key dedicada
- GAP-3: Rate limiting
- PA-05: Auditoria obrigatória
- Checklist Validação: Sprint 1 (39 itens)

**Data**: 05/11/2025
**Versão**: 1.0
