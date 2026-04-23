"""
Testes para whitelist dinamica de grupos atribuiveis (#832).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from typing import Any, cast

from django.contrib.auth.models import Group

import pytest

from apps.core.constants import ALLOWED_USER_GROUPS
from apps.core.models import PermissaoFuncional
from apps.core.services.rbac_service import get_assignable_group_names, invalidate_assignable_groups_cache


@pytest.mark.django_db
class TestRBACServiceWhitelist:
    def setup_method(self) -> None:
        invalidate_assignable_groups_cache()

    def teardown_method(self) -> None:
        invalidate_assignable_groups_cache()

    def test_fallback_static_groups_always_included(self) -> None:
        names = get_assignable_group_names()
        assert ALLOWED_USER_GROUPS.issubset(names)

    def test_dynamic_group_with_functional_permission_is_included(self) -> None:
        group, _ = Group.objects.get_or_create(name="GrupoDinamicoService")
        permission, _ = PermissaoFuncional.objects.get_or_create(
            codename="pode_usar_grupo_dinamico_service",
            defaults={
                "label": "Pode usar grupo dinâmico (service)",
                "description": "Teste de whitelist dinâmica no serviço.",
                "category": "cadastros_administrativos",
                "is_system": False,
            },
        )
        permission_any = cast(Any, permission)
        permission_any.groups.add(group)

        names = get_assignable_group_names()
        assert "GrupoDinamicoService" in names

    def test_cache_is_invalidated_on_permission_group_change(self) -> None:
        group, _ = Group.objects.get_or_create(name="GrupoCacheInvalidation")
        permission, _ = PermissaoFuncional.objects.get_or_create(
            codename="pode_invalidate_assignable_cache",
            defaults={
                "label": "Pode invalidar cache de whitelist",
                "description": "Valida invalidação do cache de grupos atribuíveis.",
                "category": "cadastros_administrativos",
                "is_system": False,
            },
        )

        names_before = get_assignable_group_names()
        assert "GrupoCacheInvalidation" not in names_before

        permission_any = cast(Any, permission)
        permission_any.groups.add(group)

        names_after = get_assignable_group_names()
        assert "GrupoCacheInvalidation" in names_after
