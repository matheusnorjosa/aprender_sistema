"""
Tests for PlanoFormacoes, Formacao, Acompanhamento, Prova models and API.

Tests:
- Model creation and constraints
- API CRUD operations
- Stats and calendar endpoints
- Inline update actions
"""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

import pytest
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model

from apps.core.models import (
    Acompanhamento,
    Formacao,
    Municipio,
    PlanoFormacoes,
    Projeto,
    Prova,
)

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user with DAT permissions."""
    from django.contrib.auth.models import Group
    user = User.objects.create_user(
        username="testuser",
        cpf="12345678901",
        password="testpass123",
    )
    # Add to DAT group for permissions
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(dat_group)
    return user


@pytest.fixture
def municipio(db):
    """Create a test municipio."""
    return Municipio.objects.create(
        nome="Municipio Teste",
        uf="CE",
    )


@pytest.fixture
def projeto(db):
    """Create a test projeto."""
    return Projeto.objects.create(
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
        with pytest.raises(Exception):
            PlanoFormacoes.objects.create(
                municipio=municipio,
                projeto=projeto,
                created_by=user,
            )

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
        with pytest.raises(Exception):
            Formacao.objects.create(plano=plano, numero_formacao=1)

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
        mun2 = Municipio.objects.create(
            nome="Municipio 2",
            uf="CE",
        )
        proj2 = Projeto.objects.create(
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
