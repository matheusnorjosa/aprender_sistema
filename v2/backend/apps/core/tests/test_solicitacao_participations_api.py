"""
Testes para API de Solicitacoes com campo participations - PR #1

Valida:
- Campo participations aparece em listagens/detalhe
- Prefetch funciona corretamente (sem erro de "formadores")
- Payload JSON estruturado conforme esperado
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def factory_solicitacao():
    """
    Factory para criar Solicitacao com dependências mínimas.
    """

    def _factory(**kwargs):
        # Usuario criador (se não fornecido)
        if "usuario" not in kwargs:
            kwargs["usuario"] = UsuarioFactory()

        # Municipio
        if "municipio" not in kwargs:
            kwargs["municipio"] = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)

        # TipoEvento
        if "tipo_evento" not in kwargs:
            kwargs["tipo_evento"] = TipoEventoFactory(nome="Formação", descricao="Formação continuada")

        # Projeto
        if "projeto" not in kwargs:
            kwargs["projeto"] = ProjetoFactory(nome="Teste Projeto", ativo=True)

        # Datas
        if "inicio" not in kwargs:
            kwargs["inicio"] = timezone.now()
        if "fim" not in kwargs:
            kwargs["fim"] = kwargs["inicio"] + timezone.timedelta(hours=2)

        # Status
        if "status" not in kwargs:
            kwargs["status"] = "pendente"

        return SolicitacaoFactory(**kwargs)

    return _factory


def test_solicitacao_list_includes_participations(factory_solicitacao):
    """
    Testa que listagem de Solicitacoes inclui campo 'participations' (read-only).
    """
    solicitacao = factory_solicitacao()

    u1 = UsuarioFactory(
        username="coordenador1",
        email="coord1@example.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Coordenador",
        last_name="Um",
    )
    u2 = UsuarioFactory(
        username="formador1",
        email="formador1@example.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Formador",
        last_name="Dois",
    )

    Participation.objects.create(solicitacao=solicitacao, usuario=u1, role=Participation.Role.COORDENADOR)
    Participation.objects.create(solicitacao=solicitacao, usuario=u2, role=Participation.Role.FORMADOR)

    client = APIClient()
    # Autenticar como superuser para ver todas as solicitações
    superuser = UsuarioFactory(superuser=True)
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

    u1 = UsuarioFactory(
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
    superuser = UsuarioFactory(superuser=True)
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

    client = APIClient()
    superuser = UsuarioFactory(superuser=True)
    client.force_authenticate(user=superuser)

    resp = client.get(f"/api/solicitacoes/{solicitacao.id}/")
    assert resp.status_code == 200

    data = resp.json()
    payload_str = str(data)

    # Verificar que "formadores" NÃO está no payload
    assert "formadores" not in payload_str.lower(), "Campo 'formadores' não deve existir no payload"
