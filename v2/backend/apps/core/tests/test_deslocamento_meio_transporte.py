"""Meio de transporte do deslocamento (decisão do dono, 11/11/2026, lista aprovada).

Campo opcional `meio_transporte`: Avião, Ônibus, Carro próprio, Carro da empresa, Uber/Táxi, Outro.
Registro antigo e importado (a planilha não tem a coluna) fica sem meio (null); vazio vale.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import Deslocamento
from apps.core.tests.conftest import get_field_errors
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

_LISTA_DO_DONO = [
    ("AVIAO", "Avião"),
    ("ONIBUS", "Ônibus"),
    ("CARRO_PROPRIO", "Carro próprio"),
    ("CARRO_EMPRESA", "Carro da empresa"),
    ("UBER_TAXI", "Uber/Táxi"),
    ("OUTRO", "Outro"),
]


@pytest.fixture
def client():
    """Quem registra o próprio deslocamento (self-service; não precisa de delegação)."""
    c = APIClient()
    c.force_authenticate(UsuarioFactory(username="desloc_meio", cpf="79400000001", superuser=True))
    return c


def _payload(**extra):
    return {"origem": "Fortaleza", "destino": "Sobral", "start_date": "2026-11-12", "end_date": "2026-11-13", **extra}


def test_choices_sao_exatamente_a_lista_do_dono():
    assert list(Deslocamento.MeioTransporte.choices) == _LISTA_DO_DONO


@pytest.mark.parametrize("valor", [v for v, _ in _LISTA_DO_DONO])
def test_cada_meio_valido_e_gravado_e_devolvido(client, valor):
    resp = client.post("/api/deslocamentos/", _payload(meio_transporte=valor), format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["meio_transporte"] == valor
    assert Deslocamento.objects.get(pk=resp.data["id"]).meio_transporte == valor


def test_meio_invalido_400(client):
    resp = client.post("/api/deslocamentos/", _payload(meio_transporte="BICICLETA"), format="json")
    assert resp.status_code == 400, resp.data
    assert "meio_transporte" in get_field_errors(resp)


@pytest.mark.parametrize("extra", [{}, {"meio_transporte": None}, {"meio_transporte": ""}])
def test_sem_meio_e_aceito_e_fica_nulo(client, extra):
    resp = client.post("/api/deslocamentos/", _payload(**extra), format="json")
    assert resp.status_code == 201, resp.data
    assert resp.data["meio_transporte"] is None
    assert Deslocamento.objects.get(pk=resp.data["id"]).meio_transporte is None


def test_editar_pode_trocar_e_limpar_o_meio(client):
    criado = client.post("/api/deslocamentos/", _payload(meio_transporte="ONIBUS"), format="json").data
    trocado = client.put(f"/api/deslocamentos/{criado['id']}/", _payload(meio_transporte="AVIAO"), format="json")
    assert trocado.status_code == 200, trocado.data
    assert trocado.data["meio_transporte"] == "AVIAO"
    limpo = client.put(f"/api/deslocamentos/{criado['id']}/", _payload(meio_transporte=None), format="json")
    assert limpo.status_code == 200, limpo.data
    assert limpo.data["meio_transporte"] is None
