"""
Epic 3.2 RBAC Refactor — parity tests para substituição de hardcoded
`user.groups.filter(name=...)` por `user_has_any_perm`.

Garantem que usuários que JÁ tinham acesso pré-refactor continuam tendo
acesso pós-refactor. Expansões de acesso (novos grupos ganham capability
via seed Epic 3.1) são mudanças deliberadas documentadas no PR body.

Ver v2/docs/plans/rbac-refactor/epic-3-hardcoded.md §3.2.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command

import pytest

from apps.core.models import Usuario
from apps.core.rbac_helpers import user_has_any_perm

pytestmark = pytest.mark.django_db


@pytest.fixture
def rbac_seeded():
    """Seed RBAC + functional permissions para testes de paridade."""
    call_command("seed_rbac")
    from apps.core.services.functional_permissions_seed import seed_functional_permissions

    seed_functional_permissions(assign_default_groups=True)


def _user_with_groups(username: str, groups: list[str]) -> Usuario:
    u = Usuario.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="x",
        cpf=username.rjust(11, "9")[-11:],
    )
    for gname in groups:
        group, _ = Group.objects.get_or_create(name=gname)
        u.groups.add(group)
    return u


# ============================================================================
# `pode_ver_todas_disponibilidades` — usada em 3 call sites (HasSectorAccess
# continua com lógica própria; _is_privileged_user de availability e monthly)
# ============================================================================


def test_superintendencia_tem_view_all_availability(rbac_seeded):
    u = _user_with_groups("paridade_super", ["Superintendência"])
    assert user_has_any_perm(u, "view_all_availability") is True


def test_controle_tem_view_all_availability(rbac_seeded):
    """Preserva comportamento de views/availability._is_privileged_user
    (Controle tinha acesso via filter name in [Super, Controle])."""
    u = _user_with_groups("paridade_controle", ["Controle"])
    assert user_has_any_perm(u, "view_all_availability") is True


def test_gerencia_tem_view_all_availability(rbac_seeded):
    """Preserva comportamento de views_availability_monthly
    (Gerência tinha acesso via filter name in [Super, Gerência, Diretoria])."""
    u = _user_with_groups("paridade_ger", ["Gerência"])
    assert user_has_any_perm(u, "view_all_availability") is True


def test_diretoria_tem_view_all_availability(rbac_seeded):
    u = _user_with_groups("paridade_dir", ["Diretoria"])
    assert user_has_any_perm(u, "view_all_availability") is True


def test_formador_nao_tem_view_all_availability(rbac_seeded):
    u = _user_with_groups("paridade_form", ["Formador"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_coordenador_nao_tem_view_all_availability(rbac_seeded):
    u = _user_with_groups("paridade_coord", ["Coordenador"])
    assert user_has_any_perm(u, "view_all_availability") is False


# ============================================================================
# `pode_operar_controle_dat` — usada em views_solicitacao:198
# (antes: filter name in [Super, Controle, DAT])
# ============================================================================


def test_super_tem_operar_controle_dat(rbac_seeded):
    u = _user_with_groups("paridade_scd_super", ["Superintendência"])
    assert user_has_any_perm(u, "operate_preagenda") is True


def test_controle_tem_operar_controle_dat(rbac_seeded):
    u = _user_with_groups("paridade_scd_ctrl", ["Controle"])
    assert user_has_any_perm(u, "operate_preagenda") is True


def test_dat_tem_operar_controle_dat(rbac_seeded):
    u = _user_with_groups("paridade_scd_dat", ["DAT"])
    assert user_has_any_perm(u, "operate_preagenda") is True


def test_formador_nao_tem_operar_controle_dat(rbac_seeded):
    u = _user_with_groups("paridade_scd_form", ["Formador"])
    assert user_has_any_perm(u, "operate_preagenda") is False


# ============================================================================
# `pode_operar_dat_exclusivo` — usada em views/acoes_notificacao:37
# (antes: filter name="DAT")
# ============================================================================


def test_dat_tem_operar_dat_exclusivo(rbac_seeded):
    u = _user_with_groups("paridade_dex_dat", ["DAT"])
    assert user_has_any_perm(u, "manage_purchases_and_materials") is True


def test_controle_nao_tem_operar_dat_exclusivo(rbac_seeded):
    u = _user_with_groups("paridade_dex_ctrl", ["Controle"])
    assert user_has_any_perm(u, "manage_purchases_and_materials") is False
