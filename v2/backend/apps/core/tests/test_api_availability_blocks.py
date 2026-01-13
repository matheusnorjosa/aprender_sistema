"""
Tests: API Availability Blocks and Current User

Tests for:
- /api/me/ endpoint (returns current user info)
- /api/availability-blocks/ endpoint (create with auto-filled usuario)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
from datetime import timedelta

from django.utils import timezone

import pytest
from apps.core.models import AvailabilityBlock, Usuario
from rest_framework import status as http_status
from rest_framework.test import APIClient


@pytest.fixture
def user_test(db):
    """Cria um usuário de teste"""
    return Usuario.objects.create_user(
        username="testuser",
        email="testuser@example.com",
        password="testpass123",
        cpf="12345678901",
    )


@pytest.fixture
def another_user(db):
    """Cria um segundo usuário de teste"""
    return Usuario.objects.create_user(
        username="anotheruser",
        email="another@example.com",
        password="testpass456",
        cpf="98765432100",
    )


@pytest.mark.django_db
class TestAPIMe:
    """
    Testes do endpoint /api/me/ (informações do usuário autenticado).
    """

    def test_api_me_returns_current_user(self, user_test):
        """
        Test: GET /api/me/ retorna informações do usuário autenticado.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        response = client.get("/api/me/")

        assert (
            response.status_code == http_status.HTTP_200_OK
        ), f"Esperado 200, obtido {response.status_code}: {response.data}"

        # Verificar estrutura da resposta
        assert "id" in response.data, "Resposta deve conter 'id'"
        assert "username" in response.data, "Resposta deve conter 'username'"
        assert "email" in response.data, "Resposta deve conter 'email'"
        assert "first_name" in response.data, "Resposta deve conter 'first_name'"
        assert "last_name" in response.data, "Resposta deve conter 'last_name'"

        # Verificar valores corretos
        assert (
            response.data["id"] == user_test.id
        ), "ID deve corresponder ao usuário autenticado"
        assert (
            response.data["username"] == user_test.username
        ), "Username deve corresponder"
        assert response.data["email"] == user_test.email, "Email deve corresponder"

    def test_api_me_requires_authentication(self):
        """
        Test: GET /api/me/ requer autenticação.
        """
        client = APIClient()
        # Não autenticado

        response = client.get("/api/me/")

        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        ], "Usuário não autenticado não deve acessar /api/me/"


@pytest.mark.django_db
class TestAPIAvailabilityBlocks:
    """
    Testes do endpoint /api/availability-blocks/ (criação de bloqueios).
    """

    def test_create_block_uses_request_user_when_missing_usuario(self, user_test):
        """
        Test: POST /api/availability-blocks/ preenche usuario com request.user automaticamente.

        Quando o payload NÃO inclui 'usuario' (ou é ignorado porque é read_only),
        o ViewSet.perform_create() deve preenchê-lo com request.user.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=24)  # Amanhã
        fim = inicio + timedelta(hours=2)

        payload = {
            # 'usuario' NÃO está no payload (deve ser preenchido automaticamente)
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "tipo": "T",  # Bloqueio total
            "motivo": "Férias",
        }

        response = client.post("/api/availability-blocks/", payload, format="json")

        assert (
            response.status_code == http_status.HTTP_201_CREATED
        ), f"Esperado 201, obtido {response.status_code}: {response.data}"

        # Verificar que usuario foi preenchido automaticamente com request.user
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert (
            block.usuario == user_test
        ), "usuario deve ser automaticamente preenchido com request.user (perform_create)"
        assert (
            response.data["usuario"] == user_test.id
        ), "Resposta deve retornar usuario correto"

    def test_create_block_cannot_override_usuario(self, user_test, another_user):
        """
        Test: POST /api/availability-blocks/ com 'usuario' no payload deve ser ignorado.

        O campo 'usuario' é read_only no serializer, então mesmo que o payload
        tente especificar outro usuário, deve ser ignorado e usar request.user.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=48)
        fim = inicio + timedelta(hours=1)

        payload = {
            "usuario": another_user.pk,  # Tentativa de especificar outro usuário
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "tipo": "P",  # Bloqueio parcial
            "motivo": "Compromisso pessoal",
        }

        response = client.post("/api/availability-blocks/", payload, format="json")

        assert (
            response.status_code == http_status.HTTP_201_CREATED
        ), f"Esperado 201, obtido {response.status_code}: {response.data}"

        # Verificar que usuario foi preenchido com request.user, não com o do payload
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert (
            block.usuario == user_test
        ), "usuario deve ser request.user, ignorando payload (campo read_only)"
        assert (
            block.usuario != another_user
        ), "usuario NÃO deve ser o especificado no payload"
        assert (
            response.data["usuario"] == user_test.id
        ), "Resposta deve retornar request.user.id"

    def test_create_block_validates_date_interval(self, user_test):
        """
        Test: Criar bloqueio com fim <= inicio deve falhar.
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()

        # Caso: fim == inicio (inválido)
        payload = {
            "inicio": now.isoformat(),
            "fim": now.isoformat(),  # fim == inicio (inválido)
            "tipo": "T",
            "motivo": "Teste inválido",
        }

        response = client.post("/api/availability-blocks/", payload, format="json")

        assert (
            response.status_code == http_status.HTTP_400_BAD_REQUEST
        ), "Criar com fim == inicio deve retornar 400"
        assert "fim" in response.data, "Deve retornar erro no campo 'fim'"

    def test_create_block_status_is_always_approved(self, user_test):
        """
        Test: Bloqueios criados via API são auto-aprovados (status='aprovado').

        Regra de Negócio:
        - Bloqueios são informações factuais (formador sabe quando estará indisponível)
        - NÃO requerem aprovação de terceiros
        - Entram automaticamente no cálculo de disponibilidade (RD-02, RD-03)
        """
        client = APIClient()
        client.force_authenticate(user=user_test)

        now = timezone.now()
        inicio = now + timedelta(hours=72)
        fim = inicio + timedelta(hours=3)

        payload = {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
            "tipo": "T",
            "motivo": "Bloqueio de teste",
            "status": "pendente",  # Tentativa de especificar (deve ser ignorado e virar 'aprovado')
        }

        response = client.post("/api/availability-blocks/", payload, format="json")

        assert (
            response.status_code == http_status.HTTP_201_CREATED
        ), f"Esperado 201, obtido {response.status_code}: {response.data}"

        # Verificar que status é aprovado (auto-aprovação)
        block = AvailabilityBlock.objects.get(pk=response.data["id"])
        assert (
            block.status == "aprovado"
        ), "Status deve ser 'aprovado' (auto-aprovação de bloqueios)"
        assert (
            response.data["status"] == "aprovado"
        ), "Resposta deve retornar status='aprovado'"

    def test_unauthenticated_cannot_create_block(self):
        """
        Test: Usuário não autenticado não pode criar bloqueio.
        """
        client = APIClient()
        # Não autenticado

        now = timezone.now()
        payload = {
            "inicio": now.isoformat(),
            "fim": (now + timedelta(hours=1)).isoformat(),
            "tipo": "T",
            "motivo": "Tentativa sem autenticação",
        }

        response = client.post("/api/availability-blocks/", payload, format="json")

        assert response.status_code in [
            http_status.HTTP_401_UNAUTHORIZED,
            http_status.HTTP_403_FORBIDDEN,
        ], "Usuário não autenticado não deve poder criar bloqueio"
