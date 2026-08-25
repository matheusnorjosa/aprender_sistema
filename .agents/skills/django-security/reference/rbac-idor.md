# RBAC + IDOR — canonical pattern (AS v2)

Single source for the access-control / row-level-security pattern referenced by
A01. All examples use real codenames and helpers from `apps.core.rbac`.

## RBAC model

```python
# 13 Setores: Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz,
#             DAT, Controle, Diretoria, Comercial, Relacionamento,
#             Logística Viagens, Logística Galpão  (SSOT: apps.core.constants.SETOR_GROUPS)
# 5 Funções: Formador, Coordenador, Apoio de Coordenação, Gerente,
#            Assistente Administrativo                (SSOT: apps.core.constants.FUNCAO_GROUPS)
# Approval: is_superuser OR (Gerente + Superintendência)
```

Authorization is **capability-based**, never identity-based. Gate with the
codename, not the group name. `apps.core.rbac` public API: `HasPerm`,
`user_has_any_perm`, `user_has_all_perms`, plus data-scope constants
`COORDENADOR_ROLE_GROUPS` / `FORMADOR_ROLE_GROUPS`. Real codenames seen in
production views: `create_solicitation`, `approve_solicitation`,
`approve_solicitation_batch`, `view_all_availability`, `operate_preagenda`,
`manage_admin_registries`, `view_overview_dashboard`, `import_spreadsheet`.

## Canonical permission idiom

```python
from apps.core.rbac import HasPerm

class SolicitacaoViewSet(ModelViewSet):
    # capability-based; compose with | (OR) / & (AND) / ~ (NOT)
    permission_classes = [HasPerm("create_solicitation")]
    # e.g. HasPerm("approve_solicitation") | HasPerm("approve_solicitation_batch")
```

Gotcha: if a ViewSet overrides `get_permissions()`, an `@action(permission_classes=...)`
decorator is **silently ignored** unless `get_permissions()` returns
`super().get_permissions()` for that action. Always read `get_permissions()`
before trusting a decorator.

## IDOR prevention — gate by capability, then scope the queryset

```python
from apps.core.rbac import HasPerm, user_has_any_perm

# WRONG — exposes every row to any authenticated user
def get_queryset(self):
    return Solicitacao.objects.all()

# WRONG — identity-coupled; banned by scripts/rbac_lint.py (the A01 control)
def get_queryset(self):
    if self.request.user.groups.filter(name="Superintendência").exists():
        return Solicitacao.objects.all()
    ...

# CORRECT — privileged capability sees all; everyone else sees only their own rows
def get_queryset(self):
    user = self.request.user
    if user_has_any_perm(
        user,
        "operate_preagenda",
        "approve_solicitation",
        "approve_solicitation_batch",
        "manage_admin_registries",
    ):
        return Solicitacao.objects.select_related(
            "usuario", "municipio", "tipo_evento", "projeto", "coordenador"
        )
    return Solicitacao.objects.filter(usuario=user)
```

This mirrors `apps/core/views_solicitacao.py`. The non-privileged branch scopes
rows by ownership (`filter(usuario=user)`); the privileged branch is gated by a
capability OR-set, never by `groups.filter(name=...)`.

## Lint guard

`scripts/rbac_lint.py` (cwd `v2/backend`) bans `user.groups.filter(name=...)`
and `Is<Role>` permission classes outside the whitelist. CI job:
`[required] backend rbac-lint`. Convention: `v2/docs/RBAC_NAMING.md`.
