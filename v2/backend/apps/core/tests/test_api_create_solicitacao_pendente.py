"""
Tests: API Create Solicitacao

PA-01: Solicitações sempre começam com status pendente.
RD-06: Datas devem ser timezone-aware (UTC).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import Solicitacao, Usuario, TipoEvento, Municipio


@pytest.fixture
def user_test(db):
    """Cria um usuário de teste com grupo Coordenador (PA-06)"""
    from django.contrib.auth.models import Group

    user = Usuario.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        cpf="12345678901",
    )

    # PA-06: Adicionar grupo Coordenador para poder criar solicitações
    coord_group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(coord_group)

    return user


@pytest.fixture
def tipo_evento_test(db):
    """Cria um tipo de evento de teste"""
    return TipoEvento.objects.create(nome="Palestra", descricao="Palestra online")


@pytest.fixture
def municipio_test(db):
    """Cria um município de teste"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE")


@pytest.mark.django_db
class TestAPICreateSolicitacaoPendente:
    """
    Testes de criação de Solicitacao via API.
    """

    def test_create_solicitacao_is_pendente_by_default(
        self, user_test, tipo_evento_test, municipio_test
    ):
        """
        Test: POST /api/solicitacoes/ com payload válido cria solicitação pendente (PA-01).
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=24)  # Amanhã
        fim = inicio + timedelta(hours=1)

        payload = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "observacoes": "Teste de criação via API",
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Esperado 201, obtido {response.status_code}: {response.data}"
        )

        # Verificar status pendente (PA-01)
        assert response.data["status"] == "pendente", (
            "Status deve ser 'pendente' ao criar solicitação (PA-01)"
        )

        # Verificar datas timezone-aware (RD-06)
        solicitacao = Solicitacao.objects.get(pk=response.data["id"])
        assert solicitacao.inicio.tzinfo is not None, "inicio deve ser timezone-aware (RD-06)"
        assert solicitacao.fim.tzinfo is not None, "fim deve ser timezone-aware (RD-06)"

        # Verificar valores corretos
        assert solicitacao.usuario == user_test
        assert solicitacao.tipo_evento == tipo_evento_test
        assert solicitacao.municipio == municipio_test
        assert solicitacao.observacoes == "Teste de criação via API"

    def test_create_solicitacao_cannot_override_status(
        self, user_test, tipo_evento_test, municipio_test
    ):
        """
        Test: Tentar criar solicitação com status aprovado deve ser ignorado (PA-01).
        O serializer marca status como read_only.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=48)
        fim = inicio + timedelta(hours=2)

        payload = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "status": "aprovado",  # Tentativa de burlar PA-01
            "observacoes": "Tentativa de criar aprovada",
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Esperado 201, obtido {response.status_code}"
        )

        # Status deve ser pendente, ignorando payload
        assert response.data["status"] == "pendente", (
            "Status deve ser 'pendente' mesmo que payload tente especificar 'aprovado' (PA-01)"
        )

        solicitacao = Solicitacao.objects.get(pk=response.data["id"])
        assert solicitacao.status == "pendente", "Status no DB deve ser 'pendente' (PA-01)"

    def test_create_solicitacao_requires_valid_interval(
        self, user_test, tipo_evento_test, municipio_test
    ):
        """
        Test: Criar solicitação com fim <= inicio deve falhar.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()

        # Caso 1: fim == inicio (inválido)
        payload = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": now.isoformat(),
            "fim": now.isoformat(),  # fim == inicio (inválido)
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == http_status.HTTP_400_BAD_REQUEST, (
            "Criar com fim == inicio deve retornar 400"
        )
        assert "fim" in response.data, "Deve retornar erro no campo 'fim'"

        # Caso 2: fim < inicio (inválido)
        payload2 = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": now.isoformat(),
            "fim": (now - timedelta(hours=1)).isoformat(),  # fim < inicio (inválido)
        }

        response2 = client.post("/api/solicitacoes/", payload2, format="json")

        assert response2.status_code == http_status.HTTP_400_BAD_REQUEST, (
            "Criar com fim < inicio deve retornar 400"
        )

    def test_create_solicitacao_municipio_optional(self, user_test, tipo_evento_test):
        """
        Test: Município é opcional ao criar solicitação.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=72)
        fim = inicio + timedelta(hours=3)

        payload = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            # municipio NÃO informado (opcional)
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "observacoes": "Evento online sem município específico",
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Criar sem município deve funcionar (esperado 201, obtido {response.status_code})"
        )

        solicitacao = Solicitacao.objects.get(pk=response.data["id"])
        assert solicitacao.municipio is None, "Município deve ser None quando não informado"
        assert solicitacao.status == "pendente", "Status deve ser pendente (PA-01)"

    def test_create_solicitacao_external_event_id_is_readonly(
        self, user_test, tipo_evento_test, municipio_test
    ):
        """
        Test: external_event_id é read-only, não pode ser definido na criação.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=96)
        fim = inicio + timedelta(hours=1)

        payload = {
            "usuario": user_test.pk,
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "external_event_id": "fake-gcal-id-123",  # Tentativa de definir (deve ser ignorado)
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code == http_status.HTTP_201_CREATED, (
            f"Criar com external_event_id no payload deve funcionar (esperado 201, obtido {response.status_code})"
        )

        solicitacao = Solicitacao.objects.get(pk=response.data["id"])
        assert solicitacao.external_event_id is None, (
            "external_event_id deve ser None (campo read-only, ignorado na criação)"
        )

    def test_unauthenticated_cannot_create_solicitacao(self, tipo_evento_test, municipio_test):
        """
        Test: Usuário não autenticado não pode criar solicitação.
        """
        client = APIClient()
        # Não autenticado

        now = timezone.now()
        payload = {
            "usuario": 1,  # ID fictício
            "tipo_evento": tipo_evento_test.pk,
            "municipio": municipio_test.pk,
            "inicio": now.isoformat(),
            "fim": (now + timedelta(hours=1)).isoformat(),
        }

        response = client.post("/api/solicitacoes/", payload, format="json")

        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        ], "Usuário não autenticado não deve poder criar solicitação"
