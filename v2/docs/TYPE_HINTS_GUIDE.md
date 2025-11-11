# 🐍 Type Hints — Guia do Desenvolvedor

**Projeto**: Aprender Sistema v2
**Python**: 3.12.12 (PEP 695 support)
**Type Checker**: Pyright (strict mode)
**Última Atualização**: 11 de Novembro de 2025

---

## 🎯 Visão Geral

Este guia ensina como usar **type hints** no Aprender Sistema v2. Type hints são anotações de tipo que tornam o código mais claro, previnem bugs e melhoram o autocomplete do VS Code (Pylance).

### Por Que Type Hints?

1. **Autocomplete Melhor**: VS Code sugere métodos e atributos corretos
2. **Bugs Prevenidos**: Pyright detecta erros de tipo antes de rodar
3. **Documentação Implícita**: Código self-documenting
4. **Refatoração Segura**: Mudanças com confiança

### Exemplo Rápido

```python
# ❌ Sem type hints (ambíguo)
def processar(dados):
    return dados.upper()

# ✅ Com type hints (claro)
def processar(dados: str) -> str:
    return dados.upper()
```

---

## 📚 Tipos Básicos

### Primitivos

```python
# Strings
nome: str = "João Silva"
email: str = "joao@example.com"

# Inteiros
idade: int = 25
quantidade: int = 100

# Floats
preco: float = 99.90
percentual: float = 15.5

# Booleanos
ativo: bool = True
aprovado: bool = False
```

### Coleções

```python
# Listas (homogêneas)
nomes: list[str] = ["Ana", "Bruno", "Carlos"]
idades: list[int] = [25, 30, 35]

# Dicionários
config: dict[str, str] = {"host": "localhost", "port": "8000"}
scores: dict[str, int] = {"Alice": 100, "Bob": 95}

# Tuplas (heterogêneas, fixas)
coordenada: tuple[float, float] = (10.5, 20.3)
usuario_info: tuple[str, int, bool] = ("João", 25, True)

# Sets (únicos)
tags: set[str] = {"python", "django", "docker"}
```

### Opcionais

```python
# T | None = valor pode ser None
nome: str | None = None
idade: int | None = obter_idade()

def buscar_usuario(id: int) -> Usuario | None:
    try:
        return Usuario.objects.get(id=id)
    except Usuario.DoesNotExist:
        return None
```

---

## 🗄️ Django Models

### Tipando Métodos

```python
from django.db import models
from typing import Self

class Solicitacao(models.Model):
    titulo = models.CharField(max_length=200)
    status = models.CharField(max_length=20, default="pendente")

    def aprovar(self) -> None:
        """Aprova solicitação (sem retorno)."""
        self.status = "aprovado"
        self.save(update_fields=["status"])

    def duplicar(self) -> Self:
        """Duplica solicitação (retorna instância da própria classe)."""
        self.pk = None
        self.save()
        return self

    @classmethod
    def pendentes(cls) -> models.QuerySet[Self]:
        """Retorna solicitações pendentes."""
        return cls.objects.filter(status="pendente")
```

### QuerySet Tipado

```python
from django.db import models

class Solicitacao(models.Model):
    # ...

    @classmethod
    def por_usuario(cls, usuario: Usuario) -> models.QuerySet[Self]:
        """Filtra solicitações por usuário."""
        return cls.objects.filter(usuario=usuario)

    @classmethod
    def aprovadas_por_periodo(
        cls,
        inicio: datetime,
        fim: datetime
    ) -> models.QuerySet[Self]:
        """Filtra solicitações aprovadas em um período."""
        return cls.objects.filter(
            status="aprovado",
            inicio__gte=inicio,
            fim__lte=fim
        )
```

---

## 📦 Django REST Framework

### Serializers

```python
from rest_framework import serializers
from typing import Any

class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    # SerializerMethodField sempre retorna Any por padrão
    fluxo = serializers.SerializerMethodField()

    class Meta:
        model = Solicitacao
        fields = "__all__"

    def get_fluxo(self, obj: Solicitacao) -> str:
        """Retorna fluxo do projeto."""
        return obj.projeto.fluxo if obj.projeto else "NAO_SUPER"

    def validate_inicio(self, value: datetime) -> datetime:
        """Valida data de início."""
        if value < timezone.now():
            raise serializers.ValidationError("Data no passado")
        return value

    def create(self, validated_data: dict[str, Any]) -> Solicitacao:
        """Cria nova solicitação."""
        return Solicitacao.objects.create(**validated_data)
```

### ViewSets

```python
from rest_framework import viewsets
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action

class SolicitacaoViewSet(viewsets.ModelViewSet[Solicitacao]):
    queryset = Solicitacao.objects.all()
    serializer_class = SolicitacaoSerializer

    def get_queryset(self) -> models.QuerySet[Solicitacao]:
        """Filtra queryset por usuário."""
        user = self.request.user
        if user.is_superuser:
            return Solicitacao.objects.all()
        return Solicitacao.objects.filter(usuario=user)

    @action(detail=True, methods=["post"])
    def aprovar(self, request: Request, pk: int | None = None) -> Response:
        """Aprova solicitação."""
        solicitacao = self.get_object()
        solicitacao.aprovar()
        serializer = self.get_serializer(solicitacao)
        return Response(serializer.data)
```

---

## 🔧 Services (Lógica de Negócio)

### Dataclasses para Estruturas

```python
from dataclasses import dataclass
from typing import Literal

# PEP 695: Type alias moderno
type ConflictCode = Literal["X", "T", "P", "D", "M"]

@dataclass
class ConflictDetail:
    code: ConflictCode
    title: str
    detail: str
    ref_id: int | None = None

@dataclass
class AvailabilityResult:
    ok: bool
    conflicts: list[ConflictDetail]

def check_conflicts(
    usuario: Usuario,
    inicio: datetime,
    fim: datetime,
    municipio: Municipio,
) -> AvailabilityResult:
    """Verifica conflitos de disponibilidade (RD-01 a RD-08)."""
    conflicts: list[ConflictDetail] = []

    # Lógica de verificação...

    return AvailabilityResult(
        ok=len(conflicts) == 0,
        conflicts=conflicts
    )
```

### TypedDict para Dicionários Estruturados

```python
from typing import TypedDict, NotRequired

class GCalEventPayload(TypedDict):
    summary: str
    start: dict[str, str]
    end: dict[str, str]
    conferenceData: NotRequired[dict[str, Any]]  # Opcional

def build_gcal_payload(
    solicitacao: Solicitacao,
    include_meet: bool = True
) -> GCalEventPayload:
    """Constrói payload para Google Calendar API."""
    payload: GCalEventPayload = {
        "summary": solicitacao.titulo,
        "start": {"dateTime": solicitacao.inicio.isoformat()},
        "end": {"dateTime": solicitacao.fim.isoformat()}
    }

    if include_meet:
        payload["conferenceData"] = {
            "createRequest": {"requestId": str(uuid.uuid4())}
        }

    return payload
```

---

## 🎯 Python 3.12 (PEP 695)

### Type Aliases Modernos

```python
# ❌ Antes (Python 3.11)
from typing import TypeAlias
UserId: TypeAlias = int

# ✅ Agora (Python 3.12 com PEP 695)
type UserId = int
type EventId = str
type JsonDict = dict[str, Any]
type Handler[T] = Callable[[T], bool]

# Uso
def obter_usuario(id: UserId) -> Usuario | None:
    return Usuario.objects.filter(id=id).first()
```

### Generics Modernos

```python
# ❌ Antes (Python 3.11)
from typing import TypeVar, Generic
T = TypeVar("T")
class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# ✅ Agora (Python 3.12 com PEP 695)
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

def processar[T](items: list[T]) -> list[T]:
    return items
```

---

## 🧪 Boas Práticas

### 1. Use Tipos Específicos

```python
# ❌ Evite Any quando possível
def processar(dados: Any) -> Any:
    return dados.upper()

# ✅ Prefira tipos específicos
def processar(dados: str) -> str:
    return dados.upper()
```

### 2. Use Type Aliases para Clareza

```python
# ❌ Tipo complexo repetido
def criar(dados: dict[str, int | str | bool | None]) -> None:
    pass

def atualizar(dados: dict[str, int | str | bool | None]) -> None:
    pass

# ✅ Type alias reutilizável
type UserData = dict[str, int | str | bool | None]

def criar(dados: UserData) -> None:
    pass

def atualizar(dados: UserData) -> None:
    pass
```

### 3. Use Literal para Constantes

```python
# ❌ String sem validação
def atualizar_status(status: str) -> None:
    # Aceita qualquer string (bug-prone)
    solicitacao.status = status

# ✅ Literal com valores fixos
type Status = Literal["pendente", "aprovado", "reprovado"]

def atualizar_status(status: Status) -> None:
    # Apenas valores válidos aceitos
    solicitacao.status = status
```

### 4. Use Dataclasses para Estruturas

```python
# ❌ Dicionário sem estrutura
def processar() -> dict[str, Any]:
    return {"ok": True, "errors": []}

# ✅ Dataclass com estrutura
@dataclass
class Result:
    ok: bool
    errors: list[str]

def processar() -> Result:
    return Result(ok=True, errors=[])
```

---

## 🔍 VS Code Integration (Pylance)

### Configuração Recomendada

```json
// .vscode/settings.json
{
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.diagnosticMode": "workspace",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.inlayHints.variableTypes": true,
    "python.analysis.inlayHints.functionReturnTypes": true,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black"
}
```

### Atalhos Úteis

- **Ctrl + Espaço**: Autocomplete
- **Ctrl + Clique**: Ir para definição
- **F2**: Renomear símbolo (refactoring seguro)
- **Ctrl + .**: Quick fix (Pyright suggestions)

---

## ❓ FAQ

### "Por que usar type hints se Python é dinâmico?"

Type hints não afetam runtime — são apenas para ferramentas (Pyright, Pylance). Eles previnem bugs SEM perder flexibilidade do Python.

### "E se eu não souber o tipo exato?"

Use `Any` como escape hatch temporário, mas documente:

```python
from typing import Any

def processar(dados: Any) -> Any:
    # TODO: Tipar quando souber estrutura de dados
    return dados
```

### "Preciso tipar tudo?"

**Não!** Foque em código crítico (35% do projeto):
- ✅ Services (lógica de negócio)
- ✅ Models (métodos personalizados)
- ✅ Serializers (validate)
- ✅ ViewSets (actions)
- ⏸️ Tests (menos crítico)

### "Type hints deixam o código lento?"

**Não!** Type hints são removidos em runtime (zero overhead).

---

## 🔗 Recursos

### Documentação
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 695 - Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Pyright Documentation](https://github.com/microsoft/pyright)

### Repositórios de Referência
- [luizomf/typehints_python](https://github.com/luizomf/typehints_python) - 47 exemplos progressivos

### Interno
- [`TYPE_HINTS_REFERENCE_FULL.md`](../../TYPE_HINTS_REFERENCE_FULL.md) - Referência completa (1500 linhas)
- [`PYRIGHT_SETUP.md`](./PYRIGHT_SETUP.md) - Setup e troubleshooting
- [`.claude/skills/django-patterns/SKILL.md`](../../.claude/skills/django-patterns/SKILL.md) - Padrões Django/DRF

---

**Dúvidas?** Consulte a equipe ou abra uma issue no GitHub.

**Happy typing! 🐍✨**
