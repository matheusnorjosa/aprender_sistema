# 🐍 Type Hints - Referência Completa e Plano de Implementação FULL

**Projeto**: Aprender Sistema v2
**Python**: 3.12.12 (PEP 695 disponível ✅)
**Type Checker**: Pyright (strict mode)
**Baseline**: 186 arquivos Python (excl. migrations), ~16% com type hints
**Meta**: 100% de cobertura em código crítico (35% do projeto = 65 arquivos)
**Tempo Total Estimado**: 144h (3.6 semanas) baseado em dados reais

---

## 📚 PARTE 1: REFERÊNCIA COMPLETA DE TYPE HINTS

### 1.1 Basic Types (Tipos Primitivos)

#### `str` - String
```python
nome: str = "João Silva"
email: str = "joao@example.com"

def formatar_nome(nome: str) -> str:
    return nome.upper()
```
**Uso**: Textos, emails, CPF, descrições

---

#### `int` - Integer
```python
idade: int = 25
quantidade: int = 100

def calcular_total(quantidade: int, preco: int) -> int:
    return quantidade * preco
```
**Uso**: IDs, contadores, quantidades inteiras

---

#### `float` - Float
```python
preco: float = 99.90
percentual: float = 15.5

def calcular_desconto(preco: float, percentual: float) -> float:
    return preco * (percentual / 100)
```
**Uso**: Preços, percentuais, medidas decimais

---

#### `bool` - Boolean
```python
ativo: bool = True
aprovado: bool = False

def verificar_elegibilidade(idade: int) -> bool:
    return idade >= 18
```
**Uso**: Flags, estados binários, condições

---

#### `None` - Nenhum valor
```python
resultado: None = None

def processar_sem_retorno() -> None:
    print("Processando...")
    # Não retorna nada
```
**Uso**: Funções sem retorno, valores ausentes

---

### 1.2 Collections (Coleções)

#### `list[T]` - Lista homogênea
```python
nomes: list[str] = ["Ana", "Bruno", "Carlos"]
idades: list[int] = [25, 30, 35]
usuarios: list[Usuario] = [user1, user2, user3]

def filtrar_pares(numeros: list[int]) -> list[int]:
    return [n for n in numeros if n % 2 == 0]
```
**Uso**: Coleções ordenadas de mesmo tipo

---

#### `dict[K, V]` - Dicionário tipado
```python
config: dict[str, str] = {"host": "localhost", "port": "8000"}
scores: dict[str, int] = {"Alice": 100, "Bob": 95}
cache: dict[int, Usuario] = {1: user1, 2: user2}

def agrupar_por_idade(users: list[Usuario]) -> dict[int, list[Usuario]]:
    resultado: dict[int, list[Usuario]] = {}
    for user in users:
        resultado.setdefault(user.idade, []).append(user)
    return resultado
```
**Uso**: Mapeamentos chave-valor

---

#### `tuple[T1, T2, ...]` - Tupla de tipos heterogêneos
```python
coordenada: tuple[float, float] = (10.5, 20.3)
usuario_info: tuple[str, int, bool] = ("João", 25, True)

def dividir_nome(nome_completo: str) -> tuple[str, str]:
    partes = nome_completo.split(" ", 1)
    return (partes[0], partes[1] if len(partes) > 1 else "")
```
**Uso**: Dados estruturados fixos, retornos múltiplos

---

#### `set[T]` - Conjunto
```python
tags: set[str] = {"python", "django", "docker"}
ids_processados: set[int] = {1, 2, 3, 5, 8}

def unir_tags(tags1: set[str], tags2: set[str]) -> set[str]:
    return tags1 | tags2
```
**Uso**: Coleções únicas, operações de conjunto

---

### 1.3 Union Types (Tipos Opcionais/Múltiplos)

#### `T | None` - Opcional (Python 3.10+)
```python
nome: str | None = None
idade: int | None = obter_idade()

def buscar_usuario(id: int) -> Usuario | None:
    try:
        return Usuario.objects.get(id=id)
    except Usuario.DoesNotExist:
        return None
```
**Uso**: Valores que podem ser ausentes

---

#### `T1 | T2 | T3` - Union de múltiplos tipos
```python
resultado: int | str | bool = processar()
valor: float | int = 10  # Aceita ambos

def processar_entrada(valor: str | int | float) -> str:
    return str(valor)
```
**Uso**: Múltiplos tipos possíveis

---

### 1.4 Literal Types (Valores Específicos)

#### `Literal[...]` - Valores literais fixos
```python
from typing import Literal

Status = Literal["pendente", "aprovado", "reprovado"]
Fluxo = Literal["SUPER", "NAO_SUPER"]
Code = Literal["X", "T", "P", "D", "M"]

def atualizar_status(status: Status) -> None:
    # status só pode ser um dos 3 valores
    print(f"Status atualizado para: {status}")

# Type checker detecta erro:
atualizar_status("invalido")  # ❌ Erro!
atualizar_status("aprovado")  # ✅ OK
```
**Uso**: Enums, constantes, valores fixos

---

### 1.5 Generic Types (Tipos Genéricos)

#### `TypeVar` - Variável de tipo
```python
from typing import TypeVar

T = TypeVar("T")  # Qualquer tipo
NumberT = TypeVar("NumberT", int, float)  # Restrito a int ou float

def primeiro(items: list[T]) -> T | None:
    return items[0] if items else None

def somar(a: NumberT, b: NumberT) -> NumberT:
    return a + b  # type: ignore

# Type checker infere:
resultado_str = primeiro(["a", "b", "c"])  # str | None
resultado_int = primeiro([1, 2, 3])        # int | None
```
**Uso**: Funções genéricas que preservam tipo

---

#### PEP 695: Sintaxe moderna de Generics (Python 3.12+)
```python
# ❌ Antes (Python 3.11)
from typing import TypeVar, Generic
T = TypeVar("T")
class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# ✅ Agora (Python 3.12+ com PEP 695)
class Container[T]:
    def __init__(self, value: T) -> None:
        self.value = value

def processar[T](items: list[T]) -> list[T]:
    return items

# Type aliases modernos
type Point = tuple[float, float]
type ConnectionOptions[T] = dict[str, T]
type Handler[T, R] = Callable[[T], R]
```
**Uso**: Código genérico reutilizável (Python 3.12+)

---

### 1.6 Callable (Funções)

#### `Callable[[Args], Return]` - Tipo de função
```python
from typing import Callable

# Função que recebe int e retorna str
Formatter = Callable[[int], str]

def formatar_numero(n: int) -> str:
    return f"#{n:03d}"

def aplicar_formato(numeros: list[int], formatter: Formatter) -> list[str]:
    return [formatter(n) for n in numeros]

# Uso
resultado = aplicar_formato([1, 2, 3], formatar_numero)
# resultado: ["#001", "#002", "#003"]
```
**Uso**: Callbacks, decorators, estratégias

---

### 1.7 TypedDict (Dicionários Estruturados)

#### `TypedDict` - Dict com chaves específicas
```python
from typing import TypedDict, NotRequired

class UsuarioDict(TypedDict):
    id: int
    nome: str
    email: str
    ativo: bool

class ConfigDict(TypedDict):
    host: str
    port: int
    debug: NotRequired[bool]  # Opcional (Python 3.11+)

def criar_usuario(dados: UsuarioDict) -> Usuario:
    return Usuario.objects.create(**dados)

# Type checker valida chaves:
usuario = criar_usuario({
    "id": 1,
    "nome": "João",
    "email": "joao@example.com",
    "ativo": True
})  # ✅ OK

usuario = criar_usuario({
    "id": 1,
    "nome": "João"
})  # ❌ Erro! Faltam chaves
```
**Uso**: Payloads API, configs, dados estruturados

---

### 1.8 Protocol (Duck Typing com Tipos)

#### `Protocol` - Interface estrutural
```python
from typing import Protocol

class Persistivel(Protocol):
    def save(self) -> None: ...
    def delete(self) -> None: ...

class EmailSender(Protocol):
    def enviar(self, destinatario: str, mensagem: str) -> bool: ...

def salvar_entidade(entidade: Persistivel) -> None:
    # Qualquer objeto com save() e delete() funciona
    entidade.save()
    print("Salvo com sucesso!")

# Django models implementam Persistivel naturalmente:
solicitacao = Solicitacao()
salvar_entidade(solicitacao)  # ✅ OK
```
**Uso**: Interfaces, abstrações, duck typing seguro

---

### 1.9 Type Aliases (PEP 695)

#### `type` - Aliases modernos (Python 3.12+)
```python
# ❌ Antes (Python 3.11)
from typing import TypeAlias
UserId: TypeAlias = int
JsonDict: TypeAlias = dict[str, Any]

# ✅ Agora (Python 3.12+ com PEP 695)
type UserId = int
type JsonDict = dict[str, Any]
type Point = tuple[float, float]
type Handler[T] = Callable[[T], bool]

# Uso
def obter_usuario(id: UserId) -> Usuario | None:
    return Usuario.objects.filter(id=id).first()

def processar_json(dados: JsonDict) -> None:
    print(dados["nome"])
```
**Uso**: Simplificar tipos complexos, semântica do domínio

---

### 1.10 Self (Tipo da própria classe)

#### `Self` - Retorno da própria instância
```python
from typing import Self

class QuerySetBuilder:
    def filtrar(self, **kwargs: Any) -> Self:
        # Retorna instância da própria classe
        return self

    def ordenar(self, campo: str) -> Self:
        return self

    def executar(self) -> list[dict[str, Any]]:
        return []

# Type checker preserva tipo:
resultado = (
    QuerySetBuilder()
    .filtrar(ativo=True)
    .ordenar("nome")
    .executar()
)
```
**Uso**: Fluent interfaces, builders, chainable methods

---

### 1.11 Any (Escape Hatch)

#### `Any` - Qualquer tipo (desabilita verificação)
```python
from typing import Any

def processar_dados(dados: Any) -> Any:
    # Type checker não valida nada aqui
    return dados.alguma_coisa()

# Use com moderação! Prefira tipos específicos
config: dict[str, Any] = {"host": "localhost", "port": 8000}
```
**Uso**: Integrações externas, migration gradual, casos complexos
**⚠️ Atenção**: Usar `Any` derrota o propósito de type hints!

---

## 📦 PARTE 2: TYPE HINTS ESPECÍFICOS DO PROJETO

### 2.1 Django Models

#### QuerySet Tipado
```python
from django.db import models
from typing import Self

class Solicitacao(models.Model):
    # Fields (Django infere tipos automaticamente)
    titulo: str = models.CharField(max_length=200)
    descricao: str | None = models.TextField(blank=True, null=True)
    status: str = models.CharField(max_length=20, default="pendente")

    # Methods
    def aprovar(self) -> None:
        self.status = "aprovado"
        self.save(update_fields=["status"])

    @classmethod
    def pendentes(cls) -> models.QuerySet[Self]:
        return cls.objects.filter(status="pendente")

    @classmethod
    def por_usuario(cls, usuario: Usuario) -> models.QuerySet[Self]:
        return cls.objects.filter(usuario=usuario)
```

#### Manager Customizado
```python
class SolicitacaoManager(models.Manager["Solicitacao"]):
    def aprovadas(self) -> models.QuerySet[Solicitacao]:
        return self.filter(status="aprovado")

    def por_periodo(
        self,
        inicio: datetime,
        fim: datetime
    ) -> models.QuerySet[Solicitacao]:
        return self.filter(inicio__gte=inicio, fim__lte=fim)

class Solicitacao(models.Model):
    objects: SolicitacaoManager = SolicitacaoManager()
```

---

### 2.2 Django REST Framework

#### Serializers
```python
from rest_framework import serializers
from typing import Any

class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    # Read-only fields
    fluxo = serializers.SerializerMethodField()
    meet_link = serializers.CharField(read_only=True)

    class Meta:
        model = Solicitacao
        fields = "__all__"

    def get_fluxo(self, obj: Solicitacao) -> str:
        return obj.projeto.fluxo if obj.projeto else "NAO_SUPER"

    def validate_inicio(self, value: datetime) -> datetime:
        if value < timezone.now():
            raise serializers.ValidationError("Data no passado")
        return value

    def create(self, validated_data: dict[str, Any]) -> Solicitacao:
        return Solicitacao.objects.create(**validated_data)

    def update(
        self,
        instance: Solicitacao,
        validated_data: dict[str, Any]
    ) -> Solicitacao:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
```

#### ViewSets
```python
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action

class SolicitacaoViewSet(viewsets.ModelViewSet[Solicitacao]):
    queryset = Solicitacao.objects.all()
    serializer_class = SolicitacaoSerializer

    def get_queryset(self) -> models.QuerySet[Solicitacao]:
        user = self.request.user
        if user.is_superuser:
            return Solicitacao.objects.all()
        return Solicitacao.objects.filter(usuario=user)

    @action(detail=True, methods=["post"])
    def aprovar(self, request: Request, pk: int | None = None) -> Response:
        solicitacao = self.get_object()
        solicitacao.aprovar()
        serializer = self.get_serializer(solicitacao)
        return Response(serializer.data, status=status.HTTP_200_OK)
```

---

### 2.3 Celery Tasks

```python
from celery import shared_task
from typing import Any

@shared_task(bind=True)
def task_publish_to_gcal(
    self,
    solicitacao_id: int,
    dry_run: bool = False
) -> dict[str, Any]:
    """Publica solicitação no Google Calendar."""
    try:
        solicitacao = Solicitacao.objects.get(id=solicitacao_id)
        resultado = publicar_gcal(solicitacao, dry_run=dry_run)
        return {"status": "success", "event_id": resultado}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
        return {"status": "error", "message": str(exc)}
```

---

### 2.4 Type Aliases do Projeto

```python
# v2/backend/apps/core/types.py

# IDs
type UserId = int
type SolicitacaoId = int
type ProjetoId = int

# Status
type Status = Literal["pendente", "aprovado", "reprovado"]
type Fluxo = Literal["SUPER", "NAO_SUPER"]
type GCalStatus = Literal["pending", "synced", "error"]

# Availability
type ConflictCode = Literal["X", "T", "P", "D", "M"]

# JSON
type JsonDict = dict[str, Any]
type JsonList = list[JsonDict]

# Handlers
type ErrorHandler = Callable[[Exception], None]
type SuccessCallback[T] = Callable[[T], None]

# Google Calendar
type EventId = str
type CalendarId = str
type MeetLink = str
```

---

## 🗓️ PARTE 3: PLANO DE IMPLEMENTAÇÃO FULL

### Timeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTAÇÃO TYPE HINTS                       │
│                  144h / 3.6 semanas / 8 PRs                      │
│           Baseado em 186 arquivos reais do projeto               │
└─────────────────────────────────────────────────────────────────┘

Semana 1 (40h)          Semana 2 (40h)          Semana 3 (40h)          Semana 4 (24h)
┌──────────────┐        ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│ PR#1: Setup  │───────>│ PR#3: Models │───────>│ PR#5: Views  │───────>│ PR#7: Tests  │
│   (4h)       │        │   (10h)      │        │   (14h)      │        │   (6h)       │
├──────────────┤        ├──────────────┤        ├──────────────┤        ├──────────────┤
│ PR#2: Servic │        │ PR#4: Serial │        │ PR#6: Tasks  │        │ PR#8: Polish │
│   (36h)      │        │   (30h)      │        │   (26h)      │        │   (18h)      │
└──────────────┘        └──────────────┘        └──────────────┘        └──────────────┘

        ↓                       ↓                       ↓                       ↓
   [Milestone 1]          [Milestone 2]          [Milestone 3]          [Milestone 4]
   Setup + Core           Domain Layer           API Layer              Complete
```

---

### 📊 Métricas de Sucesso

**Meta Final**:
- ✅ 100% dos services tipados
- ✅ 100% dos models tipados
- ✅ 100% dos serializers tipados
- ✅ 100% dos views tipados
- ✅ 100% dos tasks tipados
- ✅ Pyright strict mode: 0 erros
- ✅ CI verde em todos os PRs

---

### Fase 1: Setup e Infraestrutura (4h)

#### PR #1: Setup Pyright + CI
**Branch**: `feat/typehints-setup`
**Tempo**: 4h
**Reviewers**: @matheusnorjosa

**Checklist**:
- [ ] Instalar dependências
  - [ ] `pip install pyright`
  - [ ] `pip install django-types`
  - [ ] `pip install djangorestframework-types`
  - [ ] `pip install types-requests`
  - [ ] `pip install types-redis`
  - [ ] Atualizar `requirements-dev.txt`

- [ ] Criar configuração Pyright
  - [ ] `v2/backend/pyproject.toml` com `[tool.pyright]`
  - [ ] `typeCheckingMode = "strict"`
  - [ ] `pythonVersion = "3.12"`
  - [ ] Include paths: `apps/core`, `apps/dat_ingest`
  - [ ] Exclude: `**/migrations`, `**/tests` (temporário)

- [ ] Criar type stubs customizados
  - [ ] `v2/backend/typings/django/__init__.pyi`
  - [ ] `v2/backend/typings/rest_framework/__init__.pyi`

- [ ] Adicionar ao CI
  - [ ] Step "Type check with Pyright" em `.github/workflows/v2-ci.yml`
  - [ ] Configurar para falhar em erros

- [ ] Criar baseline
  - [ ] `pyright --outputjson > pyright-baseline.json`
  - [ ] Documentar erros existentes

- [ ] Documentação
  - [ ] `v2/docs/TYPE_HINTS_GUIDE.md`
  - [ ] `v2/docs/PYRIGHT_SETUP.md`
  - [ ] Atualizar `.claude/CLAUDE.md`

**Entregáveis**:
- [ ] Pyright configurado e funcionando
- [ ] CI executando type check
- [ ] Baseline de erros documentada
- [ ] Guia para desenvolvedores

**Merge Criteria**:
- [ ] CI verde (pode ter erros conhecidos em baseline)
- [ ] Documentação completa
- [ ] Aprovação de 1+ reviewer

---

### Fase 2: Services (36h)

#### PR #2: Type Hints em Services
**Branch**: `feat/typehints-services`
**Tempo**: 36h (~7,192 linhas de código em 24 services)
**Depende de**: PR #1
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (24 arquivos reais do projeto):
**apps/core/services/** (13 arquivos):
1. [ ] `availability_service.py` (3h)
   - [ ] Atualizar `ConflictDetail` dataclass
   - [ ] Atualizar `AvailabilityResult` dataclass
   - [ ] Tipar `check_conflicts()`
   - [ ] Tipar funções auxiliares
   - [ ] Adicionar PEP 695 type aliases

2. [ ] `gcal_sync_service.py` (3h)
   - [ ] Criar `GCalEventPayload` TypedDict
   - [ ] Tipar `build_payload()`
   - [ ] Tipar funções auxiliares

3. [ ] `gcal_google_client.py` (3h)
   - [ ] Criar `GCalClient` Protocol
   - [ ] Tipar `GoogleCalendarClient` class
   - [ ] Tipar métodos `create_event()`, `update_event()`, `delete_event()`

4. [ ] `gcal_fake_client.py` (2h)
   - [ ] Implementar `GCalClient` Protocol

5. [ ] `gcal_oauth_client.py` (2h)
   - [ ] Tipar OAuth client methods

6. [ ] `gcal_client_factory.py` (1h)
   - [ ] Tipar factory pattern

7. [ ] `config_service.py` (2h)
   - [ ] Tipar `get_config()`, `set_config()`

8. [ ] `google_oauth.py` (2h)
   - [ ] Tipar fluxo OAuth completo

9. [ ] `monthly_grid_service.py` (2h)
   - [ ] Tipar grid generation

10. [ ] `controle_imports.py` (2h)
11. [ ] `controle_acoes_import.py` (2h)
12. [ ] `dat_cadastros_import.py` (2h)
13. [ ] `__init__.py` (1h)

**apps/dat_ingest/services/** (11 arquivos):
14-24. [ ] Serviços de ingestão (11h total - 1h cada)
   - [ ] `action_import_service.py`
   - [ ] `data_validator_service.py`
   - [ ] `etl_base_service.py`
   - [ ] `file_parser_service.py`
   - [ ] Outros 7 services de ETL

**Type Aliases Criados**:
- [ ] `v2/backend/apps/core/types.py` (arquivo centralizado)
  ```python
  type EventId = str
  type CalendarId = str
  type ConflictCode = Literal["X", "T", "P", "D", "M"]
  type GCalStatus = Literal["pending", "synced", "error"]
  ```

**Entregáveis**:
- [ ] 24 services 100% tipados (~7,192 linhas)
- [ ] Pyright: 0 erros em services
- [ ] Type aliases centralizados em `apps/core/types.py`
- [ ] Protocols definidos (`GCalClient`, `ETLService`)

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/core/services/`
- [ ] Todos os testes existentes passando
- [ ] CI verde
- [ ] Code review aprovado

---

### Fase 3: Models (10h)

#### PR #3: Type Hints em Models
**Branch**: `feat/typehints-models`
**Tempo**: 10h (5 arquivos reais, models.py principal tem 1,017 linhas)
**Depende de**: PR #2
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (5 arquivos reais do projeto):

1. [ ] `apps/core/models.py` (6h - 1,017 linhas)
   - [ ] Classe `Usuario` (1h)
     - [ ] Tipar métodos personalizados
     - [ ] Tipar Manager customizado
     - [ ] QuerySet tipado: `models.QuerySet[Usuario]`

   - [ ] Classe `Solicitacao` (3h)
     - [ ] Tipar `mark_gcal()` com Literal status
     - [ ] Tipar `aprovar()`, `reprovar()`
     - [ ] Tipar métodos de validação
     - [ ] QuerySet methods: `pendentes()`, `aprovadas()`
     - [ ] ClassMethods tipados

   - [ ] Classe `AvailabilityBlock` (1h)
     - [ ] Tipar métodos de validação
     - [ ] QuerySet tipado

   - [ ] Classes auxiliares (2h)
     - [ ] `Projeto`, `TipoEvento`, `Municipio`
     - [ ] `Participation`, `Deslocamento`
     - [ ] `AuditLog`, `ConfigEntry`, `Formador`
     - [ ] Todas com QuerySets tipados

2. [ ] `apps/dat_ingest/models.py` (1h)
   - [ ] `AcaoControle`, `AcaoDAT`
   - [ ] Managers customizados

3. [ ] `apps/core/models_*.py` (3h - arquivos adicionais)
   - [ ] Modelos auxiliares se existirem
   - [ ] QuerySets e managers customizados

**Type Patterns**:
```python
# Self para métodos que retornam instância
from typing import Self

class Solicitacao(models.Model):
    def aprovar(self) -> Self:
        self.status = "aprovado"
        self.save()
        return self

# QuerySet tipado
@classmethod
def pendentes(cls) -> models.QuerySet[Self]:
    return cls.objects.filter(status="pendente")
```

**Entregáveis**:
- [ ] 5 arquivos de models 100% tipados (1,017+ linhas em models.py principal)
- [ ] Managers customizados tipados
- [ ] QuerySets tipados em todos os métodos
- [ ] Pyright: 0 erros em models

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/*/models.py`
- [ ] Migrations não afetadas
- [ ] Testes passando
- [ ] CI verde

---

### Fase 4: Serializers (30h)

#### PR #4: Type Hints em Serializers
**Branch**: `feat/typehints-serializers`
**Tempo**: 30h (serializers.py principal tem 562 linhas + arquivos adicionais)
**Depende de**: PR #3
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (1 arquivo principal + múltiplos auxiliares):

1. [ ] `apps/core/serializers.py` (arquivo principal - 14h - 562 linhas)

   **Serializers principais** (562 linhas - 14h):
   - [ ] `SolicitacaoSerializer` (4h)
     - Generic: `ModelSerializer[Solicitacao]`
     - `get_fluxo()` → `str`
     - `validate_inicio()` → `datetime`
     - `validate()` → `dict[str, Any]`
     - `create()` → `Solicitacao`
     - `update()` → `Solicitacao`

   - [ ] `AvailabilityBlockSerializer` (2h)
     - Validações de overlap
     - Métodos de data/hora

   - [ ] `UsuarioSerializer` (2h)
     - Campos read-only
     - Métodos de grupos

   - [ ] `ParticipationSerializer` (2h)
     - guest_email logic
     - Validações de role

   - [ ] `ProjetoSerializer`, `MunicipioSerializer`, `TipoEventoSerializer` (2h)
   - [ ] Outros serializers no arquivo (2h)

2-N. [ ] Arquivos serializers adicionais (16h)
   - [ ] Serializers de availability (4h)
   - [ ] Serializers OAuth (4h)
   - [ ] Serializers GCal (4h)
   - [ ] Serializers dat_ingest (2h)
   - [ ] Outros serializers auxiliares (2h)

**TypedDicts Criados**:
```python
# v2/backend/apps/core/types.py

class ValidatedSolicitacaoData(TypedDict):
    tipo_evento: TipoEvento
    municipio: Municipio
    projeto: Projeto
    inicio: datetime
    fim: datetime
    descricao: str | None
    is_online: bool

class GCalEventPayload(TypedDict):
    summary: str
    start: dict[str, str]
    end: dict[str, str]
    conferenceData: NotRequired[dict[str, Any]]
```

**Entregáveis**:
- [ ] Serializers 100% tipados (562 linhas no principal + auxiliares)
- [ ] TypedDicts para validated_data
- [ ] Generic ModelSerializer[Model]
- [ ] Pyright: 0 erros em serializers

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/*/serializers*.py`
- [ ] API responses não alteradas
- [ ] Testes de serialização passando
- [ ] CI verde

---

### Fase 5: Views (14h)

#### PR #5: Type Hints em Views
**Branch**: `feat/typehints-views`
**Tempo**: 14h (21 arquivos de views, views.py principal tem 981 linhas)
**Depende de**: PR #4
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (21 arquivos reais do projeto):

1. [ ] `apps/core/views.py` (4h - 981 linhas, arquivo principal)

   **ViewSets principais** (981 linhas - 4h):
   - [ ] `SolicitacaoViewSet`
     - Generic: `ModelViewSet[Solicitacao]`
     - `get_queryset()` → `models.QuerySet[Solicitacao]`
     - `approve()`, `reject()` actions
   - [ ] `AvailabilityBlockViewSet`
   - [ ] Outros ViewSets principais

2-21. [ ] Arquivos views adicionais (10h - ~0.5h cada)
   - [ ] `views_availability.py` - Check conflicts, monthly grid
   - [ ] `views_auth.py` - Auth/login views
   - [ ] `views_oauth.py` - OAuth flow
   - [ ] `views_gcal.py` - Google Calendar operations
   - [ ] `views_solicitacao.py` - Solicitação específicas
   - [ ] `views_controle.py` - Controle views
   - [ ] `views_dat.py` - DAT views
   - [ ] `views_reports.py` - Relatórios
   - [ ] `views_metrics.py` - Métricas
   - [ ] `views_admin.py` - Admin customizado
   - [ ] Outros 11 arquivos de views

**Type Patterns**:
```python
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action

class SolicitacaoViewSet(viewsets.ModelViewSet[Solicitacao]):
    def get_queryset(self) -> models.QuerySet[Solicitacao]:
        ...

    @action(detail=True, methods=["post"])
    def aprovar(self, request: Request, pk: int | None = None) -> Response:
        ...
```

**Entregáveis**:
- [ ] 21 arquivos de views 100% tipados (981 linhas em views.py principal)
- [ ] ViewSets com Generic[Model]
- [ ] Request/Response tipados
- [ ] Pyright: 0 erros em views

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/*/views*.py`
- [ ] API endpoints funcionando
- [ ] Testes de views passando
- [ ] CI verde

---

### Fase 6: Tasks (Celery) (26h)

#### PR #6: Type Hints em Celery Tasks
**Branch**: `feat/typehints-tasks`
**Tempo**: 26h (tasks.py principal tem 489 linhas)
**Depende de**: PR #5
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (1 arquivo principal + auxiliares):

1. [ ] `apps/core/tasks.py` (10h - 489 linhas)

   **Tasks principais** (489 linhas - 10h):
   - [ ] `task_publish_solicitacao_to_gcal` (3h)
     - Parâmetros: `solicitacao_id: int`, `dry_run: bool`
     - Retorno: `dict[str, Any]`
     - Retry logic tipada

   - [ ] `task_cancel_solicitacao_from_gcal` (2h)
   - [ ] `preview_then_apply_gcal` (3h)
   - [ ] `debug_task`, `gcal_sync_task` (2h)

2. [ ] `apps/dat_ingest/tasks.py` (8h)
   - [ ] ETL tasks
   - [ ] Batch processing

3. [ ] `config/celery.py` (6h)
   - [ ] Configuração Celery tipada
   - [ ] Beat schedule

4. [ ] Celery helpers/utils (2h)
   - [ ] Retry decorators
   - [ ] Task utilities

**Type Patterns**:
```python
from celery import shared_task
from typing import Any

@shared_task(bind=True)
def task_publish_to_gcal(
    self,
    solicitacao_id: int,
    dry_run: bool = False
) -> dict[str, Any]:
    try:
        resultado = processar(solicitacao_id)
        return {"status": "success", "data": resultado}
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
        return {"status": "error", "message": str(exc)}
```

**Entregáveis**:
- [ ] Tasks 100% tipados (489 linhas no principal)
- [ ] Retry logic tipada
- [ ] Task results tipados com TypedDict
- [ ] Pyright: 0 erros em tasks

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/*/tasks.py`
- [ ] Worker funcionando
- [ ] Beat schedule ok
- [ ] CI verde

---

### Fase 7: Tests (6h)

#### PR #7: Type Hints em Fixtures e Helpers
**Branch**: `feat/typehints-tests`
**Tempo**: 6h (82 arquivos de testes - foco em fixtures e helpers)
**Depende de**: PR #6
**Reviewers**: @matheusnorjosa

**Arquivos Alvo** (foco em fixtures, não nos testes individuais):

1. [ ] `apps/core/tests/conftest.py` (2h)
   - [ ] Tipar fixtures pytest
   - [ ] Tipar factories

2. [ ] `apps/core/tests/factories.py` (1h)
   - [ ] Tipar Factory Boy factories (se existir)

3. [ ] `apps/core/tests/utils.py` (1h)
   - [ ] Tipar helper functions

4. [ ] `apps/dat_ingest/tests/conftest.py` (1h)
   - [ ] Fixtures ETL

5. [ ] Atualizar `pyproject.toml` (1h)
   - [ ] Remover `exclude = "**/tests"` (opcional)
   - [ ] Incluir fixtures no type checking

**Nota**: Os 82 arquivos de testes NÃO precisam ser 100% tipados (testes são menos críticos). Foco em fixtures e helpers reutilizáveis.

**Type Patterns**:
```python
import pytest
from typing import Generator

@pytest.fixture
def usuario_coordenador() -> Usuario:
    return Usuario.objects.create(username="coord1")

@pytest.fixture
def solicitacao_factory() -> Generator[Callable[..., Solicitacao], None, None]:
    def _factory(**kwargs: Any) -> Solicitacao:
        return Solicitacao.objects.create(**kwargs)
    yield _factory
```

**Entregáveis**:
- [ ] Fixtures 100% tipadas
- [ ] Factories tipadas
- [ ] Test helpers tipados
- [ ] Pyright: 0 erros em tests

**Merge Criteria**:
- [ ] Pyright strict: 0 erros em `apps/*/tests/`
- [ ] Testes rodando normalmente
- [ ] CI verde

---

### Fase 8: Polish & Documentation (18h)

#### PR #8: Finalização e Documentação
**Branch**: `feat/typehints-final`
**Tempo**: 18h (27 management commands + polish + docs)
**Depende de**: PR #7
**Reviewers**: @matheusnorjosa + equipe

**Tarefas**:

1. [ ] Revisar e corrigir (6h)
   - [ ] Rodar Pyright em todo o projeto
   - [ ] Corrigir erros restantes
   - [ ] Refatorar tipos complexos
   - [ ] Adicionar type aliases faltantes

2. [ ] Management Commands (6h)
   - [ ] Tipar 27 commands em `management/commands/`
   - [ ] Foco em ETL commands (critical)
   - [ ] Commands de import/export
   - [ ] ~15min por command em média

3. [ ] Config e Utils (2h)
   - [ ] `config/settings.py` (type hints em configs)
   - [ ] `config/urls.py` (se aplicável)
   - [ ] Utility modules

4. [ ] Documentação (4h)
   - [ ] Atualizar `TYPE_HINTS_REFERENCE_FULL.md`
   - [ ] Criar `TYPE_HINTS_BEST_PRACTICES.md`
   - [ ] Atualizar `.claude/CLAUDE.md`
   - [ ] Criar guia de contribuição
   - [ ] Exemplos práticos por módulo

**Checklist Final**:
- [ ] Pyright strict: 0 erros em código crítico (65/186 arquivos = 35%)
- [ ] CI verde em todos os workflows
- [ ] Coverage de type hints: 100% em:
  - [ ] 24 services (~7,192 linhas)
  - [ ] 5 models (1,017+ linhas)
  - [ ] Serializers (562+ linhas)
  - [ ] 21 views (981+ linhas)
  - [ ] Tasks (489 linhas)
  - [ ] 27 management commands
- [ ] Documentação completa
- [ ] Apresentação para equipe

**Entregáveis**:
- [ ] 65 arquivos críticos 100% tipados (35% do projeto)
- [ ] ~12,000+ linhas de código tipadas
- [ ] Documentação completa
- [ ] Guia de boas práticas
- [ ] Pyright strict: 0 erros em código crítico

**Merge Criteria**:
- [ ] Pyright strict pass
- [ ] 100% CI verde
- [ ] Code review completo
- [ ] Aprovação de 2+ reviewers
- [ ] Documentação aprovada

---

## 📈 PARTE 4: TRACKING E MÉTRICAS

### Dashboard de Progresso

```
┌─────────────────────────────────────────────────────────────┐
│         TYPE HINTS IMPLEMENTATION - PROGRESS TRACKER         │
│              Baseado em 186 arquivos Python                  │
└─────────────────────────────────────────────────────────────┘

[████░░░░░░░░░░░░░░░░░░░░░░░░] Services      16% (4/24 arquivos, ~7,192 linhas)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Models         0% (0/5 arquivos, 1,017+ linhas)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Serializers    0% (0/1+ arquivos, 562+ linhas)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Views          0% (0/21 arquivos, 981+ linhas)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Tasks          0% (0/1+ arquivos, 489 linhas)
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] Commands       0% (0/27 arquivos)

─────────────────────────────────────────────────────────────
Total Progress:         ~6% (4 services parciais de 65 críticos)
Pyright Errors:         ??? → 0 (target: código crítico apenas)
Estimated Completion:   2025-12-01 (3.6 semanas)
Arquivos Críticos:      65/186 (35% do projeto = meta de cobertura)
─────────────────────────────────────────────────────────────
```

### Métricas por PR (Dados Reais)

| PR | Arquivos | Linhas (est.) | Tempo | Status | Data Target |
|----|----------|---------------|-------|--------|-------------|
| #1 | 3 | 150 | 4h | ⏳ Pending | 2025-11-15 |
| #2 | 24 | ~7,192 | 36h | ⏳ Pending | 2025-11-22 |
| #3 | 5 | ~1,017+ | 10h | ⏳ Pending | 2025-11-25 |
| #4 | 1+ | ~562+ | 30h | ⏳ Pending | 2025-11-29 |
| #5 | 21 | ~981+ | 14h | ⏳ Pending | 2025-12-02 |
| #6 | 1+ | ~489 | 26h | ⏳ Pending | 2025-12-05 |
| #7 | 4 | ~600 | 6h | ⏳ Pending | 2025-12-06 |
| #8 | 27+ | ~2,000 | 18h | ⏳ Pending | 2025-12-08 |

**Total Real**: 86+ arquivos, ~12,000+ linhas de código crítico

---

## ✅ PARTE 5: CRITÉRIOS DE ACEITAÇÃO

### Por PR

**Todos os PRs devem atender**:
- [ ] Pyright strict: 0 erros nos arquivos modificados
- [ ] Todos os testes existentes passando
- [ ] CI verde (lint + tests + typecheck)
- [ ] Code review aprovado (1+ reviewer)
- [ ] Documentação atualizada (se aplicável)
- [ ] Sem regressões de funcionalidade

### Global (Após PR #8)

- [ ] **Pyright strict**: 0 erros em todo o projeto
- [ ] **Coverage**: 100% em services, models, serializers, views, tasks
- [ ] **CI**: Type check automático em todos os PRs futuros
- [ ] **Documentação**: Guia completo de type hints
- [ ] **VS Code**: Autocomplete perfeito (Pylance)
- [ ] **Onboarding**: Novos devs conseguem entender tipos
- [ ] **Manutenção**: Refatorações seguras com type checking

---

## 🎯 PARTE 6: RISCOS E MITIGAÇÕES

### Riscos Identificados

#### Risco 1: Complexidade de Tipos Django
**Probabilidade**: Média (40%)
**Impacto**: Médio
**Mitigação**:
- Usar `django-types` oficial
- Consultar repositório `typeddjango/django-stubs`
- Criar stubs customizados se necessário

#### Risco 2: Tipos `Any` Excessivos
**Probabilidade**: Alta (60%)
**Impacto**: Alto (derrota propósito)
**Mitigação**:
- Revisar todos os `Any` no code review
- Preferir `dict[str, Any]` a `Any` puro
- Documentar quando `Any` é inevitável

#### Risco 3: Regressões em Funcionalidade
**Probabilidade**: Baixa (20%)
**Impacto**: Alto
**Mitigação**:
- Rodar suite completa de testes em cada PR
- CI obrigatório verde
- Review rigoroso

#### Risco 4: Tempo Subestimado
**Probabilidade**: Média (40%)
**Impacto**: Médio
**Mitigação**:
- Buffer de 20% em cada fase
- Revisar estimativas após PR #2
- Ajustar timeline se necessário

---

## 📚 PARTE 7: RECURSOS E REFERÊNCIAS

### Documentação Oficial
- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 695 - Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Django-Types](https://github.com/sbdchd/django-types)
- [DRF-Types](https://github.com/sbdchd/djangorestframework-types)

### Repositório de Referência
- [luizomf/typehints_python](https://github.com/luizomf/typehints_python)
  - 47 exemplos progressivos
  - Pyright strict mode
  - Python 3.13 patterns

### Ferramentas
- **Pyright**: Type checker (strict mode)
- **Pylance**: VS Code extension
- **django-types**: Type stubs Django
- **mypy**: Alternativa (não usaremos)

---

## 🎉 PARTE 8: CELEBRAÇÃO E RETROSPECTIVA

### Após PR #4 (Milestone 50%)
- [ ] Apresentação interna: "Type Hints em Ação"
- [ ] Demonstrar autocomplete melhorado
- [ ] Mostrar bugs evitados

### Após PR #8 (Milestone 100%)
- [ ] Release: v2025.12.08-typehints
- [ ] Blog post: "100% Type Safe Django"
- [ ] Retrospectiva de equipe
- [ ] Atualizar README com badge Pyright

---

**Documento Criado**: 10 de Novembro de 2025
**Última Atualização**: 11 de Novembro de 2025 (ajustado com dados reais)
**Autor**: Claude Code
**Versão**: 2.0 (com análise real da plataforma)
**Status**: Aguardando Aprovação

**Baseline Real da Plataforma**:
- 186 arquivos Python (excl. migrations, __pycache__)
- 24 services (~7,192 linhas)
- 5 models (1,017+ linhas)
- 1+ serializers (562+ linhas)
- 21 views (981+ linhas)
- 1+ tasks (489 linhas)
- 82 testes
- 27 management commands

**Meta Ajustada**: 65 arquivos críticos (35% do projeto) = ~12,000+ linhas
**Tempo Total**: 144h (3.6 semanas)

**Próximo Passo**: Criar PR #1 (Setup Pyright + CI)
