# Django/DRF Patterns Cheatsheet — Aprender Sistema v2

> índice — full em `.claude/skills/django-patterns/SKILL.md`

Este arquivo é só um **ponteiro**. Templates completos (models, serializers, views,
services, testing, cache, performance) ficam na skill `django-patterns`.

## Onde está a verdade (SSOT)

| Tópico | Fonte |
|--------|-------|
| Patterns de implementação (models/serializers/views/services) | `skills/django-patterns/SKILL.md` |
| RBAC (permissions canônicas) | `apps.core.rbac` + `v2/docs/RBAC_NAMING.md` + `v2/docs/specs/backend/rbac.spec.md` |
| Performance (N+1, queries) | skill `performance-optimization` |
| Testes / TDD | skill `test-driven-development` |

## Lembretes rápidos (checklist — detalhe na skill)

| Tema | Regra |
|------|-------|
| FK | `on_delete=PROTECT` + `related_name`; evitar `DO_NOTHING` |
| Choices | `models.TextChoices` |
| Validação | Constraint (DB) > validator (serializer); `full_clean()` no `save()` |
| Serializer READ | `StringRelatedField` / `SerializerMethodField` |
| Serializer WRITE | `PrimaryKeyRelatedField`, IDs only |
| View | Thin controller → delega para `services/` |
| Query | `select_related` (FK/O2O) / `prefetch_related` (M2M/reverse) |
| Timezone | `ZoneInfo('America/Fortaleza')`, sempre tz-aware (RD-06) |
| Teste | Asserta comportamento, não implementação |

## Permissions (RBAC) — idioma canônico

A linguagem canônica é `HasPerm("codename")` de `apps.core.rbac`.
`scripts/rbac_lint.py` **BANE** `user.groups.filter(name=...)` (CI job `[required] backend rbac-lint`).

```python
from apps.core.rbac import HasPerm

class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [HasPerm("codename")]

    # Composition (OR/AND/NOT) com instâncias:
    # permission_classes = [HasPerm("a") | HasPerm("b")]
```

Helper não-DRF: `user_has_any_perm(user, *codenames)`.
Convenção completa e naming: `v2/docs/RBAC_NAMING.md`.
Para acesso compartilhado por ≥3 capabilities, usar Policy class (ver `specs/backend/rbac.spec.md`).
