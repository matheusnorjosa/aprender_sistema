# Services

Documentação dos services do Aprender Sistema v2.

## Estrutura

```
apps/core/services/
├── availability_service.py   # Verificação de conflitos (RF03)
├── gcal/                     # Google Calendar (RF05/RF06)
│   ├── __init__.py
│   ├── client.py            # CalendarClientAdapter
│   ├── payload.py           # Build event payload
│   ├── sync.py              # Core sync operations
│   └── types.py             # SyncOutcome, Action
└── integrations/             # Outras integrações
```

## availability_service

Verificação de conflitos de disponibilidade.

### check_conflicts

```python
from apps.core.services.availability_service import check_conflicts

result = check_conflicts(
    usuario=formador,
    inicio=datetime(2025, 1, 15, 10, 0),
    fim=datetime(2025, 1, 15, 12, 0),
    municipio=municipio,
)

if not result.available:
    for conflict in result.conflicts:
        print(f"{conflict.code}: {conflict.title}")
        # E: Evento existente
        # T: Bloqueio total
        # P: Bloqueio parcial
        # D: Deslocamento insuficiente
        # M: Capacidade diária excedida
```

### AvailabilityResult

```python
@dataclass
class AvailabilityResult:
    available: bool
    conflicts: list[ConflictDetail]
    checked_at: datetime

@dataclass
class ConflictDetail:
    code: str      # E, T, P, D, M, X
    title: str     # Descrição curta
    detail: str    # Detalhes do conflito
    ref_id: int    # ID do objeto em conflito
```

## gcal_sync_service

Sincronização com Google Calendar.

### apply_one_solicitacao

```python
from apps.core.services.gcal.sync import apply_one_solicitacao

outcome = apply_one_solicitacao(
    solicitacao,
    apply_blocked=False,
    dry_run=False,
)

print(outcome.action)  # 'INSERT', 'UPDATE', 'NOOP'
print(outcome.external_event_id)  # 'asv2-123'
```

### build_event_payload

```python
from apps.core.services.gcal.payload import build_event_payload

payload = build_event_payload(
    solicitacao,
    enable_meet=True,
)

# {
#   "summary": "...",
#   "start": {"dateTime": "..."},
#   "end": {"dateTime": "..."},
#   "conferenceData": {...}  # se is_online=True
# }
```

### resync_solicitacao

```python
from apps.core.services.gcal.sync import resync_solicitacao

# Força re-sincronização
outcome = resync_solicitacao(solicitacao, apply_blocked=False)
```

### cancel_solicitacao

```python
from apps.core.services.gcal.sync import cancel_solicitacao

# Remove do Calendar
outcome = cancel_solicitacao(solicitacao)
# Limpa: external_event_id, meet_link, gcal_payload_hash
```

## SyncOutcome

```python
@dataclass
class SyncOutcome:
    action: Action  # 'INSERT', 'UPDATE', 'DELETE', 'NOOP', 'ERROR'
    external_event_id: str | None
    meet_link: str | None
    error: str | None
```

## Tratamento de Erros

```python
from apps.core.services.gcal.sync import apply_one_solicitacao

try:
    outcome = apply_one_solicitacao(sol, apply_blocked=False)
except ValueError as e:
    # Validação falhou (status != aprovado, etc)
    print(f"Validation error: {e}")
except Exception as e:
    # Erro na API do Google
    print(f"API error: {e}")
```

## Retry com Backoff

Operações GCal usam retry automático:

```python
# 3 tentativas com backoff exponencial
# 1s -> 2s -> 4s
```
