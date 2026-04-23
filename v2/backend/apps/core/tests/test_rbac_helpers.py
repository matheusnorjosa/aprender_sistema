"""
Epic 3.1 RBAC Refactor — tests for rbac_helpers module.

Valida:
- `user_has_any_perm` OR semantics
- `user_has_all_perms` AND semantics
- Bypass `is_superuser`
- Anonymous/None user retornam False
- Integração com `get_user_functional_permissions` (cache-aware)

Substitui o padrão proibido `user.groups.filter(name=...).exists()` por
uma API capability-oriented que passa pelo sistema oficial de permissões
funcionais do projeto.

Ver v2/docs/plans/rbac-refactor/epic-3-hardcoded.md e master-plan §4.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser, Group

import pytest

from apps.core.models import PermissaoFuncional, Usuario
from apps.core.rbac_helpers import user_has_all_perms, user_has_any_perm

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def perm_a():
    perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="test_can_a",
        defaults={
            "label": "Executar A",
            "description": "Teste A.",
            "category": "operacao",
            "is_system": False,
        },
    )
    return perm


@pytest.fixture
def perm_b():
    perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="test_can_b",
        defaults={
            "label": "Executar B",
            "description": "Teste B.",
            "category": "operacao",
            "is_system": False,
        },
    )
    return perm


@pytest.fixture
def group_with_a(perm_a):
    group, _ = Group.objects.get_or_create(name="TestGroupA")
    perm_a.groups.add(group)
    return group


@pytest.fixture
def group_with_b(perm_b):
    group, _ = Group.objects.get_or_create(name="TestGroupB")
    perm_b.groups.add(group)
    return group


@pytest.fixture
def user_with_a(group_with_a):
    user = Usuario.objects.create_user(
        username="user_a",
        email="a@test.com",
        password="x",
        cpf="30000000001",
    )
    user.groups.add(group_with_a)
    return user


@pytest.fixture
def user_with_a_and_b(group_with_a, group_with_b):
    user = Usuario.objects.create_user(
        username="user_ab",
        email="ab@test.com",
        password="x",
        cpf="30000000002",
    )
    user.groups.add(group_with_a, group_with_b)
    return user


@pytest.fixture
def user_empty():
    return Usuario.objects.create_user(
        username="user_empty",
        email="empty@test.com",
        password="x",
        cpf="30000000003",
    )


@pytest.fixture
def superuser():
    return Usuario.objects.create_superuser(
        username="su",
        email="su@test.com",
        password="x",
        cpf="30000000004",
    )


# ============================================================================
# user_has_any_perm — OR semantics
# ============================================================================


def test_any_perm_true_when_user_has_one(user_with_a):
    assert user_has_any_perm(user_with_a, "test_can_a", "test_can_b") is True


def test_any_perm_false_when_user_has_none(user_empty):
    assert user_has_any_perm(user_empty, "test_can_a", "test_can_b") is False


def test_any_perm_false_for_anonymous():
    assert user_has_any_perm(AnonymousUser(), "test_can_a") is False


def test_any_perm_false_for_none_user():
    assert user_has_any_perm(None, "test_can_a") is False


def test_any_perm_true_for_superuser_without_codenames_match(superuser):
    """Superuser sempre True, mesmo para codename inexistente."""
    assert user_has_any_perm(superuser, "nonexistent_code") is True


def test_any_perm_false_when_called_with_no_codenames(user_with_a):
    """Sem codenames, não há como ser True para user comum (mesmo tendo outras perms)."""
    assert user_has_any_perm(user_with_a) is False


# ============================================================================
# user_has_all_perms — AND semantics
# ============================================================================


def test_all_perms_true_when_user_has_both(user_with_a_and_b):
    assert user_has_all_perms(user_with_a_and_b, "test_can_a", "test_can_b") is True


def test_all_perms_false_when_user_has_only_one(user_with_a):
    assert user_has_all_perms(user_with_a, "test_can_a", "test_can_b") is False


def test_all_perms_true_for_superuser(superuser):
    assert user_has_all_perms(superuser, "any_code", "other_code") is True


def test_all_perms_false_for_anonymous():
    assert user_has_all_perms(AnonymousUser(), "test_can_a") is False
