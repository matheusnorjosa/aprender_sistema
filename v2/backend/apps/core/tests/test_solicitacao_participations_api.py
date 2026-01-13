"""
Testes para API de Solicitacoes com campo participations - PR #1

Valida:
- Campo participations aparece em listagens/detalhe
- Prefetch funciona corretamente (sem erro de "formadores")
- Payload JSON estruturado conforme esperado
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Participation, Solicitacao, Municipio, TipoEvento, Projeto

pytestmark = pytest.mark.django_db


@pytest.fixture
def factory_solicitacao():
    """
    Factory para criar Solicitacao com dependências mínimas.
    """

    def _factory(**kwargs):
        User = get_user_model()

        # Usuario criador (se não fornecido)
        if "usuario" not in kwargs:
            user = User.objects.create_user(
                username=f"user_{timezone.now().timestamp()}",
                email=f"user{timezone.now().timestamp()}@example.com",
                password="testpass123",
                cpf=f"{int(timezone.now().timestamp()) % 100000000000}",
            )
            kwargs["usuario"] = user

        # Municipio
        if "municipio" not in kwargs:
            municipio, _ = Municipio.objects.get_or_create(
                nome="Fortaleza", uf="CE", defaults={"ativo": True}
            )
            kwargs["municipio"] = municipio

        # TipoEvento
        if "tipo_evento" not in kwargs:
            tipo_evento, _ = TipoEvento.objects.get_or_create(
                nome="Formação", defaults={"descricao": "Formação continuada"}
            )
            kwargs["tipo_evento"] = tipo_evento

        # Projeto
        if "projeto" not in kwargs:
            projeto, _ = Projeto.objects.get_or_create(
                nome="Teste Projeto", defaults={"ativo": True}
            )
            kwargs["projeto"] = projeto

        # Datas
        if "inicio" not in kwargs:
            kwargs["inicio"] = timezone.now()
        if "fim" not in kwargs:
            kwargs["fim"] = kwargs["inicio"] + timezone.timedelta(hours=2)

        # Status
        if "status" not in kwargs:
            kwargs["status"] = "pendente"

        return Solicitacao.objects.create(**kwargs)

    return _factory


def test_solicitacao_list_includes_participations(factory_solicitacao):
    """
    Testa que listagem de Solicitacoes inclui campo 'participations' (read-only).
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()

    u1 = User.objects.create_user(
        username="coordenador1",
        email="coord1@example.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Coordenador",
        last_name="Um",
    )
    u2 = User.objects.create_user(
        username="formador1",
        email="formador1@example.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Formador",
        last_name="Dois",
    )

    Participation.objects.create(
        solicitacao=solicitacao, usuario=u1, role=Participation.Role.COORDENADOR
    )
    Participation.objects.create(
        solicitacao=solicitacao, usuario=u2, role=Participation.Role.FORMADOR
    )

    client = APIClient()
    # Autenticar como superuser para ver todas as solicitações
    superuser = User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="admin123",
        cpf="00000000000",
    )
    client.force_authenticate(user=superuser)

    resp = client.get("/api/solicitacoes/")
    assert resp.status_code == 200

    content = resp.json()

    # Verificar estrutura de resposta (paginada ou lista simples)
    if "results" in content:
        # DRF pagination
        solicitacao_data = content["results"][0]
    else:
        # Lista simples
        solicitacao_data = content[0]

    # Verificar que campo 'participations' existe
    assert "participations" in solicitacao_data, "Campo 'participations' deve estar presente"

    # Verificar estrutura de participations
    participations = solicitacao_data["participations"]
    assert len(participations) == 2, "Deve haver 2 participations"

    # Verificar estrutura de cada participation
    roles = [p["role"] for p in participations]
    assert "COORDENADOR" in roles
    assert "FORMADOR" in roles

    # Verificar que usuario está aninhado (UserSlimSerializer)
    coordenador_participation = [p for p in participations if p["role"] == "COORDENADOR"][0]
    assert "usuario" in coordenador_participation
    assert coordenador_participation["usuario"]["first_name"] == "Coordenador"
    assert coordenador_participation["usuario"]["email"] == "coord1@example.com"


def test_solicitacao_detail_includes_participations(factory_solicitacao):
    """
    Testa que detalhes de uma Solicitacao incluem campo 'participations'.
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()

    u1 = User.objects.create_user(
        username="convidado1",
        email="convidado@example.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Convidado",
        last_name="Especial",
    )

    Participation.objects.create(
        solicitacao=solicitacao,
        usuario=u1,
        role=Participation.Role.CONVIDADO,
        ch_horas=4.5,
        observacao="Palestrante especial",
    )

    client = APIClient()
    superuser = User.objects.create_superuser(
        username="admin2",
        email="admin2@example.com",
        password="admin123",
        cpf="00000000001",
    )
    client.force_authenticate(user=superuser)

    resp = client.get(f"/api/solicitacoes/{solicitacao.id}/")
    assert resp.status_code == 200

    data = resp.json()

    assert "participations" in data
    assert len(data["participations"]) == 1

    participation = data["participations"][0]
    assert participation["role"] == "CONVIDADO"
    assert float(participation["ch_horas"]) == 4.5
    assert participation["observacao"] == "Palestrante especial"
    assert participation["usuario"]["first_name"] == "Convidado"


def test_solicitacao_api_no_formadores_field(factory_solicitacao):
    """
    Testa que campo 'formadores' NÃO aparece no payload (prefetch removido).
    """
    solicitacao = factory_solicitacao()
    User = get_user_model()

    client = APIClient()
    superuser = User.objects.create_superuser(
        username="admin3",
        email="admin3@example.com",
        password="admin123",
        cpf="00000000002",
    )
    client.force_authenticate(user=superuser)

    resp = client.get(f"/api/solicitacoes/{solicitacao.id}/")
    assert resp.status_code == 200

    data = resp.json()
    payload_str = str(data)

    # Verificar que "formadores" NÃO está no payload
    assert "formadores" not in payload_str.lower(), "Campo 'formadores' não deve existir no payload"
