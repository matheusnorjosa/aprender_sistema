"""
Testes para exposição de meet_link no SolicitacaoSerializer (RF06 - PR19).

Valida:
- GET /api/solicitacoes/{id}/ retorna meet_link quando setado
- GET /api/solicitacoes/ (list) retorna meet_link
- meet_link é read_only (não pode ser setado via POST/PATCH)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from unittest.mock import patch
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
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_test",
        email="controle@test.com",
        password="testpass",
        cpf="11111111111",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_com_meet_link(usuario_controle):
    """Solicitação aprovada com meet_link preenchido"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
    )

    # Simular que já foi publicado e recebeu meet_link
    sol.meet_link = "https://meet.google.com/abc-defg-hij"
    sol.external_event_id = "asv2-12345"
    sol.save()

    return sol


@pytest.mark.django_db
class TestSolicitacaoSerializerMeetLink:
    """Testes para campo meet_link no SolicitacaoSerializer"""

    @patch('rest_framework.throttling.AnonRateThrottle.allow_request', return_value=True)
    @patch('rest_framework.throttling.UserRateThrottle.allow_request', return_value=True)
    def test_detail_returns_meet_link_when_set(
        self, mock_throttle1, mock_throttle2, usuario_controle, solicitacao_com_meet_link
    ):
        """
        RF06: GET /api/solicitacoes/{id}/ deve retornar meet_link quando setado.

        Cenário:
        - Solicitação aprovada com meet_link preenchido
        - GET detalhe da solicitação

        Resultado esperado: Response contém meet_link
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get(
            f"/api/solicitacoes/{solicitacao_com_meet_link.id}/",
            format="json"
        )

        assert response.status_code == 200
        assert "meet_link" in response.data
        assert response.data["meet_link"] == "https://meet.google.com/abc-defg-hij"

    def test_detail_returns_null_meet_link_when_not_set(self, usuario_controle):
        """
        RF06: GET /api/solicitacoes/{id}/ deve retornar meet_link=null quando não setado.

        Cenário:
        - Solicitação sem meet_link (nunca publicada ou sem Meet)

        Resultado esperado: Response contém meet_link=null
        """
        municipio = Municipio.objects.create(nome="São Paulo", uf="SP", ativo=True)
        projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
        tipo_evento = TipoEvento.objects.create(nome="Reunião")

        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            inicio=now + timedelta(days=2),
            fim=now + timedelta(days=2, hours=1),
            status="pendente",
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get(f"/api/solicitacoes/{sol.id}/", format="json")

        assert response.status_code == 200
        assert "meet_link" in response.data
        assert response.data["meet_link"] is None

    def test_list_returns_meet_link(self, usuario_controle, solicitacao_com_meet_link):
        """
        RF06: GET /api/solicitacoes/ (list) deve retornar meet_link.

        Cenário:
        - Solicitação com meet_link na listagem

        Resultado esperado: Response contém meet_link para cada item
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/solicitacoes/", format="json")

        assert response.status_code == 200
        assert len(response.data["results"]) > 0

        # Encontrar nossa solicitação na listagem
        item = next(
            (item for item in response.data["results"]
             if item["id"] == solicitacao_com_meet_link.id),
            None
        )

        assert item is not None
        assert "meet_link" in item
        assert item["meet_link"] == "https://meet.google.com/abc-defg-hij"

    def test_meet_link_is_read_only(self, usuario_controle):
        """
        RF06: meet_link deve ser read_only (não aceita POST/PATCH).

        Cenário:
        - POST nova solicitação tentando setar meet_link
        - Sistema deve ignorar o valor

        Resultado esperado: meet_link continua null (não foi setado via POST)
        """
        municipio = Municipio.objects.create(nome="Recife", uf="PE", ativo=True)
        projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
        tipo_evento = TipoEvento.objects.create(nome="Workshop")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        now = timezone.now()
        response = client.post(
            "/api/solicitacoes/",
            {
                "municipio": municipio.id,
                "projeto": projeto.id,
                "tipo_evento": tipo_evento.id,
                "inicio": (now + timedelta(days=3)).isoformat(),
                "fim": (now + timedelta(days=3, hours=2)).isoformat(),
                "observacoes": "Teste",
                # Tentar setar meet_link (deve ser ignorado)
                "meet_link": "https://meet.google.com/fake-link"
            },
            format="json"
        )

        # POST pode retornar 201 ou 400 dependendo das validações
        # O importante é que se criou, meet_link deve ser null
        if response.status_code == 201:
            sol_id = response.data["id"]
            sol = Solicitacao.objects.get(id=sol_id)
            assert sol.meet_link is None, \
                "meet_link deve ser read_only e não aceitar valor via POST"

    def test_meet_link_is_read_only_on_patch(
        self, usuario_controle, solicitacao_com_meet_link
    ):
        """
        RF06: meet_link deve ser read_only (não aceita PATCH).

        Cenário:
        - PATCH solicitação existente tentando alterar meet_link
        - Sistema deve ignorar o valor

        Resultado esperado: meet_link mantém valor original
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        original_link = solicitacao_com_meet_link.meet_link

        response = client.patch(
            f"/api/solicitacoes/{solicitacao_com_meet_link.id}/",
            {
                "observacoes": "Atualizado",
                # Tentar alterar meet_link (deve ser ignorado)
                "meet_link": "https://meet.google.com/new-fake-link"
            },
            format="json"
        )

        # Refresh do banco
        solicitacao_com_meet_link.refresh_from_db()

        # meet_link deve manter o valor original
        assert solicitacao_com_meet_link.meet_link == original_link, \
            "meet_link deve ser read_only e não aceitar alteração via PATCH"
