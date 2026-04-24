"""
Centralized RBAC (Role-Based Access Control) module.

SSOT público do sistema de autorização. Toda lógica de authz passa por aqui:
permission classes DRF, helpers de consulta de capability, constantes de
data scope.

Public API:
    HasPerm                      — Parametric DRF permission class
    HasFunctionalPermission      — Base class para permissions por codename
    HasSectorAccess              — Dynamic scope check via query param
    IsGerenteSuperintendencia    — Composite: funcperm + grupo "Gerente"
    IsOwnerOrPrivileged          — Object-level: owner ou usuário privilegiado
    user_has_any_perm            — True se tem QUALQUER uma das codenames
    user_has_all_perms           — True se tem TODAS as codenames
    COORDENADOR_ROLE_GROUPS      — Data-scope filter (dropdown coordenadores)
    FORMADOR_ROLE_GROUPS         — Data-scope filter (dropdown formadores)

Idiomas canônicos:
    permission_classes = [HasPerm("approve_solicitation")]
    permission_classes = [HasPerm("a") | HasPerm("b")]   # OR composition
    if user_has_any_perm(user, "operate_preagenda", "supervise_operations"): ...

Nunca fazer (lint Epic 6 bane):
    user.groups.filter(name="X")          → use HasPerm(codename) / user_has_any_perm
    class IsDAT(BasePermission)           → use HasPerm("codename") inline
    permission_classes = [IsControleOrDAT] → use HasPerm(...) direto

Ver v2/docs/RBAC_NAMING.md para convenção completa.
"""

from apps.core.rbac.constants import COORDENADOR_ROLE_GROUPS, FORMADOR_ROLE_GROUPS
from apps.core.rbac.helpers import user_has_all_perms, user_has_any_perm
from apps.core.rbac.permissions import (
    HasFunctionalPermission,
    HasPerm,
    HasSectorAccess,
    IsGerenteSuperintendencia,
    IsOwnerOrPrivileged,
)

__all__ = [
    "HasPerm",
    "HasFunctionalPermission",
    "HasSectorAccess",
    "IsGerenteSuperintendencia",
    "IsOwnerOrPrivileged",
    "user_has_any_perm",
    "user_has_all_perms",
    "COORDENADOR_ROLE_GROUPS",
    "FORMADOR_ROLE_GROUPS",
]
