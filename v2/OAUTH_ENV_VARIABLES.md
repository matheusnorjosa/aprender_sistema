# OAuth Environment Variables — Aprender Sistema v2

Documentação de variáveis de ambiente para modo OAuth do Google Calendar.

---

## 📋 Overview

O sistema suporta dois modos de autenticação com Google Calendar:

1. **Service Account Mode** (padrão): Usa credenciais de conta de serviço para autenticação servidor-a-servidor
2. **OAuth Mode**: Usa credenciais OAuth 2.0 individuais por usuário (Controle/Superintendência)

---

## 🔧 Variáveis de Ambiente

### Modo de Autenticação

```bash
# Modo OAuth (requer conexão individual por usuário)
GCAL_CLIENT_MODE=oauth

# Modo Service Account (padrão, sem conexão individual)
GCAL_CLIENT_MODE=service_account  # ou omitir (default)
```

### Cliente Google Calendar

```bash
# Cliente real do Google Calendar (produção)
GCAL_CLIENT=google

# Cliente fake (desenvolvimento/testes)
GCAL_CLIENT=fake  # ou omitir (default)
```

### Credenciais OAuth 2.0

```bash
# OAuth 2.0 Client ID (Google Cloud Console)
GCAL_OAUTH_CLIENT_ID=123456789-abc.apps.googleusercontent.com

# OAuth 2.0 Client Secret (Google Cloud Console)
GCAL_OAUTH_CLIENT_SECRET=GOCSPX-xyz123abc456

# Redirect URI (deve estar registrada no Google Cloud Console)
GCAL_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/oauth/google/callback/
```

### Chave de Criptografia

```bash
# Chave Fernet para criptografar tokens OAuth (base64-encoded, 32 bytes)
# Gerar: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
GCAL_ENCRYPTION_KEY=your-base64-encoded-fernet-key-here
```

### Calendar ID

```bash
# ID do calendário Google (produção)
GCAL_CALENDAR_ID=your-calendar-id@group.calendar.google.com

# Usar calendário primário do usuário (OAuth mode)
GCAL_CALENDAR_ID=primary
```

---

## 🚀 Configuração por Ambiente

### Desenvolvimento (Local)

```bash
# .env (desenvolvimento)
GCAL_CLIENT=fake
GCAL_CLIENT_MODE=service_account
# Sem necessidade de credenciais OAuth
```

### Staging (OAuth Habilitado)

```bash
# .env (staging)
GCAL_CLIENT=google
GCAL_CLIENT_MODE=oauth
GCAL_OAUTH_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GCAL_OAUTH_CLIENT_SECRET=GOCSPX-xyz123abc456
GCAL_OAUTH_REDIRECT_URI=https://staging.seu-dominio.com/api/oauth/google/callback/
GCAL_ENCRYPTION_KEY=your-staging-fernet-key
GCAL_CALENDAR_ID=primary
```

### Produção (OAuth Habilitado)

```bash
# .env (produção)
GCAL_CLIENT=google
GCAL_CLIENT_MODE=oauth
GCAL_OAUTH_CLIENT_ID=987654321-xyz.apps.googleusercontent.com
GCAL_OAUTH_CLIENT_SECRET=GOCSPX-prod789def012
GCAL_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/oauth/google/callback/
GCAL_ENCRYPTION_KEY=your-production-fernet-key
GCAL_CALENDAR_ID=calendario-aprender@group.calendar.google.com
```

---

## ⚙️ Modo OAuth - Comportamento

### Pré-requisitos

- **GCAL_CLIENT_MODE=oauth**: Modo OAuth ativado
- **Usuários**: Controle ou Superintendência
- **Conexão**: Cada usuário deve conectar sua conta Google via `/api/oauth/google/start/`

### Fluxo de Publicação

1. Usuário acessa Pré-agenda (`/pre-agenda`)
2. Se não conectado, vê card vermelho "Conectar conta Google"
3. Ao tentar Publish/Resync, sistema verifica conexão:
   - **Sem conexão**: Bloqueia ação, mostra modal "Conectar agora"
   - **Com conexão**: Enfileira task Celery com `operator_user_id`
4. Task usa cliente OAuth do usuário para publicar evento

### Governança

- **apply_blocked**: Ainda depende de `GCAL_CLIENT='google'`
- **403 Forbidden**: Retornado se usuário não conectado (OAuth mode)
- **202 Accepted**: Retornado se task enfileirada com sucesso

---

## 🔄 Rotação de Chave de Criptografia

### Comando

```bash
# Gerar nova chave
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Rotacionar (OLD_KEY = valor atual de GCAL_ENCRYPTION_KEY)
python manage.py rotate_gcal_encryption_key \
    --old-key="<VALOR_ANTIGO>" \
    --new-key="<NOVO_VALOR_GERADO>"

# Atualizar .env com nova chave
GCAL_ENCRYPTION_KEY="<NOVO_VALOR_GERADO>"

# Restart aplicação
docker compose restart web worker beat
```

### Processo

1. Descriptografa todos os tokens com chave antiga
2. Re-criptografa com chave nova
3. Salva no banco
4. Cria registro de auditoria (AuditLog)
5. Retorna contagem de credenciais atualizadas

---

## 🔒 Segurança

### Chave de Criptografia

- **NUNCA** commitar `GCAL_ENCRYPTION_KEY` no repositório
- Usar secrets management (HashiCorp Vault, AWS Secrets Manager, etc.)
- Rotacionar periodicamente (recomendado: 90 dias)

### OAuth Client Secret

- **NUNCA** commitar `GCAL_OAUTH_CLIENT_SECRET` no repositório
- Usar secrets management
- Restringir acesso apenas a aplicações autorizadas no Google Cloud Console

### Redirect URI

- **HTTPS obrigatório** em produção
- Registrar **exatamente** a URI usada no código (incluindo trailing slash)
- Validar domínio no Google Cloud Console

---

## 📚 Referências

- [Google Calendar API - OAuth 2.0](https://developers.google.com/calendar/api/guides/auth)
- [Fernet (Cryptography)](https://cryptography.io/en/latest/fernet/)
- [fechar_plano_gcal.md](../docs/fechar_plano_gcal.md) - Plano completo OAuth
- [GUIDE_GCAL.md](../docs/GUIDE_GCAL.md) - Guia de configuração GCal
