# Django/DRF Patterns Cheatsheet — Aprender Sistema v2

Quick reference for implementation patterns. Full details: `.claude/skills/django-patterns/SKILL.md`

---

## Estrutura Modular

```
apps/core/
├── models/           # Models por domínio
│   ├── __init__.py   # Re-exports
│   ├── usuario.py
│   ├── solicitacao.py
│   └── ...
├── serializers/      # Serializers por domínio
├── views/            # Views por feature
├── services/         # Business logic
│   └── gcal/         # GCal modular
└── permissions.py    # RBAC
```

---

## Models

### Template Básico

```python
class MyModel(models.Model):
    # FK sempre com related_name
    usuario = models.ForeignKey(
        'Usuario',
        on_delete=models.PROTECT,
        related_name='my_models'
    )

    # Choices com TextChoices
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADO = 'aprovado', 'Aprovado'

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE
    )

    # Timestamps obrigatórios
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(fim__gt=models.F('inicio')),
                name='valid_range'
            )
        ]
        indexes = [
            models.Index(fields=['status', '-created_at'])
        ]

    def save(self, *args, **kwargs):
        self.full_clean()  # SEMPRE chamar
        super().save(*args, **kwargs)
```

### on_delete Options

| Option | Uso | Quando |
|--------|-----|--------|
| `PROTECT` | Impede deleção | Dados de negócio |
| `CASCADE` | Deleta dependentes | Dados dependentes |
| `SET_NULL` | Define NULL | Opcional + histórico |
| `DO_NOTHING` | ❌ Evitar | Quebra integridade |

### Timezone (RD-06)

```python
from zoneinfo import ZoneInfo
TZ = ZoneInfo('America/Fortaleza')

# Sempre timezone-aware
inicio = timezone.now().astimezone(TZ)
```

---

## Serializers

### Read vs Write

```python
# READ (GET) - User-friendly
class MyReadSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField()  # __str__()
    data_formatada = serializers.SerializerMethodField()

    class Meta:
        model = MyModel
        fields = ['id', 'usuario', 'data_formatada']
        read_only_fields = ['id']

    def get_data_formatada(self, obj):
        return obj.data.strftime('%d/%m/%Y')


# WRITE (POST/PUT) - IDs only
class MyWriteSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.filter(is_active=True)
    )

    class Meta:
        model = MyModel
        fields = ['usuario', 'data', 'status']

    def validate_data(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Deve ser futuro")
        return value

    def validate(self, data):  # Cross-field
        if data['fim'] <= data['inicio']:
            raise serializers.ValidationError({'fim': 'Inválido'})
        return data
```

### Níveis de Validação

1. **Field validators** - `validators=[...]`
2. **validate_<field>()** - Campo individual
3. **validate()** - Cross-field

---

## Views/ViewSets

### Template Básico

```python
class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # SEMPRE otimizar queries
        return MyModel.objects.select_related(
            'usuario', 'projeto'
        ).prefetch_related(
            'participantes'
        )

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return MyReadSerializer
        return MyWriteSerializer

    @action(detail=True, methods=['post'],
            permission_classes=[IsSuperintendencia])
    def approve(self, request, pk=None):
        obj = self.get_object()
        # Delegar para service (thin controller)
        result = my_service.approve(obj, request.user)
        return Response(result)
```

### Thin Controllers

```python
# ❌ BAD - Fat controller
def approve(self, request, pk=None):
    obj = self.get_object()
    # 50 linhas de lógica aqui...

# ✅ GOOD - Thin controller
def approve(self, request, pk=None):
    obj = self.get_object()
    result = approval_service.approve(obj, request.user)
    return Response(result)
```

---

## Permissions (RBAC)

### Template

```python
class IsSuperintendencia(permissions.BasePermission):
    message = "Apenas Superintendência"

    def has_permission(self, request, view):
        return (
            request.user.is_superuser or
            request.user.groups.filter(name='Superintendência').exists()
        )

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return obj.solicitante == request.user
```

### Composição

```python
# AND (todos devem passar)
permission_classes = [IsAuthenticated, IsSuperintendencia]

# OR (custom)
class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_superuser
```

---

## Query Optimization

### N+1 Prevention

```python
# ❌ N+1 queries
queryset = Model.objects.all()
for obj in queryset:
    print(obj.usuario.nome)  # 1 query por objeto

# ✅ Otimizado (2 queries total)
queryset = Model.objects.select_related('usuario').all()
for obj in queryset:
    print(obj.usuario.nome)  # Sem query adicional
```

### Quando usar

| Método | Relacionamento | Exemplo |
|--------|----------------|---------|
| `select_related()` | FK, OneToOne | `usuario`, `projeto` |
| `prefetch_related()` | M2M, reverse FK | `participantes`, `formacoes` |

---

## Services

### Template

```python
# apps/core/services/my_service.py
from typing import TypedDict

class ApprovalResult(TypedDict):
    success: bool
    message: str

def approve_solicitacao(
    solicitacao: Solicitacao,
    aprovador: Usuario,
    justificativa: str = ""
) -> ApprovalResult:
    """
    Aprova solicitação.

    Args:
        solicitacao: Solicitação a aprovar
        aprovador: Usuário que aprova
        justificativa: Motivo (opcional)

    Returns:
        ApprovalResult com status

    Raises:
        ValueError: Se já processada
    """
    if solicitacao.status != 'pendente':
        raise ValueError("Já processada")

    solicitacao.status = 'aprovado'
    solicitacao.save()

    AuditLog.objects.create(
        usuario=aprovador,
        action='APPROVE',
        details={'id': solicitacao.id}
    )

    return {'success': True, 'message': 'Aprovado'}
```

---

## Testing

### Fixtures

```python
@pytest.fixture
def usuario_super(db):
    user = Usuario.objects.create_user(username='super')
    user.groups.add(Group.objects.get_or_create(name='Superintendência')[0])
    return user

@pytest.fixture
def solicitacao_pendente(db, usuario_super):
    return Solicitacao.objects.create(
        solicitante=usuario_super,
        status='pendente'
    )
```

### Organização

```python
class TestFeature:
    """Feature tests."""

    class TestSubRequirement:
        """Sub-requirement tests."""

        def test_specific_behavior(self, solicitacao_pendente):
            """Comportamento específico."""
            assert solicitacao_pendente.status == 'pendente'
```

### Behavior vs Implementation

```python
# ❌ Testa implementação
def test_calls_save():
    mock_save = Mock()
    ...

# ✅ Testa comportamento
def test_creates_audit_log():
    approve(solicitacao)
    assert AuditLog.objects.filter(action='APPROVE').exists()
```

---

## Cache (Redis)

```python
from django.core.cache import cache

def get_data():
    key = 'my_data:key'
    result = cache.get(key)
    if result is None:
        result = expensive_computation()
        cache.set(key, result, timeout=300)  # 5 min
    return result
```

---

## Quick Reference

| Task | Pattern |
|------|---------|
| FK | `on_delete=PROTECT`, `related_name` |
| Choices | `TextChoices` |
| Validation | Constraint > Validator |
| Serializer Read | `StringRelatedField` |
| Serializer Write | `PrimaryKeyRelatedField` |
| View | Thin controller + Service |
| Permission | Custom class |
| Query | `select_related` / `prefetch_related` |
| Test | Behavior, não implementation |
