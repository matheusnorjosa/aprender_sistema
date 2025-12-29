# Guia de Integração Google Calendar

Documentação completa da integração do Aprender Sistema v2 com Google Calendar API.

## Visão Geral

O sistema integra com Google Calendar para:

- Publicação automática de eventos aprovados
- Geração de links Google Meet para eventos online
- Sincronização idempotente e resiliente

## Configuração

### 1. Criar Service Account

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie ou selecione um projeto
3. Ative a **Google Calendar API**
4. Crie uma Service Account com chave JSON
5. Compartilhe o calendário com o email da Service Account

### 2. Variáveis de Ambiente

```bash
# Client: 'fake' (in-memory) ou 'google' (real API)
GCAL_CLIENT=fake

# Calendar ID
GCAL_CALENDAR_ID=primary

# Credenciais (escolha uma opção)
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/aprender-sa-key.json
# ou
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# Notificações para participantes
GCAL_SEND_UPDATES=none  # none, all, externalOnly
```

### 3. Desenvolvimento vs Produção

**Desenvolvimento:**
```bash
GCAL_CLIENT=fake
GCAL_SEND_UPDATES=none
```

**Produção:**
```bash
GCAL_CLIENT=google
GCAL_SEND_UPDATES=externalOnly
GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/key.json
```

## Endpoints

### Preview

```bash
GET /api/solicitacoes/{id}/preview-gcal/
```

Retorna preview do evento sem publicar.

### Publicar

```bash
POST /api/solicitacoes/{id}/publish/
{
  "dry_run": false,
  "apply_blocked": false
}
```

### Resync

```bash
POST /api/solicitacoes/{id}/resync-gcal/
```

Força re-sincronização de evento já publicado.

### Cancelar

```bash
POST /api/solicitacoes/{id}/cancel-gcal/
```

Remove evento do Calendar.

## Modalidade (Online vs Presencial)

| Campo | Valor | Comportamento |
|-------|-------|---------------|
| `is_online` | `false` | Evento presencial, sem Meet |
| `is_online` | `true` | Evento online, gera Meet link |

## Matriz de Comportamento

| GCAL_CLIENT | apply_blocked | dry_run | Resultado |
|-------------|---------------|---------|-----------|
| fake | false | true | Simulação OK |
| fake | false | false | Bloqueado (409) |
| fake | true | false | Publica (fake) |
| google | false | false | Publica (real) |

## Troubleshooting

### Erro 409 em /publish/

**Causa:** `GCAL_CLIENT=fake` e `apply_blocked=false`

**Solução:** Use `apply_blocked=true` para testes ou `GCAL_CLIENT=google` para produção.

### meet_link não é gerado

**Checklist:**

- [ ] `is_online=true` na solicitação
- [ ] `conferenceDataVersion=1` no request
- [ ] `GCAL_CLIENT=google` configurado
- [ ] Não é dry_run
