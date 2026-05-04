"""
Capability-based authorization helpers (Epic 3 RBAC Refactor, 2026-04-23).

Use estas funções **em vez de** `user.groups.filter(name="...").exists()`
em views e services. Check canônico do Django é `user.has_perm()`; este
módulo expõe variações convenience (`any`/`all`) sobre functional permission
codenames.

Filtros de data scope por nome de grupo (ex: "quem é formador?") vivem em
`apps.core.rbac.constants` — são scope, não autorização.

Ver v2/docs/RBAC_NAMING.md §4 e master-plan §4.
"""

# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.core.services.rbac_permissions import get_user_functional_permissions


def user_has_any_perm(
    user: AbstractBaseUser | AnonymousUser | None,
    *codenames: str,
) -> bool:
    """
    True se o usuário possui QUALQUER UMA das permissões funcionais listadas.

    Regras:
    - user None ou anônimo → False
    - is_superuser → True (bypass)
    - codenames vazios → False (para usuário comum; superuser ainda é True)
    - caso geral → consulta `get_user_functional_permissions` (cache-aware)

    Preferido sobre `user.groups.filter(name=...).exists()` que é bypass
    do sistema RBAC (Epic 6 lint bane o padrão antigo).
    """
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not codenames:
        return False
    user_perms = get_user_functional_permissions(user)
    return any(code in user_perms for code in codenames)


def user_is_assistente_administrativo_controle(
    user: AbstractBaseUser | AnonymousUser | None,
) -> bool:
    """
    True se o usuário é Assistente Administrativo do Controle (composite
    Setor `Controle` + Função `Assistente Administrativo`).

    SSOT extraído em PR 13 hardening RBAC (2026-05-04). Antes a checagem
    vivia inline em `IsAssistenteAdministrativoControle` (permissions.py);
    este helper é reutilizado pela classe DRF E pelo helper de delegação
    de bloqueios (`_user_can_delegate_availability_block`).

    - user None ou anônimo → False
    - is_superuser → False (bypass é decidido por quem chama)
    - caso geral → exige AMBOS os grupos
    """
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.groups.filter(name="Controle").exists()  # noqa: RBAC-composite-allowed
        and user.groups.filter(name="Assistente Administrativo").exists()  # noqa: RBAC-composite-allowed
    )


def user_has_all_perms(
    user: AbstractBaseUser | AnonymousUser | None,
    *codenames: str,
) -> bool:
    """
    True se o usuário possui TODAS as permissões funcionais listadas.

    Regras:
    - user None ou anônimo → False
    - is_superuser → True
    - codenames vazios → False para usuário comum
      (convenção: "all of nothing" é vacuously True só com bypass; para
      user regular tratamos como "sem codename não há decisão")
    """
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    if not codenames:
        return False
    user_perms = get_user_functional_permissions(user)
    return all(code in user_perms for code in codenames)
