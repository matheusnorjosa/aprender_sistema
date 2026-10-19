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
# Approval: single rule solicitation_approval_basis; see PA-02 in v2/docs/specs/domain/politica-aprovacao.spec.md (no group grants approval)
```

Authorization is **capability-based**, never identity-based. Gate with the
codename, not the group name. `apps.core.rbac` public API: `HasPerm`,
`user_has_any_perm`, `user_has_all_perms`, plus data-scope constants
`COORDENADOR_ROLE_GROUPS` / `FORMADOR_ROLE_GROUPS`. Real codenames seen in
production views: `create_solicitation`, `approve_solicitation`,
`view_all_availability`, `operate_preagenda`, `manage_admin_registries`,
`view_overview_dashboard`, `import_spreadsheet`. (`approve_solicitation_batch` foi
apagada na migration 0125, PR 8; `approve_solicitation` nenhum grupo tem — vem do
pacote do perfil da gerência, DAT e Controle.)

## Canonical permission idiom

```python
from apps.core.rbac import HasPerm

class SolicitacaoViewSet(ModelViewSet):
    # capability-based; compose with | (OR) / & (AND) / ~ (NOT)
    permission_classes = [HasPerm("create_solicitation")]
    # e.g. HasPerm("operate_preagenda") | HasPerm("manage_admin_registries")
    # Aprovar NÃO é HasPerm: usa a Policy CanAccessSolicitationApprovals
    # (SSOT `solicitation_approval_basis`, 3 bases; uma delas não é capacidade).
```

Gotcha: if a ViewSet overrides `get_permissions()`, an `@action(permission_classes=...)`
decorator is **silently ignored** unless `get_permissions()` returns
`super().get_permissions()` for that action. Always read `get_permissions()`
before trusting a decorator.

## IDOR prevention — gate by capability, then scope the queryset

```python
from apps.core.services.solicitacao_scope import scope_solicitacoes

# WRONG — exposes every row to any authenticated user
def get_queryset(self):
    return Solicitacao.objects.all()

# WRONG — identity-coupled; banned by scripts/rbac_lint.py (the A01 control)
def get_queryset(self):
    if self.request.user.groups.filter(name="Superintendência").exists():
        return Solicitacao.objects.all()
    ...

# CORRECT — delegate to the actor×gerência scope SSOT
def get_queryset(self):
    base = Solicitacao.objects.select_related(
        "usuario", "municipio", "tipo_evento", "projeto", "coordenador"
    )
    return scope_solicitacoes(base, self.request.user)
```

This mirrors `SolicitacaoViewSet.get_queryset` in `apps/core/views_solicitacao.py`.
`scope_solicitacoes` (`apps/core/services/solicitacao_scope.py`) applies the rule:
GLOBAL (superuser, `operate_preagenda`, `manage_admin_registries`, `approve_solicitation`
ou quem aprova por `solicitation_approval_basis`) vê tudo; GESTORA (papel GERENTE vigente)
vê as gerências dela + as próprias; APOIO (`publish_setor_solicitacao`) vê as aprovadas das gerências onde é APOIO; DEMAIS
só as próprias. Never `groups.filter(name=...)`. A linha fora do escopo nem entra no
queryset (→ 404); a edição/exclusão passa ainda por `IsOwnerOrPrivileged.has_object_permission`,
que usa `user_can_access_solicitacao` do mesmo módulo (mesma regra, salvo a aprovadora restrita).

## Lint guard

`scripts/rbac_lint.py` (cwd `v2/backend`) bans `user.groups.filter(name=...)`
and `Is<Role>` permission classes outside the whitelist. CI job:
`[required] backend rbac-lint`. Convention: `v2/docs/RBAC_NAMING.md`.
