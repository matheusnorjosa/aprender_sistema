"""
Testes para `GET /api/me/policies/` (Epic 4.4, Issue #1235).

Cobertura:
- Anonymous → 401/403
- Authenticated sem capabilities → []
- Superuser → todas as PUBLIC_POLICY_KEYS ordenadas
- User com cap específica (manage_admin_registries / view_compras_dashboard /
  operate_preagenda) → subset derivado da matriz (assert robusto, não hand-written)
- Contrato: response é JSON list, sorted, sem leakage de codenames
- Parity: PUBLIC_POLICY_KEYS == set de todas as classes Can* declaradas em
  apps.core.rbac.policies (guarda Epic 4.5)

Padrão: TDD-first — testes escritos antes da implementação.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.rbac.policies import ACCESS_POLICIES, PUBLIC_POLICY_KEYS, _PolicyPermission

pytestmark = pytest.mark.django_db

ENDPOINT_URL_NAME = "core:me-policies"


# ============================================================================
# Helpers (espelham test_rbac_policies.py — atomic counter, NÃO hash)
# ============================================================================


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    """CPF único determinístico por test session."""
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user(username: str, *codenames: str):
    """Cria User autenticado e atribui capabilities via grupo dedicado."""
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        cpf=_next_cpf(),
    )
    if codenames:
        group, _ = Group.objects.get_or_create(name=f"test-group-{username}")
        user.groups.add(group)
        for code in codenames:
            perm = PermissaoFuncional.objects.filter(codename=code).first()
            assert perm is not None, f"PermissaoFuncional '{code}' não está no seed"
            perm.groups.add(group)
    return user


@pytest.fixture
def seeded_db(db):
    call_command("seed_rbac")


def _public_policies_for_cap(cap: str) -> list[str]:
    """
    Subset de PUBLIC_POLICY_KEYS cujas capabilities elegíveis incluem `cap`.
    Usa a matriz como SSOT para o assert (não hand-written).
    """
    return sorted(key for key, caps in ACCESS_POLICIES.items() if key in PUBLIC_POLICY_KEYS and cap in caps)


# ============================================================================
# A. Auth
# ============================================================================


class TestAuth:
    def test_anonymous_returns_401_or_403(self):
        """User não autenticado → 401 (ou 403, depende do auth backend)."""
        client = APIClient()
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code in (401, 403)


# ============================================================================
# B. Empty / Superuser
# ============================================================================


class TestBasicCases:
    def test_authenticated_user_with_no_capabilities_returns_empty_list(self, seeded_db):
        user = _make_user("noperms")
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)
        assert body == []

    def test_superuser_returns_all_public_policy_keys_sorted(self, seeded_db):
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="super_test",
            email="super_test@example.com",
            password="testpass123",
            cpf="99900000999",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code == 200
        body = res.json()
        assert body == sorted(PUBLIC_POLICY_KEYS)


# ============================================================================
# C. Capability-derived subsets (assert robusto via matriz)
# ============================================================================


class TestCapabilityDerivedSubsets:
    def test_dat_user_returns_policies_with_manage_admin_registries(self, seeded_db):
        user = _make_user("dat_user", "manage_admin_registries")
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code == 200
        assert res.json() == _public_policies_for_cap("manage_admin_registries")

    def test_diretoria_user_returns_policies_with_view_compras_dashboard(self, seeded_db):
        user = _make_user("dir_user", "view_compras_dashboard")
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code == 200
        assert res.json() == _public_policies_for_cap("view_compras_dashboard")

    def test_controle_user_returns_policies_with_operate_preagenda(self, seeded_db):
        user = _make_user("controle_user", "operate_preagenda")
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        assert res.status_code == 200
        assert res.json() == _public_policies_for_cap("operate_preagenda")


# ============================================================================
# D. Contract (shape, sorting, no leakage)
# ============================================================================


class TestContract:
    def test_response_is_a_json_list_not_object(self, seeded_db):
        user = _make_user("contract_user", "manage_admin_registries")
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        body = res.json()
        assert isinstance(body, list), f"Response deve ser JSON list (flat), não object. Got: {type(body).__name__}"

    def test_response_is_alphabetically_sorted(self, seeded_db):
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="sorted_test",
            email="sorted_test@example.com",
            password="testpass123",
            cpf="99900001000",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        body = res.json()
        assert body == sorted(body), "Response deve estar ordenada alfabeticamente"

    def test_response_never_leaks_keys_outside_public_registry(self, seeded_db):
        """
        Anti-leakage guard: nenhum elemento da response pode ser uma key fora
        de PUBLIC_POLICY_KEYS. Garante que policy interna futura não vaze.
        """
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="leak_test",
            email="leak_test@example.com",
            password="testpass123",
            cpf="99900001001",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        body = set(res.json())
        leaked = body - PUBLIC_POLICY_KEYS
        assert not leaked, (
            f"Response contém keys fora do registry público: {sorted(leaked)}. "
            "PUBLIC_POLICY_KEYS é o contrato — nada além dele pode aparecer."
        )

    def test_response_never_contains_capability_codenames(self, seeded_db):
        """
        Defesa em profundidade: garante que nenhum codename "nu" (ex:
        "approve_solicitation_batch") apareça na response. As únicas keys
        que coincidem com codenames são single-cap policies registradas em
        PUBLIC_POLICY_KEYS (manage_admin_registries, manage_purchases_and_materials,
        view_compras_dashboard, view_overview_dashboard, view_map_metrics,
        view_all_availability) — essas são intencionais.
        """
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="codename_leak_test",
            email="codename_leak_test@example.com",
            password="testpass123",
            cpf="99900001002",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse(ENDPOINT_URL_NAME))
        body = set(res.json())

        # Capabilities multi-cap (compostas em policies via OR) NÃO podem
        # aparecer como key direta na response — só policies semânticas.
        all_caps: set[str] = set()
        for caps in ACCESS_POLICIES.values():
            all_caps.update(caps)
        # Codenames que são também keys públicas são intencionais (single-cap policies)
        intentional_overlap = all_caps & PUBLIC_POLICY_KEYS
        forbidden_codenames = all_caps - intentional_overlap
        leaked = body & forbidden_codenames
        assert not leaked, (
            f"Capability codenames vazaram na response: {sorted(leaked)}. "
            "Endpoint deve expor APENAS policy keys, nunca capabilities brutas."
        )


# ============================================================================
# E. Parity (guarda contra esquecimento de registrar Can* nova)
# ============================================================================


class TestParity:
    def test_public_policy_keys_match_all_policy_classes_in_module(self):
        """
        PUBLIC_POLICY_KEYS deve cobrir EXATAMENTE o conjunto de policies
        declaradas como Can* em apps.core.rbac.policies. Falha se:
          - Dev adicionou Can* nova mas esqueceu de registrar em PUBLIC_POLICY_KEYS
          - Dev removeu Can* mas esqueceu de remover de PUBLIC_POLICY_KEYS

        Quando Epic 4.5+ introduzir Policy interna (não pública), upgrade:
            INTERNAL_POLICY_KEYS = frozenset(...)
            assert all_class_policies == PUBLIC_POLICY_KEYS | INTERNAL_POLICY_KEYS
            assert PUBLIC_POLICY_KEYS.isdisjoint(INTERNAL_POLICY_KEYS)
        """
        all_class_policies = {
            cls.policy
            for cls in _PolicyPermission.__subclasses__()
            if cls.policy and cls.__module__ == "apps.core.rbac.policies"
        }
        missing_in_registry = all_class_policies - set(PUBLIC_POLICY_KEYS)
        extra_in_registry = set(PUBLIC_POLICY_KEYS) - all_class_policies
        assert not missing_in_registry, (
            f"Classes Can* sem entrada em PUBLIC_POLICY_KEYS: {sorted(missing_in_registry)}. "
            "Toda Can* nova deve ser registrada conscientemente como pública."
        )
        assert not extra_in_registry, (
            f"PUBLIC_POLICY_KEYS contém keys sem classe Can* correspondente: "
            f"{sorted(extra_in_registry)}. Remover key órfã."
        )

    def test_all_public_keys_exist_in_access_policies_matrix(self):
        """PUBLIC_POLICY_KEYS é subset de ACCESS_POLICIES (sem keys fantasmas)."""
        orphans = set(PUBLIC_POLICY_KEYS) - set(ACCESS_POLICIES.keys())
        assert not orphans, f"PUBLIC_POLICY_KEYS contém keys ausentes de ACCESS_POLICIES: {sorted(orphans)}"
