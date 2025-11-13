# 🐍 Proposta: Type Hints com Pyright (Baseada em luizomf/typehints_python)

**Data**: 10 de Novembro de 2025
**Baseado em**: https://github.com/luizomf/typehints_python
**Python**: 3.12 (PEP 695 disponível ✅)

---

## 📊 Situação Atual

### Cobertura de Type Hints
- **16% de arquivos** com type hints (24/150)
- **Inconsistente**: Bom em services, ruim em views/serializers
- **Sem type checker**: mypy instalado mas não configurado
- **Sem CI**: Nenhuma validação automática

### Ferramentas Instaladas
```txt
mypy==1.11.2  # Instalado mas não configurado
# Sem pyright
# Sem django-stubs/django-types
```

---

## 🎯 Proposta: Pyright Strict Mode

Inspirado no repositório **luizomf/typehints_python**, proposta de implementar **Pyright em modo strict** ao invés de mypy.

### Por Que Pyright?

#### Vantagens vs Mypy
1. **Performance**: 2-5x mais rápido
2. **Modo Strict**: Configuração rigorosa desde o início
3. **PEP 695**: Suporte nativo à sintaxe Python 3.12
4. **VS Code**: Integração perfeita (Pylance = Pyright)
5. **Menos Configuração**: Funciona out-of-the-box

#### Pyright + Django
- ✅ **django-types** disponível (alternativa a django-stubs)
- ✅ **djangorestframework-types** disponível
- ✅ Suporte oficial para Django models

---

## 📋 Plano de Implementação (64h)

### Fase 1: Setup Pyright (4h) ⭐ QUICK WIN

#### 1.1 Instalar Dependências
```bash
cd v2/backend
pip install pyright django-types djangorestframework-types types-requests
pip freeze > requirements-dev.txt
```

#### 1.2 Criar pyproject.toml
```toml
# v2/backend/pyproject.toml
[tool.pyright]
# Configuração baseada em luizomf/typehints_python
typeCheckingMode = "strict"
pythonVersion = "3.12"
venvPath = "."
venv = ".venv"
useLibraryCodeForTypes = true

# Diretórios para verificar
include = ["apps/core", "apps/dat_ingest"]

# Ignorar temporariamente (baseline)
exclude = [
    "**/__pycache__",
    "**/migrations",
    "**/tests",
]

# Django settings
stubPath = "typings"

[tool.pyright.executionEnvironments]
[[tool.pyright.executionEnvironments]]
root = "."
pythonVersion = "3.12"
extraPaths = ["apps"]
```

#### 1.3 Adicionar ao CI
```yaml
# .github/workflows/v2-ci.yml
- name: Type check with Pyright
  run: |
    cd v2/backend
    pip install pyright django-types djangorestframework-types
    pyright apps/core apps/dat_ingest
```

#### 1.4 Criar Baseline
```bash
# Gerar relatório inicial (aceitar erros existentes)
pyright --outputjson > pyright-baseline.json
```

---

### Fase 2: Services (16h)

Começar pelos **services** (já têm boa base de type hints):

#### 2.1 availability_service.py (Já 80% feito)
```python
# apps/core/services/availability_service.py
from typing import Literal
from dataclasses import dataclass
from datetime import datetime

# PEP 695: Sintaxe moderna
type Code = Literal["X", "T", "P", "D", "M"]

@dataclass
class ConflictDetail:
    code: Code
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

    # Implementação...

    return AvailabilityResult(
        ok=len(conflicts) == 0,
        conflicts=conflicts,
    )
```

#### 2.2 gcal_sync_service.py (Adicionar tipos)
```python
# apps/core/services/gcal_sync_service.py
from typing import TypedDict, NotRequired
from datetime import datetime

# PEP 695: Type alias moderno
type EventId = str
type CalendarId = str

class GCalEventPayload(TypedDict):
    summary: str
    start: dict[str, str]
    end: dict[str, str]
    conferenceData: NotRequired[dict[str, Any]]

class GCalSyncService:
    def build_payload(
        self,
        solicitacao: Solicitacao,
        *,
        include_meet_link: bool = True,
    ) -> GCalEventPayload:
        """Constrói payload para Google Calendar API."""
        ...
```

#### 2.3 gcal_google_client.py (Adicionar protocols)
```python
# apps/core/services/gcal_google_client.py
from typing import Protocol, Any
from google.oauth2.credentials import Credentials

# Protocol para duck typing
class GCalClient(Protocol):
    def create_event(
        self,
        calendar_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        ...

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        ...

class GoogleCalendarClient:
    def __init__(self, credentials: Credentials) -> None:
        self._credentials = credentials
        self._service: Any = None  # googleapiclient.discovery.Resource

    def create_event(
        self,
        calendar_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        ...
```

---

### Fase 3: Models (12h)

#### 3.1 Adicionar Type Hints aos Métodos
```python
# apps/core/models.py
from typing import Literal, Self
from datetime import datetime

class Solicitacao(models.Model):
    # Fields já estão ok (Django types)

    def mark_gcal(
        self,
        *,
        status: Literal["pending", "synced", "error"],
        payload_hash: str | None = None,
        error: str | None = None,
        sync_at: datetime | None = None,
        meet_link: str | None = None,
    ) -> None:
        """Marca status de sincronização com Google Calendar."""
        self.gcal_status = status
        if payload_hash:
            self.gcal_payload_hash = payload_hash
        if error:
            self.gcal_error = error
        if sync_at:
            self.gcal_sync_at = sync_at
        if meet_link:
            self.meet_link = meet_link
        self.save(update_fields=[
            "gcal_status",
            "gcal_payload_hash",
            "gcal_error",
            "gcal_sync_at",
            "meet_link",
        ])

    @classmethod
    def filter_by_status(
        cls,
        status: Literal["pendente", "aprovado", "reprovado"],
    ) -> models.QuerySet[Self]:
        """Filtra solicitações por status."""
        return cls.objects.filter(status=status)
```

---

### Fase 4: Serializers (16h)

#### 4.1 SolicitacaoSerializer
```python
# apps/core/serializers.py
from rest_framework import serializers
from typing import Any, TypedDict

class ValidatedSolicitacaoData(TypedDict):
    tipo_evento: TipoEvento
    municipio: Municipio
    projeto: Projeto
    inicio: datetime
    fim: datetime
    descricao: str | None
    is_online: bool

class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
    meet_link = serializers.CharField(read_only=True)
    fluxo = serializers.SerializerMethodField()

    def get_fluxo(self, obj: Solicitacao) -> str:
        return obj.projeto.fluxo if obj.projeto else "NAO_SUPER"

    def validate_inicio(self, value: datetime) -> datetime:
        """Valida data de início."""
        if value < timezone.now():
            raise serializers.ValidationError(
                "Data de início não pode ser no passado"
            )
        return value

    def validate(self, attrs: dict[str, Any]) -> ValidatedSolicitacaoData:
        """Validação cross-field."""
        inicio = attrs.get("inicio")
        fim = attrs.get("fim")

        if inicio and fim and fim <= inicio:
            raise serializers.ValidationError({
                "fim": "Data de fim deve ser após o início"
            })

        return attrs  # type: ignore[return-value]

    def create(self, validated_data: ValidatedSolicitacaoData) -> Solicitacao:
        """Cria nova solicitação."""
        return Solicitacao.objects.create(**validated_data)
```

---

### Fase 5: Views (12h)

#### 5.1 SolicitacaoViewSet
```python
# apps/core/views.py
from rest_framework import viewsets, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import action
from typing import Any

class SolicitacaoViewSet(viewsets.ModelViewSet[Solicitacao]):
    queryset = Solicitacao.objects.all()
    serializer_class = SolicitacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> models.QuerySet[Solicitacao]:
        """Filtra solicitações por usuário."""
        user = self.request.user
        if user.is_superuser or user.groups.filter(
            name__in=["Superintendência", "Controle"]
        ).exists():
            return Solicitacao.objects.all()
        return Solicitacao.objects.filter(usuario=user)

    @action(detail=True, methods=["post"], permission_classes=[IsSuperintendencia])
    def approve(self, request: Request, pk: int | None = None) -> Response:
        """Aprova solicitação (PA-02)."""
        solicitacao = self.get_object()
        justificativa = request.data.get("justificativa", "")

        if solicitacao.status != "pendente":
            return Response(
                {"detail": "Solicitação já foi processada"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Aprovar...
        solicitacao.status = "aprovado"
        solicitacao.save()

        # Audit log (PA-05)
        AuditLog.objects.create(
            usuario=request.user,
            action="APPROVE",
            model_name="Solicitacao",
            details={
                "solicitacao_id": solicitacao.id,
                "justificativa": justificativa,
            },
        )

        return Response(
            SolicitacaoSerializer(solicitacao).data,
            status=status.HTTP_200_OK,
        )
```

---

### Fase 6: Validação e CI (4h)

#### 6.1 Rodar Pyright Localmente
```bash
cd v2/backend
pyright apps/core apps/dat_ingest
```

#### 6.2 Corrigir Erros Críticos
```bash
# Gerar relatório detalhado
pyright --outputjson > pyright-report.json
python scripts/analyze_pyright_report.py
```

#### 6.3 CI Verde
```bash
# Garantir que CI passa
gh pr checks --watch
```

---

## 📊 Comparação: Mypy vs Pyright

| Critério | Mypy | Pyright | Vencedor |
|----------|------|---------|----------|
| **Performance** | 🟡 Moderado | 🟢 Rápido (2-5x) | Pyright |
| **Django** | 🟢 django-stubs | 🟡 django-types | Mypy |
| **PEP 695** | 🟡 Parcial | 🟢 Nativo | Pyright |
| **VS Code** | 🟡 Plugin | 🟢 Pylance | Pyright |
| **Strict Mode** | 🟡 Manual | 🟢 Built-in | Pyright |
| **Comunidade** | 🟢 Grande | 🟡 Crescendo | Mypy |
| **Setup** | 🟡 Complexo | 🟢 Simples | Pyright |

**Recomendação**: Pyright (como luizomf/typehints_python)

---

## 🎯 Estimativas de Tempo

### Opção 1: Implementação Completa (64h)
- Fase 1: Setup (4h)
- Fase 2: Services (16h)
- Fase 3: Models (12h)
- Fase 4: Serializers (16h)
- Fase 5: Views (12h)
- Fase 6: Validação (4h)

### Opção 2: Piloto Incremental (20h)
- Fase 1: Setup (4h)
- Fase 2: Services (16h) ← Parar aqui, validar
- Fases 3-6: PRs futuros

### Opção 3: Quick Win (4h) ⭐ RECOMENDADO
- Só setup + CI
- Type hints em PRs futuros (gradual)

---

## 🚀 Benefícios Esperados

### Imediato (Após Setup)
- ✅ Autocomplete melhor no VS Code (Pylance)
- ✅ Erros de tipo detectados antes de rodar
- ✅ Documentação implícita (type hints)

### Curto Prazo (Após Services)
- ✅ Menos bugs em `availability_service.py` (RF03)
- ✅ Refatoração mais segura
- ✅ Onboarding de novos devs mais rápido

### Longo Prazo (Após 100%)
- ✅ Código self-documenting
- ✅ Refatoração com confiança
- ✅ Integração com ferramentas (IDEs, linters)

---

## 📚 Recursos de Referência

### Repositório Base
- **GitHub**: https://github.com/luizomf/typehints_python
- **YouTube**: Playlist Type Hints no Python
- **Autor**: Otávio Miranda (otaviomiranda.com.br)

### Documentação Oficial
- [PEP 695 - Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [Django-Types](https://github.com/sbdchd/django-types)
- [DRF-Types](https://github.com/sbdchd/djangorestframework-types)

### Ferramentas
- **Pyright**: Type checker
- **Pylance**: VS Code extension (powered by Pyright)
- **django-types**: Type stubs para Django
- **djangorestframework-types**: Type stubs para DRF

---

## 🤔 Decisão Requerida

Qual abordagem você prefere?

### A) **Quick Win (4h)** ⭐ RECOMENDADO
- Setup Pyright + CI agora
- Type hints gradualmente em PRs futuros
- Baixo risco, retorno imediato

### B) **Piloto (20h)**
- Setup + Services completos
- Validar abordagem antes de escalar
- Médio risco, retorno visível

### C) **Implementação Completa (64h)**
- Fazer tudo de uma vez
- Cobertura 35% crítico
- Alto investimento, máximo retorno

### D) **Postergar**
- Focar em Issue #105 (testes 403) primeiro
- Type hints depois

---

## ✅ Próximos Passos (Se Aprovado)

1. [ ] Criar branch `feat/typehints-pyright-setup`
2. [ ] Instalar pyright + django-types
3. [ ] Criar `pyproject.toml` com config
4. [ ] Adicionar step no CI
5. [ ] Criar baseline (aceitar erros existentes)
6. [ ] PR com setup + documentação
7. [ ] Escolher fase 2 (services, models, etc)

**Aguardando aprovação para prosseguir.**
