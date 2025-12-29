# Views

Documentação das views e endpoints do Aprender Sistema v2.

## Estrutura Modular

```
apps/core/views/
├── __init__.py          # Re-exports
├── utils.py             # _get_client_ip, api_root
├── solicitacao.py       # SolicitacaoViewSet
├── availability.py      # AvailabilityBlockViewSet
├── user.py              # CurrentUserView
├── admin.py             # CRUD ViewSets
└── options.py           # Dropdown options
```

## Endpoints Principais

### Autenticação

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/login/` | POST | Login (username, password) |
| `/api/logout/` | POST | Logout |
| `/api/me/` | GET | Dados do usuário atual |

### Solicitações

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/solicitacoes/` | GET | Listar solicitações |
| `/api/solicitacoes/` | POST | Criar solicitação |
| `/api/solicitacoes/{id}/` | GET | Detalhe |
| `/api/solicitacoes/{id}/approve/` | POST | Aprovar |
| `/api/solicitacoes/{id}/reject/` | POST | Reprovar |
| `/api/solicitacoes/{id}/publish/` | POST | Publicar no GCal |
| `/api/solicitacoes/{id}/preview-gcal/` | GET | Preview GCal |
| `/api/solicitacoes/{id}/resync-gcal/` | POST | Resync GCal |
| `/api/solicitacoes/{id}/cancel-gcal/` | POST | Cancelar GCal |

### Disponibilidade

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/api/availability/check/` | GET | Verificar conflitos |
| `/api/availability/check-many/` | POST | Verificar em lote |
| `/api/availability/blocks/` | GET | Listar bloqueios |
| `/api/availability/blocks/` | POST | Criar bloqueio |

### Admin

| Endpoint | Descrição |
|----------|-----------|
| `/api/municipios/` | CRUD Municípios |
| `/api/projetos/` | CRUD Projetos |
| `/api/usuarios/` | CRUD Usuários |
| `/api/formadores/` | CRUD Formadores |

## Permissões

### Classes de Permissão

```python
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsSuperintendencia, IsControleOrSuper

class SolicitacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        # Apenas Superintendência
        self.permission_classes = [IsSuperintendencia]
```

### Decorators

```python
@action(
    detail=True,
    methods=['post'],
    permission_classes=[IsSuperintendencia]
)
def approve(self, request, pk=None):
    ...
```

## Serializers

### SolicitacaoSerializer

```python
from apps.core.serializers import SolicitacaoSerializer

serializer = SolicitacaoSerializer(solicitacao)
data = serializer.data
# {
#   "id": 1,
#   "projeto": {...},
#   "municipio": {...},
#   "inicio": "2025-01-15T10:00:00-03:00",
#   "fim": "2025-01-15T12:00:00-03:00",
#   "status": "pendente",
#   "is_online": true,
#   "meet_link": null,
#   ...
# }
```

## Throttling

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_RATES': {
        'availability_check': '100/hour',
    }
}
```

## Paginação

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Response
{
    "count": 100,
    "next": "/api/solicitacoes/?page=2",
    "previous": null,
    "results": [...]
}
```

## Filtros

```python
# Filtrar por status
GET /api/solicitacoes/?status=pendente

# Filtrar por projeto
GET /api/solicitacoes/?projeto=1

# Filtrar por período
GET /api/solicitacoes/?inicio_after=2025-01-01&inicio_before=2025-01-31
```
