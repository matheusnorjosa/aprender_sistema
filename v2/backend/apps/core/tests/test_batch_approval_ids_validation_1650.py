"""
M11-04 (#1650) — validação do payload `ids` em batch-approve / batch-reject.

Sem validação de entrada, a view repassava `ids` cru ao serviço, que só checava
falsiness e tamanho:
- string `"8910"` → `filter(id__in="8910")` decompõe em dígitos → aprova alvos
  não nomeados (8, 9, 1, 0), sem que apareçam no payload;
- int escalar `5` → `len(5)` estoura TypeError → HTTP 500;
- dict / lista com não-inteiros passavam adiante.

Contrato: `ids` DEVE ser uma lista não-vazia de inteiros positivos (≤100);
qualquer outra coisa → 400 (nunca 200 com alvo implícito, nunca 500).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db

APPROVE_URL = "/api/solicitacoes/batch-approve/"
REJECT_URL = "/api/solicitacoes/batch-reject/"


@pytest.fixture
def aprovador():
    """Gerente da Superintendência → policy access_solicitation_approvals (PA-02)."""
    user = UsuarioFactory(username="aprovador_m1104", cpf="74000000001")
    user.groups.add(GroupFactory(name="Superintendência"), GroupFactory(name="Gerente"))
    return user


@pytest.fixture
def coordenador():
    user = UsuarioFactory(username="coord_m1104", cpf="74000000002")
    user.groups.add(GroupFactory(name="Coordenador"))
    return user


@pytest.fixture
def solicitacao_pendente(coordenador):
    return SolicitacaoFactory(
        usuario=coordenador,
        municipio=MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True),
        projeto=ProjetoFactory(nome="Projeto M1104", codigo="M1104", fluxo="SUPER", ativo=True),
        tipo_evento=TipoEventoFactory(nome="Formacao M1104"),
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
        status="pendente",
    )


@pytest.fixture
def client_aprovador(aprovador):
    c = APIClient()
    c.force_authenticate(aprovador)
    return c


class TestBatchIdsRejectsMalformed:
    def test_string_ids_returns_400_nao_decompoe_em_digitos(self, client_aprovador, solicitacao_pendente):
        """RED: hoje `"8910"` vira id__in dos dígitos e retorna 200 (aprova alvo implícito)."""
        resp = client_aprovador.post(APPROVE_URL, {"ids": "8910"}, format="json")
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"
        solicitacao_pendente.refresh_from_db()
        assert solicitacao_pendente.status == "pendente"

    def test_int_escalar_returns_400_nao_500(self, client_aprovador):
        """RED: hoje `len(5)` estoura TypeError → 500."""
        resp = client_aprovador.post(APPROVE_URL, {"ids": 5}, format="json")
        assert resp.status_code == 400, f"esperado 400, obteve {resp.status_code}"

    def test_dict_ids_returns_400(self, client_aprovador):
        resp = client_aprovador.post(APPROVE_URL, {"ids": {"a": 1}}, format="json")
        assert resp.status_code == 400

    def test_lista_com_nao_inteiro_returns_400(self, client_aprovador):
        resp = client_aprovador.post(APPROVE_URL, {"ids": ["abc"]}, format="json")
        assert resp.status_code == 400

    def test_reject_string_ids_returns_400(self, client_aprovador, solicitacao_pendente):
        resp = client_aprovador.post(REJECT_URL, {"ids": "8910"}, format="json")
        assert resp.status_code == 400
        solicitacao_pendente.refresh_from_db()
        assert solicitacao_pendente.status == "pendente"


class TestBatchIdsAcceptsValid:
    def test_lista_valida_aprova(self, client_aprovador, solicitacao_pendente):
        """Não-regressão: lista de inteiros válida aprova normalmente."""
        resp = client_aprovador.post(APPROVE_URL, {"ids": [solicitacao_pendente.id]}, format="json")
        assert resp.status_code == 200, resp.data
        assert resp.data["approved"] == 1
        solicitacao_pendente.refresh_from_db()
        assert solicitacao_pendente.status == "aprovado"

    def test_lista_vazia_returns_400(self, client_aprovador):
        """Contrato preservado: lista vazia continua 400 (obrigatório)."""
        resp = client_aprovador.post(APPROVE_URL, {"ids": []}, format="json")
        assert resp.status_code == 400
