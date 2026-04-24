"""
Epic 4.1 RBAC Refactor — testes do dual-write de codenames.

Garantem que após o seed `verb_noun` ser aplicado, usuários com grupo
têm AMBOS os codenames (antigo `pode_*` e novo `verb_noun`) em
`get_user_functional_permissions`. Isso permite migração gradual de
consumidores sem breaking change durante o soak de 1 semana.

Ver v2/docs/plans/rbac-refactor/epic-4-codenames.md §4.1.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command

import pytest

from apps.core.models import PermissaoFuncional, Usuario

pytestmark = pytest.mark.django_db


# Mapeamento canônico old → new (espelha CODENAME_MAPPING em
# apps/core/services/functional_permissions_seed.py).
EXPECTED_MAPPING: tuple[tuple[str, str], ...] = (
    ("pode_aprovar_superintendencia", "approve_solicitation"),
    ("pode_aprovar_gerente_superintendencia", "approve_solicitation_batch"),
    ("pode_gerenciar_superintendencia_only", "execute_restricted_operations"),
    ("pode_criar_solicitacao_coord_dat", "create_solicitation"),
    ("pode_importar_controle_super", "import_spreadsheet"),
    ("pode_operar_dat", "manage_admin_registries"),
    ("pode_acessar_dashboard_compras", "view_compras_dashboard"),
    ("pode_operar_dat_exclusivo", "manage_purchases_and_materials"),
    ("pode_operar_controle_dat", "operate_preagenda"),
    ("pode_operar_controle", "run_daily_operations"),
    ("pode_operar_gerencia", "supervise_operations"),
    ("pode_acessar_dashboard_overview", "view_overview_dashboard"),
    ("pode_acessar_map_metrics", "view_map_metrics"),
    ("pode_editar_como_owner_ou_privilegiado", "edit_solicitation_as_owner_or_privileged"),
    ("pode_ver_todas_disponibilidades", "view_all_availability"),
)


@pytest.fixture
def rbac_seeded():
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


def test_seed_creates_30_permissions_total():
    """Pós-Epic 4.1: 15 antigos + 15 novos = 30 permissões."""
    call_command("seed_rbac")
    from apps.core.services.functional_permissions_seed import seed_functional_permissions

    seed_functional_permissions(assign_default_groups=True)

    assert PermissaoFuncional.objects.count() == 30, (
        f"Dual-write deve resultar em 30 permissões "
        f"(15 antigas + 15 novas verb_noun). Achei {PermissaoFuncional.objects.count()}."
    )


def test_each_old_codename_has_corresponding_new(rbac_seeded):
    """Para cada codename antigo, o novo equivalente deve existir."""
    missing: list[tuple[str, str]] = []
    for old, new in EXPECTED_MAPPING:
        if not PermissaoFuncional.objects.filter(codename=old).exists():
            missing.append((old, "OLD missing"))
        if not PermissaoFuncional.objects.filter(codename=new).exists():
            missing.append((new, "NEW missing"))
    assert not missing, f"Codenames faltando: {missing}"


def test_old_and_new_share_same_groups(rbac_seeded):
    """O M2M de groups deve ser idêntico entre old e new."""
    diffs: list[tuple[str, str, set[str], set[str]]] = []
    for old, new in EXPECTED_MAPPING:
        old_groups = set(PermissaoFuncional.objects.get(codename=old).groups.values_list("name", flat=True))
        new_groups = set(PermissaoFuncional.objects.get(codename=new).groups.values_list("name", flat=True))
        if old_groups != new_groups:
            diffs.append((old, new, old_groups, new_groups))
    assert not diffs, "Cada par (old, new) deve compartilhar o mesmo conjunto de groups. " f"Diferenças: {diffs}"


def test_user_in_dat_group_has_both_old_and_new_codename(rbac_seeded):
    """Dual-write: user no grupo DAT tem `pode_operar_dat` E `manage_admin_registries`."""
    user = _user_with_groups("dual_dat_user", ["DAT"])

    from apps.core.services.rbac_permissions import get_user_functional_permissions

    perms = get_user_functional_permissions(user)
    assert "pode_operar_dat" in perms, "Codename antigo deve continuar acessível durante soak"
    assert "manage_admin_registries" in perms, "Codename novo deve estar disponível pós-Epic 4.1"


def test_user_in_super_group_has_both_old_and_new_for_approve(rbac_seeded):
    """User no grupo Superintendência tem ambos os codenames de approve."""
    user = _user_with_groups("dual_super_user", ["Superintendência"])

    from apps.core.services.rbac_permissions import get_user_functional_permissions

    perms = get_user_functional_permissions(user)
    assert "pode_aprovar_superintendencia" in perms
    assert "approve_solicitation" in perms


def test_new_codenames_use_capability_oriented_naming():
    """Sanity: novos codenames seguem `verb_noun` em inglês, sem nome de setor."""
    from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED

    new_codenames = {seed.codename for seed in FUNCTIONAL_PERMISSIONS_SEED} - {old for old, _ in EXPECTED_MAPPING}
    forbidden = {"dat", "controle", "superintend", "gerencia", "coordenador", "formador", "diretoria", "pode_"}
    offenders: list[tuple[str, str]] = []
    for code in new_codenames:
        for token in forbidden:
            if token in code.lower():
                offenders.append((code, token))
                break
    assert not offenders, f"Novos codenames devem ser capability-oriented: {offenders}"
