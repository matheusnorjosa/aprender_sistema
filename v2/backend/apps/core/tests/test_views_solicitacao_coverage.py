"""
Tests for views_solicitacao.py coverage improvement.

Issue #320: Aumentar cobertura de views_solicitacao.py (70% -> 85%+)

Covers:
- _get_client_ip: X-Forwarded-For, X-Real-IP headers
- Filters: sector, date_from, date_to, q
- extra_participants: coord_acompanha_ids, coord_acompanha_emails, invalid IDs
- batch_approve and batch_reject actions
- Edge cases: already approved, already rejected
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Municipio, Participation, Projeto, Solicitacao, TipoEvento, Usuario


@pytest.fixture
def api_client():
    """REST API client."""
    return APIClient()


@pytest.fixture
def grupos():
    """Create Django groups."""
    return {
        "Coordenador": Group.objects.get_or_create(name="Coordenador")[0],
        "Superintendência": Group.objects.get_or_create(name="Superintendência")[0],
        "Controle": Group.objects.get_or_create(name="Controle")[0],
        "DAT": Group.objects.get_or_create(name="DAT")[0],
        "Gerente": Group.objects.get_or_create(name="Gerente")[0],
    }


@pytest.fixture
def usuario_coordenador(grupos):
    """User with Coordenador role."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"coord_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"coord_{uid}@test.com",
    )
    user.groups.add(grupos["Coordenador"])
    return user


@pytest.fixture
def usuario_gerente_superintendencia(grupos):
    """User with Gerente + Superintendência roles (can batch approve/reject)."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"gerente_super_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"gerente_super_{uid}@test.com",
    )
    user.groups.add(grupos["Gerente"])
    user.groups.add(grupos["Superintendência"])
    return user


@pytest.fixture
def usuario_superintendencia(grupos):
    """User with Superintendência role."""
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"super_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"super_{uid}@test.com",
    )
    user.groups.add(grupos["Superintendência"])
    return user


@pytest.fixture
def usuario_formador(grupos):
    """User to be used as formador."""
    uid = uuid4().hex[:8]
    return Usuario.objects.create_user(
        username=f"formador_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"formador_{uid}@test.com",
    )


@pytest.fixture
def municipio():
    """Test municipality."""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto_super():
    """Project with SUPER flow (requires approval)."""
    uid = uuid4().hex[:8]
    return Projeto.objects.create(
        nome=f"Projeto SUPER {uid}",
        codigo=f"SUPER{uid[:4]}",
        fluxo="SUPER",
        ativo=True,
    )


@pytest.fixture
def tipo_evento():
    """Test event type."""
    return TipoEvento.objects.get_or_create(nome="Formação")[0]


# ============================================================
# Tests for _get_client_ip (lines 36, 39)
# ============================================================


@pytest.mark.django_db
class TestGetClientIP:
    """Tests for _get_client_ip helper function."""

    def test_x_forwarded_for_header(
        self,
        api_client,
        usuario_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """X-Forwarded-For header is correctly extracted (line 36)."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        AuditLog.objects.all().delete()

        # Request with X-Forwarded-For header
        response = api_client.patch(
            f"/api/solicitacoes/{sol.id}/approve/",
            HTTP_X_FORWARDED_FOR="192.168.1.100, 10.0.0.1",
        )

        assert response.status_code == 200
        audit = AuditLog.objects.filter(action="APPROVE").first()
        assert audit is not None
        assert audit.details["ip_address"] == "192.168.1.100"

    def test_x_real_ip_header(
        self,
        api_client,
        usuario_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """X-Real-IP header is correctly extracted (line 39)."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        AuditLog.objects.all().delete()

        # Request with X-Real-IP header (no X-Forwarded-For)
        response = api_client.patch(
            f"/api/solicitacoes/{sol.id}/approve/",
            HTTP_X_REAL_IP="10.0.0.50",
        )

        assert response.status_code == 200
        audit = AuditLog.objects.filter(action="APPROVE").first()
        assert audit is not None
        assert audit.details["ip_address"] == "10.0.0.50"


# ============================================================
# Tests for filters (lines 134, 137-142, 145-150, 153-154)
# ============================================================


@pytest.mark.django_db
class TestSolicitacaoFilters:
    """Tests for query parameter filters."""

    def test_sector_filter(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        tipo_evento,
    ):
        """Sector filter works correctly (line 134)."""
        projeto_acerta = Projeto.objects.create(
            nome="ACerta Teste",
            codigo="ACERTA",
            fluxo="SUPER",
            ativo=True,
        )
        projeto_vidas = Projeto.objects.create(
            nome="Vidas Teste",
            codigo="VIDAS",
            fluxo="SUPER",
            ativo=True,
        )

        sol_acerta = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_acerta,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )
        sol_vidas = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_vidas,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=2),
            fim=timezone.now() + timedelta(days=2, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Filter by sector=ACerta
        response = api_client.get("/api/solicitacoes/?sector=ACerta")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == sol_acerta.id

    def test_date_from_filter(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """date_from filter works correctly (lines 137-142)."""
        today = timezone.now().date()

        sol_past = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() - timedelta(days=10),
            fim=timezone.now() - timedelta(days=10) + timedelta(hours=2),
            status="pendente",
        )
        sol_future = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=10),
            fim=timezone.now() + timedelta(days=10, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Filter from today
        response = api_client.get(f"/api/solicitacoes/?date_from={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == sol_future.id

    def test_date_from_invalid_format_ignored(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Invalid date_from format is ignored (lines 141-142)."""
        Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Invalid date format should be ignored (returns all)
        response = api_client.get("/api/solicitacoes/?date_from=invalid-date")
        assert response.status_code == 200
        assert response.json()["count"] >= 1

    def test_date_to_filter(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """date_to filter works correctly (lines 145-150)."""
        today = timezone.now().date()

        sol_past = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() - timedelta(days=5),
            fim=timezone.now() - timedelta(days=5) + timedelta(hours=2),
            status="pendente",
        )
        sol_future = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=30),
            fim=timezone.now() + timedelta(days=30, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Filter up to today
        response = api_client.get(f"/api/solicitacoes/?date_to={today.isoformat()}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == sol_past.id

    def test_date_to_invalid_format_ignored(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Invalid date_to format is ignored (lines 149-150)."""
        Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Invalid date format should be ignored (returns all)
        response = api_client.get("/api/solicitacoes/?date_to=not-a-date")
        assert response.status_code == 200
        assert response.json()["count"] >= 1

    def test_q_search_filter(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """q search filter works correctly (lines 153-154)."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
            observacoes="Reunião especial de planejamento",
        )

        api_client.force_authenticate(user=usuario_coordenador)

        # Search by observacoes
        response = api_client.get("/api/solicitacoes/?q=planejamento")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        found_ids = [r["id"] for r in data["results"]]
        assert sol.id in found_ids


# ============================================================
# Tests for extra_participants edge cases (lines 220-221, 244-267)
# ============================================================


@pytest.mark.django_db
class TestExtraParticipantsEdgeCases:
    """Tests for extra_participants edge cases."""

    def test_formador_id_not_found_is_ignored(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Invalid formador_id is silently ignored (lines 220-221)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto_super.id,
                "tipo_evento": tipo_evento.id,
                "tipo": "PRESENCIAL",
                "inicio": timezone.now().isoformat(),
                "fim": (timezone.now() + timedelta(hours=2)).isoformat(),
                "extra_participants": {
                    "formador_ids": [999999],  # Non-existent ID
                    "formador_emails": [],
                    "coord_acompanha_ids": [],
                    "coord_acompanha_emails": [],
                },
            },
            format="json",
        )

        assert response.status_code == 201
        sol_id = response.json()["id"]

        # Only coordinator participation should exist
        participations = Participation.objects.filter(solicitacao_id=sol_id)
        assert participations.count() == 1
        assert participations.first().role == "COORDENADOR"

    def test_coord_acompanha_id_creates_participation(
        self,
        api_client,
        usuario_coordenador,
        usuario_formador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """coord_acompanha_ids creates COORD_ACOMPANHA participation (lines 244-253)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto_super.id,
                "tipo_evento": tipo_evento.id,
                "tipo": "PRESENCIAL",
                "inicio": timezone.now().isoformat(),
                "fim": (timezone.now() + timedelta(hours=2)).isoformat(),
                "extra_participants": {
                    "formador_ids": [],
                    "formador_emails": [],
                    "coord_acompanha_ids": [usuario_formador.id],
                    "coord_acompanha_emails": [],
                },
            },
            format="json",
        )

        assert response.status_code == 201
        sol_id = response.json()["id"]

        # Verify COORD_ACOMPANHA participation was created
        coord_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            usuario=usuario_formador,
            role="COORD_ACOMPANHA",
        )
        assert coord_part.exists()

    def test_coord_acompanha_id_not_found_is_ignored(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Invalid coord_acompanha_id is silently ignored (lines 252-253)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto_super.id,
                "tipo_evento": tipo_evento.id,
                "tipo": "PRESENCIAL",
                "inicio": timezone.now().isoformat(),
                "fim": (timezone.now() + timedelta(hours=2)).isoformat(),
                "extra_participants": {
                    "formador_ids": [],
                    "formador_emails": [],
                    "coord_acompanha_ids": [888888],  # Non-existent ID
                    "coord_acompanha_emails": [],
                },
            },
            format="json",
        )

        assert response.status_code == 201
        sol_id = response.json()["id"]

        # Only coordinator participation should exist
        participations = Participation.objects.filter(solicitacao_id=sol_id)
        assert participations.count() == 1

    def test_coord_acompanha_email_existing_user(
        self,
        api_client,
        usuario_coordenador,
        usuario_formador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """coord_acompanha_emails resolves to existing user (lines 257-264)."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto_super.id,
                "tipo_evento": tipo_evento.id,
                "tipo": "PRESENCIAL",
                "inicio": timezone.now().isoformat(),
                "fim": (timezone.now() + timedelta(hours=2)).isoformat(),
                "extra_participants": {
                    "formador_ids": [],
                    "formador_emails": [],
                    "coord_acompanha_ids": [],
                    "coord_acompanha_emails": [usuario_formador.email.upper()],
                },
            },
            format="json",
        )

        assert response.status_code == 201
        sol_id = response.json()["id"]

        # Verify resolved to existing user
        coord_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            usuario=usuario_formador,
            role="COORD_ACOMPANHA",
        )
        assert coord_part.exists()

    def test_coord_acompanha_email_guest(
        self,
        api_client,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """coord_acompanha_emails creates guest participation (lines 265-271)."""
        api_client.force_authenticate(user=usuario_coordenador)
        guest_email = f"guest_coord_{uuid4().hex[:8]}@external.com"

        response = api_client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto_super.id,
                "tipo_evento": tipo_evento.id,
                "tipo": "PRESENCIAL",
                "inicio": timezone.now().isoformat(),
                "fim": (timezone.now() + timedelta(hours=2)).isoformat(),
                "extra_participants": {
                    "formador_ids": [],
                    "formador_emails": [],
                    "coord_acompanha_ids": [],
                    "coord_acompanha_emails": [guest_email],
                },
            },
            format="json",
        )

        assert response.status_code == 201
        sol_id = response.json()["id"]

        # Verify guest participation with role COORD_ACOMPANHA
        guest_part = Participation.objects.filter(
            solicitacao_id=sol_id,
            guest_email=guest_email.lower(),
            role="COORD_ACOMPANHA",
        )
        assert guest_part.exists()


# ============================================================
# Tests for already approved/rejected edge cases (lines 284, 350)
# ============================================================


@pytest.mark.django_db
class TestApproveRejectEdgeCases:
    """Tests for approve/reject edge cases."""

    def test_approve_already_approved_returns_400(
        self,
        api_client,
        usuario_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Approving already approved solicitation returns 400 (line 284)."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="aprovado",  # Already approved
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        response = api_client.patch(f"/api/solicitacoes/{sol.id}/approve/")

        assert response.status_code == 400
        assert "já está aprovada" in response.json()["detail"]

    def test_reject_already_rejected_returns_400(
        self,
        api_client,
        usuario_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Rejecting already rejected solicitation returns 400 (line 350)."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="reprovado",  # Already rejected
        )

        api_client.force_authenticate(user=usuario_superintendencia)
        response = api_client.patch(
            f"/api/solicitacoes/{sol.id}/reject/",
            {"justificativa": "Teste"},
        )

        assert response.status_code == 400
        assert "já está reprovada" in response.json()["detail"]


# ============================================================
# Tests for batch_approve (lines 777-843)
# ============================================================


@pytest.mark.django_db
class TestBatchApprove:
    """Tests for batch_approve action."""

    def test_batch_approve_success(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch approve multiple solicitations successfully."""
        sol1 = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )
        sol2 = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=2),
            fim=timezone.now() + timedelta(days=2, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)
        AuditLog.objects.all().delete()

        response = api_client.post(
            "/api/solicitacoes/batch-approve/",
            {"ids": [sol1.id, sol2.id]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] == 2
        assert data["errors"] == []

        # Verify both are approved
        sol1.refresh_from_db()
        sol2.refresh_from_db()
        assert sol1.status == "aprovado"
        assert sol2.status == "aprovado"

        # Verify AuditLogs created with batch=True
        audits = AuditLog.objects.filter(action="APPROVE")
        assert audits.count() == 2
        for audit in audits:
            assert audit.details.get("batch") is True

    def test_batch_approve_empty_ids_returns_400(
        self,
        api_client,
        usuario_gerente_superintendencia,
    ):
        """Batch approve with empty ids returns 400."""
        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-approve/",
            {"ids": []},
            format="json",
        )

        assert response.status_code == 400
        assert "obrigatório" in response.json()["detail"]

    def test_batch_approve_exceeds_limit_returns_400(
        self,
        api_client,
        usuario_gerente_superintendencia,
    ):
        """Batch approve with more than 100 ids returns 400."""
        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-approve/",
            {"ids": list(range(1, 102))},  # 101 ids
            format="json",
        )

        assert response.status_code == 400
        assert "100" in response.json()["detail"]

    def test_batch_approve_with_already_approved(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch approve handles already approved solicitations."""
        sol_pendente = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )
        sol_aprovado = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=2),
            fim=timezone.now() + timedelta(days=2, hours=2),
            status="aprovado",  # Already approved
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-approve/",
            {"ids": [sol_pendente.id, sol_aprovado.id]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["id"] == sol_aprovado.id
        assert "aprovado" in data["errors"][0]["detail"]

    def test_batch_approve_with_nonexistent_id(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch approve handles non-existent ids."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-approve/",
            {"ids": [sol.id, 999999]},  # 999999 doesn't exist
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["approved"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["id"] == 999999
        assert "não encontrada" in data["errors"][0]["detail"]


# ============================================================
# Tests for batch_reject (lines 870-936)
# ============================================================


@pytest.mark.django_db
class TestBatchReject:
    """Tests for batch_reject action."""

    def test_batch_reject_success(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch reject multiple solicitations successfully."""
        sol1 = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )
        sol2 = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=2),
            fim=timezone.now() + timedelta(days=2, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)
        AuditLog.objects.all().delete()

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": [sol1.id, sol2.id]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rejected"] == 2
        assert data["errors"] == []

        # Verify both are rejected
        sol1.refresh_from_db()
        sol2.refresh_from_db()
        assert sol1.status == "reprovado"
        assert sol2.status == "reprovado"

        # Verify AuditLogs created with batch=True
        audits = AuditLog.objects.filter(action="REJECT")
        assert audits.count() == 2
        for audit in audits:
            assert audit.details.get("batch") is True

    def test_batch_reject_empty_ids_returns_400(
        self,
        api_client,
        usuario_gerente_superintendencia,
    ):
        """Batch reject with empty ids returns 400."""
        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": []},
            format="json",
        )

        assert response.status_code == 400
        assert "obrigatório" in response.json()["detail"]

    def test_batch_reject_exceeds_limit_returns_400(
        self,
        api_client,
        usuario_gerente_superintendencia,
    ):
        """Batch reject with more than 100 ids returns 400."""
        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": list(range(1, 102))},  # 101 ids
            format="json",
        )

        assert response.status_code == 400
        assert "100" in response.json()["detail"]

    def test_batch_reject_with_already_rejected(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch reject handles already rejected solicitations."""
        sol_pendente = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )
        sol_reprovado = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=2),
            fim=timezone.now() + timedelta(days=2, hours=2),
            status="reprovado",  # Already rejected
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": [sol_pendente.id, sol_reprovado.id]},
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["id"] == sol_reprovado.id
        assert "reprovado" in data["errors"][0]["detail"]

    def test_batch_reject_with_nonexistent_id(
        self,
        api_client,
        usuario_gerente_superintendencia,
        usuario_coordenador,
        municipio,
        projeto_super,
        tipo_evento,
    ):
        """Batch reject handles non-existent ids."""
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=municipio,
            projeto=projeto_super,
            tipo_evento=tipo_evento,
            inicio=timezone.now() + timedelta(days=1),
            fim=timezone.now() + timedelta(days=1, hours=2),
            status="pendente",
        )

        api_client.force_authenticate(user=usuario_gerente_superintendencia)

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": [sol.id, 888888]},  # 888888 doesn't exist
            format="json",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["id"] == 888888
        assert "não encontrada" in data["errors"][0]["detail"]

    def test_batch_reject_permission_denied_for_regular_user(
        self,
        api_client,
        usuario_coordenador,
    ):
        """Batch reject requires Gerente + Superintendência permission."""
        api_client.force_authenticate(user=usuario_coordenador)

        response = api_client.post(
            "/api/solicitacoes/batch-reject/",
            {"ids": [1, 2, 3]},
            format="json",
        )

        assert response.status_code == 403
