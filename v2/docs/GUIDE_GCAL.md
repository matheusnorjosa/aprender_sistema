# Guia de Integração Google Calendar + Meet (RF05/RF06 - PR19)

## Visão Geral

Este guia documenta a configuração e uso da integração do **Aprender Sistema v2** com Google Calendar API para:

- ✅ Publicação automática de eventos aprovados no Google Calendar
- ✅ Geração automática de links Google Meet para reuniões online
- ✅ Sincronização idempotente e resiliente (retry/backoff)
- ✅ Suporte a dry-run para testes sem impacto

## 1. Autenticação: Service Account

### Criar Service Account no Google Cloud

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie ou selecione um projeto
3. Ative a **Google Calendar API**:
   - Navegue até "APIs e Serviços" → "Biblioteca"
   - Busque "Google Calendar API"
   - Clique em "Ativar"

4. Crie uma Service Account:
   - "APIs e Serviços" → "Credenciais"
   - "Criar credenciais" → "Conta de serviço"
   - Preencha nome, ID e descrição
   - Clique em "Criar e continuar"
   - (Opcional) Adicione papel "Editor" para testes
   - "Concluído"

5. Gere chave JSON:
   - Clique na Service Account criada
   - Aba "Chaves" → "Adicionar chave" → "Criar nova chave"
   - Tipo: JSON
   - A chave será baixada automaticamente (ex: `aprender-sa-key.json`)

### Compartilhar Calendário com Service Account

1. Abra Google Calendar no navegador
2. Clique em "⚙️" → "Configurações"
3. Na lateral, encontre o calendário que deseja usar
4. Clique em "Compartilhar com pessoas específicas"
5. Adicione o **email da Service Account** (ex: `aprender-sa@projeto.iam.gserviceaccount.com`)
6. Permissão: "Fazer alterações em eventos"
7. Salvar

### Obter Calendar ID

1. Ainda nas configurações do calendário
2. Seção "Integrar calendário"
3. Copie o **ID do calendário** (ex: `primary` ou `abc123@group.calendar.google.com`)

## 2. Variáveis de Ambiente

Adicione as seguintes variáveis ao seu `.env` (local ou em `v2/infra/.env`):

```bash
# ================================================================
# GOOGLE CALENDAR / SHEETS (RF05/RF06)
# ================================================================

# Service Account credentials (escolha UMA das opções):
# Opção 1: Path para arquivo JSON
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/aprender-sa-key.json

# Opção 2: JSON inline (útil para CI/CD)
# GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"..."}'

# Calendar ID (primary ou ID específico)
GCAL_CALENDAR_ID=primary

# Calendar client: 'fake' (in-memory, safe) ou 'google' (real API)
# Default: 'fake' para evitar publicações acidentais
GCAL_CLIENT=fake

# Email notifications to attendees (RF05/RF06)
# Options: 'none' (default), 'all', 'externalOnly'
GCAL_SEND_UPDATES=none
```

### Exemplo para Desenvolvimento

```bash
# .env local (não commitar!)
GCAL_CLIENT=fake
GCAL_SEND_UPDATES=none
GCAL_CALENDAR_ID=primary
# Deixar GOOGLE_SERVICE_ACCOUNT_FILE vazio → usa fake client
```

### Exemplo para Produção

```bash
# .env produção
GCAL_CLIENT=google
GCAL_SEND_UPDATES=externalOnly
GCAL_CALENDAR_ID=abc123@group.calendar.google.com
GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/aprender-prod-sa.json
```

## 3. Configuração apply_blocked vs dry_run

### Conceitos

- **GCAL_CLIENT**: Define qual cliente usar:
  - `fake`: Cliente in-memory (seguro, sem chamadas reais)
  - `google`: Cliente real (chama Google Calendar API)

- **apply_blocked**: Comportamento quando `GCAL_CLIENT != "google"`:
  - Se `false` (default): Bloqueia publicação real com 409
  - Se `true`: Força publicação mesmo com client fake (útil para testes)

- **dry_run**: Modo simulação:
  - Se `true`: Executa lógica mas NÃO persiste no DB nem no Calendar
  - Se `false`: Executa e persiste (publicação real)

### Matriz de Comportamento

| GCAL_CLIENT | apply_blocked | dry_run | Resultado |
|-------------|---------------|---------|-----------|
| `fake` | `false` | `true` | ✅ Executa simulação |
| `fake` | `false` | `false` | ❌ Bloqueado (409) |
| `fake` | `true` | `false` | ✅ Publica (fake client) |
| `google` | `false` | `true` | ✅ Executa simulação |
| `google` | `false` | `false` | ✅ Publica (real) |

### Exemplo: Testar Localmente sem Impacto

```bash
# 1. Configure env
export GCAL_CLIENT=fake
export GCAL_SEND_UPDATES=none

# 2. Preview (sempre permitido)
curl -X POST http://localhost:8000/api/solicitacoes/123/preview-gcal/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Dry-run (simula publicação)
curl -X POST http://localhost:8000/api/solicitacoes/123/publish/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "apply_blocked": false}'

# 4. Publicação real (bloqueada por GCAL_CLIENT=fake)
curl -X POST http://localhost:8000/api/solicitacoes/123/publish/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "apply_blocked": false}'
# → Retorna 409 CONFLICT

# 5. Forçar publicação (teste com fake client)
curl -X POST http://localhost:8000/api/solicitacoes/123/publish/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "apply_blocked": true}'
# → 200/202 OK (usa fake client)
```

## 4. Meet Link Exposto via meet_link

### Fluxo de Criação

1. Solicitação é aprovada
2. API `POST /api/solicitacoes/{id}/publish/` é chamada
3. Payload inclui `conferenceData` com `requestId` único
4. Google Calendar cria evento + gera link Meet
5. Backend extrai `hangoutLink` do response
6. Campo `meet_link` é persistido no banco
7. Serializer expõe `meet_link` na API

### Endpoints Afetados

```bash
# GET detalhe - retorna meet_link
GET /api/solicitacoes/123/
{
  "id": 123,
  "status": "aprovado",
  "meet_link": "https://meet.google.com/abc-defg-hij",
  ...
}

# GET list - retorna meet_link
GET /api/solicitacoes/
{
  "results": [
    {
      "id": 123,
      "meet_link": "https://meet.google.com/abc-defg-hij",
      ...
    }
  ]
}
```

### UI: Botões "Entrar na reunião"

**3 locais exibem meet_link:**

1. **Solicitacoes.jsx** (drawer de detalhes):
   - Campo "Reunião Online" com botão primário
   - Ícone: `<VideoCameraOutlined />`

2. **PreAgendaPage.jsx** (coluna ações):
   - Botão pequeno tipo link na coluna "Ações"
   - Aparece ao lado de Preview/Publicar

3. **MySolicitacoesPage.jsx** (coluna reunião):
   - Coluna dedicada "Reunião"
   - Botão "Entrar" ou "-" se não houver link

## 5. Auto-apply (Celery) desativado por padrão

### Fase 3: Governança Consolidada via /pre-agenda

A partir da **Fase 3**, a publicação automática de eventos no Google Calendar via Celery (task `preview_then_apply_gcal`) está **desativada por padrão**. Isso consolida a governança para que **todas as publicações ocorram exclusivamente via interface /pre-agenda**.

### Variável de Ambiente

```bash
# Auto-apply GCal (Celery task preview_then_apply_gcal)
# Default: 0 (desativado) - governança consolidada via /pre-agenda
# Quando 0: Task retorna status="SKIPPED" sem executar sync
# Quando 1: Celery beat executa preview_then_apply_gcal periodicamente
FEATURE_AUTO_APPLY_ENABLED=0
```

### Comportamento

| FEATURE_AUTO_APPLY_ENABLED | Comportamento |
|----------------------------|---------------|
| `0` (default) | Task Celery retorna `status="SKIPPED"`, registra AuditLog, **não executa sync** |
| `1` | Task Celery executa normalmente (preview → apply se houver mudanças) |

### Endpoint /api/features/

O endpoint `/api/features/` expõe o estado atual da flag:

```bash
curl http://localhost:8000/api/features/ \
  -H "Authorization: Bearer $TOKEN"

{
  "USE_V2_ONLY": true,
  "GCAL_MODE": "fake",
  "PREVIEW_ONLY": true,
  "METRICS_ENABLED": true,
  "SHOW_PRE_AGENDA": true,
  "GCAL_CLIENT": "fake",
  "apply_blocked": true,
  "auto_apply_enabled": false,  # ← Nova flag (Fase 3)
  "ENVIRONMENT": "development",
  "realtime_check_enabled": false
}
```

### Motivação

- **Controle explícito**: Evita publicações automáticas em background sem supervisão
- **Governança única**: Toda criação/atualização de eventos passa por revisão manual em /pre-agenda
- **Auditoria completa**: AuditLog registra tentativas de execução (mesmo quando skipped)
- **Segurança**: Previne sincronizações acidentais em ambientes de desenvolvimento/staging

### Como Ativar Auto-apply (Opcional)

```bash
# 1. Configure a variável de ambiente
export FEATURE_AUTO_APPLY_ENABLED=1

# 2. Rebuild containers (Docker)
docker compose build web
docker compose up -d web

# 3. Verificar via API
curl http://localhost:8000/api/features/ | jq '.auto_apply_enabled'
# → true

# 4. Monitorar logs do Celery Beat
docker compose logs -f celery-beat
# → Task executará a cada 5 minutos (ver CELERY_BEAT_SCHEDULE)
```

⚠️ **Atenção**: Ativar auto-apply requer configuração adequada de `GCAL_CLIENT=google` e credenciais válidas para evitar erros.

## 7. Comandos Úteis

### Preview (GET /preview-gcal/)

```bash
# Preview sempre funciona, independente de GCAL_CLIENT
docker compose exec web python manage.py shell
>>> from apps.core.models import Solicitacao
>>> from apps.core.services.gcal_sync_service import build_preview_for_solicitacao
>>> s = Solicitacao.objects.get(id=123)
>>> preview = build_preview_for_solicitacao(s)
>>> print(preview)
```

### Publish via Management Command

```bash
# Dry-run (simulação)
docker compose exec web python manage.py sync_calendar \
  --solicitacao-id 123 \
  --dry-run

# Publish real (requer GCAL_CLIENT=google)
docker compose exec web python manage.py sync_calendar \
  --solicitacao-id 123
```

### Testes

```bash
# Rodar todos os testes GCal
docker compose exec web pytest apps/core/tests/test_gcal*.py -v

# Testes específicos
pytest apps/core/tests/test_gcal_publish_apply_blocked.py -v
pytest apps/core/tests/test_gcal_retry_backoff.py -v
pytest apps/core/tests/test_gcal_send_updates.py -v
pytest apps/core/tests/test_gcal_conference_version.py -v
pytest apps/core/tests/test_solicitacao_serializer_meet_link.py -v
```

## 8. Troubleshooting

### Erro: "GCAL_CLIENT não configurado"

**Sintoma:** 409 CONFLICT em `/publish/`

**Causa:** `GCAL_CLIENT=fake` e `apply_blocked=false`

**Solução:**
- Para testes: `apply_blocked=true` no payload
- Para produção: `GCAL_CLIENT=google` no .env

### Erro: "Service Account credentials not found"

**Sintoma:** Exception ao inicializar GoogleCalendarClient

**Causa:** `GOOGLE_SERVICE_ACCOUNT_FILE` ou `GOOGLE_SERVICE_ACCOUNT_JSON` não definidos

**Solução:**
```bash
# Opção 1: Path para arquivo
export GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/key.json

# Opção 2: JSON inline
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
```

### Erro: "403 Forbidden" na Google Calendar API

**Causa:** Service Account não tem permissão no calendário

**Solução:**
1. Abra Google Calendar
2. Compartilhe calendário com email da SA
3. Permissão: "Fazer alterações em eventos"

### meet_link não está sendo gerado

**Checklist:**
- ✅ `conferenceDataVersion=1` está sendo passado? (ver `gcal_google_client.py`)
- ✅ Payload inclui `conferenceData`? (ver `_build_payload` com `enable_meet=True`)
- ✅ Response do Google inclui `hangoutLink`? (verificar logs)
- ✅ `s.meet_link` está sendo persistido? (ver `upsert_one` linhas 748-750)

**Debug:**
```python
# Verificar payload
from apps.core.services.gcal_sync_service import build_event_payload
payload = build_event_payload(s, enable_meet=True)
print(payload['conferenceData'])  # Deve existir

# Verificar response
# Adicionar logging em gcal_google_client.py:
logger.info(f"GCal response: {result}")
```

## 9. Referências

- [Google Calendar API - Events.insert](https://developers.google.com/calendar/api/v3/reference/events/insert)
- [Google Calendar API - Conference Data](https://developers.google.com/calendar/api/v3/reference/events#conferenceData)
- [Service Account Authentication](https://developers.google.com/identity/protocols/oauth2/service-account)
- [GCAL_SEND_UPDATES.md](../backend/GCAL_SEND_UPDATES.md)

## 10. Histórico

- **PR19** (RF05/RF06): Implementação inicial
- **2025-10-23**: Guia criado
- **Fase 3** (2025-10-28): Auto-apply Celery desativado por padrão (FEATURE_AUTO_APPLY_ENABLED=0), governança consolidada via /pre-agenda
