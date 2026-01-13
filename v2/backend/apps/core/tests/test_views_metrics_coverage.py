"""
Tests for views_metrics.py uncovered lines (Issue #322).

Coverage targets:
- Lines 78-79, 115: metrics_map with UF filter and coordinator counting
- Lines 191-261: metrics_map_coordinators endpoint
- Lines 423-427: formadores_metrics username fallback

Endpoints tested:
- GET /api/metrics/map/?uf=CE
- GET /api/metrics/map/coordinators/?uf=CE
- GET /api/metrics/formadores/
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

import pytest
from apps.core.models import (
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def grupos():
    """Create required groups for tests."""
    return {
        "controle": Group.objects.get_or_create(name="Controle")[0],
        "dat": Group.objects.get_or_create(name="DAT")[0],
        "superintendencia": Group.objects.get_or_create(name="Superintendência")[0],
        "coordenador": Group.objects.get_or_create(name="Coordenador")[0],
        "formador": Group.objects.get_or_create(name="Formador")[0],
        "gerente": Group.objects.get_or_create(name="Gerente")[0],
        "gerencia": Group.objects.get_or_create(name="Gerência")[0],
    }


@pytest.fixture
def user_controle(grupos):
    """User in Controle group (has access to metrics)."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"controle_{uid}",
        email=f"controle_{uid}@test.com",
        password="test123",
        cpf=f"1{uid[:10].ljust(10, '0')}",
    )
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def user_gerencia(grupos):
    """User in Gerência group (has access to formadores_metrics)."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"gerencia_{uid}",
        email=f"gerencia_{uid}@test.com",
        password="test123",
        cpf=f"2{uid[:10].ljust(10, '0')}",
    )
    user.groups.add(grupos["gerencia"])
    return user


@pytest.fixture
def municipios():
    """Create municipalities in different states."""
    return {
        "fortaleza": Municipio.objects.create(
            nome="Fortaleza",
            uf="CE",
            ibge_code=f"23{uuid4().hex[:5]}",
            latitude=-3.717200,
            longitude=-38.543400,
        ),
        "caucaia": Municipio.objects.create(
            nome="Caucaia",
            uf="CE",
            ibge_code=f"23{uuid4().hex[:5]}",
            latitude=-3.736111,
            longitude=-38.653889,
        ),
        "sao_paulo": Municipio.objects.create(
            nome="São Paulo",
            uf="SP",
            ibge_code=f"35{uuid4().hex[:5]}",
            latitude=-23.550520,
            longitude=-46.633308,
        ),
    }


@pytest.fixture
def projeto():
    """Create a test project."""
    return Projeto.objects.create(
        nome=f"Projeto Test {uuid4().hex[:6]}",
        codigo=f"PT{uuid4().hex[:4].upper()}",
        fluxo="SUPER",
    )


@pytest.fixture
def tipo_evento():
    """Create an event type."""
    return TipoEvento.objects.create(nome=f"Tipo {uuid4().hex[:6]}")


@pytest.fixture
def coordenador_user(grupos):
    """Create a coordinator user with first/last name."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"coord_{uid}",
        email=f"coord_{uid}@test.com",
        password="test123",
        cpf=f"3{uid[:10].ljust(10, '0')}",
        first_name="Maria",
        last_name="Silva",
    )
    user.groups.add(grupos["coordenador"])
    return user


@pytest.fixture
def formador_sem_nome(grupos):
    """Create a formador without first_name/last_name (for fallback test)."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"formador_anonimo_{uid}",
        email=f"formador_{uid}@test.com",
        password="test123",
        cpf=f"4{uid[:10].ljust(10, '0')}",
        first_name="",
        last_name="",
    )
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def formador_com_nome(grupos):
    """Create a formador with first_name/last_name."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"formador_nomeado_{uid}",
        email=f"formador_nome_{uid}@test.com",
        password="test123",
        cpf=f"5{uid[:10].ljust(10, '0')}",
        first_name="João",
        last_name="Santos",
    )
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def solicitacoes_ce(
    municipios, projeto, tipo_evento, coordenador_user, formador_com_nome, grupos
):
    """Create approved solicitations in CE state with coordinator and formador participations."""
    now = timezone.now()
    solicitacoes = []

    # Create user to be the creator
    uid = uuid4().hex[:8]
    criador = Usuario.objects.create_user(
        username=f"criador_{uid}",
        email=f"criador_{uid}@test.com",
        password="test123",
        cpf=f"6{uid[:10].ljust(10, '0')}",
    )

    # Create 3 solicitations in Fortaleza-CE
    for i in range(3):
        sol = Solicitacao.objects.create(
            usuario=criador,
            status="aprovado",
            inicio=now + timedelta(days=i),
            fim=now + timedelta(days=i, hours=2),
            municipio=municipios["fortaleza"],
            projeto=projeto,
            tipo_evento=tipo_evento,
        )
        sol.formadores.add(formador_com_nome)

        # Add coordinator participation
        Participation.objects.create(
            solicitacao=sol,
            usuario=coordenador_user,
            role=Participation.Role.COORDENADOR,
        )

        # Add formador participation
        Participation.objects.create(
            solicitacao=sol,
            usuario=formador_com_nome,
            role=Participation.Role.FORMADOR,
        )

        solicitacoes.append(sol)

    # Create 1 solicitation in Caucaia-CE
    sol = Solicitacao.objects.create(
        usuario=criador,
        status="aprovado",
        inicio=now + timedelta(days=10),
        fim=now + timedelta(days=10, hours=3),
        municipio=municipios["caucaia"],
        projeto=projeto,
        tipo_evento=tipo_evento,
    )
    sol.formadores.add(formador_com_nome)

    Participation.objects.create(
        solicitacao=sol,
        usuario=coordenador_user,
        role=Participation.Role.COORDENADOR,
    )
    Participation.objects.create(
        solicitacao=sol,
        usuario=formador_com_nome,
        role=Participation.Role.FORMADOR,
    )
    solicitacoes.append(sol)

    return solicitacoes


@pytest.fixture
def solicitacao_sp(municipios, projeto, tipo_evento, grupos):
    """Create a solicitation in SP state (should be excluded by CE filter)."""
    now = timezone.now()

    uid = uuid4().hex[:8]
    criador = Usuario.objects.create_user(
        username=f"criador_sp_{uid}",
        email=f"criador_sp_{uid}@test.com",
        password="test123",
        cpf=f"7{uid[:10].ljust(10, '0')}",
    )

    sol = Solicitacao.objects.create(
        usuario=criador,
        status="aprovado",
        inicio=now + timedelta(days=20),
        fim=now + timedelta(days=20, hours=2),
        municipio=municipios["sao_paulo"],
        projeto=projeto,
        tipo_evento=tipo_evento,
    )
    return sol


# ============================================================================
# TESTS: metrics_map with UF filter (lines 78-79, 115)
# ============================================================================


class TestMetricsMapUFFilter:
    """Tests for metrics_map UF filter (lines 78-79) and coordinator count (line 115)."""

    def test_filter_by_uf_returns_only_matching_state(
        self, user_controle, solicitacoes_ce, solicitacao_sp
    ):
        """
        Test: ?uf=CE returns only Ceará municipalities.

        Covers lines 78-79: UF filter application.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        # Should only have CE municipalities
        for mun in data["by_municipio"]:
            assert mun["uf"] == "CE", f"Expected CE, got {mun['uf']}"

        # Should have 2 CE municipalities (Fortaleza and Caucaia)
        municipio_names = [m["municipio"] for m in data["by_municipio"]]
        assert "Fortaleza" in municipio_names
        assert "Caucaia" in municipio_names
        assert "São Paulo" not in municipio_names

    def test_filter_by_uf_shows_in_meta_filters(
        self, user_controle, solicitacoes_ce
    ):
        """
        Test: UF filter value appears in meta.filters.

        Covers line 79: filters_applied["uf"] = uf_filter
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        assert "meta" in data
        assert "filters" in data["meta"]
        assert data["meta"]["filters"]["uf"] == "CE"

    def test_filter_by_uf_counts_events_correctly(
        self, user_controle, solicitacoes_ce, solicitacao_sp
    ):
        """
        Test: Total count only includes filtered UF.

        Without filter: 5 total (4 CE + 1 SP)
        With ?uf=CE: 4 total (only CE)
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map")

        # Without filter - should have all 5
        response_all = client.get(url)
        assert response_all.status_code == 200
        assert response_all.json()["totals"]["all"] == 5

        # With CE filter - should have only 4
        response_ce = client.get(url, {"uf": "CE"})
        assert response_ce.status_code == 200
        assert response_ce.json()["totals"]["all"] == 4

    def test_coordinator_count_per_municipality(
        self, user_controle, solicitacoes_ce, coordenador_user
    ):
        """
        Test: Coordinator count per municipality is calculated.

        Covers line 115: coordenadores_por_municipio[item["..."]] = item["coordenadores"]
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        # Find Fortaleza in the response
        fortaleza = next(
            (m for m in data["by_municipio"] if m["municipio"] == "Fortaleza"),
            None,
        )
        assert fortaleza is not None, "Fortaleza should be in response"

        # Should have 1 coordinator (coordenador_user participates in 3 events there)
        assert fortaleza["coordenadores"] == 1

    def test_nonexistent_uf_returns_empty(self, user_controle, solicitacoes_ce):
        """
        Test: Filter by non-existent UF returns empty results.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map")
        response = client.get(url, {"uf": "XX"})

        assert response.status_code == 200
        data = response.json()

        assert data["totals"]["all"] == 0
        assert data["by_municipio"] == []


# ============================================================================
# TESTS: metrics_map_coordinators endpoint (lines 191-261)
# ============================================================================


class TestMetricsMapCoordinators:
    """Tests for metrics_map_coordinators endpoint (lines 191-261)."""

    def test_requires_uf_parameter(self, user_controle):
        """
        Test: Endpoint returns 400 if uf parameter is missing.

        Covers lines 191-193: UF validation.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url)

        assert response.status_code == 400
        assert "uf" in response.json()["detail"].lower()

    def test_returns_coordinators_for_uf(
        self, user_controle, solicitacoes_ce, coordenador_user
    ):
        """
        Test: Returns coordinator list for given UF.

        Covers lines 196-264: Main logic.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        assert data["uf"] == "CE"
        assert "coordenadores" in data
        assert len(data["coordenadores"]) >= 1

    def test_coordinator_has_expected_structure(
        self, user_controle, solicitacoes_ce, coordenador_user
    ):
        """
        Test: Each coordinator has id, nome, eventos, projetos, municipios.

        Covers lines 214-220, 251-257: Data structure.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        assert len(data["coordenadores"]) >= 1
        coord = data["coordenadores"][0]

        assert "id" in coord
        assert "nome" in coord
        assert "eventos" in coord
        assert "projetos" in coord
        assert "municipios" in coord
        assert isinstance(coord["projetos"], list)
        assert isinstance(coord["municipios"], list)

    def test_coordinator_nome_uses_full_name(
        self, user_controle, solicitacoes_ce, coordenador_user
    ):
        """
        Test: Coordinator nome uses first_name + last_name.

        Covers lines 211-213: Nome building.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        # Find our coordenador_user (Maria Silva)
        coord = next(
            (c for c in data["coordenadores"] if c["id"] == coordenador_user.id),
            None,
        )
        assert coord is not None
        assert coord["nome"] == "Maria Silva"

    def test_coordinator_projetos_list(
        self, user_controle, solicitacoes_ce, projeto, coordenador_user
    ):
        """
        Test: Projetos list contains project names with event counts.

        Covers lines 224-229: Project aggregation.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        coord = next(
            (c for c in data["coordenadores"] if c["id"] == coordenador_user.id),
            None,
        )
        assert coord is not None
        assert len(coord["projetos"]) >= 1

        # Each project should have nome and eventos
        proj = coord["projetos"][0]
        assert "nome" in proj
        assert "eventos" in proj
        assert proj["eventos"] >= 1

    def test_coordinator_municipios_list(
        self, user_controle, solicitacoes_ce, municipios, coordenador_user
    ):
        """
        Test: Municipios list contains municipality names with event counts.

        Covers lines 231-236: Municipality aggregation.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        coord = next(
            (c for c in data["coordenadores"] if c["id"] == coordenador_user.id),
            None,
        )
        assert coord is not None
        assert len(coord["municipios"]) >= 1

        # Each municipio should have nome and eventos
        mun = coord["municipios"][0]
        assert "nome" in mun
        assert "eventos" in mun

    def test_coordinators_ordered_by_eventos_desc(
        self, user_controle, solicitacoes_ce, grupos
    ):
        """
        Test: Coordinators are ordered by eventos descending.

        Covers line 259: Sorting.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        coords = data["coordenadores"]
        if len(coords) >= 2:
            for i in range(len(coords) - 1):
                assert coords[i]["eventos"] >= coords[i + 1]["eventos"]

    def test_uf_without_coordinators_returns_empty(self, user_controle, solicitacao_sp):
        """
        Test: UF without any coordinator participations returns empty list.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "SP"})

        assert response.status_code == 200
        data = response.json()

        assert data["uf"] == "SP"
        assert data["coordenadores"] == []

    def test_coordinator_username_fallback(self, user_controle, municipios, projeto, tipo_evento, grupos):
        """
        Test: Coordinator without first/last name uses username.

        Covers lines 212-213: Fallback to username.
        """
        client = APIClient()
        client.force_authenticate(user=user_controle)

        # Create coordinator without name
        uid = uuid4().hex[:8]
        coord_sem_nome = Usuario.objects.create_user(
            username=f"coord_anonimo_{uid}",
            email=f"coord_anonimo_{uid}@test.com",
            password="test123",
            cpf=f"8{uid[:10].ljust(10, '0')}",
            first_name="",
            last_name="",
        )
        coord_sem_nome.groups.add(grupos["coordenador"])

        # Create solicitation with this coordinator
        criador = Usuario.objects.create_user(
            username=f"criador_x_{uid}",
            email=f"criador_x_{uid}@test.com",
            password="test123",
            cpf=f"9{uid[:10].ljust(10, '0')}",
        )

        sol = Solicitacao.objects.create(
            usuario=criador,
            status="aprovado",
            inicio=timezone.now(),
            fim=timezone.now() + timedelta(hours=2),
            municipio=municipios["fortaleza"],
            projeto=projeto,
            tipo_evento=tipo_evento,
        )

        Participation.objects.create(
            solicitacao=sol,
            usuario=coord_sem_nome,
            role=Participation.Role.COORDENADOR,
        )

        url = reverse("core:metrics-map-coordinators")
        response = client.get(url, {"uf": "CE"})

        assert response.status_code == 200
        data = response.json()

        # Find coordinator without name
        coord = next(
            (c for c in data["coordenadores"] if c["id"] == coord_sem_nome.id),
            None,
        )
        assert coord is not None
        assert coord["nome"] == f"coord_anonimo_{uid}"


# ============================================================================
# TESTS: formadores_metrics username fallback (lines 423-427)
# ============================================================================


class TestFormadoresMetricsUsernameFallback:
    """Tests for formadores_metrics username fallback (lines 423-427)."""

    def test_formador_with_name_shows_full_name(
        self, user_gerencia, solicitacoes_ce, formador_com_nome
    ):
        """
        Test: Formador with first/last name shows full name.

        Covers line 420: nome = f"{first_name} {last_name}".strip()
        """
        client = APIClient()
        client.force_authenticate(user=user_gerencia)

        url = reverse("core:metrics-team-formadores")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        # Find our formador
        formador = next(
            (f for f in data["formadores"] if f["id"] == formador_com_nome.id),
            None,
        )
        assert formador is not None
        assert formador["nome"] == "João Santos"

    def test_formador_without_name_uses_username(
        self, user_gerencia, municipios, projeto, tipo_evento, formador_sem_nome, grupos
    ):
        """
        Test: Formador without first/last name uses username.

        Covers lines 421-427: Fallback logic.
        """
        client = APIClient()
        client.force_authenticate(user=user_gerencia)

        # Create solicitation with formador_sem_nome
        uid = uuid4().hex[:8]
        criador = Usuario.objects.create_user(
            username=f"criador_form_{uid}",
            email=f"criador_form_{uid}@test.com",
            password="test123",
            cpf=f"1{uid[:10].ljust(10, '1')}",
        )

        sol = Solicitacao.objects.create(
            usuario=criador,
            status="aprovado",
            inicio=timezone.now() - timedelta(days=5),
            fim=timezone.now() - timedelta(days=5) + timedelta(hours=2),
            municipio=municipios["fortaleza"],
            projeto=projeto,
            tipo_evento=tipo_evento,
        )
        sol.formadores.add(formador_sem_nome)

        Participation.objects.create(
            solicitacao=sol,
            usuario=formador_sem_nome,
            role=Participation.Role.FORMADOR,
        )

        url = reverse("core:metrics-team-formadores")
        response = client.get(url, {"days": 30})

        assert response.status_code == 200
        data = response.json()

        # Find our formador without name
        formador = next(
            (f for f in data["formadores"] if f["id"] == formador_sem_nome.id),
            None,
        )
        assert formador is not None
        # Should use username as fallback
        assert formador["nome"] == formador_sem_nome.username

    def test_formadores_metrics_returns_expected_fields(
        self, user_gerencia, solicitacoes_ce, formador_com_nome
    ):
        """
        Test: Each formador has id, nome, eventos, horas_trabalhadas, municipios_atendidos.
        """
        client = APIClient()
        client.force_authenticate(user=user_gerencia)

        url = reverse("core:metrics-team-formadores")
        response = client.get(url)

        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "formadores" in data

        if len(data["formadores"]) > 0:
            formador = data["formadores"][0]
            assert "id" in formador
            assert "nome" in formador
            assert "eventos" in formador
            assert "horas_trabalhadas" in formador
            assert "municipios_atendidos" in formador

    def test_formadores_metrics_respects_days_parameter(
        self, user_gerencia, solicitacoes_ce
    ):
        """
        Test: days parameter filters by date range.
        """
        client = APIClient()
        client.force_authenticate(user=user_gerencia)

        url = reverse("core:metrics-team-formadores")

        # With default days=30
        response_30 = client.get(url, {"days": 30})
        assert response_30.status_code == 200
        assert response_30.json()["period"] == "30d"

        # With days=7
        response_7 = client.get(url, {"days": 7})
        assert response_7.status_code == 200
        assert response_7.json()["period"] == "7d"
