"""
Servicos RBAC para permissoes funcionais com cache.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model
from django.core.cache import cache

from apps.core.models import PermissaoFuncional

CACHE_TTL_SECONDS = 300
_CACHE_VERSION_KEY = "as2:funcperms:version"


def _ensure_cache_version() -> int:
    current = cache.get(_CACHE_VERSION_KEY)
    if isinstance(current, int) and current > 0:
        return current
    cache.set(_CACHE_VERSION_KEY, 1, None)
    return 1


def _cache_key_for_user(user_id: int) -> str:
    version = _ensure_cache_version()
    return f"as2:funcperms:{version}:{user_id}"


def bump_functional_permissions_cache_version() -> int:
    """
    Invalida todos os caches de permissao funcional de uma vez.
    """

    current = _ensure_cache_version()
    next_version = current + 1
    cache.set(_CACHE_VERSION_KEY, next_version, None)
    return next_version


def invalidate_user_functional_permissions_cache(user_id: int) -> None:
    cache.delete(_cache_key_for_user(user_id))


def invalidate_users_functional_permissions_cache(user_ids: Iterable[int]) -> None:
    keys = [_cache_key_for_user(user_id) for user_id in set(user_ids)]
    if keys:
        cache.delete_many(keys)


def invalidate_group_functional_permissions_cache(group_ids: Iterable[int]) -> None:
    """
    Invalida cache dos usuarios que pertencem aos grupos informados.
    """

    normalized_ids = {int(group_id) for group_id in group_ids}
    if not normalized_ids:
        return

    User = get_user_model()
    impacted_user_ids = list(User.objects.filter(groups__id__in=normalized_ids).values_list("id", flat=True).distinct())
    invalidate_users_functional_permissions_cache(impacted_user_ids)


def get_user_functional_permissions(user: object) -> set[str]:
    """
    Retorna codenames de permissao funcional efetivos para o usuario.
    """

    user_id = getattr(user, "id", None)
    if not isinstance(user_id, int):
        return set()

    cache_key = _cache_key_for_user(user_id)
    cached = cache.get(cache_key)
    if isinstance(cached, list):
        return set(str(item) for item in cached)

    codenames = list(
        PermissaoFuncional.objects.filter(groups__user__id=user_id).values_list("codename", flat=True).distinct()
    )
    cache.set(cache_key, codenames, CACHE_TTL_SECONDS)
    return set(codenames)
