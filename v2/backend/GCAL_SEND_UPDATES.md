# Configuração GCAL_SEND_UPDATES

## Descrição

Controla se notificações por email são enviadas aos participantes quando eventos são criados, atualizados ou deletados no Google Calendar.

## Variável de Ambiente

```bash
GCAL_SEND_UPDATES=none
```

## Valores Permitidos

| Valor | Descrição |
|-------|-----------|
| `none` | Nenhum email é enviado (padrão, recomendado para testes) |
| `all` | Emails enviados para todos os participantes |
| `externalOnly` | Emails apenas para participantes externos |

## Validação

A validação ocorre na inicialização do Django em `config/settings.py`:

```python
_VALID_SEND_UPDATES = {"none", "all", "externalOnly"}
if GCAL_SEND_UPDATES not in _VALID_SEND_UPDATES:
    print(f"❌ ERRO: GCAL_SEND_UPDATES='{GCAL_SEND_UPDATES}' inválido.")
    sys.exit(1)
```

**Valores inválidos causam falha na inicialização com mensagem clara.**

## Uso

O valor é lido automaticamente pelo `GoogleCalendarClient` em três métodos:

1. **insert()** - Criação de eventos
2. **update()** - Atualização de eventos (via PATCH)
3. **delete()** - Deleção de eventos

```python
# Exemplo: apps/core/services/gcal_google_client.py
from django.conf import settings

send_updates = getattr(settings, "GCAL_SEND_UPDATES", "none")

self.service.events().insert(
    calendarId=calendar_id,
    body=body,
    sendUpdates=send_updates  # ← Usa configuração
).execute()
```

## Referência Google Calendar API

- [Events.insert](https://developers.google.com/calendar/api/v3/reference/events/insert#parameters)
- [Events.patch](https://developers.google.com/calendar/api/v3/reference/events/patch#parameters)
- [Events.delete](https://developers.google.com/calendar/api/v3/reference/events/delete#parameters)

## Testes

Suite completa em `apps/core/tests/test_gcal_send_updates.py`:

- ✅ Default é `'none'`
- ✅ `override_settings` funciona corretamente
- ✅ Valores inválidos são rejeitados
- ✅ `insert()`, `update()`, `delete()` respeitam configuração
- ✅ Preview usa configuração (decisão de design: consistência)

```bash
# Rodar testes
docker compose exec web pytest apps/core/tests/test_gcal_send_updates.py -v
```

## Exemplo .env.example

Adicione ao seu `.env.example`:

```bash
# ================================================================
# GOOGLE CALENDAR / SHEETS
# ================================================================
GOOGLE_SERVICE_ACCOUNT_JSON=
GCAL_CALENDAR_ID=

# Calendar client: 'fake' (in-memory, safe) or 'google' (real API)
GCAL_CLIENT=fake

# Email notifications to attendees (RF05/RF06 - PR19)
# Options: 'none' (default), 'all', 'externalOnly'
# https://developers.google.com/calendar/api/v3/reference/events/insert#parameters
GCAL_SEND_UPDATES=none
```

## Decisões de Design

### Preview usa configuração

**Decisão:** Preview usa o mesmo `sendUpdates` configurado.

**Justificativa:** Consistência. Se admin quer testar com `'all'`, preview deve refletir isso. Facilita validação end-to-end do comportamento.

**Alternativa rejeitada:** Forçar `'none'` para preview. Motivo: Reduz utilidade do preview para testes realistas.

## Histórico

- **PR19** (RF05/RF06): Implementação inicial
- **Etapa 7**: Configuração via `GCAL_SEND_UPDATES`
- **Data:** 2025-10-23
