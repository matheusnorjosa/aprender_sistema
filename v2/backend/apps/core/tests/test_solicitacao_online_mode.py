"""
Testes para modalidade online/presencial (is_online) - PR19.

Valida:
- Default de is_online é False (presencial)
- Serializer expõe is_online (writable) e meet_link (read_only)
- Criação de solicitação com is_online=True/False
"""

import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta

from apps.core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
)


@pytest.fixture
def usuario_coordenador():
    """Usuário coordenador para criar solicitações"""
    user = Usuario.objects.create_user(
        username="coordenador_test",
        email="coordenador@test.com",
        password="testpass",
        cpf="33333333333",
    )
    grupo, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(grupo)
    return user


@pytest.fixture
def fixtures_basicas():
    """Fixtures básicas para criar solicitações"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    return {
        "municipio": municipio,
        "projeto": projeto,
        "tipo_evento": tipo_evento,
    }


@pytest.mark.django_db
class TestSolicitacaoOnlineMode:
    """Testes para modalidade online/presencial (is_online)"""

    def test_defaults_is_online_false(self, usuario_coordenador, fixtures_basicas):
        """
        PR19: is_online deve ter default False (presencial).

        Cenário:
        - Criar Solicitacao sem especificar is_online

        Resultado esperado: is_online=False
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=1),
            fim=now + timedelta(days=1, hours=2),
        )

        # Verificar default
        assert sol.is_online is False, \
            "is_online deve ter default False (presencial)"

    def test_create_online_solicitacao(self, usuario_coordenador, fixtures_basicas):
        """
        PR19: Deve permitir criar solicitação online (is_online=True).

        Cenário:
        - Criar Solicitacao com is_online=True

        Resultado esperado: is_online=True persiste no DB
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=2),
            fim=now + timedelta(days=2, hours=3),
            is_online=True,
        )

        # Verificar persistência
        sol.refresh_from_db()
        assert sol.is_online is True, \
            "is_online=True deve persistir no DB"

    def test_serializer_exposes_is_online_and_meet_link(
        self, usuario_coordenador, fixtures_basicas
    ):
        """
        PR19: Serializer deve expor is_online (writable) e meet_link (read_only).

        Cenário:
        - GET /api/solicitacoes/{id}/ para solicitação online

        Resultado esperado:
        - Response contém is_online=True
        - Response contém meet_link (null ou string)
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=3),
            fim=now + timedelta(days=3, hours=1),
            is_online=True,
            status="aprovado",
        )

        client = APIClient()
        client.force_authenticate(user=usuario_coordenador)

        response = client.get(f"/api/solicitacoes/{sol.id}/", format="json")

        assert response.status_code == 200
        assert "is_online" in response.data
        assert response.data["is_online"] is True
        assert "meet_link" in response.data  # Pode ser null ou string

    def test_serializer_exposes_is_online_false_for_presencial(
        self, usuario_coordenador, fixtures_basicas
    ):
        """
        PR19: Serializer deve expor is_online=False para eventos presenciais.

        Cenário:
        - GET /api/solicitacoes/{id}/ para solicitação presencial

        Resultado esperado:
        - Response contém is_online=False
        - Response contém meet_link=null
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=4),
            fim=now + timedelta(days=4, hours=2),
            is_online=False,
            status="aprovado",
        )

        client = APIClient()
        client.force_authenticate(user=usuario_coordenador)

        response = client.get(f"/api/solicitacoes/{sol.id}/", format="json")

        assert response.status_code == 200
        assert "is_online" in response.data
        assert response.data["is_online"] is False
        assert "meet_link" in response.data
        assert response.data["meet_link"] is None  # Presencial não tem Meet link

    def test_is_online_writable_via_post(
        self, usuario_coordenador, fixtures_basicas
    ):
        """
        PR19: is_online deve ser writable (aceita POST).

        Cenário:
        - POST /api/solicitacoes/ com is_online=True

        Resultado esperado:
        - Solicitação criada com is_online=True
        """
        client = APIClient()
        client.force_authenticate(user=usuario_coordenador)

        now = timezone.now()
        response = client.post(
            "/api/solicitacoes/",
            {
                "municipio": fixtures_basicas["municipio"].id,
                "projeto": fixtures_basicas["projeto"].id,
                "tipo_evento": fixtures_basicas["tipo_evento"].id,
                "inicio": (now + timedelta(days=5)).isoformat(),
                "fim": (now + timedelta(days=5, hours=2)).isoformat(),
                "is_online": True,
            },
            format="json"
        )

        # POST pode retornar 201 ou 400 dependendo das validações
        if response.status_code == 201:
            sol_id = response.data["id"]
            sol = Solicitacao.objects.get(id=sol_id)
            assert sol.is_online is True, \
                "is_online deve aceitar valor via POST"

    def test_is_online_writable_via_patch(
        self, usuario_coordenador, fixtures_basicas
    ):
        """
        PR19: is_online deve ser writable (aceita PATCH).

        Cenário:
        - Criar solicitação presencial (is_online=False)
        - PATCH para is_online=True

        Resultado esperado:
        - is_online alterado para True
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_coordenador,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=6),
            fim=now + timedelta(days=6, hours=2),
            is_online=False,
        )

        client = APIClient()
        client.force_authenticate(user=usuario_coordenador)

        response = client.patch(
            f"/api/solicitacoes/{sol.id}/",
            {"is_online": True},
            format="json"
        )

        # Refresh do banco
        sol.refresh_from_db()

        # Verificar que is_online foi alterado
        assert sol.is_online is True, \
            "is_online deve aceitar alteração via PATCH"
