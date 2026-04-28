"""
Tests RBAC do endpoint /api/availability/monthly (Bug 1 — Grade Mensal Controle).

Reproduz o bug reportado em produção (2026-04-27):
    - Usuário "Fabiana Veras Paz Cândido"
    - Setor: Controle
    - Função: Apoio de Coordenação
    - Capability: view_all_availability (atribuída via seed 0077)
    - Esperado: GET /api/availability/monthly → 200
    - Real: 403 "O grupo Controle não tem acesso à grade mensal de disponibilidade."

Causa raiz: `HasSectorAccess.has_permission` tem block hardcoded de Controle por
nome de grupo, ignorando a capability `view_all_availability`. Programa RBAC
Access Policy Realignment (#1226-#1247) migrou outras views para Capability
Policy Layer mas perdeu MonthlyAvailabilityView.

Fix: usar composition `[IsAuthenticated, CanViewAllAvailability | HasSectorAccess]`
e remover o block de Controle (incompatível com a intent matrix —
view_all_availability é atribuído a Controle/Gerente/Coord/Apoio por design).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false, reportPrivateUsage=false

from __future__ import annotations

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

import pytest

from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional, Usuario

pytestmark = pytest.mark.django_db


_USER_COUNTER = {"i": 0}


def _next_cpf() -> str:
    """CPF determinístico — evita colisão de hash (memória feedback_deterministic_unique_in_pytest)."""
    _USER_COUNTER["i"] += 1
    return f"99988{_USER_COUNTER['i']:06d}"


def _make_user_with_groups_and_caps(username: str, group_names: list[str], capability_codenames: list[str]) -> Usuario:
    """
    Cria user, atribui aos grupos pedidos, garante que cada capability está
    ligada a pelo menos um desses grupos. Espelha o cenário de produção onde
    o seed 0077 atribuiu `view_all_availability` ao grupo Controle.
    """
    user = Usuario.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="testpass123",
        cpf=_next_cpf(),
    )
    for gname in group_names:
        group, _ = Group.objects.get_or_create(name=gname)
        user.groups.add(group)
        for code in capability_codenames:
            perm = PermissaoFuncional.objects.filter(codename=code).first()
            assert perm is not None, f"PermissaoFuncional '{code}' não está no seed"
            perm.groups.add(group)
    return user


@pytest.fixture(autouse=True)
def _seed_rbac(db):
    """Garante seed antes de cada test (idempotente)."""
    call_command("seed_rbac")


@pytest.fixture(autouse=True)
def _clear_cache():
    """Cache Redis 5min — limpa entre testes para isolar."""
    cache.clear()
    yield
    cache.clear()


URL = "/api/availability/monthly/"
QS = "?year=2026&month=4&role=FORMADOR"


# ============================================================================
# Bug 1 — reproduz o caso reportado (Fabiana, Controle + Apoio de Coordenação)
# ============================================================================


class TestControleAccessViaCapability:
    def test_controle_with_view_all_availability_returns_200(self):
        """
        Caso da Fabiana (2026-04-27 — Bug 1):
        user no grupo Controle COM capability view_all_availability → DEVE acessar.

        Esse test FALHA hoje (HasSectorAccess block hardcoded de Controle).
        """
        user = _make_user_with_groups_and_caps(
            "fabiana",
            group_names=["Controle"],
            capability_codenames=["view_all_availability"],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 200, (
            f"Controle com view_all_availability deveria acessar a grade mensal. "
            f"Got {res.status_code}: {res.content!r}"
        )

    def test_apoio_coordenacao_in_controle_returns_200(self):
        """
        Cenário expandido: Apoio de Coordenação no setor Controle (combo da Fabiana).
        Mesmo resultado esperado — capability view_all_availability libera.
        """
        user = _make_user_with_groups_and_caps(
            "apoio_user",
            group_names=["Controle", "Apoio de Coordenação"],
            capability_codenames=["view_all_availability"],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 200


# ============================================================================
# Comportamento mantido (escopo por gerência via HasSectorAccess)
# ============================================================================


class TestSectorScopePreserved:
    def test_user_without_capability_no_gerencia_no_vinculo_returns_403(self):
        """
        D8 (2026-04-28): sem capability + sem gerencia_id na query + sem
        EquipeGerencia ativa → 403. Antes era "SUPER comportamento" (200) mas
        permitia que Formador/DAT/Diretoria entrassem na Grade Mensal sem
        vínculo organizacional. Agora HasSectorAccess exige `view_all_availability`
        OU pelo menos 1 EquipeGerencia ativo.
        """
        user = _make_user_with_groups_and_caps(
            "no_cap_user",
            group_names=["Coordenador"],
            capability_codenames=[],
        )
        # Sem EquipeGerencia ativa para esse user.
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 403, (
            f"Coord sem cap E sem EquipeGerencia deve receber 403 (D8). " f"Got {res.status_code}: {res.content!r}"
        )

    def test_user_without_capability_with_invalid_gerencia_returns_403(self):
        """
        Sem capability + gerencia_id de gerência que não pertence ao user → 403.
        Mantém scope check do HasSectorAccess.
        """
        user = _make_user_with_groups_and_caps(
            "no_cap_user2",
            group_names=["Coordenador"],
            capability_codenames=[],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS + "&gerencia_id=99999")
        assert res.status_code == 403


# ============================================================================
# D8 (2026-04-28) — Formador, DAT e Diretoria não acessam Grade Mensal
# ============================================================================


class TestFormadorAndOthersDenied:
    """
    Decisão D8: Formador, DAT e Diretoria não devem acessar Grade Mensal.

    - Formador: caso especial RD-02/RD-03; acessa apenas Meus Eventos + Bloqueios próprios
    - DAT: não tem motivo legítimo para consultar grade
    - Diretoria: decisão executiva, não consulta operacional

    Regra do backend após D8: sem `view_all_availability` E sem EquipeGerencia
    ativa → 403, mesmo sem `gerencia_id` na query.
    """

    def test_formador_returns_403(self):
        user = _make_user_with_groups_and_caps(
            "formador_user",
            group_names=["Formador"],
            capability_codenames=[],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 403, (
            f"Formador NÃO deve acessar Grade Mensal (D8). " f"Got {res.status_code}: {res.content!r}"
        )

    def test_dat_returns_403(self):
        user = _make_user_with_groups_and_caps(
            "dat_user",
            group_names=["DAT"],
            capability_codenames=[],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 403, (
            f"DAT NÃO deve acessar Grade Mensal (D8). " f"Got {res.status_code}: {res.content!r}"
        )

    def test_diretoria_returns_403(self):
        user = _make_user_with_groups_and_caps(
            "diretoria_user",
            group_names=["Diretoria"],
            capability_codenames=[],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 403, (
            f"Diretoria NÃO deve acessar Grade Mensal (D8). " f"Got {res.status_code}: {res.content!r}"
        )


class TestCoordenadorScopedAccess:
    """
    Coordenador/Apoio acessam Grade Mensal apenas com vínculo de EquipeGerencia
    ativa (D6 — scope via gerência). Sem vínculo, 403.
    """

    def test_coordenador_with_equipe_gerencia_returns_200(self):
        """
        Coordenador com EquipeGerencia ativa → 200. View escopa pessoas pela
        gerência vinculada. Sem `gerencia_id` na query, HasSectorAccess
        confirma que tem ao menos 1 vínculo e libera; view filtra dados.
        """
        user = _make_user_with_groups_and_caps(
            "coord_with_gerencia",
            group_names=["Coordenador"],
            capability_codenames=[],
        )
        gerencia = Gerencia.objects.create(
            nome="GERENCIA D8 TEST",
            nome_setor="Vidas D8",
        )
        EquipeGerencia.objects.create(
            gerencia=gerencia,
            usuario=user,
            papel="COORDENADOR",
            ativo=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 200, (
            f"Coord com EquipeGerencia ativa deve acessar Grade Mensal (escopo "
            f"resolvido em runtime). Got {res.status_code}: {res.content!r}"
        )

    def test_coordenador_without_equipe_gerencia_returns_403(self):
        """
        Coordenador SEM EquipeGerencia ativa → 403 (D8).

        Esse é o ponto-chave do hardening: antes era 200 com lista vazia; agora
        é 403 explícito porque nem cap global nem vínculo de gerência.
        """
        user = _make_user_with_groups_and_caps(
            "coord_no_gerencia",
            group_names=["Coordenador"],
            capability_codenames=[],
        )
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.get(URL + QS)
        assert res.status_code == 403, (
            f"Coord sem EquipeGerencia deve receber 403 (D8). " f"Got {res.status_code}: {res.content!r}"
        )


# ============================================================================
# Sanity (anonymous, superuser)
# ============================================================================


class TestSanity:
    def test_anonymous_blocked(self):
        client = APIClient()
        res = client.get(URL + QS)
        assert res.status_code in (401, 403)

    def test_superuser_returns_200(self):
        super_user = Usuario.objects.create_superuser(
            username="super_test_monthly",
            email="super_test_monthly@example.com",
            password="testpass123",
            cpf="99900099997",
        )
        client = APIClient()
        client.force_authenticate(user=super_user)
        res = client.get(URL + QS)
        assert res.status_code == 200
