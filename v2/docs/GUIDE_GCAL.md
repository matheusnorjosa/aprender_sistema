# Guia de Integração Google Calendar + Meet (RF05/RF06 - PR19)

## Visão Geral

Este guia documenta a configuração e uso da integração do **Aprender Sistema v2** com Google Calendar API para:

- ✅ Publicação automática de eventos aprovados no Google Calendar
- ✅ Geração automática de links Google Meet para reuniões online
- ✅ Sincronização idempotente e resiliente (retry/backoff)
- ✅ Suporte a dry-run para testes sem impacto

> 🔴 **Leia antes de configurar (revisto 2026-07-24).**
> **Produção roda em modo OAuth, não Service Account.** Configuração confirmada em produção:
> `GCAL_AUTH_MODE=oauth`, `GCAL_CLIENT=google` (cliente real, **não** stub),
> `GCAL_ALLOWED_DOMAIN=aprendereditora.com.br`, com `GCAL_OAUTH_CLIENT_ID`,
> `GCAL_OAUTH_CLIENT_SECRET`, `GCAL_OAUTH_REDIRECT_URI` e `GCAL_ENCRYPTION_KEY` preenchidos.
> **`GCAL_SERVICE_ACCOUNT_JSON` não existe em produção.**
>
> Consequência para quem lê este guia:
> - A **§1 (Service Account)** abaixo é o caminho **legado/alternativo**. Não use como referência
>   para produção.
> - O caminho de produção é a **§2 (OAuth)**.
> - O bloco "Exemplo para Produção" da §3 aponta para Service Account e **está errado para o
>   ambiente atual** — há um aviso no local.
> - `service_account` continua sendo o default **no código** (`GCAL_AUTH_MODE` em `config/settings.py`), o que
>   torna fácil configurar um ambiente novo no modo errado. Sempre defina `GCAL_AUTH_MODE`
>   explicitamente.
>
> Fonte dos fatos de ambiente: [audits/ACHADOS_REAIS.md](./audits/ACHADOS_REAIS.md), premissa F4.

## 1. Autenticação: Service Account (legado / alternativo)

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

### Modo OAuth — **o modo usado em produção**

O sistema suporta dois modos de autenticação com o Google Calendar, selecionados por `GCAL_AUTH_MODE`:

| Modo | Variável | Credenciais | Uso |
|------|----------|-------------|-----|
| **OAuth** — ✅ **produção** | `GCAL_AUTH_MODE=oauth` | Credenciais OAuth 2.0 por usuário, cifradas em `GoogleOAuthCredential` | Cada usuário conecta sua conta Google |
| Service Account — legado | `GCAL_AUTH_MODE=service_account` (**default do código**, `config/settings.py`) | `GOOGLE_SERVICE_ACCOUNT_JSON` | Autenticação servidor-a-servidor |

> ⚠️ `service_account` ser o **default do código** não significa que seja o modo em uso.
> Em produção `GCAL_AUTH_MODE=oauth` está definido explicitamente e
> `GCAL_SERVICE_ACCOUNT_JSON` não existe. **Sempre defina `GCAL_AUTH_MODE` explicitamente**
> em ambientes novos, ou eles cairão no caminho errado em silêncio.
>
> ⚠️ Apenas `GOOGLE_SERVICE_ACCOUNT_JSON` é lido por `config/settings.py`.
> `GOOGLE_SERVICE_ACCOUNT_FILE` **não** passa pelo settings — é lido direto via `os.getenv`
> em `apps/core/services/gcal_google_client.py`.

> Em ambos os modos, `GCAL_CLIENT=google` é obrigatório para chamar a API real. A variável de modo é `GCAL_AUTH_MODE` (**não** `GCAL_CLIENT_MODE`).

#### Variáveis de ambiente do modo OAuth

```bash
# Cliente real + modo OAuth
GCAL_CLIENT=google
GCAL_AUTH_MODE=oauth

# Credenciais OAuth 2.0 (Google Cloud Console)
GCAL_OAUTH_CLIENT_ID=<oauth-client-id>
GCAL_OAUTH_CLIENT_SECRET=<oauth-client-secret>
GCAL_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/oauth/google/callback/

# Chave Fernet para criptografar tokens OAuth (ver seção 8 — SEC-011)
GCAL_ENCRYPTION_KEY=<fernet-key-base64>

# Calendário da ORGANIZAÇÃO onde toda escrita OAuth acontece (id do "Formações", c_…@group.calendar.google.com)
GCAL_OAUTH_CALENDAR_ID=<id-do-calendario-da-organizacao>

# Service account / comando preagenda_to_gcal / auto-apply (não vale para o modo OAuth)
GCAL_CALENDAR_ID=primary
```

> Esses vars OAuth são lidos via `os.getenv` em `apps/core/services/oauth/oauth_flow.py`, `services/oauth/token_manager.py` e `services/gcal_oauth_client.py` (não ficam em `settings.py`). Ausência de `GCAL_OAUTH_CLIENT_ID`/`GCAL_OAUTH_REDIRECT_URI` levanta `ValueError`. Exceção: `GCAL_OAUTH_CALENDAR_ID` fica em `settings.py`.

#### Calendário de publicação (OAuth)

Toda escrita OAuth — publicar, resincronizar e cancelar, por qualquer operador — vai para **um** calendário, resolvido no servidor (`resolve_publish_calendar_id`):

1. `GCAL_OAUTH_CALENDAR_ID` (o pino da organização), se definido;
2. senão, o calendário **escolhido** na credencial de quem age (`default_calendar_id`) — só para quem tem `use_gcal`; a Apoio de Coordenação publica apenas no pino (#1656);
3. senão, **nada**: o request responde `409 {"code": "google_calendar_not_configured"}` antes de marcar PENDING — nunca o calendário pessoal da conta.

Por que o pino vale para todos: sem ele, o calendário era re-derivado de quem age, e um resync feito por outro operador criava um evento duplicado no calendário dele, enquanto o cancel "dava certo" (404 = sucesso) e deixava o evento órfão no calendário da organização. Com o pino, todos miram o mesmo calendário do evento.

O cancel também confere, antes de apagar, se a conta enxerga o calendário (`calendar_accessible`). Sem acesso, ele não apaga às cegas: a linha vira ERROR, mantém `external_event_id` e pode ser repetida depois que o calendário for compartilhado.

> ⚠️ **Não troque o pino com eventos PUBLISHED.** Resync e cancel desses eventos passariam a mirar o calendário novo (duplicados e órfãos). Para trocar: cancele os eventos publicados, troque `GCAL_OAUTH_CALENDAR_ID` e publique de novo.

#### Comportamento do modo OAuth

- **Pré-requisito**: quem publica conecta a PRÓPRIA conta Google via `GET /api/oauth/google/start/` (callback em `/api/oauth/google/callback/`): Controle e Superintendência (`use_gcal`) e a Apoio de Coordenação com setor vigente (`publish_setor_solicitacao`, #1656). A Apoio não escolhe calendário: publica no da organização (`GCAL_OAUTH_CALENDAR_ID`), então a conta conectada precisa do compartilhamento «Fazer alterações nos eventos» nesse calendário.
- **Fluxo de publicação**: ao publicar/resync na Pré-agenda, o sistema verifica a conexão. Sem conexão retorna **403 Forbidden** (UI mostra card/modal "Conectar conta Google"); com conexão enfileira a task Celery com `operator_user_id` e retorna **202 Accepted**.
- **Governança**: `apply_blocked` continua dependendo de `GCAL_CLIENT='google'`.
- **Verificação diária das contas** (#2039): às 05:00 o job `probe_google_credentials` força o refresh de cada credencial. Conta que o Google recusa (`invalid_grant`) é removida e a pessoa vê o aviso de reconectar; o Controle vê a lista no resumo de alertas do GCal. Erro de rede ou 5xx não remove nada. Ver §6, "Conta Google desconectada pelo sistema".

Tokens OAuth são criptografados em repouso (ver seção 8 — SEC-011, `GCAL_ENCRYPTION_KEY`).

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

> 🔴 Corrigido em 2026-07-24. O exemplo anterior usava
> `GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/aprender-prod-sa.json` — **não é a configuração de
> produção**, e a variável nem é lida pelo `settings.py`.

```bash
# .env produção — modo OAuth (o que roda hoje)
GCAL_CLIENT=google
GCAL_AUTH_MODE=oauth
GCAL_SEND_UPDATES=externalOnly
GCAL_ALLOWED_DOMAIN=aprendereditora.com.br
GCAL_CALENDAR_ID=primary

GCAL_OAUTH_CLIENT_ID=<oauth-client-id>
GCAL_OAUTH_CLIENT_SECRET=<oauth-client-secret>
GCAL_OAUTH_REDIRECT_URI=https://seu-dominio.com/api/oauth/google/callback/
GCAL_ENCRYPTION_KEY=<fernet-key-base64>          # obrigatório em prod — ver §8 (SEC-011)
```

Os segredos reais vivem no Portainer, não no repositório.

### Validação fail-fast (boot)

Na inicialização do Django (`config/settings.py`), o valor de `GCAL_SEND_UPDATES` é validado contra a allowlist `{none, all, externalOnly}`. Valor inválido aborta o boot com `sys.exit(1)` e mensagem clara em stderr:

```python
# config/settings.py
GCAL_SEND_UPDATES = os.getenv("GCAL_SEND_UPDATES", "none")
_VALID_SEND_UPDATES = {"none", "all", "externalOnly"}
if GCAL_SEND_UPDATES not in _VALID_SEND_UPDATES:
    print(
        f"ERRO: GCAL_SEND_UPDATES='{GCAL_SEND_UPDATES}' invalido. "
        f"Valores permitidos: {', '.join(_VALID_SEND_UPDATES)}",
        file=sys.stderr,
    )
    sys.exit(1)
```

O `GoogleCalendarClient` (`apps/core/services/gcal_google_client.py`) lê `settings.GCAL_SEND_UPDATES` e o repassa como `sendUpdates` em três operações — `insert()` (criação), `update()` (PATCH) e `delete()`. O Preview usa o mesmo `sendUpdates` configurado (consistência com a publicação real). Testes em `apps/core/tests/test_gcal_send_updates.py`.

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
curl -X POST http://localhost:8002/api/solicitacoes/123/preview-gcal/ \
  -H "Authorization: Bearer $TOKEN"

# 3. Dry-run (simula publicação)
curl -X POST http://localhost:8002/api/solicitacoes/123/publish/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true, "apply_blocked": false}'

# 4. Publicação real (bloqueada por GCAL_CLIENT=fake)
curl -X POST http://localhost:8002/api/solicitacoes/123/publish/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false, "apply_blocked": false}'
# → Retorna 409 CONFLICT

# 5. Forçar publicação (teste com fake client)
curl -X POST http://localhost:8002/api/solicitacoes/123/publish/ \
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

> ⚠️ Corrigido em 2026-07-24: o frontend migrou para TypeScript. Todos os arquivos citados nesta
> seção e nas seguintes são `.tsx`, não `.jsx`.

**Componente Reutilizável** (`v2/frontend/src/components/MeetLink.tsx`):
- Props: `href` (string | null | undefined)
- Retorna `null` se href não existir
- Renderiza dois botões:
  1. **"Entrar na reunião"** (primário, abre em nova aba)
  2. **"Copiar link"** (copia para clipboard com feedback)

**3 locais integrados:**

1. **`src/pages/Solicitacoes.tsx`** (drawer de detalhes):
   - Campo "Reunião Online" com `<MeetLink href={selectedSolicitacao.meet_link} />`
   - Exibido apenas se meet_link existir

2. **`src/pages/PreAgenda/PreAgendaPage.tsx`** (coluna ações):
   - `<MeetLink href={record.meet_link} />` na coluna "Ações"
   - Aparece ao lado de Preview/Publicar

3. **`src/pages/Solicitacoes/MySolicitacoesPage.tsx`** (coluna reunião):
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
# v2/backend/apps/core/models/solicitacao.py:204
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

**Localização**: `v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.tsx` (`<Form.Item name="is_online">`)

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

**Payload Building** — implementação real em `build_event_payload` (`apps/core/services/gcal/payload.py`).

> ⚠️ Corrigido em 2026-07-24. Dois pontos: (a) `apps/core/services/gcal_sync_service.py` é hoje
> apenas uma **fachada de re-export** (`:1-60`) — o código vive no pacote
> `apps/core/services/gcal/` (`payload.py`, `sync.py`); (b) a assinatura real é
> **keyword-only e com default `False`**:
> `build_event_payload(s: Solicitacao, *, enable_meet: bool = False)`.

```python
# apps/core/services/gcal/payload.py:274
def build_event_payload(s, *, enable_meet: bool = False):
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

**Guard de ciclo de vida (M10-03, #1625):** enquanto a sincronização está em andamento
(`gcal_status == "PENDING"`, entre o enfileiramento da task e sua conclusão), **excluir a
solicitação é bloqueado** — `perform_destroy` (`views_solicitacao.py`) retorna `400`, senão a
task Celery operaria sobre um registro já removido. Aguarde a conclusão da sincronização.

### Endpoints

#### POST /api/solicitacoes/{id}/resync-gcal/

**Descrição**: Republicar solicitação no Google Calendar (força UPDATE)

**Permissão**: `CanUseGcal` (policy `use_gcal` = `{operate_preagenda, approve_solicitation}`,
entrada `use_gcal` de `ACCESS_POLICIES` em `apps/core/rbac/policies.py`). *(Corrigido em 2026-07-24: a classe `IsControleOrSuper`
não existe no codebase.)*

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

**Permissão**: `CanUseGcal` (policy `use_gcal` = `{operate_preagenda, approve_solicitation}`,
entrada `use_gcal` de `ACCESS_POLICIES` em `apps/core/rbac/policies.py`). *(Corrigido em 2026-07-24: a classe `IsControleOrSuper`
não existe no codebase.)*

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

**Arquivo real**: pacote `v2/backend/apps/core/services/gcal/`
— `payload.py` (`build_event_payload:274`) e `sync.py`
(`upsert_one:143`, `resync_solicitacao:388`, `cancel_solicitacao:416`).

`v2/backend/apps/core/services/gcal_sync_service.py` continua importável, mas é apenas uma
**fachada de re-export** (`:1-60`). Ao procurar código, vá no pacote.
*(Corrigido em 2026-07-24; os números de linha antigos — "cancel_solicitacao linha ~1015",
"upsert_one linhas 748-750" — eram do arquivo monolítico anterior ao split.)*

#### resync_solicitacao(s, *, apply_blocked=False)

```python
from apps.core.services.gcal_sync_service import resync_solicitacao

# Republicar solicitação aprovada
outcome = resync_solicitacao(solicitacao, apply_blocked=False)
# outcome.action == "UPDATE"
# outcome.external_event_id == "asv2123"
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

**Arquivo**: `v2/frontend/src/pages/PreAgenda/PreAgendaPage.tsx`

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

### UI: Publicar na agenda (Apoio de Coordenação, #1656)

**Arquivo**: `v2/frontend/src/pages/Solicitacoes/PublicacaoSetorPage.tsx`, rota `/solicitacoes/publicacao`. O gate é a policy `publish_setor_solicitacao`, a mesma da API; `use_gcal` não abre esta página, e a Apoio continua sem acesso à Pré-agenda.

Fluxo da Apoio de Coordenação:

1. **Menu**: *Solicitações → Publicar na agenda*. O item só aparece para quem tem `publish_setor_solicitacao`.
2. **Conectar uma vez**: no card "Integração Google Calendar", *Conectar conta Google* abre o OAuth com `return_to=/solicitacoes/publicacao`. A conexão é da **própria** conta corporativa dela. Na volta, a página mostra o resultado (`?google=connected` ou `?google=error&reason=…`), limpa a URL e relê o status. O card não oferece escolha de calendário, porque os eventos vão para o calendário oficial da organização, e não mostra a expiração do access token (o refresh token o renova sozinho).
3. **Publicar**: a tabela lista os eventos **aprovados do setor dela, a partir de hoje** (data de Fortaleza), 20 por página: `GET /api/solicitacoes/?status=aprovado&publishable=true&date_from=…&ordering=inicio`. Cada ação pede confirmação antes de chamar a API: *Publicar* (status NONE) e *Tentar de novo* (ERROR sem evento no Google) chamam `/publish/`; *Atualizar no Google* chama `/resync-gcal/`; *Remover do Google* chama `/cancel-gcal/`. Uma linha PENDING não tem ação.
4. **Acompanhar**: a coluna *Google Agenda* mostra Não publicado, Publicando…, Publicado ou Erro, com a mensagem do erro visível na linha. Enquanto alguma linha está PENDING, a página recarrega a lista a cada 5 s; sem PENDING, não há polling.

Os bloqueios vêm de `publish_ready` e `publish_block_reason` em `GET /api/integrations/google/status/`. Sem setor vigente, a página mostra um alerta para pedir o vínculo de gerência à DAT e não oferece conexão. Sem conta conectada, as ações ficam desabilitadas até ela conectar. Com a agenda da organização ainda não configurada, um alerta pede para avisar o Controle.

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

**Implementação** (`apps/core/services/gcal/sync.py`, função `cancel_solicitacao`):
```python
try:
    _retry_with_circuit_breaker(
        lambda: client.delete(calendar_id, event_id),
        operation_name=f"GCal CANCEL #{s.id}",
    )
except Exception as e:
    # 404 = já foi deletado (idempotência OK)
    if "404" not in str(e):
        raise
```

> **Circuit breaker** (`apps/core/services/gcal/circuit_breaker.py`, `gcal_breaker`): as chamadas
> ao Google Calendar (create/update/cancel) passam por `_retry_with_circuit_breaker`, que **falha
> rápido** enquanto o circuito está aberto (após uma sequência de falhas), evitando martelar a API.
> O retry/backoff (`_retry_with_backoff`) roda por dentro do breaker.

## 5. Comandos Úteis

### Preview (POST /preview-gcal/)

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

> 🔴 **Corrigido em 2026-07-24: o command `sync_calendar` NÃO EXISTE.** Nunca existiu neste
> repositório. O único management command relacionado a GCal é
> `apps/core/management/commands/preagenda_to_gcal.py`:

```bash
# Consultar as opções reais antes de usar
docker compose exec web python manage.py preagenda_to_gcal --help
```

Para publicar uma solicitação específica, o caminho suportado é o endpoint
`POST /api/solicitacoes/{id}/publish/` (gate `CanUseGcal`), que despacha a task
`task_publish_solicitacao_to_gcal`.

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

### Erro: "Sua conexão com o Google expirou ou foi removida"

**Sintoma:** o status Google do evento fica *Erro* com essa mensagem (antes ele ficava preso em PENDING).

**Causa:** a credencial Google de quem publicou/cancelou não existe mais ou foi revogada — por exemplo, refresh token emitido com o app OAuth em modo Teste, que vence em 7 dias.

**Solução:** a pessoa desconecta e conecta a conta Google de novo e repete a ação. O erro cru fica no `AuditLog` (`PUBLISH_GCAL_ERROR`, `details.error`).

### Aviso: conta Google desconectada pelo sistema (`reconnect_required`)

**Sintoma:** `GET /api/integrations/google/status/` responde `connected=false` e `reconnect_required=true`; o Controle vê a pessoa em `google_reconnect.users` no `GET /api/gcal/dashboard/alerts/summary/`.

**Na tela:** na Pré-agenda e na página "Publicar na agenda", o card do Google mostra acima de "Conectar conta Google" o aviso "O Google revogou o acesso da sua conta ao sistema, então ela foi desconectada. Conecte de novo para voltar a publicar."; quem tem `use_gcal` (Controle/Superintendência) recebe um toast com os nomes (até 3 e "e mais N"), repetido só quando a lista de pessoas muda. O card não alarma mais pela validade do access token de 1h ("Expirado"/"Expira em N dias"): o refresh token o renova sozinho.

**Causa:** o Google recusou o refresh token (`invalid_grant`): acesso revogado na conta Google, app OAuth em modo Teste (token vence em 7 dias), token sem uso por 6 meses ou conta suspensa. O sistema apagou a credencial e gravou `AuditLog` `GOOGLE_DISCONNECT` com `details.status="auto_removed"`. Quem detecta é o job diário `probe_google_credentials` (05:00) ou o próprio publish/cancel.

**Solução:** a pessoa conecta a conta Google de novo. Não precisa "Desconectar" antes, porque não há credencial. O aviso some no próximo status: o `GOOGLE_CONNECT` do callback passa a ser o último evento. Para investigar, procure o `GOOGLE_DISCONNECT` com `details.status="auto_removed"` da pessoa no `AuditLog`.

Erro de rede ou 5xx do Google no job **não** remove a credencial. Aparece só no log do worker, sem e-mail: `probe_google_credentials: credencial #N (usuario #M) mantida; refresh falhou (<TipoDoErro>)`. O resumo da execução (`{"ok", "removed", "errors"}`) sai em WARNING quando há remoção ou erro. Se o aviso nunca aparece para ninguém, confira se o beat e o worker estão de pé: com eles parados o job não roda.

### Erro: "O Google recusou o acesso ao calendário da organização"

**Causa:** a conta Google de quem agiu recebeu 403/404 no calendário (sem permissão de edição, ou calendário não compartilhado com ela).

**Solução:** compartilhar o calendário da organização com a conta (ou com o Grupo Google dela) com a permissão "Fazer alterações nos eventos" e repetir a ação.

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
- ✅ `s.meet_link` está sendo persistido? (ver `upsert_one` em `apps/core/services/gcal/sync.py`; a gravação de `s.meet_link` fica nos branches INSERT e UPDATE de `upsert_one`)

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
- Detalhes de `GCAL_SEND_UPDATES` (validação fail-fast + uso no client): seção 2 deste guia — conteúdo consolidado do antigo `v2/backend/GCAL_SEND_UPDATES.md` (arquivado em `_archive/`).

## 8. Criptografia de Tokens OAuth (SEC-011)

### Visão Geral

Tokens OAuth (access/refresh) são criptografados em repouso usando **Fernet** (AES-128-CBC + HMAC-SHA256) via `GCAL_ENCRYPTION_KEY`.

### Configuração por Ambiente

| Ambiente       | Comportamento                                                             |
| -------------- | ------------------------------------------------------------------------- |
| **Produção**   | `GCAL_ENCRYPTION_KEY` obrigatória. Ausência causa `ValueError` (fail-fast) |
| **Dev/Staging** | Fallback para chave derivada de `SECRET_KEY` com warning no log           |

### Rotação de Chave

A rotação é zero-downtime via management command:

```bash
# 1. Gerar nova chave Fernet
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. Executar rotação (descriptografa com antiga, re-criptografa com nova)
python manage.py rotate_gcal_encryption_key \
  --old-key="CHAVE_ATUAL" \
  --new-key="CHAVE_NOVA_GERADA"

# 3. Atualizar GCAL_ENCRYPTION_KEY no Portainer com a nova chave

# 4. Reiniciar containers (web, worker, beat)
```

A rotação cria entrada no AuditLog com ação `GCAL_ENCRYPTION_KEY_ROTATION`.

### Arquivos Relevantes

- `apps/core/services/oauth/token_manager.py` — encrypt/decrypt/rotate
- `apps/core/management/commands/rotate_gcal_encryption_key.py` — comando
- `apps/core/models/integracao.py` — GoogleOAuthCredential (BinaryField)
- `apps/core/tests/test_google_oauth.py` — testes de encrypt/decrypt/rotation

## 9. Histórico

- **PR19** (RF05/RF06): Implementação inicial (GCal + Meet integration)
- **2025-10-23**: Guia criado
- **2025-10-28**: Adicionado componente MeetLink reutilizável e testes de persistência
- **2025-10-30**: Fase 4 completa (Resync/Cancel) - 13 testes backend, endpoints DRF, UI PreAgenda
