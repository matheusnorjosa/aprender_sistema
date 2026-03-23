"""
Servicos RBAC de suporte para regras de atribuicao de grupos.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db.models import Q

from apps.core.constants import ALLOWED_USER_GROUPS

ASSIGNABLE_GROUPS_CACHE_KEY = "as2:rbac:assignable-groups:v1"
ASSIGNABLE_GROUPS_CACHE_TTL_SECONDS = 300


def invalidate_assignable_groups_cache() -> None:
    cache.delete(ASSIGNABLE_GROUPS_CACHE_KEY)


def get_assignable_group_names() -> set[str]:
    """
    Resolve whitelist dinamica de grupos atribuiveis.

    Regra:
    - Sempre inclui fallback estatico (ALLOWED_USER_GROUPS em settings/constants)
    - Inclui grupos que tenham permissao funcional vinculada (via UI RBAC)
    """

    cached = cache.get(ASSIGNABLE_GROUPS_CACHE_KEY)
    if isinstance(cached, list):
        cached_names = cast(list[str], cached)
        return set(cached_names)

    fallback = set(getattr(settings, "ALLOWED_USER_GROUPS", ALLOWED_USER_GROUPS))
    dynamic = set(
        Group.objects.filter(
            Q(name__in=fallback) | Q(permissoes_funcionais__isnull=False),
        )
        .values_list("name", flat=True)
        .distinct()
    )
    resolved = fallback | dynamic

    cache.set(
        ASSIGNABLE_GROUPS_CACHE_KEY,
        sorted(resolved),
        ASSIGNABLE_GROUPS_CACHE_TTL_SECONDS,
    )
    return resolved


def get_disallowed_group_names(groups: Iterable[Group]) -> set[str]:
    allowed = get_assignable_group_names()
    return {group.name for group in groups if group.name not in allowed}
