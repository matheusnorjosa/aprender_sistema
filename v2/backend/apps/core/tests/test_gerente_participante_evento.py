"""Gerente pode ser participante de evento (decisão do dono, 11/11/2026).

Caso real: a lista de formadores da Nova Solicitação/edição pedia só os papéis FORMADOR e
COORDENADOR, então a gerente da gerência do projeto não aparecia. O seletor passa a pedir também
GERENTE (`role=Formador,Coordenador,Gerente`). A regra de servidor não muda: entra quem tem vínculo
vigente com escopo (papel ≠ EQUIPE) na gerência do projeto (`participantes_fora_da_gerencia`, P9-5),
o que já inclui o GERENTE. Gerente de outra gerência segue recusado. Quem cria/aprova/edita não muda.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

import itertools
from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Participation
from apps.core.tests.factories import (
    GerenciaFactory,
    MunicipioFactory,
    ProjetoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
    liberar_par,
)

pytestmark = pytest.mark.django_db

_CPF = itertools.count(79300000001)
_ROLE_DO_SELETOR = "Formador,Coordenador,Gerente"


def _pessoa(nome, papel, gerencia):
    u = UsuarioFactory(username=nome, cpf=str(next(_CPF)))
    com_papel(u, papel, gerencia)
    return u


def _client(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def gerencias():
    return {"a": GerenciaFactory(nome="G-A-gerente-part"), "b": GerenciaFactory(nome="G-B-gerente-part")}


@pytest.fixture
def coordenador(gerencias):
    return _pessoa("coord_gerente_part", "COORDENADOR", gerencias["a"])


@pytest.fixture
def municipio():
    return MunicipioFactory(nome="Fortaleza gerente part", uf="CE", ativo=True)


@pytest.fixture
def tipo_evento():
    return TipoEventoFactory(nome="Formacao gerente part")


@pytest.fixture
def projeto(municipio, gerencias):
    proj = ProjetoFactory(
        nome="Projeto gerente part", codigo="PGP1111", gerencia=gerencias["a"], fluxo="NAO_SUPER", ativo=True
    )
    liberar_par(municipio, proj)
    return proj


def _payload(municipio, projeto, tipo_evento, formador_ids):
    inicio = timezone.now() + timedelta(days=3)
    return {
        "municipio": municipio.id,
        "projeto": projeto.id,
        "tipo_evento": tipo_evento.id,
        "coordenador_acompanha": False,
        "tipo": "PRESENCIAL",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(hours=2)).isoformat(),
        "extra_participants": {"formador_ids": formador_ids},
    }


class TestLookupOfereceGerente:
    def test_lista_inclui_gerente_da_gerencia_do_projeto_e_nao_a_de_outra(self, coordenador, gerencias, projeto):
        gerente_a = _pessoa("gerente_a_part", "GERENTE", gerencias["a"])
        gerente_b = _pessoa("gerente_b_part", "GERENTE", gerencias["b"])
        resp = _client(coordenador).get("/api/lookup/usuarios/", {"role": _ROLE_DO_SELETOR, "projeto_id": projeto.id})
        assert resp.status_code == 200, resp.data
        ids = {item["id"] for item in resp.json()}
        assert gerente_a.id in ids
        assert gerente_b.id not in ids


class TestCriarComGerenteParticipante:
    def test_gerente_da_gerencia_do_projeto_entra_e_ocupa_como_formador(
        self, coordenador, gerencias, municipio, projeto, tipo_evento
    ):
        gerente = _pessoa("gerente_a_cria", "GERENTE", gerencias["a"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, [gerente.id]), format="json"
        )
        assert resp.status_code == 201, resp.data
        assert Participation.objects.filter(solicitacao_id=resp.json()["id"], usuario=gerente, role="FORMADOR").exists()

    def test_gerente_de_outra_gerencia_e_recusado(self, coordenador, gerencias, municipio, projeto, tipo_evento):
        gerente = _pessoa("gerente_b_cria", "GERENTE", gerencias["b"])
        resp = _client(coordenador).post(
            "/api/solicitacoes/", _payload(municipio, projeto, tipo_evento, [gerente.id]), format="json"
        )
        assert resp.status_code == 400, resp.data
        assert "extra_participants" in resp.data.get("errors", resp.data)
