"""
Backcompat shim para `apps.core.rbac.permissions`.

Após Epic 6 do RBAC Refactor (2026-04-24), o SSOT das DRF permission classes
migrou para `apps.core.rbac.permissions`. Este arquivo existe apenas para
preservar imports legacy (`from apps.core.permissions import HasPerm`).

Para novos imports, prefira:
    from apps.core.rbac import HasPerm

Ver: apps/core/rbac/README.md e v2/docs/RBAC_NAMING.md
"""

from apps.core.rbac.permissions import (  # noqa: F401
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
]
