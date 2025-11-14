# 🚀 Quick Start - Batch Operations (Issue #95)

## ✅ O que foi feito?

**PR #102 - MERGED**: Implementação completa de ações em massa (reapply/resync) para eventos do Google Calendar.

---

## 📦 Funcionalidades

### Backend
- ✅ `POST /api/gcal/dashboard/batch/reapply/` - Reaplica eventos (força UPDATE)
- ✅ `POST /api/gcal/dashboard/batch/resync/` - Resync completo (reseta hash + PENDING)
- ✅ OAuth mode: valida credenciais e propaga `operator_user_id`
- ✅ RBAC: Apenas Controle/Superintendência
- ✅ 12 testes automatizados (100% passing)

### Frontend
- ✅ Seleção múltipla de eventos (checkboxes)
- ✅ Toolbar com botões "Reapply" e "Resync"
- ✅ OAuth guards (CTA "Conectar Google")
- ✅ Feedback detalhado (sucesso/erros por ID)

---

## 🎯 Como Usar (Depois de configurar OAuth)

### 1. Acessar Pré-Agenda
```
http://localhost:5173/pre-agenda
```

### 2. Conectar Google (primeira vez)
- Clicar botão **"Conectar conta Google"** no card azul
- Autorizar acesso ao Google Calendar
- Será redirecionado de volta com `?google=connected`

### 3. Selecionar Eventos
- Marcar checkboxes de 2+ eventos aprovados
- Toolbar aparece automaticamente com contador

### 4. Executar Ação em Massa

**Reapply** (força UPDATE sem resetar hash):
```
Botão laranja "Reapply Selecionados"
→ Confirmar modal
→ Mensagem: "{N} eventos enfileirados para reapply!"
```

**Resync** (reseta hash + marca PENDING):
```
Botão vermelho "Resync Selecionados"
→ Confirmar modal (aviso: reseta hash)
→ Mensagem: "{N} eventos enfileirados para resync!"
```

---

## ⚙️ Configuração OAuth (Primeira Vez)

### Passo 1: Gerar Encryption Key
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copiar output: puo0c1u0EJLTGI-fMntHGIjPM1LPjd2Qf_SjFCUXAPc=
```

### Passo 2: Obter Credenciais Google
1. Acessar: https://console.cloud.google.com/
2. **APIs & Services** → **Credentials**
3. **+ CREATE CREDENTIALS** → **OAuth client ID**
4. Type: **Web application**
5. **Authorized redirect URIs**: `http://localhost:8002/api/oauth/google/callback/`
6. Copiar **Client ID** e **Client secret**

### Passo 3: Adicionar ao .env
Editar `v2/infra/.env`:
```bash
GCAL_OAUTH_CLIENT_ID=<Client ID copiado>
GCAL_OAUTH_CLIENT_SECRET=<Client Secret copiado>
GCAL_OAUTH_REDIRECT_URI=http://localhost:8002/api/oauth/google/callback/
GCAL_ENCRYPTION_KEY=puo0c1u0EJLTGI-fMntHGIjPM1LPjd2Qf_SjFCUXAPc=
GCAL_AUTH_MODE=oauth
```

### Passo 4: Validar e Reiniciar
```bash
cd v2/infra

# Validar configuração
python validate_oauth_config.py

# Reiniciar containers
docker compose restart web worker beat

# Verificar logs
docker compose logs -f web | grep -i oauth
```

---

## 🧪 Testar

### Backend
```bash
cd v2/infra
docker compose exec -T web pytest apps/core/tests/test_gcal_batch_operations.py -v
# Esperado: 12 passed ✅
```

### Frontend
```bash
cd v2/frontend
npm run lint && npm run build
# Esperado: 0 errors ✅
```

### Manual
1. Acessar `/pre-agenda`
2. Conectar Google (primeira vez)
3. Selecionar 2-3 eventos
4. Clicar "Reapply Selecionados"
5. Verificar mensagem de sucesso

---

## 📚 Documentação Completa

| Arquivo | Descrição |
|---------|-----------|
| **`OAUTH_SETUP_GUIDE.md`** | Guia completo OAuth (300+ linhas) |
| **`v2/infra/validate_oauth_config.py`** | Script de validação |
| **`v2/infra/.env.oauth.template`** | Template de variáveis |
| **`SUMMARY_ISSUE95_COMPLETE.md`** | Resumo completo da implementação |

---

## ❓ Troubleshooting

### "redirect_uri_mismatch"
**Solução**: Verificar se `GCAL_OAUTH_REDIRECT_URI` no `.env` está registrado no Google Cloud Console.

### "Invalid encryption key"
**Solução**: Gerar nova chave com `Fernet.generate_key()`.

### "google_not_connected" (403)
**Solução**: Clicar "Conectar conta Google" e completar consent flow.

### Botões não aparecem
**Solução**: Verificar permissões (apenas Controle/Superintendência).

---

## 🔗 Links Úteis

- **PR #102**: https://github.com/matheusnorjosa/aprender_sistema/pull/102
- **Issue #95**: https://github.com/matheusnorjosa/aprender_sistema/issues/95
- **Google Cloud Console**: https://console.cloud.google.com/

---

## 📞 Comandos Úteis

```bash
# Ver status OAuth do usuário
curl -X GET http://localhost:8002/api/integrations/google/status/ \
  -H "Cookie: sessionid=<seu-session-id>"

# Limpar credenciais OAuth (reset)
docker compose exec web python manage.py shell -c "
from apps.core.models import GoogleOAuthCredential
GoogleOAuthCredential.objects.filter(user__username='seu_usuario').delete()
"

# Ver logs OAuth
docker compose logs -f web | grep -i oauth

# Gerar nova encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

**Pronto! Batch operations funcionais após configurar OAuth.** 🚀
