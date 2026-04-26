"""
Testes da Fase 2 RBAC funcional (#828).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIRequestFactory

import pytest

from apps.core.models import PermissaoFuncional, Usuario
from apps.core.permissions import HasPerm, IsGerenteSuperintendencia

pytestmark = pytest.mark.django_db


class _MockView:
    kwargs: dict[str, str] = {}


def _request_with_user(factory: APIRequestFactory, user: Usuario):
    request = factory.get("/")
    request.user = user
    request.query_params = {}
    return request


def test_functional_permission_allows_access_via_group_mapping():
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="dat_funcperm",
        email="dat_funcperm@test.com",
        password="test123",
        cpf="10000000001",
    )
    user.groups.add(dat_group)

    request = _request_with_user(APIRequestFactory(), user)
    assert HasPerm("manage_purchases_and_materials")().has_permission(request, _MockView()) is True


def test_functional_permission_denies_user_without_mapping():
    user = Usuario.objects.create_user(
        username="sem_funcperm",
        email="sem_funcperm@test.com",
        password="test123",
        cpf="10000000002",
    )

    request = _request_with_user(APIRequestFactory(), user)
    assert HasPerm("manage_purchases_and_materials")().has_permission(request, _MockView()) is False


def test_functional_permission_cache_hit_miss(django_assert_num_queries):
    cache.clear()
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="cache_funcperm",
        email="cache_funcperm@test.com",
        password="test123",
        cpf="10000000003",
    )
    user.groups.add(dat_group)

    request = _request_with_user(APIRequestFactory(), user)
    permission = HasPerm("manage_purchases_and_materials")()

    with django_assert_num_queries(1):
        assert permission.has_permission(request, _MockView()) is True

    with django_assert_num_queries(0):
        assert permission.has_permission(request, _MockView()) is True


def test_cache_invalidated_when_user_groups_change():
    cache.clear()
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="invalidate_user_groups",
        email="invalidate_user_groups@test.com",
        password="test123",
        cpf="10000000004",
    )
    user.groups.add(dat_group)

    permission = HasPerm("manage_purchases_and_materials")()
    request = _request_with_user(APIRequestFactory(), user)
    assert permission.has_permission(request, _MockView()) is True

    user.groups.clear()  # dispara m2m_changed em User.groups.through
    assert permission.has_permission(request, _MockView()) is False


def test_cache_invalidated_when_permission_m2m_changes():
    cache.clear()
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="invalidate_perm_m2m",
        email="invalidate_perm_m2m@test.com",
        password="test123",
        cpf="10000000005",
    )
    user.groups.add(dat_group)

    custom_perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="perm_temp_m2m",
        defaults={
            "label": "Permissão temporária M2M",
            "description": "Teste",
            "category": "test",
            "is_system": False,
        },
    )
    custom_perm.groups.set([dat_group])

    # Epic 5.3 (2026-04-24): funcperm_factory removido. Uso direto de HasPerm.
    permission = HasPerm("perm_temp_m2m")
    request = _request_with_user(APIRequestFactory(), user)
    assert permission.has_permission(request, _MockView()) is True

    custom_perm.groups.clear()  # dispara m2m_changed em PermissaoFuncional.groups.through
    assert permission.has_permission(request, _MockView()) is False


def test_cache_invalidated_when_permission_saved():
    cache.clear()
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="invalidate_perm_save",
        email="invalidate_perm_save@test.com",
        password="test123",
        cpf="10000000006",
    )
    user.groups.add(dat_group)

    custom_perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="perm_temp_save",
        defaults={
            "label": "Permissão temporária Save",
            "description": "Teste",
            "category": "test",
            "is_system": False,
        },
    )
    custom_perm.groups.set([dat_group])

    # Epic 5.3: HasPerm substitui funcperm_factory
    permission = HasPerm("perm_temp_save")
    request = _request_with_user(APIRequestFactory(), user)
    assert permission.has_permission(request, _MockView()) is True

    custom_perm.codename = "perm_temp_save_updated"
    custom_perm.save(update_fields=["codename", "updated_at"])
    assert permission.has_permission(request, _MockView()) is False


def test_cache_invalidated_when_permission_deleted():
    cache.clear()
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user = Usuario.objects.create_user(
        username="invalidate_perm_delete",
        email="invalidate_perm_delete@test.com",
        password="test123",
        cpf="10000000007",
    )
    user.groups.add(dat_group)

    custom_perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="perm_temp_delete",
        defaults={
            "label": "Permissão temporária Delete",
            "description": "Teste",
            "category": "test",
            "is_system": False,
        },
    )
    custom_perm.groups.set([dat_group])

    # Epic 5.3: HasPerm substitui funcperm_factory
    permission = HasPerm("perm_temp_delete")
    request = _request_with_user(APIRequestFactory(), user)
    assert permission.has_permission(request, _MockView()) is True

    custom_perm.delete()
    assert permission.has_permission(request, _MockView()) is False


def test_is_gerente_superintendencia_requires_funcperm_and_gerente_group():
    super_group, _ = Group.objects.get_or_create(name="Superintendência")
    gerente_group, _ = Group.objects.get_or_create(name="Gerente")

    user_ok = Usuario.objects.create_user(
        username="gerente_super_ok",
        email="gerente_super_ok@test.com",
        password="test123",
        cpf="10000000008",
    )
    user_ok.groups.add(super_group, gerente_group)

    user_without_gerente = Usuario.objects.create_user(
        username="gerente_super_no_gerente",
        email="gerente_super_no_gerente@test.com",
        password="test123",
        cpf="10000000009",
    )
    user_without_gerente.groups.add(super_group)

    user_without_super = Usuario.objects.create_user(
        username="gerente_super_no_super",
        email="gerente_super_no_super@test.com",
        password="test123",
        cpf="10000000010",
    )
    user_without_super.groups.add(gerente_group)

    permission = IsGerenteSuperintendencia()
    factory = APIRequestFactory()

    assert permission.has_permission(_request_with_user(factory, user_ok), _MockView()) is True
    assert permission.has_permission(_request_with_user(factory, user_without_gerente), _MockView()) is False
    # Issue #1222 (Epic 1): após realign, `approve_solicitation_batch` é
    # atribuído ao grupo Gerente (e Super). User só com Gerente passa o
    # composite (tem perm + tem grupo Gerente). Antes era restrito a quem
    # estava em Super.
    assert permission.has_permission(_request_with_user(factory, user_without_super), _MockView()) is True
