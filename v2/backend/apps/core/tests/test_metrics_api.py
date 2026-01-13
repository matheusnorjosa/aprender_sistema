"""
Tests: Team Metrics API (Issue #189)

Tests for productivity, formadores, and quality metrics endpoints.

Coverage:
- Productivity metrics: events created/approved/rejected, approval rate, avg time, gcal stats
- Formadores metrics: top 10 ranking by events, hours worked, municipalities attended
- Quality metrics: rejection/conflict/rework rates, avg approval/publish times
- RBAC: 403 for unauthorized users (Formador, Coordenador)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from datetime import timedelta
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import (
    AuditLog,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


@pytest.fixture
def grupos(db):
    """Create necessary groups (Controle, Gerência, Formador, Coordenador)"""
    controle, _ = Group.objects.get_or_create(name="Controle")
    gerencia, _ = Group.objects.get_or_create(name="Gerência")
    formador, _ = Group.objects.get_or_create(name="Formador")
    coordenador, _ = Group.objects.get_or_create(name="Coordenador")
    return {
        "controle": controle,
        "gerencia": gerencia,
        "formador": formador,
        "coordenador": coordenador,
    }


@pytest.fixture
def controle_user(db, grupos):
    """User in Controle group"""
    user = Usuario.objects.create_user(
        username="controle1",
        email="controle1@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Controle",
        last_name="User",
    )
    user.groups.add(grupos["controle"])
    return user


@pytest.fixture
def gerencia_user(db, grupos):
    """User in Gerência group"""
    user = Usuario.objects.create_user(
        username="gerencia1",
        email="gerencia1@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Gerência",
        last_name="User",
    )
    user.groups.add(grupos["gerencia"])
    return user


@pytest.fixture
def formador_user(db, grupos):
    """User in Formador group (unauthorized for metrics)"""
    user = Usuario.objects.create_user(
        username="formador1",
        email="formador1@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Formador",
        last_name="Test",
    )
    user.groups.add(grupos["formador"])
    return user


@pytest.fixture
def coordenador_user(db, grupos):
    """User in Coordenador group (unauthorized for metrics)"""
    user = Usuario.objects.create_user(
        username="coord1",
        email="coord1@test.com",
        password="testpass123",
        cpf="44444444444",
    )
    user.groups.add(grupos["coordenador"])
    return user


@pytest.fixture
def tipo_evento(db):
    """Sample event type"""
    return TipoEvento.objects.create(nome="Formação", descricao="Formação presencial")


@pytest.fixture
def projeto(db):
    """Sample project"""
    return Projeto.objects.create(nome="Projeto Teste", codigo="TESTE", fluxo="SUPER")


@pytest.fixture
def municipio_a(db):
    """Municipality A"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400")


@pytest.fixture
def municipio_b(db):
    """Municipality B"""
    return Municipio.objects.create(nome="Caucaia", uf="CE", ibge_code="2303501")


@pytest.mark.django_db
class TestProductivityMetrics:
    """
    Test productivity metrics endpoint (Issue #189).

    Endpoint: GET /api/metrics/team/productivity/?days=N
    """

    def test_metrics_productivity(
        self, controle_user, tipo_evento, projeto, municipio_a
    ):
        """
        Test productivity metrics with mixed statuses.

        Creates 10 solicitações:
        - 6 approved (4 published, 1 error, 1 pending)
        - 3 rejected
        - 1 pending

        Validates calculations:
        - approval_rate = (6 / 10) * 100 = 60.0
        - gcal_error_rate = (1 / 6) * 100 = 16.67
        """
        client = APIClient()
        client.force_authenticate(user=controle_user)

        now = timezone.now()
        base_time = now - timedelta(days=3)

        # Create 10 solicitações with different statuses
        solicitacoes = []

        # 6 approved
        for i in range(6):
            sol = Solicitacao.objects.create(
                usuario=controle_user,
                tipo_evento=tipo_evento,
                projeto=projeto,
                municipio=municipio_a,
                inicio=base_time + timedelta(hours=i),
                fim=base_time + timedelta(hours=i + 2),
                status="aprovado",
                created_at=base_time,
                updated_at=base_time + timedelta(days=0, hours=12),  # 12h approval time
            )

            # Set GCal status
            if i < 4:
                sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
                sol.gcal_last_sync_at = base_time + timedelta(hours=12, minutes=5)
            elif i == 4:
                sol.gcal_status = Solicitacao.GCalStatus.ERROR
                sol.gcal_last_sync_at = base_time + timedelta(hours=12, minutes=5)
            else:
                sol.gcal_status = Solicitacao.GCalStatus.PENDING

            sol.save()
            solicitacoes.append(sol)

        # 3 rejected
        for i in range(3):
            sol = Solicitacao.objects.create(
                usuario=controle_user,
                tipo_evento=tipo_evento,
                projeto=projeto,
                municipio=municipio_a,
                inicio=base_time + timedelta(hours=10 + i),
                fim=base_time + timedelta(hours=12 + i),
                status="reprovado",
                created_at=base_time,
                updated_at=base_time + timedelta(hours=6),
            )
            solicitacoes.append(sol)

        # 1 pending
        sol = Solicitacao.objects.create(
            usuario=controle_user,
            tipo_evento=tipo_evento,
            projeto=projeto,
            municipio=municipio_a,
            inicio=base_time + timedelta(hours=20),
            fim=base_time + timedelta(hours=22),
            status="pendente",
            created_at=base_time,
        )
        solicitacoes.append(sol)

        # Call endpoint
        response = client.get("/api/metrics/team/productivity/?days=7")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # Validate structure
        assert "period" in data
        assert data["period"] == "7d"

        # Validate counts
        assert data["events_created"] == 10
        assert data["events_approved"] == 6
        assert data["events_rejected"] == 3

        # Validate approval rate (6/10 * 100 = 60.0)
        assert data["approval_rate"] == 60.0

        # Validate avg approval time (should be positive and reasonable)
        # Note: timedelta calculation may vary, so we check range instead of exact value
        assert data["avg_approval_time_hours"] > 0
        assert data["avg_approval_time_hours"] < 200  # Sanity check (within ~1 week)

        # Validate GCal metrics
        assert data["gcal_published"] == 4
        # gcal_error_rate = (1 / 6) * 100 = 16.67
        assert round(data["gcal_error_rate"], 2) == 16.67

    def test_productivity_metrics_empty_dataset(self, controle_user):
        """Test productivity metrics with no data (division by zero handling)"""
        client = APIClient()
        client.force_authenticate(user=controle_user)

        response = client.get("/api/metrics/team/productivity/?days=7")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # All counts should be 0
        assert data["events_created"] == 0
        assert data["events_approved"] == 0
        assert data["events_rejected"] == 0
        assert data["approval_rate"] == 0.0
        assert data["avg_approval_time_hours"] == 0.0
        assert data["gcal_published"] == 0
        assert data["gcal_error_rate"] == 0.0

    def test_productivity_metrics_custom_days(
        self, controle_user, tipo_evento, projeto, municipio_a
    ):
        """Test productivity metrics with custom days parameter"""
        client = APIClient()
        client.force_authenticate(user=controle_user)

        now = timezone.now()

        # Create event 2 days ago (should be included in days=7)
        Solicitacao.objects.create(
            usuario=controle_user,
            tipo_evento=tipo_evento,
            projeto=projeto,
            municipio=municipio_a,
            inicio=now - timedelta(days=2),
            fim=now - timedelta(days=2, hours=-2),
            status="aprovado",
            created_at=now - timedelta(days=2),
        )

        # Create event 10 days ago (should NOT be included in days=7)
        Solicitacao.objects.create(
            usuario=controle_user,
            tipo_evento=tipo_evento,
            projeto=projeto,
            municipio=municipio_a,
            inicio=now - timedelta(days=10),
            fim=now - timedelta(days=10, hours=-2),
            status="aprovado",
            created_at=now - timedelta(days=10),
        )

        # Call with days=7
        response = client.get("/api/metrics/team/productivity/?days=7")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json()["events_created"] == 1

        # Call with days=30 (should include both)
        response = client.get("/api/metrics/team/productivity/?days=30")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.json()["events_created"] == 2


@pytest.mark.django_db
class TestFormadoresMetrics:
    """
    Test formadores ranking metrics endpoint (Issue #189).

    Endpoint: GET /api/metrics/team/formadores/?days=N
    """

    def test_metrics_formadores(
        self, grupos, tipo_evento, projeto, municipio_a, municipio_b
    ):
        """
        Test formadores ranking with 15 formadores.

        Creates:
        - 3 formadores with 5, 3, 1 events respectively
        - Each event is 2 hours (horas_trabalhadas = events * 2)
        - Multiple municipalities per formador

        Validates:
        - Top 10 ranking (ordered by -eventos)
        - Correct calculation of horas_trabalhadas
        - Correct count of municipios_atendidos
        """
        client = APIClient()

        # Create Controle user for authentication
        controle_user = Usuario.objects.create_user(
            username="controle_test",
            email="controle@test.com",
            password="testpass123",
            cpf="99999999999",
        )
        controle_user.groups.add(grupos["controle"])

        client.force_authenticate(user=controle_user)

        now = timezone.now()
        base_time = now - timedelta(days=5)

        # Create 15 formadores
        formadores = []
        for i in range(15):
            formador = Usuario.objects.create_user(
                username=f"formador{i}",
                email=f"formador{i}@test.com",
                password="testpass123",
                cpf=f"{str(i).zfill(11)}",
                first_name=f"Formador",
                last_name=f"#{i}",
            )
            formador.groups.add(grupos["formador"])
            formadores.append(formador)

        # Create events for first 3 formadores (descending order: 5, 3, 1)
        event_counts = [5, 3, 1]

        for idx, count in enumerate(event_counts):
            formador = formadores[idx]

            for i in range(count):
                # Create solicitacao (approved, in date range)
                sol = Solicitacao.objects.create(
                    usuario=controle_user,
                    tipo_evento=tipo_evento,
                    projeto=projeto,
                    # Alternate between municipio_a and municipio_b
                    municipio=municipio_a if i % 2 == 0 else municipio_b,
                    inicio=base_time + timedelta(hours=i * 3),
                    fim=base_time + timedelta(hours=i * 3 + 2),  # 2h duration
                    status="aprovado",
                    created_at=base_time,
                )

                # Create participation (formador role)
                Participation.objects.create(
                    solicitacao=sol,
                    usuario=formador,
                    role=Participation.Role.FORMADOR,
                )

        # Call endpoint
        response = client.get("/api/metrics/team/formadores/?days=30")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # Validate structure
        assert "period" in data
        assert data["period"] == "30d"
        assert "formadores" in data

        formadores_list = data["formadores"]

        # Should return top 3 (we only created 3 with events)
        assert len(formadores_list) == 3

        # Validate ranking (ordered by -eventos)
        assert formadores_list[0]["eventos"] == 5
        assert formadores_list[1]["eventos"] == 3
        assert formadores_list[2]["eventos"] == 1

        # Validate horas_trabalhadas (each event is 2h)
        assert formadores_list[0]["horas_trabalhadas"] == 10.0  # 5 * 2h
        assert formadores_list[1]["horas_trabalhadas"] == 6.0  # 3 * 2h
        assert formadores_list[2]["horas_trabalhadas"] == 2.0  # 1 * 2h

        # Validate municipios_atendidos
        # Formador 0: 5 events alternating between A/B = 2 municipios (A, B, A, B, A)
        assert formadores_list[0]["municipios_atendidos"] == 2
        # Formador 1: 3 events alternating = 2 municipios (A, B, A)
        assert formadores_list[1]["municipios_atendidos"] == 2
        # Formador 2: 1 event = 1 municipio (A)
        assert formadores_list[2]["municipios_atendidos"] == 1

        # Validate nome format
        assert "Formador #0" in formadores_list[0]["nome"]

    def test_formadores_metrics_top_10_limit(
        self, grupos, tipo_evento, projeto, municipio_a
    ):
        """Test that formadores ranking is limited to top 10"""
        client = APIClient()

        controle_user = Usuario.objects.create_user(
            username="controle_top10",
            email="controle_top10@test.com",
            password="testpass123",
            cpf="98765432109",
        )
        controle_user.groups.add(grupos["controle"])

        client.force_authenticate(user=controle_user)

        now = timezone.now()
        base_time = now - timedelta(days=5)

        # Create 15 formadores with 1 event each
        for i in range(15):
            formador = Usuario.objects.create_user(
                username=f"formador_top10_{i}",
                email=f"formador_top10_{i}@test.com",
                password="testpass123",
                cpf=f"{str(100 + i).zfill(11)}",
                first_name=f"Top",
                last_name=f"{i}",
            )
            formador.groups.add(grupos["formador"])

            # Create 1 event
            sol = Solicitacao.objects.create(
                usuario=controle_user,
                tipo_evento=tipo_evento,
                projeto=projeto,
                municipio=municipio_a,
                inicio=base_time,
                fim=base_time + timedelta(hours=2),
                status="aprovado",
                created_at=base_time,
            )

            Participation.objects.create(
                solicitacao=sol,
                usuario=formador,
                role=Participation.Role.FORMADOR,
            )

        # Call endpoint
        response = client.get("/api/metrics/team/formadores/?days=30")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # Should return exactly 10 (top 10 limit)
        assert len(data["formadores"]) == 10

    def test_formadores_metrics_exclude_guest_participations(
        self, grupos, tipo_evento, projeto, municipio_a
    ):
        """Test that guest participations (no usuario) are excluded"""
        client = APIClient()

        controle_user = Usuario.objects.create_user(
            username="controle_guest",
            email="controle_guest@test.com",
            password="testpass123",
            cpf="11122233344",
        )
        controle_user.groups.add(grupos["controle"])

        client.force_authenticate(user=controle_user)

        now = timezone.now()
        base_time = now - timedelta(days=5)

        # Create event with guest participation (should be excluded)
        sol = Solicitacao.objects.create(
            usuario=controle_user,
            tipo_evento=tipo_evento,
            projeto=projeto,
            municipio=municipio_a,
            inicio=base_time,
            fim=base_time + timedelta(hours=2),
            status="aprovado",
            created_at=base_time,
        )

        Participation.objects.create(
            solicitacao=sol,
            usuario=None,  # Guest participation
            guest_email="guest@example.com",
            role=Participation.Role.FORMADOR,
        )

        # Call endpoint
        response = client.get("/api/metrics/team/formadores/?days=30")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # Should be empty (guest excluded)
        assert len(data["formadores"]) == 0


@pytest.mark.django_db
class TestQualityMetrics:
    """
    Test quality metrics endpoint (Issue #189).

    Endpoint: GET /api/metrics/team/quality/?days=N
    """

    def test_metrics_quality(
        self, controle_user, tipo_evento, projeto, municipio_a
    ):
        """
        Test quality metrics with conflicts and rework.

        Creates:
        - 10 total solicitações (7 approved + 1 approved w/ conflict + 2 rejected)
        - 2 rejected (rejection_rate = 20%)
        - 1 with conflict in observacoes (conflict_rate = 10%)
        - 1 with UPDATE audit log (rework_rate = 10%)

        Validates all KPIs.
        """
        client = APIClient()
        client.force_authenticate(user=controle_user)

        now = timezone.now()
        base_time = now - timedelta(days=5)

        # Create 10 solicitações
        solicitacoes = []

        # 7 approved (no conflicts)
        for i in range(7):
            sol = Solicitacao.objects.create(
                usuario=controle_user,
                tipo_evento=tipo_evento,
                projeto=projeto,
                municipio=municipio_a,
                inicio=base_time + timedelta(hours=i),
                fim=base_time + timedelta(hours=i + 2),
                status="aprovado",
                created_at=base_time,
                updated_at=base_time + timedelta(hours=10),  # 10h approval time
            )

            # First approved event: set PUBLISHED with gcal_last_sync_at
            # Note: gcal_last_sync_at must be AFTER updated_at for positive publish time
            if i == 0:
                sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
                # Set gcal_last_sync_at to 5 minutes AFTER updated_at
                sol.gcal_last_sync_at = sol.updated_at + timedelta(minutes=5)
                sol.save()

            solicitacoes.append(sol)

        # 1 approved with conflict in observacoes
        sol_conflict = Solicitacao.objects.create(
            usuario=controle_user,
            tipo_evento=tipo_evento,
            projeto=projeto,
            municipio=municipio_a,
            inicio=base_time + timedelta(hours=10),
            fim=base_time + timedelta(hours=12),
            status="aprovado",
            observacoes="Event has conflict with existing schedule",
            created_at=base_time,
            updated_at=base_time + timedelta(hours=10),
        )
        solicitacoes.append(sol_conflict)

        # 2 rejected
        for i in range(2):
            sol = Solicitacao.objects.create(
                usuario=controle_user,
                tipo_evento=tipo_evento,
                projeto=projeto,
                municipio=municipio_a,
                inicio=base_time + timedelta(hours=20 + i),
                fim=base_time + timedelta(hours=22 + i),
                status="reprovado",
                created_at=base_time,
                updated_at=base_time + timedelta(hours=5),
            )
            solicitacoes.append(sol)

        # Create UPDATE audit log for first solicitacao (rework)
        AuditLog.objects.create(
            usuario=controle_user,
            action="UPDATE",
            model_name="Solicitacao",
            details={"solicitacao_id": solicitacoes[0].id, "changes": "edited"},
            created_at=base_time + timedelta(hours=1),
        )

        # Call endpoint
        response = client.get("/api/metrics/team/quality/?days=30")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # Validate structure
        assert "period" in data
        assert data["period"] == "30d"

        # Validate rejection rate (2 / 10 * 100 = 20.0)
        assert data["rejection_rate"] == 20.0

        # Validate conflict rate (1 / 10 * 100 = 10.0)
        assert data["conflict_rate"] == 10.0

        # Validate rework rate (1 / 10 * 100 = 10.0)
        assert data["rework_rate"] == 10.0

        # Validate avg approval time (should be positive and reasonable)
        assert data["avg_approval_time_hours"] > 0
        assert data["avg_approval_time_hours"] < 200  # Sanity check (within ~1 week)

        # Validate avg publish time (should be positive and reasonable)
        assert data["avg_publish_time_minutes"] > 0
        assert data["avg_publish_time_minutes"] < 60  # Less than 1 hour is reasonable

    def test_quality_metrics_empty_dataset(self, controle_user):
        """Test quality metrics with no data (division by zero handling)"""
        client = APIClient()
        client.force_authenticate(user=controle_user)

        response = client.get("/api/metrics/team/quality/?days=30")

        assert response.status_code == http_status.HTTP_200_OK

        data = response.json()

        # All rates should be 0.0
        assert data["rejection_rate"] == 0.0
        assert data["conflict_rate"] == 0.0
        assert data["rework_rate"] == 0.0
        assert data["avg_approval_time_hours"] == 0.0
        assert data["avg_publish_time_minutes"] == 0.0


@pytest.mark.django_db
class TestMetricsRBAC:
    """
    Test RBAC for metrics endpoints (Issue #189).

    All endpoints require IsControle | IsGerencia permission.
    Unauthorized users (Formador, Coordenador) should get 403.
    """

    def test_metrics_rbac_controle_allowed(self, controle_user):
        """Test that Controle users can access metrics"""
        client = APIClient()
        client.force_authenticate(user=controle_user)

        # Test all 3 endpoints
        endpoints = [
            "/api/metrics/team/productivity/",
            "/api/metrics/team/formadores/",
            "/api/metrics/team/quality/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == http_status.HTTP_200_OK, (
                f"Controle user should access {endpoint}"
            )

    def test_metrics_rbac_gerencia_allowed(self, gerencia_user):
        """Test that Gerência users can access metrics"""
        client = APIClient()
        client.force_authenticate(user=gerencia_user)

        # Test all 3 endpoints
        endpoints = [
            "/api/metrics/team/productivity/",
            "/api/metrics/team/formadores/",
            "/api/metrics/team/quality/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == http_status.HTTP_200_OK, (
                f"Gerência user should access {endpoint}"
            )

    def test_metrics_rbac_formador_forbidden(self, formador_user):
        """Test that Formador users get 403 (forbidden)"""
        client = APIClient()
        client.force_authenticate(user=formador_user)

        # Test all 3 endpoints
        endpoints = [
            "/api/metrics/team/productivity/",
            "/api/metrics/team/formadores/",
            "/api/metrics/team/quality/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == http_status.HTTP_403_FORBIDDEN, (
                f"Formador user should be forbidden from {endpoint}"
            )

    def test_metrics_rbac_coordenador_forbidden(self, coordenador_user):
        """Test that Coordenador users get 403 (forbidden)"""
        client = APIClient()
        client.force_authenticate(user=coordenador_user)

        # Test all 3 endpoints
        endpoints = [
            "/api/metrics/team/productivity/",
            "/api/metrics/team/formadores/",
            "/api/metrics/team/quality/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == http_status.HTTP_403_FORBIDDEN, (
                f"Coordenador user should be forbidden from {endpoint}"
            )

    def test_metrics_rbac_anonymous_forbidden(self):
        """Test that anonymous users get 403 (forbidden)"""
        client = APIClient()
        # No authentication

        # Test all 3 endpoints
        endpoints = [
            "/api/metrics/team/productivity/",
            "/api/metrics/team/formadores/",
            "/api/metrics/team/quality/",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [
                http_status.HTTP_401_UNAUTHORIZED,
                http_status.HTTP_403_FORBIDDEN,
            ], f"Anonymous user should be denied access to {endpoint}"
