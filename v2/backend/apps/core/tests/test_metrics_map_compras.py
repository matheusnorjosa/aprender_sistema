"""
Mapa (`GET /api/metrics/map/`): a coluna "Compras" conta a lista atual (G19, decisão do dono 05/11/2026).

Regra (a mesma da criação, `services/compra_elegibilidade.py`):
- só conta `DATCompra` ativa com `quantidade > 0`; a tabela `Compra` antiga não entra;
- conta par município × projeto: duas compras do mesmo projeto no mesmo município contam 1;
- com o filtro de projeto, vale a família da coleção: a compra de outro projeto da mesma coleção
  no município conta 1 para o projeto filtrado (o par é município × projeto filtrado);
- o filtro de datas olha `DATCompra.data_compra`; compra sem data só fica de fora quando há filtro.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, Produto, ProjetoGeral
from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    UsuarioFactory,
    com_pacote_da_diretoria,
    liberar_par,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_diretoria():
    user = UsuarioFactory(username="mapa_compras_dir", email="mapa_compras_dir@example.invalid")
    com_pacote_da_diretoria(user)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def cenario():
    """Um município com evento em CE; outro em SP sem evento; dois projetos da mesma coleção."""
    colecao = ProjetoGeral.objects.create(nome="Colecao Mapa Ficticia")
    outra = ProjetoGeral.objects.create(nome="Colecao Mapa Outra")
    proj_a = ProjetoFactory(nome="Mapa Ficticio A", projeto_geral=colecao)
    proj_b = ProjetoFactory(nome="Mapa Ficticio B", projeto_geral=colecao)
    proj_c = ProjetoFactory(nome="Mapa Ficticio C", projeto_geral=outra)
    mun_ce = MunicipioFactory(nome="Cidade Mapa CE", uf="CE", latitude=-3.7, longitude=-38.5)
    mun_sp = MunicipioFactory(nome="Cidade Mapa SP", uf="SP", latitude=-23.5, longitude=-46.6)
    now = timezone.now()
    SolicitacaoFactory(status="aprovado", inicio=now, fim=now + timedelta(hours=2), municipio=mun_ce, projeto=proj_a)
    return {"a": proj_a, "b": proj_b, "c": proj_c, "ce": mun_ce, "sp": mun_sp}


def _get(client, **params):
    res = client.get(reverse("core:metrics-map"), params)
    assert res.status_code == 200, res.content
    data = res.json()
    by_uf = {item["uf"]: item["compras"] for item in data["by_uf"]}
    by_mun = {item["municipio"]: item["compras"] for item in data["by_municipio"]}
    return data["totals"]["compras"], by_uf, by_mun


def test_compra_antiga_sem_datcompra_nao_conta(client_diretoria, cenario):
    produto = Produto.objects.create(nome="Kit Mapa", codigo="KITMAPA", projeto=cenario["a"])
    Compra.objects.create(
        codigo="MAPA-LEG-1",
        produto=produto,
        projeto=cenario["a"],
        municipio=cenario["ce"],
        quantidade=10,
        data=timezone.localdate(),
        uso="Uso 1",
        external_hash="hash_mapa_legado_1",
    )

    total, by_uf, by_mun = _get(client_diretoria)

    assert total == 0
    assert by_uf["CE"] == 0
    assert by_mun["Cidade Mapa CE"] == 0


def test_datcompra_inativa_ou_sem_quantidade_nao_conta(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["a"], ativo=False)
    liberar_par(cenario["ce"], cenario["b"], quantidade=0)

    total, by_uf, by_mun = _get(client_diretoria)

    assert (total, by_uf["CE"], by_mun["Cidade Mapa CE"]) == (0, 0, 0)


def test_conta_par_municipio_projeto_sem_repetir(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["a"])
    liberar_par(cenario["ce"], cenario["a"], quantidade=5)  # mesma dupla: conta uma vez
    liberar_par(cenario["ce"], cenario["c"])
    liberar_par(cenario["sp"], cenario["a"])

    total, by_uf, by_mun = _get(client_diretoria)

    assert by_mun["Cidade Mapa CE"] == 2
    assert by_uf["CE"] == 2
    assert total == 3  # o total conta também SP, que não tem evento


def test_filtro_de_projeto_vale_a_familia_da_colecao(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["b"])  # mesma coleção de A: libera A em CE
    liberar_par(cenario["ce"], cenario["b"], quantidade=3)
    liberar_par(cenario["sp"], cenario["c"])  # outra coleção: não libera A

    total, by_uf, by_mun = _get(client_diretoria, projeto_id=cenario["a"].pk)

    assert (total, by_uf["CE"], by_mun["Cidade Mapa CE"]) == (1, 1, 1)


def test_filtro_de_projeto_inexistente_conta_zero(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["a"])

    total, _, _ = _get(client_diretoria, projeto_id=999999)

    assert total == 0


def test_filtro_de_data_usa_data_compra_e_tira_compra_sem_data(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["a"], data_compra=date(2026, 3, 10))
    liberar_par(cenario["ce"], cenario["c"])  # sem data
    liberar_par(cenario["sp"], cenario["a"], data_compra=date(2025, 1, 5))

    assert _get(client_diretoria)[0] == 3

    total, by_uf, _ = _get(client_diretoria, data_inicio="2026-01-01", data_fim="2026-12-31")

    assert total == 1
    assert by_uf["CE"] == 1


def test_filtro_de_uf_restringe_as_compras(client_diretoria, cenario):
    liberar_par(cenario["ce"], cenario["a"])
    liberar_par(cenario["sp"], cenario["a"])

    total, _, _ = _get(client_diretoria, uf="CE")

    assert total == 1
