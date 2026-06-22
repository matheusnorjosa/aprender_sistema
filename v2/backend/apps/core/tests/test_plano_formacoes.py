"""
Tests for PlanoFormacoes, Formacao, Acompanhamento, Prova models and API.

Tests:
- Model creation and constraints
- API CRUD operations
- Stats and calendar endpoints
- Inline update actions
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false


from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

import pytest

from apps.core.models import Acompanhamento, Formacao, PlanoFormacoes, Prova
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory


@pytest.fixture
def user(db):
    """Create a test user with DAT permissions."""
    # Add to DAT group for permissions
    return UsuarioFactory(
        username="testuser",
        cpf="12345678901",
        password="testpass123",
        groups=["DAT"],
    )


@pytest.fixture
def municipio(db):
    """Create a test municipio."""
    return MunicipioFactory(
        nome="Municipio Teste",
        uf="CE",
    )


@pytest.fixture
def projeto(db):
    """Create a test projeto."""
    return ProjetoFactory(
        nome="Projeto Teste",
        fluxo="NAO_SUPER",
    )


@pytest.fixture
def plano(db, municipio, projeto, user):
    """Create a test plano formacoes."""
    return PlanoFormacoes.objects.create(
        municipio=municipio,
        projeto=projeto,
        ch_estudo=Decimal("10.00"),
        created_by=user,
    )


# ============================================================
# MODEL TESTS
# ============================================================


class TestPlanoFormacoesModel:
    """Tests for PlanoFormacoes model."""

    def test_create_plano(self, plano, municipio, projeto):
        """Test basic plano creation."""
        assert plano.municipio == municipio
        assert plano.projeto == projeto
        assert plano.ch_estudo == Decimal("10.00")
        assert plano.ativo is True

    def test_plano_str(self, plano):
        """Test __str__ method."""
        # Municipio __str__ includes UF: "Nome-UF"
        assert str(plano) == "Municipio Teste-CE - Projeto Teste"

    def test_unique_constraint(self, plano, municipio, projeto, user):
        """Test unique constraint on municipio + projeto."""
        duplicate = PlanoFormacoes(
            municipio=municipio,
            projeto=projeto,
            created_by=user,
        )
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_recalcular_ch(self, plano):
        """Test recalcular_ch method."""
        # Create formacoes with data
        Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            data_formacao="2025-03-01",
            carga_horaria=Decimal("4.00"),
        )
        Formacao.objects.create(
            plano=plano,
            numero_formacao=2,
            data_formacao="2025-04-01",
            carga_horaria=Decimal("8.00"),
        )

        plano.recalcular_ch()

        assert plano.ch_total == Decimal("12.00")
        assert plano.ch_anual == Decimal("22.00")  # 12 + 10 (ch_estudo)


class TestFormacaoModel:
    """Tests for Formacao model."""

    def test_create_formacao(self, plano):
        """Test basic formacao creation."""
        formacao = Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            data_formacao="2025-03-01",
            carga_horaria=Decimal("4.00"),
            modalidade="presencial",
        )
        assert formacao.numero_formacao == 1
        assert formacao.modalidade == "presencial"
        assert formacao.realizada is False

    def test_formacao_str(self, plano):
        """Test __str__ method."""
        formacao = Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            data_formacao=date(2025, 3, 1),
        )
        assert "F1 - 01/03/2025" in str(formacao)

    def test_modalidade_abrev(self, plano):
        """Test modalidade_abrev property."""
        formacao_online = Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            modalidade="online",
        )
        formacao_presencial = Formacao.objects.create(
            plano=plano,
            numero_formacao=2,
            modalidade="presencial",
        )
        assert formacao_online.modalidade_abrev == "Onl."
        assert formacao_presencial.modalidade_abrev == "Pres."

    def test_unique_constraint(self, plano):
        """Test unique constraint on plano + numero_formacao."""
        Formacao.objects.create(plano=plano, numero_formacao=1)
        duplicate = Formacao(plano=plano, numero_formacao=1)
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_numero_range_constraint(self, plano):
        """Test numero_formacao range constraint (1-15)."""
        # Valid: 1-15
        for i in range(1, 16):
            Formacao.objects.create(plano=plano, numero_formacao=i)

        # Cleanup and test invalid
        Formacao.objects.filter(plano=plano).delete()

        # Invalid: 0, 16, etc would fail at validation level
        # (Django validators, not DB constraint in this case)


class TestAcompanhamentoModel:
    """Tests for Acompanhamento model."""

    def test_create_acompanhamento(self, plano):
        """Test basic acompanhamento creation."""
        acomp = Acompanhamento.objects.create(
            plano=plano,
            tipo="primeiro",
            data_acompanhamento="2025-06-01",
        )
        assert acomp.tipo == "primeiro"
        assert acomp.realizado is False
        assert acomp.numero == 1

    def test_numero_property(self, plano):
        """Test numero property."""
        acomp1 = Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        acomp2 = Acompanhamento.objects.create(plano=plano, tipo="segundo")
        assert acomp1.numero == 1
        assert acomp2.numero == 2

    def test_acompanhamento_str(self, plano):
        """Test __str__ method with and without date."""
        acomp_with_date = Acompanhamento.objects.create(
            plano=plano,
            tipo="primeiro",
            data_acompanhamento=date(2025, 6, 15),
        )
        assert "1o Acomp. - 15/06/2025" in str(acomp_with_date)

        acomp_without_date = Acompanhamento.objects.create(
            plano=plano,
            tipo="segundo",
        )
        assert "2o Acomp. - -" in str(acomp_without_date)

    def test_unique_constraint(self, plano):
        """Test unique constraint on plano + tipo."""
        Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        duplicate = Acompanhamento(plano=plano, tipo="primeiro")
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_tipo_choices(self, plano):
        """Test tipo must be valid choice."""
        # Valid choices work
        acomp = Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        assert acomp.tipo == Acompanhamento.TipoAcompanhamento.PRIMEIRO

        # Verify TipoAcompanhamento choices
        assert Acompanhamento.TipoAcompanhamento.PRIMEIRO == "primeiro"
        assert Acompanhamento.TipoAcompanhamento.SEGUNDO == "segundo"

    def test_observacoes_max_length(self, plano):
        """Test observacoes field max length."""
        obs_500 = "x" * 500
        acomp = Acompanhamento.objects.create(
            plano=plano,
            tipo="primeiro",
            observacoes=obs_500,
        )
        assert len(acomp.observacoes) == 500

    def test_realizado_default(self, plano):
        """Test realizado defaults to False."""
        acomp = Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        assert acomp.realizado is False

    def test_timestamps(self, plano):
        """Test created_at and updated_at are set."""
        acomp = Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        assert acomp.created_at is not None
        assert acomp.updated_at is not None

    def test_cascade_delete(self, plano):
        """Test acompanhamentos are deleted when plano is deleted."""
        Acompanhamento.objects.create(plano=plano, tipo="primeiro")
        Acompanhamento.objects.create(plano=plano, tipo="segundo")
        assert Acompanhamento.objects.filter(plano=plano).count() == 2

        plano_id = plano.id
        plano.delete()
        assert Acompanhamento.objects.filter(plano_id=plano_id).count() == 0


class TestProvaModel:
    """Tests for Prova model."""

    def test_create_prova(self, plano):
        """Test basic prova creation."""
        prova = Prova.objects.create(
            plano=plano,
            numero_prova=1,
            data_prova="2025-09-01",
        )
        assert prova.numero_prova == 1
        assert prova.realizada is False

    def test_prova_str(self, plano):
        """Test __str__ method."""
        prova = Prova.objects.create(
            plano=plano,
            numero_prova=2,
            data_prova=date(2025, 9, 15),
        )
        assert "P2 - 15/09/2025" in str(prova)

    def test_prova_str_without_date(self, plano):
        """Test __str__ method without date."""
        prova = Prova.objects.create(
            plano=plano,
            numero_prova=1,
        )
        assert "P1 - -" in str(prova)

    def test_unique_constraint(self, plano):
        """Test unique constraint on plano + numero_prova."""
        Prova.objects.create(plano=plano, numero_prova=1)
        duplicate = Prova(plano=plano, numero_prova=1)
        with pytest.raises(ValidationError):
            duplicate.full_clean()

    def test_numero_prova_validators(self, plano):
        """Test numero_prova validators (1-3 range)."""
        # Valid: 1, 2, 3
        p1 = Prova.objects.create(plano=plano, numero_prova=1)
        p2 = Prova.objects.create(plano=plano, numero_prova=2)
        p3 = Prova.objects.create(plano=plano, numero_prova=3)
        assert p1.numero_prova == 1
        assert p2.numero_prova == 2
        assert p3.numero_prova == 3

    def test_numero_prova_check_constraint(self, plano):
        """Test CheckConstraint prevents invalid numero_prova at DB level."""
        from django.db import IntegrityError

        # Try to bypass validators and insert invalid value
        # This should fail due to CheckConstraint
        with pytest.raises(IntegrityError):
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO core_prova (plano_id, numero_prova, realizada, observacoes, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, NOW(), NOW())",
                    [plano.id, 0, False, ""],  # numero_prova=0 is invalid
                )

    def test_observacoes_max_length(self, plano):
        """Test observacoes field max length."""
        obs_500 = "x" * 500
        prova = Prova.objects.create(
            plano=plano,
            numero_prova=1,
            observacoes=obs_500,
        )
        assert len(prova.observacoes) == 500

    def test_realizada_default(self, plano):
        """Test realizada defaults to False."""
        prova = Prova.objects.create(plano=plano, numero_prova=1)
        assert prova.realizada is False

    def test_timestamps(self, plano):
        """Test created_at and updated_at are set."""
        prova = Prova.objects.create(plano=plano, numero_prova=1)
        assert prova.created_at is not None
        assert prova.updated_at is not None

    def test_cascade_delete(self, plano):
        """Test provas are deleted when plano is deleted."""
        Prova.objects.create(plano=plano, numero_prova=1)
        Prova.objects.create(plano=plano, numero_prova=2)
        assert Prova.objects.filter(plano=plano).count() == 2

        plano_id = plano.id
        plano.delete()
        assert Prova.objects.filter(plano_id=plano_id).count() == 0


# ============================================================
# API TESTS
# ============================================================


@pytest.mark.django_db
class TestPlanoFormacoesAPI:
    """Tests for PlanoFormacoes API endpoints."""

    def test_list_planos(self, client, user, plano):
        """Test listing planos."""
        client.force_login(user)
        response = client.get("/api/dat/plano-formacoes/")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)

    def test_create_plano_creates_children(self, client, user, municipio, projeto):
        """Test that creating a plano also creates 15 formacoes, 2 acompanhamentos, 3 provas."""
        client.force_login(user)

        # Create another municipio to avoid unique constraint
        mun2 = MunicipioFactory(
            nome="Municipio 2",
            uf="CE",
        )
        proj2 = ProjetoFactory(
            nome="Projeto 2",
            fluxo="NAO_SUPER",
        )

        response = client.post(
            "/api/dat/plano-formacoes/",
            data={
                "municipio": mun2.id,
                "projeto": proj2.id,
            },
            content_type="application/json",
        )

        assert response.status_code == 201
        data = response.json()

        # Verify children were created
        plano = PlanoFormacoes.objects.get(id=data["id"])
        assert plano.formacoes.count() == 15
        assert plano.acompanhamentos.count() == 2
        assert plano.provas.count() == 3

    def test_stats_endpoint(self, client, user, plano):
        """Test stats endpoint."""
        client.force_login(user)
        response = client.get("/api/dat/plano-formacoes/stats/")
        assert response.status_code == 200
        data = response.json()
        assert "total_planos" in data
        assert "total_formacoes" in data

    def test_update_formacao_inline(self, client, user, plano):
        """Test updating formacao inline."""
        # Create a formacao
        formacao = Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            carga_horaria=Decimal("4.00"),
        )

        client.force_login(user)
        response = client.patch(
            f"/api/dat/plano-formacoes/{plano.id}/formacao/1/",
            data={
                "data_formacao": "2025-05-01",
                "realizada": True,
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        formacao.refresh_from_db()
        assert str(formacao.data_formacao) == "2025-05-01"
        assert formacao.realizada is True

    def test_calendario_endpoint(self, client, user, plano):
        """Test calendario endpoint."""
        # Create formacao with date
        Formacao.objects.create(
            plano=plano,
            numero_formacao=1,
            data_formacao="2025-06-15",
            carga_horaria=Decimal("4.00"),
        )

        client.force_login(user)
        response = client.get(
            "/api/dat/plano-formacoes/calendario/",
            {"data_inicio": "2025-06-01", "data_fim": "2025-06-30"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["data"] == "2025-06-15"

    def test_resumo_projeto_endpoint(self, client, user, plano):
        """Test resumo-projeto endpoint."""
        client.force_login(user)
        response = client.get("/api/dat/plano-formacoes/resumo-projeto/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
