"""
Tests RBAC dos endpoints `/api/metrics/team/*` (Onda 2 A3 — 2026-04-27).

Reproduz o mismatch identificado no RBAC Matrix Sweep:
- Frontend `canDashboardEquipe` (após Onda 1 C1) inclui DAT
- Backend metrics endpoints exigiam `run_daily_operations | supervise_operations`
  (sem DAT) — DAT via menu, recebia 403 ao carregar dados

Decisão (β, stakeholder 2026-04-27): adicionar `manage_admin_registries`
à composition existente em vez de criar policy unificada nova. Preserva
decisão prévia Lote 4.2.b2 (não consolidar 3 endpoints com objetos
protegidos diferentes em uma policy artificial).

Capabilities envolvidas (motivos legítimos):
- `run_daily_operations`    → Controle (operar)
- `supervise_operations`    → Diretoria (supervisionar)
- `manage_admin_registries` → DAT (validar/suportar — ator transversal)

Doc §3 da matriz canônica:
   Dashboard Equipe: Diretoria + DAT + super
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user(username: str, group_names: list[str]) -> Usuario:
    user = UsuarioFactory(username=username, email=f"{username}@example.com", password="testpass123", cpf=_next_cpf())
    for gname in group_names:
        group = GroupFactory(name=gname)
        user.groups.add(group)
    return user


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    cache.clear()
    yield
    cache.clear()


ENDPOINTS = [
    "/api/metrics/team/productivity/",
    "/api/metrics/team/quality/",
    "/api/metrics/team/formadores/",
]


# ============================================================================
# β: DAT acessa via `manage_admin_registries` (ator transversal)
# ============================================================================


class TestDATAccessTeamMetrics:
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_dat_user_can_access_team_metrics(self, endpoint):
        """
        DAT é ator transversal de validação/suporte. Após Onda 2 A3 (β),
        composition `run_daily_operations | supervise_operations |
        manage_admin_registries` libera DAT para os 3 endpoints metrics.

        Antes do fix: 403 (DAT sem run_daily_operations nem supervise_operations).
        Depois do fix: 200.
        """
        dat_user = _make_user("dat_metrics", ["DAT"])
        client = APIClient()
        client.force_authenticate(user=dat_user)
        res = client.get(endpoint)
        assert res.status_code == 200, (
            f"DAT deveria acessar {endpoint} via manage_admin_registries. " f"Got {res.status_code}: {res.content!r}"
        )


# ============================================================================
# Comportamento mantido (Controle, Diretoria, Super continuam acessando)
# ============================================================================


class TestExistingAccessPreserved:
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_controle_continues_to_access(self, endpoint):
        """Controle tem `run_daily_operations` → mantém acesso."""
        user = _make_user("controle_metrics", ["Controle"])
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(endpoint)
        assert res.status_code == 200

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_diretoria_continues_to_access(self, endpoint):
        """Diretoria tem `supervise_operations` → mantém acesso."""
        user = _make_user("diretoria_metrics", ["Diretoria"])
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(endpoint)
        assert res.status_code == 200

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_superuser_bypass(self, endpoint):
        super_user = UsuarioFactory(superuser=True)
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(endpoint)
        assert res.status_code == 200


# ============================================================================
# Bloqueio mantido (Coordenador/Apoio/Formador NÃO acessam)
# ============================================================================


class TestBlockingPreserved:
    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_coordenador_blocked(self, endpoint):
        """Coordenador não tem nenhuma das 3 capabilities → 403."""
        user = _make_user("coord_metrics", ["Coordenador"])
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(endpoint)
        assert res.status_code == 403

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_formador_blocked(self, endpoint):
        user = _make_user("form_metrics", ["Formador"])
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(endpoint)
        assert res.status_code == 403

    @pytest.mark.parametrize("endpoint", ENDPOINTS)
    def test_anonymous_blocked(self, endpoint):
        client = APIClient()
        res = client.get(endpoint)
        assert res.status_code in (401, 403)
