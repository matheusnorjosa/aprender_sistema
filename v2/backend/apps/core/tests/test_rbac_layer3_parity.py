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
    """Issue #1222 (Epic 1): Super NÃO tem mais view_all_availability no seed
    realinhado (passa para Controle/Gerente/Coord/Apoio Coord)."""
    u = _user_with_groups("paridade_super", ["Superintendência"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_controle_tem_view_all_availability(rbac_seeded):
    """Controle mantém view_all_availability."""
    u = _user_with_groups("paridade_controle", ["Controle"])
    assert user_has_any_perm(u, "view_all_availability") is True


def test_gerencia_tem_view_all_availability(rbac_seeded):
    """Issue #1222 (Epic 1): grupo 'Gerência' descontinuado; Gerente (função)
    é quem tem view_all_availability agora."""
    u = _user_with_groups("paridade_ger", ["Gerência"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_diretoria_tem_view_all_availability(rbac_seeded):
    """Issue #1222 (Epic 1): Diretoria perdeu view_all_availability (escopo
    é Controle + funções operacionais)."""
    u = _user_with_groups("paridade_dir", ["Diretoria"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_formador_nao_tem_view_all_availability(rbac_seeded):
    u = _user_with_groups("paridade_form", ["Formador"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_coordenador_nao_tem_view_all_availability(rbac_seeded):
    """
    Bug 1 follow-up (PR #1248, migration 0078, 2026-04-27):
    Coordenador é SCOPED — não tem capability transversal `view_all_availability`.
    Vê apenas a gerência vinculada via `EquipeGerencia` (HasSectorAccess scope).

    Antes (Epic 1, migration 0077): tinha a capability — quebrou E2E J05
    (coord_fluir conseguindo ver grade de Vidas). Stakeholder confirmou em
    2026-04-27 que coordenador deve ser scoped por setor vinculado.
    """
    u = _user_with_groups("paridade_coord", ["Coordenador"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_apoio_coordenacao_nao_tem_view_all_availability(rbac_seeded):
    """Apoio de Coordenação tem mesma regra de scope que Coordenador."""
    u = _user_with_groups("paridade_apoio", ["Apoio de Coordenação"])
    assert user_has_any_perm(u, "view_all_availability") is False


def test_gerente_funcao_tem_view_all_availability(rbac_seeded):
    """Gerente (função) é transversal — mantém capability ampla. Distingue
    de `test_gerencia_tem_view_all_availability` acima que testa o GRUPO
    'Gerência' (descontinuado, sempre False)."""
    u = _user_with_groups("paridade_ger_funcao", ["Gerente"])
    assert user_has_any_perm(u, "view_all_availability") is True


# ============================================================================
# `pode_operar_controle_dat` — usada em views_solicitacao:198
# (antes: filter name in [Super, Controle, DAT])
# ============================================================================


def test_super_tem_operar_controle_dat(rbac_seeded):
    """Issue #1222 (Epic 1): Super não tem mais operate_preagenda (só Controle)."""
    u = _user_with_groups("paridade_scd_super", ["Superintendência"])
    assert user_has_any_perm(u, "operate_preagenda") is False


def test_controle_tem_operar_controle_dat(rbac_seeded):
    """Controle mantém operate_preagenda."""
    u = _user_with_groups("paridade_scd_ctrl", ["Controle"])
    assert user_has_any_perm(u, "operate_preagenda") is True


def test_dat_tem_operar_controle_dat(rbac_seeded):
    """Issue #1222 (Epic 1): DAT não tem mais operate_preagenda (só Controle)."""
    u = _user_with_groups("paridade_scd_dat", ["DAT"])
    assert user_has_any_perm(u, "operate_preagenda") is False


def test_formador_nao_tem_operar_controle_dat(rbac_seeded):
    u = _user_with_groups("paridade_scd_form", ["Formador"])
    assert user_has_any_perm(u, "operate_preagenda") is False


# ============================================================================
# `pode_operar_dat_exclusivo` — usada em views/acoes_notificacao:37
# (antes: filter name="DAT")
# ============================================================================


def test_dat_tem_operar_dat_exclusivo(rbac_seeded):
    """DAT mantém manage_purchases_and_materials."""
    u = _user_with_groups("paridade_dex_dat", ["DAT"])
    assert user_has_any_perm(u, "manage_purchases_and_materials") is True


def test_controle_tem_operar_dat_exclusivo(rbac_seeded):
    """Issue #1222 (Epic 1): Controle agora também tem manage_purchases_and_materials."""
    u = _user_with_groups("paridade_dex_ctrl", ["Controle"])
    assert user_has_any_perm(u, "manage_purchases_and_materials") is True
