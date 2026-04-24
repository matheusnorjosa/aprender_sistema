"""
Epic 2 RBAC Refactor — tests for HasPerm(codename) parametric permission class.

Valida:
- HasPerm grant/deny baseado em get_user_functional_permissions
- Bypass para is_superuser
- Composition DRF: & (AND), | (OR), ~ (NOT)
- Deprecation warnings nas 12 classes factory legacy
- Integração com o cache de permissões funcionais

Ver v2/docs/plans/rbac-refactor/epic-2-hasperm.md e master-plan §3.3.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportImplicitStringConcatenation=false

from __future__ import annotations

import warnings

from django.contrib.auth.models import AnonymousUser, Group
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

import pytest

from apps.core.models import PermissaoFuncional, Usuario
from apps.core.permissions import (
    HasPerm,
    IsComprasDashboardAccess,
    IsControle,
    IsControleOrDAT,
    IsControleOrSuper,
    IsCoordenadorOrDAT,
    IsDashboardOverview,
    IsDAT,
    IsDATOrSuper,
    IsGerencia,
    IsMapMetrics,
    IsSuperintendencia,
    IsSuperintendenciaOnly,
)

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def seeded_permission():
    """Cria uma PermissaoFuncional real para testes de HasPerm."""
    perm, _ = PermissaoFuncional.objects.get_or_create(
        codename="can_do_test_action",
        defaults={
            "label": "Executar ação de teste",
            "description": "Permissão para testes de HasPerm.",
            "category": "operacao",
            "is_system": False,
        },
    )
    return perm


@pytest.fixture
def group_with_permission(seeded_permission):
    """Cria um group Django associado à permission de teste."""
    group, _ = Group.objects.get_or_create(name="TestCapabilityGroup")
    seeded_permission.groups.add(group)
    return group


@pytest.fixture
def user_with_capability(group_with_permission):
    """Usuário cuja associação de group lhe dá a permissão funcional."""
    user = Usuario.objects.create_user(
        username="cap_user",
        email="cap@test.com",
        password="x",
        cpf="10000000001",
    )
    user.groups.add(group_with_permission)
    return user


@pytest.fixture
def user_without_capability():
    """Usuário autenticado mas sem a permissão de teste."""
    return Usuario.objects.create_user(
        username="no_cap_user",
        email="nocap@test.com",
        password="x",
        cpf="10000000002",
    )


@pytest.fixture
def superuser():
    """Superuser — sempre passa em HasPerm (bypass)."""
    return Usuario.objects.create_superuser(
        username="su",
        email="su@test.com",
        password="x",
        cpf="10000000003",
    )


@pytest.fixture
def request_factory():
    return APIRequestFactory()


def _build_request(factory, user) -> Request:
    """Constrói um request DRF autenticado com o user fornecido."""
    django_req = factory.get("/")
    req = Request(django_req)
    req.user = user
    return req


# ============================================================================
# HasPerm — comportamento básico
# ============================================================================


def test_hasperm_grants_user_with_functional_permission(request_factory, user_with_capability):
    """HasPerm('codename') deve retornar True para user com a permissão via group."""
    perm = HasPerm("can_do_test_action")
    req = _build_request(request_factory, user_with_capability)
    assert perm.has_permission(req, None) is True


def test_hasperm_denies_user_without_functional_permission(request_factory, user_without_capability):
    """HasPerm retorna False para user autenticado sem a permissão."""
    perm = HasPerm("can_do_test_action")
    req = _build_request(request_factory, user_without_capability)
    assert perm.has_permission(req, None) is False


def test_hasperm_denies_anonymous_user(request_factory):
    """HasPerm retorna False para user não autenticado (nunca bypass)."""
    perm = HasPerm("can_do_test_action")
    req = _build_request(request_factory, AnonymousUser())
    assert perm.has_permission(req, None) is False


def test_hasperm_grants_superuser_bypass(request_factory, superuser):
    """HasPerm sempre retorna True para is_superuser, sem consultar funcperm."""
    perm = HasPerm("nonexistent_codename_ever")
    req = _build_request(request_factory, superuser)
    assert perm.has_permission(req, None) is True


def test_hasperm_strips_app_label_prefix(request_factory, user_with_capability):
    """HasPerm aceita 'core.codename' e 'codename' como formas equivalentes.

    Django has_perm usa prefixo app_label; o sistema funcional usa codename
    bare. HasPerm aceita as duas formas para familiaridade com API do Django.
    """
    bare = HasPerm("can_do_test_action")
    prefixed = HasPerm("core.can_do_test_action")
    req = _build_request(request_factory, user_with_capability)
    assert bare.has_permission(req, None) is True
    assert prefixed.has_permission(req, None) is True


def test_hasperm_custom_message():
    """HasPerm aceita message customizada no kwarg."""
    perm = HasPerm("some_codename", message="Operação restrita a auditores.")
    assert perm.message == "Operação restrita a auditores."


def test_hasperm_repr_includes_codename():
    """__repr__ expõe o codename para debug/logs (sem prefixo app_label)."""
    perm = HasPerm("core.approve_solicitation")
    assert "approve_solicitation" in repr(perm)


# ============================================================================
# Composition DRF (&, |, ~)
# ============================================================================


def test_hasperm_composition_or_grants_if_any_match(request_factory, user_with_capability):
    """HasPerm('A') | HasPerm('B') deve grantar se user tem A OU B."""
    composed = HasPerm("can_do_test_action") | HasPerm("nonexistent_perm")
    req = _build_request(request_factory, user_with_capability)
    assert composed.has_permission(req, None) is True


def test_hasperm_composition_and_requires_both(request_factory, user_with_capability):
    """HasPerm('A') & HasPerm('B') deve negar se user tem só A."""
    composed = HasPerm("can_do_test_action") & HasPerm("nonexistent_perm")
    req = _build_request(request_factory, user_with_capability)
    assert composed.has_permission(req, None) is False


def test_hasperm_composition_not_inverts_grant(request_factory, user_with_capability):
    """~HasPerm('A') deve negar user que TEM a permissão A."""
    composed = ~HasPerm("can_do_test_action")
    req = _build_request(request_factory, user_with_capability)
    assert composed.has_permission(req, None) is False


# ============================================================================
# Deprecation — 12 classes factory legacy emitem DeprecationWarning
# ============================================================================


LEGACY_CLASSES = [
    IsSuperintendencia,
    IsSuperintendenciaOnly,
    IsCoordenadorOrDAT,
    IsControleOrSuper,
    IsDATOrSuper,
    IsComprasDashboardAccess,
    IsDAT,
    IsControleOrDAT,
    IsControle,
    IsGerencia,
    IsDashboardOverview,
    IsMapMetrics,
]


@pytest.mark.parametrize("legacy_cls", LEGACY_CLASSES)
def test_legacy_factory_class_emits_deprecation_warning(legacy_cls):
    """Cada uma das 12 factory classes deve emitir DeprecationWarning no __init__."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        legacy_cls()
        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert deprecation_warnings, f"{legacy_cls.__name__} não emitiu DeprecationWarning. " "Ver master-plan §3.3."
        msg = str(deprecation_warnings[0].message)
        assert (
            "HasPerm" in msg
        ), f"Mensagem de deprecation de {legacy_cls.__name__} deve apontar para HasPerm equivalente."


def test_legacy_classes_still_work_behaviorally(
    request_factory, user_with_capability, seeded_permission, group_with_permission
):
    """
    Deprecation é cosmética: comportamento das 12 classes legacy deve
    permanecer idêntico para garantir backward compat até o Epic 5.
    """
    # Conecta a permissão "can_do_test_action" ao codename de uma legacy class
    # para validar que a classe legacy ainda funciona.
    # Usamos IsDAT (codename=pode_operar_dat_exclusivo) como piloto.
    pode_operar_dat_exclusivo = PermissaoFuncional.objects.filter(codename="manage_purchases_and_materials").first()
    assert pode_operar_dat_exclusivo is not None, "Seed deve ter a permissão."

    # Adiciona o group do user à permissão pode_operar_dat_exclusivo
    pode_operar_dat_exclusivo.groups.add(group_with_permission)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        perm = IsDAT()
    req = _build_request(request_factory, user_with_capability)
    assert perm.has_permission(req, None) is True
