"""
Contract snapshot tests para o Capability Policy Layer (Epic 4.5, Issue #1236).

Estes testes congelam o **contrato externo** da camada de policies para que
qualquer rename, remoção, adição ou drift de shape force revisão consciente
no PR (diff do snapshot = checklist de breaking change).

Escopo intencionalmente mínimo (memória `feedback_capability_policy_layer_pattern.md`):

- ✅ Snapshot literal de `PUBLIC_POLICY_KEYS` (contrato externo)
- ✅ Snapshot literal do response do endpoint `GET /api/me/policies/`
- ✅ Defense-in-depth do shape (sorted list[str])

NÃO duplica:
- Matrix integrity / no empty / frozenset type → cobertos em `test_rbac_policies.py`
- Naming convention regex / no `_policy` suffix → idem
- Parity Can* ↔ PUBLIC_POLICY_KEYS → coberto em `test_me_policies.py::TestParity`

NÃO snapshota:
- `ACCESS_POLICIES` completo. A matriz interna é "implementação mutável"
  (capabilities elegíveis podem mudar sem breaking — ver
  `feedback_capability_policy_layer_pattern.md §6`). Snapshotar tudo geraria
  ruído de PR sem proteção real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportPrivateUsage=false

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.rbac.policies import PUBLIC_POLICY_KEYS

pytestmark = pytest.mark.django_db


# ============================================================================
# Snapshot literal — contrato externo
# ============================================================================
#
# Esta lista É o contrato. Atualizá-la deve ser DECISÃO CONSCIENTE no PR:
#   - Adicionar key      → compatible (frontend opt-in)
#   - Remover/renomear   → BREAKING (deprecation period 2 releases)
#
# Diff desta lista no PR review = checklist obrigatório.

EXPECTED_PUBLIC_POLICY_KEYS_SORTED: list[str] = [
    "access_audit_logs",
    "access_solicitacao_approvals",
    "import_availability_blocks",
    "import_compras",
    "import_generic_spreadsheet",
    "manage_admin_registries",
    "manage_purchases_and_materials",
    "manage_solicitacao_status",
    "use_gcal",
    "view_all_availability",
    "view_compras_dashboard",
    "view_compras_pendencias",
    "view_compras_stats",
    "view_map_metrics",
    "view_overview_dashboard",
    "view_reports",
]


class TestPublicPolicyContract:
    def test_public_policy_keys_snapshot(self):
        """
        Snapshot literal de `PUBLIC_POLICY_KEYS`. Falha se alguém adiciona,
        remove ou renomeia uma key sem atualizar este teste — forçando
        revisão consciente do contrato público no PR.
        """
        assert sorted(PUBLIC_POLICY_KEYS) == EXPECTED_PUBLIC_POLICY_KEYS_SORTED


# ============================================================================
# Snapshot do endpoint real
# ============================================================================


class TestPoliciesEndpointContract:
    def test_me_policies_endpoint_response_snapshot(self):
        """
        Superuser → response idêntico à lista snapshotada acima. Cobre num
        único teste:
            - shape (lista flat, não dict/object)
            - ordenação alfabética
            - conteúdo público
            - integração view ↔ auth ↔ resolve_public_policies
            - paridade com PUBLIC_POLICY_KEYS
        """
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="contract_snapshot_super",
            email="contract_snapshot@example.com",
            password="testpass123",
            cpf="99900099999",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse("core:me-policies"))
        assert res.status_code == 200
        assert res.json() == EXPECTED_PUBLIC_POLICY_KEYS_SORTED

    def test_endpoint_response_is_sorted_string_list(self):
        """
        Defense-in-depth: mesmo se alguém atualizar o snapshot acima sem
        pensar, este teste semântico continua pegando drift de shape:
            - response NÃO pode ser dict / object
            - todos os elementos devem ser str
            - ordem alfabética obrigatória

        Esta é a última linha de defesa antes de quebrar consumidor frontend
        que faz `policies.includes("...")`.
        """
        User = get_user_model()
        super_user = User.objects.create_superuser(
            username="contract_shape_super",
            email="contract_shape@example.com",
            password="testpass123",
            cpf="99900099998",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(reverse("core:me-policies"))
        body = res.json()
        assert isinstance(body, list), f"Response deve ser list, got {type(body).__name__}"
        assert all(isinstance(x, str) for x in body), "Todos os elementos devem ser str"
        assert body == sorted(body), "Response deve estar ordenado alfabeticamente"
