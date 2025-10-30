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
2. API `POST /api/solicitacoes/{id}/publish/` é chamada com `dry_run=false` e `apply_blocked=false` (ou `GCAL_CLIENT=google`)
3. Payload inclui `conferenceData` com `requestId` único
4. Google Calendar cria evento + gera link Meet
5. Backend extrai `hangoutLink` do response
6. Campo `meet_link` é **persistido no banco APENAS em APPLY real**
7. Serializer expõe `meet_link` na API

**⚠️ IMPORTANTE - Quando meet_link NÃO é persistido:**
- **PREVIEW** (`/preview-gcal/`): Retorna meet_link no payload mas NÃO persiste no DB
- **apply_blocked (409)**: Quando `GCAL_CLIENT != "google"` e `apply_blocked=false`, retorna 409 e NÃO persiste
- **dry_run=true**: Simula publicação mas NÃO persiste

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

### UI: Componente MeetLink

**Componente Reutilizável** (`frontend/src/components/MeetLink.jsx`):
- Props: `href` (string | null | undefined)
- Retorna `null` se href não existir
- Renderiza dois botões:
  1. **"Entrar na reunião"** (primário, abre em nova aba)
  2. **"Copiar link"** (copia para clipboard com feedback)

**3 locais integrados:**

1. **Solicitacoes.jsx** (drawer de detalhes):
   - Campo "Reunião Online" com `<MeetLink href={selectedSolicitacao.meet_link} />`
   - Exibido apenas se meet_link existir

2. **PreAgendaPage.jsx** (coluna ações):
   - `<MeetLink href={record.meet_link} />` na coluna "Ações"
   - Aparece ao lado de Preview/Publicar

3. **MySolicitacoesPage.jsx** (coluna reunião):
   - Coluna dedicada "Reunião"
   - `<MeetLink href={meet_link} />` (retorna null se vazio)

## 4.5. Modalidade (Online x Presencial)

### Visão Geral

O campo `is_online` determina a modalidade do evento:
- **`is_online=false` (padrão)**: Evento presencial, **sem conferenceData**, sem Meet link
- **`is_online=true`**: Evento online, **com conferenceData**, gera Meet link automaticamente

### Modelo e Migration

**Campo**:
```python
# v2/backend/apps/core/models.py (linha 86)
is_online = models.BooleanField(
    default=False,
    verbose_name='Evento Online?',
    help_text='Se True, gera Google Meet link no APPLY (RF06). Se False, evento presencial sem conferenceData.'
)
```

**Migration**: `0023_add_is_online.py`

### Payload Google Calendar

#### Evento Presencial (`is_online=false`)
```json
{
  "summary": "Evento Teste",
  "start": {"dateTime": "2025-10-28T10:00:00-03:00"},
  "end": {"dateTime": "2025-10-28T12:00:00-03:00"},
  "description": "...",
  "attendees": [...]
  // SEM conferenceData
}
```

#### Evento Online (`is_online=true`)
```json
{
  "summary": "Evento Teste",
  "start": {"dateTime": "2025-10-28T10:00:00-03:00"},
  "end": {"dateTime": "2025-10-28T12:00:00-03:00"},
  "description": "...",
  "attendees": [...],
  "conferenceData": {
    "createRequest": {
      "requestId": "asv2-123-1730123456",
      "conferenceSolutionKey": {"type": "hangoutsMeet"}
    }
  }
}
```

**Nota**: `conferenceDataVersion=1` deve ser passado no parâmetro de query da API para criar Meet links.

### UI: Checkbox no Wizard

**Localização**: `v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.jsx` (linhas 358-365)

```jsx
<Form.Item name="is_online" valuePropName="checked">
  <Checkbox
    checked={formData.is_online}
    onChange={(e) => setFormData({ ...formData, is_online: e.target.checked })}
  >
    Evento online (Google Meet)
  </Checkbox>
</Form.Item>

<Alert
  message="Modalidade do evento"
  description={
    formData.is_online
      ? 'Link do Google Meet será gerado automaticamente após publicação do evento no calendário.'
      : 'Evento presencial — nenhum link de reunião será gerado.'
  }
  type={formData.is_online ? 'info' : 'warning'}
  showIcon
/>
```

### Comportamento no Backend

**Payload Building** (`gcal_sync_service.py`):
```python
def build_event_payload(solicitacao, enable_meet=True):
    payload = {
        "summary": "...",
        "start": {...},
        "end": {...},
        # ...
    }

    # Adiciona conferenceData apenas se is_online=True
    if enable_meet and solicitacao.is_online:
        payload["conferenceData"] = {
            "createRequest": {
                "requestId": f"asv2-{solicitacao.id}-{int(datetime.now().timestamp())}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"}
            }
        }

    return payload
```

**Persistência do Meet Link**:
- Apenas eventos com `is_online=True` + APPLY real persistem `meet_link`
- Eventos presenciais (`is_online=False`) nunca geram/persistem `meet_link`

### Testes

**Cobertura** (`v2/backend/apps/core/tests/test_gcal_conference_version.py`):
- Testa que `conferenceDataVersion=1` é obrigatório
- Valida que payload com `is_online=true` inclui `conferenceData`
- Valida que payload com `is_online=false` **não** inclui `conferenceData`

## 4.6. Resync/Cancel (Fase 4)

### Visão Geral

A **Fase 4** implementa funcionalidades para **reenviar (resync)** e **cancelar** eventos já publicados no Google Calendar, permitindo correções e manutenção do calendário diretamente pelo sistema.

**Casos de uso:**
- **Resync**: Corrigir dados de um evento já publicado (ex: horário alterado, descrição atualizada)
- **Cancel**: Remover permanentemente um evento do Calendar quando cancelado/reprovado

### Endpoints

#### POST /api/solicitacoes/{id}/resync-gcal/

**Descrição**: Republicar solicitação no Google Calendar (força UPDATE)

**Permissão**: `IsControleOrSuper`

**Fluxo**:
1. Valida `status == 'aprovado'`
2. Reseta `gcal_payload_hash = None` (força UPDATE mesmo se já publicado)
3. Marca `gcal_status = PENDING`
4. Enfileira `task_publish_solicitacao_to_gcal.delay(id)`
5. Retorna **202 Accepted** com `task_id`

**AuditLog**: Action `RESYNC_GCAL_REQUESTED`

**Exemplo**:
```bash
curl -X POST http://localhost:8002/api/solicitacoes/123/resync-gcal/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "detail": "Resincronização solicitada com sucesso (processando em background).",
  "task_id": "abc-123-def",
  "solicitacao_id": 123
}
```

#### POST /api/solicitacoes/{id}/cancel-gcal/

**Descrição**: Cancelar evento no Google Calendar e limpar campos

**Permissão**: `IsControleOrSuper`

**Fluxo**:
1. Valida que evento foi publicado (`external_event_id` existe ou `gcal_status == PUBLISHED`)
2. Marca `gcal_status = PENDING` temporariamente
3. Enfileira `task_cancel_solicitacao_from_gcal.delay(id)`
4. Task deleta evento do Calendar (trata 404 como sucesso - idempotência)
5. Limpa campos: `external_event_id`, `meet_link`, `gcal_payload_hash`
6. Marca `gcal_status = NONE`, `last_sync_action = DELETE`

**AuditLog**: Actions `CANCEL_GCAL_REQUESTED` (endpoint) e `CANCEL_GCAL` (task)

**Retornos**:
- **202 Accepted**: Cancelamento enfileirado com sucesso
- **409 Conflict**: Evento não foi publicado (não pode cancelar)

**Exemplo**:
```bash
curl -X POST http://localhost:8002/api/solicitacoes/123/cancel-gcal/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response**:
```json
{
  "detail": "Cancelamento solicitado com sucesso (processando em background).",
  "task_id": "xyz-789-ghi",
  "solicitacao_id": 123
}
```

### Helpers (Service Layer)

**Arquivo**: `v2/backend/apps/core/services/gcal_sync_service.py`

#### resync_solicitacao(s, *, apply_blocked=False)

```python
from apps.core.services.gcal_sync_service import resync_solicitacao

# Republicar solicitação aprovada
outcome = resync_solicitacao(solicitacao, apply_blocked=False)
# outcome.action == "UPDATE"
# outcome.external_event_id == "asv2-123"
```

**Comportamento**:
- Reseta `gcal_payload_hash = None` para forçar UPDATE
- Reutiliza `apply_one_solicitacao()` para lógica de sincronização
- Raises `ValueError` se `status != 'aprovado'`

#### cancel_solicitacao(s)

```python
from apps.core.services.gcal_sync_service import cancel_solicitacao

# Cancelar evento publicado
outcome = cancel_solicitacao(solicitacao)
# outcome.action == "DELETE"
# outcome.external_event_id == None (limpo)
```

**Comportamento**:
- Deleta evento do Calendar via `client.delete(calendar_id, event_id)`
- Trata **404 como sucesso** (idempotência)
- Limpa **todos** os campos GCal: `external_event_id`, `meet_link`, `gcal_payload_hash`
- Marca `gcal_status = NONE`, `last_sync_action = DELETE`
- Raises `ValueError` se evento não foi publicado

### UI: Botões em PreAgendaPage

**Arquivo**: `v2/frontend/src/pages/PreAgenda/PreAgendaPage.jsx`

**Botões condicionais** na coluna "Ações":

1. **Botão "Reenviar"** (ícone: `SyncOutlined`, cor: laranja)
   - **Visível quando**: `gcal_status === 'PUBLISHED' || gcal_status === 'ERROR'`
   - **Modal.confirm**: Warning (okType: 'warning')
   - **Ação**: Chama `resyncSolicitacao(id)` → message.success → reload

2. **Botão "Cancelar"** (ícone: `StopOutlined`, cor: vermelho)
   - **Visível quando**: `gcal_status === 'PUBLISHED' && external_event_id`
   - **Modal.confirm**: Danger (okType: 'danger')
   - **Ação**: Chama `cancelSolicitacao(id)` → message.success → reload

**Exemplo de uso**:
```jsx
{showResync && (
  <Button
    size="small"
    type="default"
    icon={<SyncOutlined />}
    onClick={() => handleResync(record.id)}
    title="Reenviar (forçar UPDATE)"
    style={{ color: '#faad14', borderColor: '#faad14' }}
  />
)}

{showCancel && (
  <Button
    size="small"
    danger
    icon={<StopOutlined />}
    onClick={() => handleCancel(record.id)}
    title="Cancelar evento no Calendar"
  />
)}
```

### Testes

**Cobertura** (`v2/backend/apps/core/tests/test_gcal_cancel_resync.py`):

**13 testes totais**:
- **3 testes helpers**:
  - `test_resync_requires_approved_status`: ValueError se `status != 'aprovado'`
  - `test_resync_resets_hash_and_calls_apply`: Valida reset de hash e chamada de `apply_one`
  - `test_cancel_validates_published`: ValueError se não publicado
  - `test_cancel_deletes_and_clears_fields`: Valida delete + limpeza de campos

- **2 testes task**:
  - `test_task_cancel_success`: Sucesso com AuditLog
  - `test_task_cancel_not_found`: DoesNotExist tratado

- **7 testes endpoints**:
  - `test_resync_endpoint_requires_approved`: 400 se não aprovado
  - `test_resync_endpoint_success`: 202 + task_id + AuditLog
  - `test_resync_endpoint_requires_permission`: 403 para não-autorizados
  - `test_cancel_endpoint_requires_published`: 409 se não publicado
  - `test_cancel_endpoint_success`: 202 + task_id + AuditLog
  - `test_cancel_endpoint_requires_permission`: 403 para não-autorizados
  - `test_cancel_endpoint_idempotent_404`: 404 tratado como sucesso

**Rodar testes**:
```bash
cd v2/infra
docker compose exec -T web pytest apps/core/tests/test_gcal_cancel_resync.py -v
# ========================= 13 passed in 10.00s =========================
```

### Idempotência

**Cancel é idempotente**: Se o evento já foi deletado do Calendar (404), a operação é tratada como sucesso. Isso permite múltiplas tentativas sem erro.

**Implementação** (`cancel_solicitacao` linha ~1015):
```python
try:
    _retry_with_backoff(
        lambda: client.delete(calendar_id, event_id),
        operation_name=f"GCal CANCEL #{s.id}",
    )
except Exception as e:
    # 404 = já foi deletado (idempotência OK)
    if "404" not in str(e):
        raise
```

## 5. Comandos Úteis

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
pytest apps/core/tests/test_gcal_meet_link_persist.py -v  # RF06: meet_link persistence
pytest apps/core/tests/test_solicitacao_serializer_meet_link.py -v
```

## 6. Troubleshooting

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

## 7. Referências

- [Google Calendar API - Events.insert](https://developers.google.com/calendar/api/v3/reference/events/insert)
- [Google Calendar API - Conference Data](https://developers.google.com/calendar/api/v3/reference/events#conferenceData)
- [Service Account Authentication](https://developers.google.com/identity/protocols/oauth2/service-account)
- [GCAL_SEND_UPDATES.md](../backend/GCAL_SEND_UPDATES.md)

## 8. Histórico

- **PR19** (RF05/RF06): Implementação inicial (GCal + Meet integration)
- **2025-10-23**: Guia criado
- **2025-10-28**: Adicionado componente MeetLink reutilizável e testes de persistência
- **2025-10-30**: Fase 4 completa (Resync/Cancel) - 13 testes backend, endpoints DRF, UI PreAgenda
