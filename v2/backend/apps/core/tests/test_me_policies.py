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

from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.models import PermissaoFuncional
from apps.core.rbac.policies import ACCESS_POLICIES, PUBLIC_POLICY_KEYS, _PolicyPermission
from apps.core.tests.factories import GroupFactory, UsuarioFactory

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
    user = UsuarioFactory(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        cpf=_next_cpf(),
    )
    if codenames:
        group = GroupFactory(name=f"test-group-{username}")
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
        super_user = UsuarioFactory(superuser=True)
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
        super_user = UsuarioFactory(superuser=True)
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
        super_user = UsuarioFactory(superuser=True)
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
        super_user = UsuarioFactory(superuser=True)
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


# ============================================================================
# F. Policies de menu (#1589) — paridade com gates legacy do frontend
# ============================================================================
#
# Expectativas HAND-WRITTEN (não derivadas da matriz) para provar comportamento,
# não tautologia. Paridade a preservar (usePermissions.ts:106,115,116):
#   canControle       = is_superuser OR Setor Controle
#   canDashboardEquipe = is_superuser OR Diretoria OR DAT
#   canDashboardGcal   = is_superuser OR Diretoria OR DAT OR Controle
#
# As capabilities-âncora (verificadas em functional_permissions_seed.py):
#   operate_preagenda / run_daily_operations -> só Controle
#   supervise_operations                     -> só Diretoria
#   manage_admin_registries                  -> só DAT
# então o OR sobre elas reproduz exatamente os setores dos gates legacy.


def _policies_for(user) -> set[str]:
    from apps.core.rbac.policies import resolve_public_policies

    return set(resolve_public_policies(user))


class TestMenuPolicies1589:
    """#1589 — 3 policies públicas que destravam o menu policy-only do #1270."""

    NEW_KEYS = ("access_controle_section", "view_team_dashboard", "view_gcal_dashboard")

    def test_new_keys_are_public(self):
        for key in self.NEW_KEYS:
            assert key in PUBLIC_POLICY_KEYS, f"{key} deveria estar em PUBLIC_POLICY_KEYS"

    def test_controle_user_gets_controle_section_and_gcal(self, seeded_db):
        # Setor Controle recebe operate_preagenda E run_daily_operations no seed.
        user = _make_user("m1589_controle", "operate_preagenda", "run_daily_operations")
        policies = _policies_for(user)
        assert "access_controle_section" in policies
        assert "view_gcal_dashboard" in policies
        assert "view_team_dashboard" not in policies  # Controle NÃO é Diretoria/DAT

    def test_controle_via_run_daily_only_still_gets_section(self, seeded_db):
        # Robustez: qualquer uma das capabilities de Controle basta.
        user = _make_user("m1589_controle_rdo", "run_daily_operations")
        policies = _policies_for(user)
        assert "access_controle_section" in policies
        assert "view_gcal_dashboard" in policies

    def test_diretoria_user_gets_team_and_gcal(self, seeded_db):
        user = _make_user("m1589_diretoria", "supervise_operations")
        policies = _policies_for(user)
        assert "view_team_dashboard" in policies
        assert "view_gcal_dashboard" in policies
        assert "access_controle_section" not in policies  # Diretoria NÃO é Controle

    def test_dat_user_gets_team_and_gcal(self, seeded_db):
        user = _make_user("m1589_dat", "manage_admin_registries")
        policies = _policies_for(user)
        assert "view_team_dashboard" in policies
        assert "view_gcal_dashboard" in policies
        assert "access_controle_section" not in policies  # DAT NÃO é Controle

    def test_unrelated_user_gets_none_of_the_three(self, seeded_db):
        # create_solicitation não pertence a nenhum dos 3 gates de menu.
        user = _make_user("m1589_unrelated", "create_solicitation")
        policies = _policies_for(user)
        for key in self.NEW_KEYS:
            assert key not in policies, f"{key} não deveria aparecer para usuário sem os setores"

    def test_superuser_gets_all_three(self, seeded_db):
        policies = _policies_for(UsuarioFactory(superuser=True))
        for key in self.NEW_KEYS:
            assert key in policies, f"superuser deveria ter {key} (bypass)"


def test_openapi_me_policies_declara_array_de_strings():
    """Guard de drift (#1463 item #10): o schema OpenAPI de GET /api/me/policies/
    deve declarar um ARRAY de strings — nao um objeto {policies: [...]} — porque o
    runtime devolve a lista crua (`Response(resolve_public_policies(...))`).
    Regenera o schema e trava a forma para pegar regressao de annotation.
    """
    from drf_spectacular.generators import SchemaGenerator

    schema = SchemaGenerator().get_schema(request=None, public=True)
    resp = schema["paths"]["/api/me/policies/"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert resp == {"type": "array", "items": {"type": "string"}}
