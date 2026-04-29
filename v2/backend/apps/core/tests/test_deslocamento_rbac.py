"""
Tests RBAC do `DeslocamentoViewSet` (Onda 1, C2 — 2026-04-27).

Reproduz divergência identificada no RBAC Matrix Sweep:
- Sidebar mostrava item "Deslocamentos" para `canControle || canCoordenador || canDAT`
- Backend exigia `HasPerm("view_all_availability")` (após 0078: Controle/Gerente only)
- Coord/DAT viam menu mas recebiam 403 ao clicar

Decisão (stakeholder, 2026-04-27): C2 = (B) — backend ganha composition +
acesso scoped via gerência. Coord/Apoio/DAT veem **apenas deslocamentos de
usuários nas próprias gerências vinculadas** (cross-table via EquipeGerencia).
Controle/Gerente continuam vendo tudo (capability `view_all_availability`).

Doc §3 da matriz canônica (`v2/docs/rbac_authorization_matrix.md`):
    Deslocamentos: Controle/Gerente ✅ | Coord/Apoio ⚠️ scope | DAT ⚠️ scope
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import Group
from django.core.cache import cache
from rest_framework.test import APIClient

import pytest

from apps.core.models import Deslocamento, EquipeGerencia, Gerencia, Usuario

pytestmark = pytest.mark.django_db


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user(username: str, group_names: list[str]) -> Usuario:
    user = Usuario.objects.create_user(
        username=username, email=f"{username}@example.com", password="testpass123", cpf=_next_cpf()
    )
    for gname in group_names:
        group, _ = Group.objects.get_or_create(name=gname)
        user.groups.add(group)
    return user


@pytest.fixture(autouse=True)
def _clear_rbac_cache(db):
    """
    Invalida cache de RBAC permissions entre tests (groups M2M atualizado
    pelo conftest session-scope `seed_functional_permissions_fixture`).
    """
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def gerencia_vidas():
    return Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")


@pytest.fixture
def gerencia_fluir():
    return Gerencia.objects.create(nome="GERENCIA 3", nome_setor="Fluir")


URL = "/api/deslocamentos/"


# ============================================================================
# Setup helper: user da gerência X cria deslocamento dele próprio
# ============================================================================


def _user_in_gerencia(username: str, group_names: list[str], gerencia: Gerencia) -> Usuario:
    user = _make_user(username, group_names)
    EquipeGerencia.objects.create(usuario=user, gerencia=gerencia)
    return user


def _create_deslocamento(usuario: Usuario, origem: str = "Fortaleza", destino: str = "Salvador") -> Deslocamento:
    return Deslocamento.objects.create(
        usuario=usuario,
        origem=origem,
        destino=destino,
        start_date=date(2026, 5, 1),
        end_date=date(2026, 5, 3),
    )


# ============================================================================
# Capability ampla — Controle/Gerente veem TUDO (bypass scope)
# ============================================================================


class TestCapacidadeAmpla:
    def test_controle_user_sees_all_deslocamentos(self, gerencia_vidas, gerencia_fluir):
        """Controle tem `view_all_availability` (seed 0078) → bypass scope."""
        user_vidas = _user_in_gerencia("user_v", ["Coordenador"], gerencia_vidas)
        user_fluir = _user_in_gerencia("user_f", ["Coordenador"], gerencia_fluir)
        _create_deslocamento(user_vidas, "Vidas-A", "Vidas-B")
        _create_deslocamento(user_fluir, "Fluir-A", "Fluir-B")

        controle_user = _make_user("controle_user", ["Controle"])
        client = APIClient()
        client.force_authenticate(user=controle_user)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 2

    def test_dat_user_sees_all_deslocamentos(self, gerencia_vidas, gerencia_fluir):
        """D9 (PR 2 RBAC hardening, 2026-04-28): DAT recebe `view_all_availability`
        no seed 0080 (papel transversal admin). Mesma cap libera bypass de scope —
        DAT vê todos os deslocamentos como Controle."""
        user_vidas = _user_in_gerencia("dt_user_v", ["Coordenador"], gerencia_vidas)
        user_fluir = _user_in_gerencia("dt_user_f", ["Coordenador"], gerencia_fluir)
        _create_deslocamento(user_vidas, "Vidas-A", "Vidas-B")
        _create_deslocamento(user_fluir, "Fluir-A", "Fluir-B")

        dat_user = _make_user("dat_user", ["DAT"])
        client = APIClient()
        client.force_authenticate(user=dat_user)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 2


# ============================================================================
# Scope por gerência — Coord/Apoio/DAT veem só usuários da própria gerência
# ============================================================================


class TestScopePorGerencia:
    def test_coord_with_gerencia_sees_only_own_sector(self, gerencia_vidas, gerencia_fluir):
        """
        Coord vinculado à gerência Vidas vê deslocamentos de usuários Vidas
        e NÃO vê deslocamentos de usuários Fluir.
        """
        user_vidas = _user_in_gerencia("v_user", ["Formador"], gerencia_vidas)
        user_fluir = _user_in_gerencia("f_user", ["Formador"], gerencia_fluir)
        desl_vidas = _create_deslocamento(user_vidas, "Vidas-A", "Vidas-B")
        _create_deslocamento(user_fluir, "Fluir-A", "Fluir-B")

        coord_vidas = _user_in_gerencia("coord_vidas", ["Coordenador"], gerencia_vidas)
        client = APIClient()
        client.force_authenticate(user=coord_vidas)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 1
        assert results[0]["id"] == desl_vidas.id

    def test_coord_without_any_gerencia_sees_nothing(self, gerencia_vidas):
        """
        Coord SEM EquipeGerencia vinculação vê 0 deslocamentos (não 403 — fail-safe).
        """
        user_vidas = _user_in_gerencia("v_user2", ["Formador"], gerencia_vidas)
        _create_deslocamento(user_vidas)

        coord_orphan = _make_user("coord_orphan", ["Coordenador"])
        # Sem EquipeGerencia
        client = APIClient()
        client.force_authenticate(user=coord_orphan)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert results == []

    def test_apoio_coordenacao_with_gerencia_sees_only_own_sector(self, gerencia_vidas, gerencia_fluir):
        """Apoio de Coordenação tem mesma regra de scope que Coordenador."""
        user_vidas = _user_in_gerencia("ap_v", ["Formador"], gerencia_vidas)
        user_fluir = _user_in_gerencia("ap_f", ["Formador"], gerencia_fluir)
        desl_vidas = _create_deslocamento(user_vidas, "VA", "VB")
        _create_deslocamento(user_fluir, "FA", "FB")

        apoio_vidas = _user_in_gerencia("apoio_vidas", ["Apoio de Coordenação"], gerencia_vidas)
        client = APIClient()
        client.force_authenticate(user=apoio_vidas)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 1
        assert results[0]["id"] == desl_vidas.id

    def test_gerente_user_with_gerencia_sees_only_own_sector(self, gerencia_vidas, gerencia_fluir):
        """D9 (PR 2 RBAC hardening, 2026-04-28): Gerente perde `view_all_availability`
        global (seed 0080) e cai em scope via EquipeGerencia (igual Coord/Apoio).
        Gerente pedagógico (Vidas, Fluir, ACerta, etc.) ou Gerente Sup vê apenas
        a própria gerência via vínculo organizacional."""
        user_vidas = _user_in_gerencia("gv_user", ["Formador"], gerencia_vidas)
        user_fluir = _user_in_gerencia("gf_user", ["Formador"], gerencia_fluir)
        desl_vidas = _create_deslocamento(user_vidas, "GV-A", "GV-B")
        _create_deslocamento(user_fluir, "GF-A", "GF-B")

        gerente_vidas = _user_in_gerencia("gerente_vidas", ["Gerente"], gerencia_vidas)
        client = APIClient()
        client.force_authenticate(user=gerente_vidas)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 1
        assert results[0]["id"] == desl_vidas.id


# ============================================================================
# Sanity (anonymous, superuser)
# ============================================================================


class TestSanity:
    def test_anonymous_blocked(self):
        client = APIClient()
        res = client.get(URL)
        assert res.status_code in (401, 403)

    def test_superuser_sees_all(self, gerencia_vidas):
        user = _user_in_gerencia("u", ["Formador"], gerencia_vidas)
        _create_deslocamento(user)
        super_user = Usuario.objects.create_superuser(
            username="super_d", email="super_d@example.com", password="testpass123", cpf="99900099996"
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(URL)
        assert res.status_code == 200
        results = res.json().get("results", res.json())
        assert len(results) == 1
