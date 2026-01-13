"""
Tests for PR 8/N — Nova Solicitação (Coordenador) + Options API + Pré-checagem Consultiva

Testa:
- Novos campos do modelo Solicitacao
- Options API endpoints (/api/options/*)
- Endpoint de pré-checagem em lote (/api/availability/check-many/)
- RBAC para criação de solicitações (apenas Coordenador e DAT)
- Serializers com novos campos
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


class TestSolicitacaoNewFields:
    """Testa novos campos adicionados ao modelo Solicitacao"""

    def test_solicitacao_has_new_fields(self):
        """PR 8/N: Solicitacao deve ter todos os novos campos"""
        # Arrange
        user = Usuario.objects.create_user(
            username="coord1",
            password="pass123",
            cpf="12345678901",
            first_name="João",
            last_name="Coordenador",
        )
        municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        projeto = Projeto.objects.create(nome="Projeto Teste")
        tipo_evento = TipoEvento.objects.create(nome="Formação")

        inicio = timezone.now()
        fim = inicio + timezone.timedelta(hours=2)

        # Act
        solicitacao = Solicitacao.objects.create(
            usuario=user,
            municipio=municipio,
            projeto=projeto,
            tipo="evento",
            tipo_evento=tipo_evento,
            encontro="Encontro 1",
            segmento="Fundamental I",
            coordenador_acompanha=True,
            coordenador=user,
            inicio=inicio,
            fim=fim,
        )
        solicitacao.formadores.add(user)

        # Assert
        assert solicitacao.projeto == projeto
        assert solicitacao.tipo == "evento"
        assert solicitacao.encontro == "Encontro 1"
        assert solicitacao.segmento == "Fundamental I"
        assert solicitacao.coordenador_acompanha is True
        assert solicitacao.coordenador == user
        assert user in solicitacao.formadores.all()


class TestOptionsAPI:
    """Testa endpoints da Options API"""

    def test_municipios_options_returns_active_only(self):
        """GET /api/options/municipios/ deve retornar apenas municípios ativos"""
        # Arrange
        client = APIClient()
        user = Usuario.objects.create_user(
            username="user1", password="pass", cpf="11111111111"
        )
        client.force_authenticate(user=user)

        Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
        Municipio.objects.create(nome="Inativo City", uf="XX", ativo=False)

        # Act
        response = client.get("/api/options/municipios/")

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["nome"] == "Fortaleza"

    def test_options_require_authentication(self):
        """Options API deve exigir autenticação"""
        client = APIClient()

        # Act & Assert
        assert (
            client.get("/api/options/municipios/").status_code
            == status.HTTP_403_FORBIDDEN
        )


class TestAvailabilityCheckMany:
    """Testa endpoint de checagem de disponibilidade em lote"""

    def test_check_many_all_available(self):
        """POST /api/availability/check-many/ deve retornar ok=true quando todos disponíveis"""
        # Arrange
        client = APIClient()
        user1 = Usuario.objects.create_user(
            username="user1", password="pass", cpf="11111111111"
        )
        user2 = Usuario.objects.create_user(
            username="user2", password="pass", cpf="22222222222"
        )
        coord = Usuario.objects.create_user(
            username="coord", password="pass", cpf="33333333333"
        )

        # P2.2: check-many endpoint requires IsControleOrDAT permission
        controle_group, _ = Group.objects.get_or_create(name="Controle")
        coord.groups.add(controle_group)

        client.force_authenticate(user=coord)

        inicio = timezone.now() + timezone.timedelta(days=1)
        fim = inicio + timezone.timedelta(hours=2)

        # Act
        response = client.post(
            "/api/availability/check-many/",
            {
                "usuarios_ids": [user1.id, user2.id],
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
            },
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.data["ok"] is True
        assert len(response.data["results"]) == 2

    def test_check_many_requires_authentication(self):
        """POST /api/availability/check-many/ deve exigir autenticação"""
        client = APIClient()

        # Act
        response = client.post("/api/availability/check-many/", {})

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestSolicitacaoRBAC:
    """Testa RBAC para criação de solicitações"""

    def test_coordenador_can_create_solicitacao(self):
        """PR 8/N: Coordenador pode criar solicitação"""
        # Arrange
        client = APIClient()
        coord = Usuario.objects.create_user(
            username="coord1", password="pass", cpf="11111111111"
        )
        group_coord, _ = Group.objects.get_or_create(name="Coordenador")
        coord.groups.add(group_coord)

        tipo_evento = TipoEvento.objects.create(nome="Formação")
        municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
        projeto = Projeto.objects.create(nome="Projeto X", fluxo="SUPER")  # SUPER=pendente

        client.force_authenticate(user=coord)

        inicio = timezone.now() + timezone.timedelta(days=1)
        fim = inicio + timezone.timedelta(hours=2)

        # Act
        response = client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto.id,
                "tipo": "evento",
                "tipo_evento": tipo_evento.id,
                "encontro": "Encontro 1",
                "segmento": "Fundamental I",
                "coordenador_acompanha": True,
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
            },
            format="json",
        )

        # Assert
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Response status: {response.status_code}")
            print(f"Response data: {response.data}")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "pendente"
        assert response.data["tipo"] == "evento"
        assert response.data["encontro"] == "Encontro 1"

    def test_formador_cannot_create_solicitacao(self):
        """PR 8/N: Formador NÃO pode criar solicitação"""
        # Arrange
        client = APIClient()
        formador = Usuario.objects.create_user(
            username="formador1", password="pass", cpf="11111111111"
        )
        group_formador, _ = Group.objects.get_or_create(name="Formador")
        formador.groups.add(group_formador)

        tipo_evento = TipoEvento.objects.create(nome="Formação")
        client.force_authenticate(user=formador)

        inicio = timezone.now() + timezone.timedelta(days=1)
        fim = inicio + timezone.timedelta(hours=2)

        # Act
        response = client.post(
            "/api/solicitacoes/",
            {
                "tipo_evento": tipo_evento.id,
                "tipo": "evento",
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
            },
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Coordenadores ou DAT" in str(response.data)  # Match actual message

    def test_superuser_can_create_solicitacao(self):
        """PR 8/N: Superuser pode criar solicitação"""
        # Arrange
        client = APIClient()
        superuser = Usuario.objects.create_superuser(
            username="admin", password="pass", cpf="11111111111"
        )
        tipo_evento = TipoEvento.objects.create(nome="Formação")
        client.force_authenticate(user=superuser)

        inicio = timezone.now() + timezone.timedelta(days=1)
        fim = inicio + timezone.timedelta(hours=2)

        # Act
        response = client.post(
            "/api/solicitacoes/",
            {
                "tipo_evento": tipo_evento.id,
                "tipo": "evento",
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
            },
            format="json",
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
