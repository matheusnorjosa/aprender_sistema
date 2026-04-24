# `apps.core.rbac` — Centralized RBAC Module

SSOT (Single Source of Truth) do sistema de autorização do Aprender Sistema v2.

## Módulos

| Arquivo          | Conteúdo                                                         |
| ---------------- | ---------------------------------------------------------------- |
| `__init__.py`    | API pública (re-exports)                                         |
| `permissions.py` | DRF permission classes (`HasPerm` + 3 mantidas)                  |
| `helpers.py`     | `user_has_any_perm`, `user_has_all_perms`                        |
| `constants.py`   | `COORDENADOR_ROLE_GROUPS`, `FORMADOR_ROLE_GROUPS` (data-scope)   |

## Como usar

### Em views DRF

```python
from apps.core.rbac import HasPerm

class ApproveSolicitacaoView(APIView):
    permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]
```

### Composition OR/AND/NOT

```python
from apps.core.rbac import HasPerm

class OperarView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasPerm("operate_preagenda") | HasPerm("supervise_operations"),
    ]
```

### Em services/helpers (não-DRF)

```python
from apps.core.rbac import user_has_any_perm

def my_service(user):
    if not user_has_any_perm(user, "operate_preagenda", "supervise_operations"):
        raise PermissionDenied
    ...
```

### Filtros de data-scope

```python
from apps.core.rbac import COORDENADOR_ROLE_GROUPS

queryset = Usuario.objects.filter(groups__name__in=COORDENADOR_ROLE_GROUPS)
```

## O que NÃO fazer (lint Epic 6 bane)

### V001 — `groups.filter(name=...)` em views/services

```python
# ❌ Errado
if user.groups.filter(name="DAT").exists():
    ...

# ✅ Certo
if user_has_any_perm(user, "manage_admin_registries"):
    ...
```

### V002 — Criar classes `Is<Role>`

```python
# ❌ Errado
class IsDAT(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="DAT").exists()

# ✅ Certo — não precisa classe, usa HasPerm inline
permission_classes = [HasPerm("manage_admin_registries")]
```

## Exceções (whitelist)

Usos legítimos de `groups.filter(name=...)` devem ter marker `# noqa: RBAC-*-allowed`:

- **`# noqa: RBAC-composite-allowed`** — classes compostas (funcperm + grupo)
- **`# noqa: RBAC-block-allowed`** — bloqueio explícito de um grupo por design
- **`# noqa: RBAC-data-scope-allowed`** — filtro de escopo de dados (não authz)

## Shims de backcompat

Por decisão de migração Epic 6, os arquivos antigos continuam funcionando como shim:

- `apps/core/permissions.py` → re-exporta de `apps.core.rbac.permissions`
- `apps/core/rbac_helpers.py` → re-exporta de `apps.core.rbac.helpers`

Para novos imports, prefira `from apps.core.rbac import ...`. Os shims serão
mantidos indefinidamente para não quebrar branches em flight.

## Ver também

- [v2/docs/RBAC_NAMING.md](../../../../docs/RBAC_NAMING.md) — Convenção canônica
- [scripts/rbac_lint.py](../../../scripts/rbac_lint.py) — Lint AST que enforça as regras
