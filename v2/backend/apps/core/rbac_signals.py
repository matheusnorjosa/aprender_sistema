"""
Signals de invalidação de cache para RBAC funcional.
"""

# pyright: reportUnusedFunction=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.core.models import PermissaoFuncional
from apps.core.services.rbac_permissions import (
    bump_functional_permissions_cache_version,
    invalidate_group_functional_permissions_cache,
    invalidate_user_functional_permissions_cache,
)

User = get_user_model()


@receiver(m2m_changed, sender=User.groups.through)
def _invalidate_funcperm_on_user_groups_change(
    sender: type[Any],
    instance: Any,
    action: str,
    **kwargs: Any,
) -> None:
    if action in {"post_add", "post_remove", "post_clear"}:
        user_id = getattr(instance, "id", None)
        if isinstance(user_id, int):
            invalidate_user_functional_permissions_cache(user_id)


@receiver(m2m_changed, sender=PermissaoFuncional.groups.through)
def _invalidate_funcperm_on_permission_groups_change(
    sender: type[Any],
    instance: PermissaoFuncional,
    action: str,
    pk_set: set[int] | None = None,
    **kwargs: Any,
) -> None:
    if action == "pre_clear":
        existing_group_ids = list(instance.groups.values_list("id", flat=True))
        invalidate_group_functional_permissions_cache(existing_group_ids)
        return

    if action in {"post_add", "post_remove"} and pk_set:
        invalidate_group_functional_permissions_cache(pk_set)


@receiver(post_save, sender=PermissaoFuncional)
def _invalidate_funcperm_on_permission_save(
    sender: type[PermissaoFuncional],
    instance: PermissaoFuncional,
    **kwargs: Any,
) -> None:
    group_ids = list(instance.groups.values_list("id", flat=True))
    if group_ids:
        invalidate_group_functional_permissions_cache(group_ids)
    else:
        bump_functional_permissions_cache_version()


@receiver(post_delete, sender=PermissaoFuncional)
def _invalidate_funcperm_on_permission_delete(
    sender: type[PermissaoFuncional],
    instance: PermissaoFuncional,
    **kwargs: Any,
) -> None:
    # Relações M2M podem já ter sido removidas; invalidação global protege contra stale cache.
    bump_functional_permissions_cache_version()


@receiver(post_save, sender=Group)
@receiver(post_delete, sender=Group)
def _invalidate_funcperm_on_group_change(
    sender: type[Group],
    instance: Group,
    **kwargs: Any,
) -> None:
    group_id = getattr(instance, "id", None)
    if isinstance(group_id, int):
        invalidate_group_functional_permissions_cache([group_id])
