"""
Testes para modelo e seed de PermissaoFuncional (issue #827).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.db import IntegrityError

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.services.functional_permissions_seed import FUNCTIONAL_PERMISSIONS_SEED, seed_functional_permissions

pytestmark = pytest.mark.django_db


def _snapshot() -> list[tuple[str, str, tuple[str, ...]]]:
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for perm in PermissaoFuncional.objects.order_by("codename").prefetch_related("groups"):
        groups = tuple(sorted(perm.groups.values_list("name", flat=True)))
        rows.append((perm.codename, perm.category, groups))
    return rows


def test_permissao_funcional_unique_codename():
    PermissaoFuncional.objects.create(
        codename="permissao_unica",
        label="Permissão Única",
        category="teste",
    )

    with pytest.raises(IntegrityError):
        PermissaoFuncional.objects.create(
            codename="permissao_unica",
            label="Duplicada",
            category="teste",
        )


def test_permissao_funcional_is_system_default_true():
    perm = PermissaoFuncional.objects.create(
        codename="permissao_default",
        label="Permissão Default",
        category="teste",
    )
    assert perm.is_system is True


def test_permissao_funcional_groups_m2m():
    g1, _ = Group.objects.get_or_create(name="Grupo Teste 1")
    g2, _ = Group.objects.get_or_create(name="Grupo Teste 2")
    perm = PermissaoFuncional.objects.create(
        codename="permissao_m2m",
        label="Permissão M2M",
        category="teste",
    )

    perm.groups.set([g1, g2])

    assert set(perm.groups.values_list("name", flat=True)) == {"Grupo Teste 1", "Grupo Teste 2"}


def test_seed_functional_permissions_idempotent():
    first = seed_functional_permissions()
    snapshot_first = _snapshot()

    second = seed_functional_permissions()
    snapshot_second = _snapshot()

    assert len(snapshot_first) == 14
    assert snapshot_first == snapshot_second
    assert first["permissions_created"] + first["permissions_updated"] == 14
    assert second["permissions_created"] == 0
    assert second["permissions_updated"] == 14


def test_seed_functional_permissions_has_no_default_group_links():
    seed_functional_permissions()

    for item in FUNCTIONAL_PERMISSIONS_SEED:
        perm = PermissaoFuncional.objects.get(codename=item.codename)
        groups = tuple(sorted(perm.groups.values_list("name", flat=True)))
        assert groups == ()


def test_seed_functional_permissions_can_assign_groups_in_legacy_mode():
    seed_functional_permissions(assign_default_groups=True)

    for item in FUNCTIONAL_PERMISSIONS_SEED:
        perm = PermissaoFuncional.objects.get(codename=item.codename)
        groups = tuple(sorted(perm.groups.values_list("name", flat=True)))
        assert groups == tuple(sorted(item.group_names))


def test_seed_rbac_includes_functional_permissions():
    call_command("seed_rbac")

    assert PermissaoFuncional.objects.count() == 14
    expected = {item.codename for item in FUNCTIONAL_PERMISSIONS_SEED}
    assert set(PermissaoFuncional.objects.values_list("codename", flat=True)) == expected


def test_seed_functional_permissions_fixture_autouse():
    """
    Fixture autouse de apps.core/tests/conftest.py deve manter baseline disponível.
    """

    assert PermissaoFuncional.objects.count() >= 14
