"""
Backcompat shim para `apps.core.rbac.helpers`.

Após Epic 6 do RBAC Refactor (2026-04-24), o SSOT dos helpers de capability
migrou para `apps.core.rbac.helpers`. Este arquivo existe apenas para
preservar imports legacy (`from apps.core.rbac_helpers import user_has_any_perm`).

Para novos imports, prefira:
    from apps.core.rbac import user_has_any_perm, user_has_all_perms

Ver: apps/core/rbac/README.md e v2/docs/RBAC_NAMING.md
"""

from apps.core.rbac.helpers import user_has_all_perms, user_has_any_perm  # noqa: F401

__all__ = ["user_has_any_perm", "user_has_all_perms"]
