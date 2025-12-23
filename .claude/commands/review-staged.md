---
description: Review staged changes against AS v2 standards (Pyright, Django patterns, RBAC, compliance)
allowed-tools: Bash(git:*)
---

# Review Staged Changes — AS v2

Review all staged changes for quality and adherence to AS v2 standards.

## Process

### 1. Get Staged Changes
```bash
git diff --cached
git diff --cached --name-only
```

### 2. Review Checklist

#### Type Safety (Pyright Strict)
- [ ] `from __future__ import annotations` at top
- [ ] Type hints on all function parameters
- [ ] Return types specified
- [ ] No `Any` without documented justification
- [ ] TypeAlias from `apps/core/types.py` used

#### Django/DRF Patterns
- [ ] Models: SSOT, constraints in Meta class
- [ ] Services: Pure functions, dataclass returns, no side effects
- [ ] Views: select_related/prefetch_related optimization
- [ ] Serializers: Read vs Write distinction
- [ ] Permissions: IsSuperintendencia, IsCoordenadorOrDAT

#### Naming Conventions
- [ ] Classes: `UpperCamelCase` (Usuario, Solicitacao)
- [ ] Functions: `snake_case` (check_conflicts)
- [ ] Constants: `SNAKE_CAPS` (ETL_MAX_PCT)
- [ ] No vague terms (data, info, manager, helper)

#### Code Structure
- [ ] Early returns (flat code, no deep nesting)
- [ ] 1 function = 1 purpose
- [ ] No useless abstractions (helpers used once)
- [ ] Local imports to avoid circular deps

#### Security & RBAC
- [ ] Permission classes on views/actions
- [ ] AuditLog for critical actions (PA-05)
- [ ] No raw SQL (ORM only)
- [ ] No hardcoded secrets

#### Compliance Check
- [ ] PA-01 to PA-07 respected (if approval related)
- [ ] RD-01 to RD-08 respected (if availability related)
- [ ] CP-01 to CP-06 not violated

#### Docstrings (PEP 257)
- [ ] Module docstring explains purpose
- [ ] Function docstrings with Args/Returns/Raises
- [ ] References to PA/RD rules in comments

#### Testing
- [ ] Tests for new functionality
- [ ] 3rd person verbs (not "should")
- [ ] Behavior tested (not implementation)
- [ ] Fixtures with meaningful names

### 3. Output Format

```markdown
## Summary
[Brief overview of changes]

## Files Changed
- `apps/core/services/new_service.py` (new)
- `apps/core/views/solicitacao.py` (modified)

## Issues Found

### Critical (must fix before commit)
- [ ] **Type Safety**: Missing return type on `foo()` in `bar.py:42`
- [ ] **RBAC**: No permission class on `MyViewSet.approve()`
- [ ] **PA-05**: AuditLog missing in approval action

### Suggested (should fix)
- [ ] **Naming**: `data` → `solicitacao_pendente` in `views.py:85`
- [ ] **Query**: Add `select_related('municipio')` in `views.py:20`

### Minor (nice to have)
- [ ] **Docstring**: Add Args section to `check_xyz()`

## Approval
✅ Ready to commit | ⚠️ Minor fixes needed | ❌ Needs changes
```

## Quick Fixes

### Missing Type Hints
```python
# Before
def foo(user, data):
    return result

# After
def foo(user: Usuario, data: dict[str, Any]) -> CheckResult:
    return result
```

### Missing AuditLog (PA-05)
```python
# Add after critical action
AuditLog.objects.create(
    usuario=request.user,
    acao='approve',
    detalhes={'solicitacao_id': obj.id},
    ip=_get_client_ip(request),
)
```

### Missing Query Optimization
```python
# Before (N+1 queries)
qs = Solicitacao.objects.all()

# After
qs = Solicitacao.objects.select_related(
    'usuario', 'municipio', 'projeto'
).prefetch_related('participations__usuario')
```
