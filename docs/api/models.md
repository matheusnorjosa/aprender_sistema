# Models

Documentação dos models Django do Aprender Sistema v2.

## Estrutura Modular

```
apps/core/models/
├── __init__.py          # Re-exports
├── usuario.py           # Usuario (custom user)
├── projeto.py           # Projeto, Gerencia
├── municipio.py         # Municipio, Deslocamento
├── solicitacao.py       # Solicitacao, Participation
├── availability.py      # AvailabilityBlock
├── compra.py            # Compra, Produto
├── controle.py          # AcaoControle, AcaoDAT
├── config.py            # SystemConfig
└── audit.py             # AuditLog
```

## Models Principais

### Usuario

Custom user model com RBAC.

```python
from apps.core.models import Usuario

usuario = Usuario.objects.get(username='maria')
print(usuario.setores)  # ['Superintendência']
print(usuario.funcoes)  # ['Gerente']
print(usuario.can_approve_super)  # True
```

### Solicitacao

Representa uma solicitação de evento.

```python
from apps.core.models import Solicitacao

# Criar solicitação
sol = Solicitacao.objects.create(
    projeto=projeto,
    municipio=municipio,
    inicio=datetime(2025, 1, 15, 10, 0),
    fim=datetime(2025, 1, 15, 12, 0),
    descricao='Formação de professores',
    is_online=True,
)

# Status automático
# SUPER -> 'pendente'
# NAO_SUPER -> 'aprovado'
```

**Campos principais:**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| projeto | FK | Projeto relacionado |
| municipio | FK | Local do evento |
| inicio | DateTime | Início do evento |
| fim | DateTime | Fim do evento |
| status | Char | pendente, aprovado, reprovado |
| is_online | Bool | Modalidade online |
| meet_link | URL | Link do Google Meet |
| external_event_id | Char | ID no Google Calendar |

### AvailabilityBlock

Bloqueios de disponibilidade de formadores.

```python
from apps.core.models import AvailabilityBlock

# Bloqueio total (T)
block = AvailabilityBlock.objects.create(
    usuario=formador,
    tipo='T',
    inicio=datetime(2025, 1, 15, 0, 0),
    fim=datetime(2025, 1, 15, 23, 59),
    motivo='Férias',
)
```

**Tipos:**

| Código | Descrição |
|--------|-----------|
| T | Bloqueio total |
| P | Bloqueio parcial |

### AuditLog

Log de auditoria de ações.

```python
from apps.core.models import AuditLog

# Registrar ação
AuditLog.objects.create(
    usuario=request.user,
    acao='APPROVE',
    objeto_tipo='Solicitacao',
    objeto_id=sol.id,
    detalhes={'status_anterior': 'pendente'},
)
```

## QuerySets Customizados

### Solicitacao

```python
# Pendentes
Solicitacao.objects.pendentes()

# Aprovadas
Solicitacao.objects.aprovadas()

# Por projeto
Solicitacao.objects.do_projeto(projeto_id)

# Por período
Solicitacao.objects.no_periodo(inicio, fim)
```

## Imports Compatíveis

```python
# Import direto (recomendado)
from apps.core.models import Solicitacao, Usuario

# Import de submódulo
from apps.core.models.solicitacao import Solicitacao
```
