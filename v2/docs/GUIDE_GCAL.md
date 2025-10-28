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

## 5. Publicação em Massa via Pré-agenda

### Visão Geral

A funcionalidade de publicação em massa permite que usuários com perfil **Controle** ou **Superintendência** publiquem múltiplas solicitações aprovadas no Google Calendar de uma só vez, através da página `/pre-agenda`.

### Endpoint: POST /api/gcal/publish-batch/

#### Request

```bash
POST /api/gcal/publish-batch/
Authorization: Bearer <token>
Content-Type: application/json

{
  "solicitacao_ids": [123, 456, 789],  # Array de IDs (obrigatório)
  "dry_run": false,                     # Simulação? (opcional, default: false)
  "apply_blocked": false                # Forçar com fake client? (opcional, default: false)
}
```

#### Response 202 Accepted

```json
{
  "queued": 2,                          // Quantidade enfileirada com sucesso
  "errors": [                           // Lista de erros (um por ID que falhou)
    {
      "id": 789,
      "detail": "Status deve ser 'aprovado' (atual: pendente)"
    }
  ],
  "dry_run": false,
  "apply_blocked": false
}
```

#### Regras de Validação

1. **Array de IDs obrigatório**: `solicitacao_ids` deve ser um array não-vazio
2. **Status aprovado**: Apenas solicitações com `status='aprovado'` são processadas
3. **GCAL_CLIENT validation**:
   - Se `GCAL_CLIENT != "google"` AND `dry_run=false` AND `apply_blocked=false` → erro
   - Para testes com fake client: usar `apply_blocked=true`
4. **RBAC**: Apenas usuários dos grupos **Controle** ou **Superintendência** podem chamar

#### Comportamento

Para cada ID na lista:

1. **Busca a solicitação** no banco
2. **Valida status='aprovado'**
3. **Valida GCAL_CLIENT** (ou `apply_blocked=true`)
4. Se válida:
   - Marca `gcal_status=PENDING`
   - Enfileira task Celery `task_publish_solicitacao_to_gcal`
   - Adiciona ID ao array `queued`
5. Se inválida:
   - Adiciona objeto `{id, detail}` ao array `errors`

### UI: Pré-agenda com Multi-select

**Localização**: `/pre-agenda` (menu lateral → "Pré-agenda")

**Features**:

1. **Checkboxes na tabela**: Permite selecionar múltiplas linhas
   - Eventos com `gcal_status='PUBLISHED'` ficam desabilitados (não podem ser republicados)

2. **Botão "Publicar Selecionados (N)"**: Aparece no topo da tabela quando N > 0
   - Abre modal de confirmação
   - Mostra quantidade selecionada
   - Se `GCAL_CLIENT != "google"`: exibe aviso sobre modo fake

3. **Modal de Resultado**: Após publicação, exibe:
   - ✅ Contador de eventos enfileirados (verde)
   - ⚠️ Lista de erros (se houver), com ID e mensagem detalhada

4. **Auto-reload**: Tabela recarrega após publicação para atualizar `gcal_status`

### Exemplo de Uso

#### Cenário 1: Publicação bem-sucedida (todos aprovados)

```bash
# Request
POST /api/gcal/publish-batch/
{
  "solicitacao_ids": [101, 102, 103],
  "dry_run": false,
  "apply_blocked": false
}

# Response 202
{
  "queued": 3,
  "errors": [],
  "dry_run": false,
  "apply_blocked": false
}
```

**UI exibe**: "3 evento(s) enfileirado(s) para publicação!" (success message)

#### Cenário 2: Misto de aprovados e pendentes

```bash
# Request
POST /api/gcal/publish-batch/
{
  "solicitacao_ids": [101, 102, 999],  # 999 está pendente
  "dry_run": false,
  "apply_blocked": false
}

# Response 202
{
  "queued": 2,
  "errors": [
    {
      "id": 999,
      "detail": "Status deve ser 'aprovado' (atual: pendente)"
    }
  ],
  "dry_run": false,
  "apply_blocked": false
}
```

**UI exibe**: "2 enfileirado(s), 1 erro(s)" (warning message) + modal com lista de erros

#### Cenário 3: GCAL_CLIENT=fake sem apply_blocked

```bash
# Ambiente: GCAL_CLIENT=fake
POST /api/gcal/publish-batch/
{
  "solicitacao_ids": [101],
  "dry_run": false,
  "apply_blocked": false  # ❌ Não permitido com fake client
}

# Response 202
{
  "queued": 0,
  "errors": [
    {
      "id": 101,
      "detail": "GCAL_CLIENT=fake (não-google) requer dry_run=true ou apply_blocked=true"
    }
  ],
  "dry_run": false,
  "apply_blocked": false
}
```

**Solução**: Usar `apply_blocked=true` para testes com fake client:

```bash
POST /api/gcal/publish-batch/
{
  "solicitacao_ids": [101],
  "dry_run": false,
  "apply_blocked": true  # ✅ Permite publicação com fake client
}

# Response 202
{
  "queued": 1,
  "errors": [],
  "dry_run": false,
  "apply_blocked": true
}
```

### Testes Backend

```bash
# Rodar todos os testes de batch publish
docker compose exec web pytest apps/core/tests/test_gcal_publish_batch.py -v

# 8 cenários cobertos:
# 1. test_batch_publish_aprovados_sucesso - Todos aprovados → queued=N
# 2. test_batch_publish_mistura_aprovado_pendente - Misto → errors para pendentes
# 3. test_batch_publish_requer_apply_blocked_quando_fake - GCAL_CLIENT validation
# 4. test_batch_publish_com_apply_blocked_true - Forçar com fake client
# 5. test_batch_publish_rbac_403_sem_permissao - RBAC enforcement
# 6. test_batch_publish_array_vazio - Validação array vazio → 400
# 7. test_batch_publish_dry_run_nao_persiste - Dry-run não persiste
# 8. test_batch_publish_id_inexistente - IDs não encontrados → errors
```

### Monitoramento

**Logs Celery** (worker):

```bash
docker compose logs -f worker --tail=50
```

Busque por:
- `Batch publish queued: solicitacao_id=123, dry_run=false`
- `Batch publish dry-run: solicitacao_id=123`

**Banco de Dados**:

```sql
-- Ver solicitações em fila (PENDING)
SELECT id, inicio, municipio_id, gcal_status, updated_at
FROM core_solicitacao
WHERE gcal_status = 'PENDING'
ORDER BY updated_at DESC;

-- Ver publicações recentes
SELECT id, inicio, municipio_id, gcal_status, external_event_id, meet_link
FROM core_solicitacao
WHERE gcal_status = 'PUBLISHED'
  AND updated_at > NOW() - INTERVAL '1 hour'
ORDER BY updated_at DESC;
```

## 6. Auto-apply (Celery) desativado por padrão

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

- **PR19** (RF05/RF06): Implementação inicial de integração Google Calendar + Meet
- **2025-10-23**: Guia criado
<<<<<<< HEAD
- **Fase 3** (2025-10-28): Auto-apply Celery desativado por padrão (FEATURE_AUTO_APPLY_ENABLED=0), governança consolidada via /pre-agenda
=======
- **feat/preagenda-bulk-publish** (Fase 2): Publicação em massa via `/pre-agenda`
  - Endpoint POST `/api/gcal/publish-batch/`
  - UI com multi-select e botão "Publicar Selecionados"
  - 8 testes backend cobrindo validações e RBAC
>>>>>>> origin/main
