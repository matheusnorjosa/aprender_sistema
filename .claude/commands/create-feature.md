---
description: Plan and implement a new feature following AS v2 Django/DRF patterns with focus on type-safety, RBAC, and compliance
argument-hint: [feature description]
---

# Create Feature — AS v2

Implement: $ARGUMENTS

## Pre-Flight Checks

### 1. Load Domain Context
Before starting, check which rules apply:
- Use `aprender-domain` skill for business rules (CP, RD, PA, RF)
- Use `django-patterns` skill for implementation patterns

### 2. Branch Creation
```bash
git checkout main && git pull
git checkout -b feat/<feature-name>
```

## Planning Phase

### 1. Identify Compliance Requirements
Check CLAUDE.md for applicable rules:
- **CP-01 to CP-06**: Cláusulas pétreas (imutáveis)
- **RD-01 to RD-08**: Regras de disponibilidade
- **PA-01 to PA-07**: Política de aprovação
- **RF01 to RF08**: Requisitos funcionais

### 2. Analyze Codebase Patterns
Search for related patterns:
```
apps/core/services/     → Business logic (pure functions, dataclasses)
apps/core/views/        → ViewSets (DRF patterns)
apps/core/models/       → Models (SSOT)
apps/core/serializers/  → Read/Write serializers
apps/core/tests/        → Pytest fixtures, behavior tests
```

### 3. Plan Implementation
Break into atomic tasks:
1. **Service layer** (pure functions, no side effects)
2. **Serializers** (Read vs Write)
3. **Views/ViewSets** (RBAC, custom actions)
4. **Tests** (behavior, 3rd person verbs)

## Implementation Standards

### Type Safety (Pyright Strict)
```python
from __future__ import annotations
from apps.core.types import UserId, Status, ConflictCode

def my_function(user_id: UserId, status: Status) -> CheckResult:
    """Docstring with Args/Returns/Raises."""
    ...
```

### Service Layer Pattern
```python
@dataclass
class MyResult:
    """Return type with clear contract."""
    ok: bool
    data: list[Item]

def check_something(
    usuario: Usuario,
    ...
) -> MyResult:
    """
    Docstring explaining which rules (RD/PA) are implemented.

    Pure function: reads DB, returns dataclass, no side effects.
    """
    from apps.core.models import Solicitacao  # Local import
    # Implementation
    return MyResult(ok=True, data=[])
```

### ViewSet Pattern
```python
class MyViewSet(viewsets.ModelViewSet):
    """Docstring with RBAC info."""

    queryset = Model.objects.select_related('fk').prefetch_related('m2m')
    serializer_class = MySerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """Different permissions per action."""
        if self.action == 'approve':
            return [IsSuperintendencia()]
        return super().get_permissions()

    @action(detail=True, methods=['patch'], permission_classes=[IsSuperintendencia])
    def approve(self, request, pk=None):
        """Custom action with AuditLog (PA-05)."""
        obj = self.get_object()
        # Logic
        AuditLog.objects.create(...)  # PA-05
        return Response(...)
```

### Test Pattern
```python
@pytest.mark.django_db
class TestMyFeature:
    """Tests for <feature> following PA/RD rules."""

    def test_behavior_description(self, usuario_test, municipio_a):
        """Verbo em 3ª pessoa, não 'should'."""
        result = my_function(usuario_test, ...)
        assert result.ok
        assert len(result.data) == expected
```

## Quality Checklist

### Code Quality
- [ ] Type hints on all functions (Pyright strict)
- [ ] Docstrings (PEP 257, Google style)
- [ ] Early returns (flat code)
- [ ] No magic numbers/strings
- [ ] select_related/prefetch_related optimizations

### Security & RBAC
- [ ] Permission classes defined
- [ ] AuditLog for critical actions (PA-05)
- [ ] No raw SQL (ORM only)
- [ ] Secrets in .env (not hardcoded)

### Compliance
- [ ] PA rules validated (if approval related)
- [ ] RD rules validated (if availability related)
- [ ] CP cláusulas respeitadas

### Testing
- [ ] Unit tests for service functions
- [ ] API tests for ViewSet actions
- [ ] 3rd person verbs (not "should")
- [ ] Coverage ≥90%

## Stage Changes
```bash
git add -A
```

## Output
Leave all changes staged for review with `/review-staged` before commit.
