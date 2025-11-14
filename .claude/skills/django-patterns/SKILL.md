---
name: django-patterns
description: Django and DRF implementation patterns for AS v2. Use when implementing models, serializers, views, services, and other Django components. Covers SSOT, constraints, permissions, testing, and performance optimization.
---

# Django/DRF Patterns — Aprender Sistema v2

## 🎯 Purpose

This skill provides implementation patterns for Django 5.1 + DRF 3.14+ specific to Aprender Sistema v2. Use this when:
- Creating or modifying models
- Implementing serializers (read/write separation)
- Writing views/viewsets
- Organizing business logic (services layer)
- Setting up permissions (RBAC)
- Optimizing queries (N+1 prevention)

---

## 📋 Quick Reference

| Task | Pattern | Example |
|------|---------|---------|
| **Model** | SSOT + Constraints + Indexes | `Solicitacao` |
| **Serializer (Read)** | StringRelatedField | `SolicitacaoReadSerializer` |
| **Serializer (Write)** | PrimaryKeyRelatedField | `SolicitacaoWriteSerializer` |
| **View** | Thin controller | Logic in services |
| **Service** | Type hints + Early returns | `availability_service.py` |
| **Permission** | Custom class | `IsSuperintendencia` |
| **Query** | select_related/prefetch | Avoid N+1 |

---

## 🗄️ Models (SSOT - Single Source of Truth)

### Core Principles

1. **Models = Business Logic**: Constraints, validation, and business rules belong in the database
2. **Explicit > Implicit**: Use verbose field names and help_text
3. **Timezone-aware**: Always use `America/Fortaleza` via `settings.TIME_ZONE`
4. **Indexes**: Add for filter/order fields
5. **related_name**: Always explicit and descriptive

### Model Template

```python
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import datetime
from zoneinfo import ZoneInfo


class ExampleModel(models.Model):
    """
    Brief description of the model.

    Business Rules:
    - Rule 1 (e.g., RD-01: Non-overlapping)
    - Rule 2 (e.g., CP-02: Manual approval required)

    Relationships:
    - FK to Usuario (solicitante)
    - M2M to Usuario (participantes)
    """

    # Primary fields
    nome = models.CharField(
        max_length=200,
        verbose_name="Nome",
        help_text="Nome descritivo do exemplo"
    )

    # Foreign Keys (always with related_name)
    solicitante = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,  # PROTECT prevents accidental deletion
        related_name='exemplos_solicitados',
        verbose_name="Solicitante"
    )

    # DateTimeField (timezone-aware)
    inicio = models.DateTimeField(
        verbose_name="Data/Hora de Início",
        help_text="Timezone: America/Fortaleza"
    )

    # Choices (use TextChoices)
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADO = 'aprovado', 'Aprovado'
        REPROVADO = 'reprovado', 'Reprovado'

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
        verbose_name="Status"
    )

    # Validators
    prioridade = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3,
        verbose_name="Prioridade"
    )

    # Timestamps (always include)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Exemplo"
        verbose_name_plural = "Exemplos"
        ordering = ['-created_at']

        # Constraints (business logic in DB)
        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F('inicio')),
                name='valid_time_range'
            ),
            models.UniqueConstraint(
                fields=['solicitante', 'inicio'],
                name='unique_solicitante_inicio'
            )
        ]

        # Indexes (for filter/order fields)
        indexes = [
            models.Index(fields=['status', 'inicio']),
            models.Index(fields=['solicitante', '-created_at'])
        ]

    def clean(self):
        """
        Model-level validation (runs before save).

        Validates business rules that can't be expressed in DB constraints.
        """
        super().clean()

        # Example: Custom validation
        if self.inicio and self.fim and self.fim <= self.inicio:
            raise ValidationError({
                'fim': 'Fim deve ser posterior ao início'
            })

    def save(self, *args, **kwargs):
        """
        Override save for business logic.

        IMPORTANT: Call full_clean() to run validators + clean().
        """
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome} ({self.status})"
```

### Key Patterns

#### 1. Foreign Key on_delete Options

```python
# PROTECT: Prevent deletion if referenced (recommended for business data)
usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)

# CASCADE: Delete dependents (use for truly dependent data)
participacao = models.ForeignKey(Solicitacao, on_delete=models.CASCADE)

# SET_NULL: Set to NULL (use when optional + historical)
aprovador = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)

# DO_NOTHING: No action (AVOID - can break referential integrity)
```

#### 2. Timezone Handling

```python
from django.utils import timezone
from zoneinfo import ZoneInfo

# ALWAYS use timezone-aware datetimes
TZ_FORTALEZA = ZoneInfo('America/Fortaleza')

# Creating
inicio = timezone.now().astimezone(TZ_FORTALEZA)

# Querying (Django ORM handles conversion)
Solicitacao.objects.filter(inicio__date=datetime(2025, 1, 15).date())

# Display (convert to local TZ)
solicitacao.inicio.astimezone(TZ_FORTALEZA).strftime('%d/%m/%Y %H:%M')
```

#### 3. Constraints vs Validators

**Constraints** (DB-level, preferred):
```python
constraints = [
    models.CheckConstraint(
        check=models.Q(prioridade__gte=1) & models.Q(prioridade__lte=5),
        name='valid_prioridade'
    )
]
```

**Validators** (Python-level, for complex logic):
```python
from django.core.validators import MinValueValidator

prioridade = models.IntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
)
```

**Rule of thumb**: Use constraints when possible (faster, enforced at DB level). Use validators for logic that requires Python (e.g., external API calls).

---

## 📦 Serializers (DRF)

### Read vs Write Separation

**Why separate?**
- **Read**: User-friendly (strings, nested objects)
- **Write**: Efficient (IDs only, validation)

### Serializer Template

```python
from rest_framework import serializers
from apps.core.models import Solicitacao, Usuario, Municipio


# READ Serializer (for GET requests)
class SolicitacaoReadSerializer(serializers.ModelSerializer):
    """
    Read-only serializer with user-friendly representations.

    Usage: GET /api/solicitacoes/
    """

    # StringRelatedField: Uses model's __str__()
    solicitante = serializers.StringRelatedField()
    municipio = serializers.StringRelatedField()

    # SerializerMethodField: Custom formatting
    inicio_formatado = serializers.SerializerMethodField()

    # Nested serializer (careful: N+1 queries)
    participantes = UsuarioReadSerializer(many=True, read_only=True)

    class Meta:
        model = Solicitacao
        fields = [
            'id', 'solicitante', 'municipio', 'inicio', 'fim',
            'inicio_formatado', 'status', 'participantes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_inicio_formatado(self, obj):
        """Format inicio for Brazilian locale."""
        from zoneinfo import ZoneInfo
        tz = ZoneInfo('America/Fortaleza')
        return obj.inicio.astimezone(tz).strftime('%d/%m/%Y %H:%M')


# WRITE Serializer (for POST/PUT/PATCH)
class SolicitacaoWriteSerializer(serializers.ModelSerializer):
    """
    Write serializer with validation.

    Usage: POST /api/solicitacoes/, PUT /api/solicitacoes/{id}/
    """

    # PrimaryKeyRelatedField: Accept IDs, validate existence
    solicitante = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(is_active=True)
    )

    municipio = serializers.PrimaryKeyRelatedField(
        queryset=Municipio.objects.filter(ativo=True)
    )

    participantes = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Usuario.objects.filter(is_active=True),
        required=False
    )

    class Meta:
        model = Solicitacao
        fields = [
            'solicitante', 'municipio', 'inicio', 'fim',
            'status', 'participantes', 'observacao'
        ]

    def validate_inicio(self, value):
        """Validate inicio is in the future."""
        from django.utils import timezone
        if value < timezone.now():
            raise serializers.ValidationError(
                "Início deve ser no futuro"
            )
        return value

    def validate(self, data):
        """
        Cross-field validation.

        Runs AFTER individual field validation.
        """
        if data['fim'] <= data['inicio']:
            raise serializers.ValidationError({
                'fim': 'Fim deve ser posterior ao início'
            })
        return data

    def create(self, validated_data):
        """
        Override create for custom logic.

        Example: Extract M2M before creation.
        """
        participantes = validated_data.pop('participantes', [])

        solicitacao = Solicitacao.objects.create(**validated_data)

        # Add M2M relationships
        solicitacao.participantes.set(participantes)

        return solicitacao
```

### Key Patterns

#### 1. Validation Levels

```python
# Level 1: Field validators
inicio = serializers.DateTimeField(
    validators=[validate_future_date]
)

# Level 2: validate_<field>()
def validate_inicio(self, value):
    if value < timezone.now():
        raise serializers.ValidationError("Must be future")
    return value

# Level 3: validate() (cross-field)
def validate(self, data):
    if data['fim'] <= data['inicio']:
        raise serializers.ValidationError("Invalid range")
    return data
```

#### 2. Read-Only Fields

```python
# Make field read-only in serializer
meet_link = serializers.CharField(read_only=True)

# Or in Meta
class Meta:
    read_only_fields = ['id', 'meet_link', 'created_at']
```

#### 3. Nested Writes (Complex)

```python
# Avoid nested writes when possible (use separate endpoints)
# If needed:

def create(self, validated_data):
    nested_data = validated_data.pop('nested_field')
    instance = Model.objects.create(**validated_data)

    # Create nested
    for item in nested_data:
        Nested.objects.create(parent=instance, **item)

    return instance
```

---

## 🔧 Views/ViewSets

### ViewSet Template

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsSuperintendencia
from apps.core.serializers import SolicitacaoReadSerializer, SolicitacaoWriteSerializer
from apps.core.services.availability_service import check_conflicts


class SolicitacaoViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Solicitacao CRUD + custom actions.

    Endpoints:
    - GET /api/solicitacoes/ - List
    - POST /api/solicitacoes/ - Create
    - GET /api/solicitacoes/{id}/ - Retrieve
    - PUT/PATCH /api/solicitacoes/{id}/ - Update
    - DELETE /api/solicitacoes/{id}/ - Destroy
    - POST /api/solicitacoes/{id}/approve/ - Custom action
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optimize queryset with select_related/prefetch_related.

        CRITICAL: Avoid N+1 queries.
        """
        queryset = Solicitacao.objects.select_related(
            'solicitante',
            'municipio',
            'projeto'
        ).prefetch_related(
            'participantes'
        )

        # Filter by user role
        user = self.request.user
        if not user.is_superuser:
            queryset = queryset.filter(solicitante=user)

        return queryset

    def get_serializer_class(self):
        """
        Use different serializers for read vs write.
        """
        if self.action in ['list', 'retrieve']:
            return SolicitacaoReadSerializer
        return SolicitacaoWriteSerializer

    def perform_create(self, serializer):
        """
        Override to add custom logic on creation.

        IMPORTANT: Keep thin - move business logic to services.
        """
        # Set solicitante to current user
        serializer.save(solicitante=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperintendencia])
    def approve(self, request, pk=None):
        """
        Approve solicitacao (Superintendência only).

        POST /api/solicitacoes/{id}/approve/
        Body: {"justificativa": "..."}
        """
        solicitacao = self.get_object()

        # Validate status
        if solicitacao.status != 'pendente':
            return Response(
                {'error': 'Solicitação já foi processada'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Business logic in service
        from apps.core.services.approval_service import approve_solicitacao

        try:
            result = approve_solicitacao(
                solicitacao=solicitacao,
                aprovador=request.user,
                justificativa=request.data.get('justificativa', '')
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

### Key Patterns

#### 1. Thin Controllers

**❌ BAD (fat controller)**:
```python
def approve(self, request, pk=None):
    solicitacao = self.get_object()

    # 50 lines of business logic here
    # ...
```

**✅ GOOD (thin controller)**:
```python
def approve(self, request, pk=None):
    solicitacao = self.get_object()

    # Delegate to service
    from apps.core.services.approval_service import approve_solicitacao
    result = approve_solicitacao(solicitacao, request.user)

    return Response(result)
```

#### 2. Permission Classes

```python
# Method 1: ViewSet-level
class SolicitacaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

# Method 2: Action-level
@action(detail=True, permission_classes=[IsSuperintendencia])
def approve(self, request, pk=None):
    pass

# Method 3: Mixed
def get_permissions(self):
    if self.action == 'approve':
        return [IsSuperintendencia()]
    return [IsAuthenticated()]
```

#### 3. Query Optimization

```python
# select_related (FKs, OneToOne)
queryset = Solicitacao.objects.select_related(
    'solicitante',
    'municipio'
)

# prefetch_related (M2M, reverse FKs)
queryset = queryset.prefetch_related(
    'participantes',
    'participantes__grupos'  # Nested prefetch
)

# Result: 3 queries instead of N+1
```

---

## 🔐 Permissions (RBAC)

### Custom Permission Template

```python
from rest_framework import permissions


class IsSuperintendencia(permissions.BasePermission):
    """
    Permission: User must be Superintendência or superuser.

    Usage:
    - PA-02: Only Superintendência can approve/reject
    """

    message = "Apenas Superintendência pode executar esta ação"

    def has_permission(self, request, view):
        """
        Check user-level permission (before fetching object).
        """
        if not request.user or not request.user.is_authenticated:
            return False

        return (
            request.user.is_superuser or
            request.user.groups.filter(name='Superintendência').exists()
        )

    def has_object_permission(self, request, view, obj):
        """
        Check object-level permission (after fetching object).

        Example: User can only edit own solicitacoes.
        """
        # Superuser can always access
        if request.user.is_superuser:
            return True

        # Superintendência can access all
        if request.user.groups.filter(name='Superintendência').exists():
            return True

        # Owner can access own
        return obj.solicitante == request.user
```

### Key Patterns

#### 1. Permission Composition

```python
# AND (all must pass)
permission_classes = [IsAuthenticated, IsSuperintendencia]

# OR (any must pass)
class IsOwnerOrSuperintendencia(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.solicitante == request.user or
            request.user.groups.filter(name='Superintendência').exists()
        )
```

#### 2. Read vs Write Permissions

```python
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Read allowed for all
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write allowed for owner only
        return obj.solicitante == request.user
```

---

## 🧪 Testing Patterns

### Test Template

```python
import pytest
from django.contrib.auth.models import Group
from apps.core.models import Usuario, Solicitacao
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@pytest.fixture
def tz_fortaleza():
    """Timezone fixture."""
    return ZoneInfo('America/Fortaleza')


@pytest.fixture
def grupo_superintendencia(db):
    """Superintendência group."""
    return Group.objects.get_or_create(name='Superintendência')[0]


@pytest.fixture
def usuario_superintendencia(db, grupo_superintendencia):
    """User with Superintendência permission."""
    usuario = Usuario.objects.create_user(
        username='super1',
        email='super@example.com',
        password='pass123'
    )
    usuario.groups.add(grupo_superintendencia)
    return usuario


@pytest.fixture
def solicitacao_pendente(db, usuario_superintendencia, tz_fortaleza):
    """Pending solicitacao for testing."""
    from apps.core.models import Projeto, Municipio

    projeto = Projeto.objects.create(nome='Teste', fluxo='SUPER')
    municipio = Municipio.objects.create(nome='Fortaleza', uf='CE')

    inicio = datetime(2025, 1, 15, 9, 0, tzinfo=tz_fortaleza)
    fim = inicio + timedelta(hours=3)

    return Solicitacao.objects.create(
        solicitante=usuario_superintendencia,
        projeto=projeto,
        municipio=municipio,
        inicio=inicio,
        fim=fim,
        status='pendente'
    )


class TestSolicitacaoApproval:
    """Approval flow tests (PA-01 to PA-07)."""

    class TestManualApproval:
        """PA-01: No auto-approval for SUPER projects."""

        def test_super_project_stays_pending(self, solicitacao_pendente):
            """Solicitacao with SUPER project remains pendente after creation."""
            assert solicitacao_pendente.status == 'pendente'

    class TestPermissions:
        """PA-02: Only Superintendência can approve."""

        def test_superintendencia_approves_successfully(
            self, client, usuario_superintendencia, solicitacao_pendente
        ):
            """Superintendência user can approve solicitacao."""
            client.force_login(usuario_superintendencia)

            response = client.post(
                f'/api/solicitacoes/{solicitacao_pendente.id}/approve/',
                {'justificativa': 'Aprovado para teste'}
            )

            assert response.status_code == 200
            solicitacao_pendente.refresh_from_db()
            assert solicitacao_pendente.status == 'aprovado'
```

### Key Patterns

#### 1. Fixture Organization

```python
# conftest.py (shared fixtures)
@pytest.fixture
def base_usuario(db):
    return Usuario.objects.create_user(...)

# test_file.py (specific fixtures)
@pytest.fixture
def solicitacao_aprovada(base_usuario):
    return Solicitacao.objects.create(..., status='aprovado')
```

#### 2. Test Organization (Nested Classes)

```python
class TestFeatureName:
    """Feature description."""

    class TestSubRequirement1:
        """Sub-requirement description."""

        def test_specific_behavior(self):
            """Test description in 3rd person."""
            pass
```

#### 3. Behavior Testing (Not Implementation)

```python
# ❌ BAD (tests implementation)
def test_approve_calls_save():
    mock_save = Mock()
    solicitacao.save = mock_save
    approve(solicitacao)
    assert mock_save.called

# ✅ GOOD (tests behavior)
def test_approve_creates_audit_log():
    approve(solicitacao)
    assert AuditLog.objects.filter(
        action='APPROVE',
        details__solicitacao_id=solicitacao.id
    ).exists()
```

---

## 🚀 Performance Optimization

### N+1 Query Prevention

**❌ BAD (N+1)**:
```python
# View
solicitacoes = Solicitacao.objects.all()  # 1 query

# Template
{% for s in solicitacoes %}
    {{ s.solicitante.nome }}  # N queries (1 per solicitacao)
{% endfor %}
```

**✅ GOOD (Optimized)**:
```python
# View
solicitacoes = Solicitacao.objects.select_related('solicitante').all()  # 2 queries

# Template
{% for s in solicitacoes %}
    {{ s.solicitante.nome }}  # No additional queries
{% endfor %}
```

### Cache Strategy

```python
from django.core.cache import cache


def get_monthly_grid(year, month):
    """
    Get monthly availability grid with 5-min cache.

    Cache key format: monthly_grid:{year}:{month}
    """
    cache_key = f'monthly_grid:{year}:{month}'

    # Try cache first
    result = cache.get(cache_key)
    if result is not None:
        return result

    # Compute if not cached
    result = expensive_computation(year, month)

    # Cache for 5 minutes
    cache.set(cache_key, result, timeout=300)

    return result
```

---

## 📚 Quick Reference Examples

### Complete CRUD Example

See implementation in:
- Models: `apps/core/models.py` (Solicitacao, Usuario, Projeto)
- Serializers: `apps/core/serializers.py` (SolicitacaoReadSerializer, SolicitacaoWriteSerializer)
- Views: `apps/core/views.py` (SolicitacaoViewSet)
- Permissions: `apps/core/permissions.py` (IsSuperintendencia)
- Tests: `apps/core/tests/test_solicitacao.py`

### Service Layer Example

See implementation in:
- `apps/core/services/availability_service.py` - RD-01 to RD-08
- `apps/core/services/gcal_sync_service.py` - RF05/RF06

---

## 🔗 Related Documentation

- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md` (CP, RD, PA, RF)
- **Code Quality**: `.claude/CLAUDE-principles.md`
- **Project Context**: `.claude/CLAUDE.md`

---

**Last Updated**: 04/11/2025
**Version**: 1.0
**Based on**: Django 5.1 + DRF 3.14 + AS v2 patterns
