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

# pyright: reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false

from __future__ import annotations

from typing import Final

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

from apps.core.services.rbac_permissions import get_user_functional_permissions

# SSOT dos composites Setor×Função que conferem autoridade de APROVAÇÃO de
# solicitações (H2 / refactor rename-robusto, 2026-09-15). Cada dupla é
# (nome do grupo de SETOR, nome do grupo de FUNÇÃO); "aprovador" = estar em AMBOS.
# Único lugar onde esses nomes vivem — consumido por
# `policies._user_has_solicitation_approvals`, `user_is_assistente_administrativo_controle`
# (abaixo) e `views_basic` (/api/me/). Uma capability não expressa isto (é por-grupo,
# o composite é AND de 2 grupos), por isso a robustez a rename vem da guarda de drift
# (system check + teste-sentinela) que valida estes nomes contra SETOR_GROUPS/FUNCAO_GROUPS.
APPROVER_COMPOSITES: Final[tuple[tuple[str, str], ...]] = (
    ("Superintendência", "Gerente"),
    ("Controle", "Assistente Administrativo"),
)


def user_in_composite(
    user: AbstractBaseUser | AnonymousUser | None,
    setor: str,
    funcao: str,
) -> bool:
    """True se o usuário está em AMBOS os grupos (Setor E Função) do composite.

    NÃO faz bypass de superuser (quem chama decide) — espelha
    `user_is_assistente_administrativo_controle`.
    """
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.groups.filter(name=setor).exists()  # noqa: RBAC-composite-allowed
        and user.groups.filter(name=funcao).exists()  # noqa: RBAC-composite-allowed
    )


def user_matches_any_approver_composite(
    user: AbstractBaseUser | AnonymousUser | None,
) -> bool:
    """True se o usuário casa QUALQUER composite aprovador de `APPROVER_COMPOSITES`.

    Sem bypass de superuser (quem chama decide — `_user_has_solicitation_approvals`
    trata superuser antes).
    """
    if not user or not user.is_authenticated:
        return False
    return any(user_in_composite(user, setor, funcao) for setor, funcao in APPROVER_COMPOSITES)


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

    Nomes do composite vêm da SSOT `APPROVER_COMPOSITES` (não mais literais aqui).
    """
    return user_in_composite(user, "Controle", "Assistente Administrativo")


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
