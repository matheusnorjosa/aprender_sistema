"""O que vai para a tela chama a família (`ProjetoGeral`) de "coleção" (decisão do dono, 06/10/2026).

Só o rótulo muda: model, campo e URL da API continuam `projeto_geral`/`projetos-gerais`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

import csv
import io

from rest_framework.test import APIClient

import pytest

from apps.core.models import DATRegistro, ProjetoGeral
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _client(user=None) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user or UsuarioFactory(superuser=True))
    return client


def test_projeto_de_outra_colecao_no_registro_dat_diz_colecao():
    colecao = ProjetoGeral.objects.create(nome="COLECAO A")
    outra = ProjetoGeral.objects.create(nome="COLECAO B")
    projeto = ProjetoFactory(nome="Serie B1", projeto_geral=outra)

    resp = _client().post(
        "/api/dat/registros/",
        {"municipio": MunicipioFactory().id, "projeto_geral": colecao.id, "projeto": projeto.id, "professor_qtde": 10},
        format="json",
    )

    assert resp.status_code == 400, resp.data
    assert "Projeto 'Serie B1' não pertence à coleção 'COLECAO A'." in str(resp.data)
    assert "Projeto Geral" not in str(resp.data)


def test_exportacao_dos_registros_dat_chama_a_coluna_de_colecao():
    colecao = ProjetoGeral.objects.create(nome="COLECAO EXPORT")
    usuario = UsuarioFactory(superuser=True)
    DATRegistro.objects.create(
        municipio=MunicipioFactory(),
        projeto_geral=colecao,
        projeto=ProjetoFactory(projeto_geral=colecao),
        professor_qtde=10,
        created_by=usuario,
    )

    resp = _client(usuario).get("/api/dat/registros/export/")

    assert resp.status_code == 200
    cabecalho = next(csv.reader(io.StringIO(resp.content.decode("utf-8-sig"))))
    assert cabecalho[2] == "Coleção"
    assert "Projeto Geral" not in cabecalho


def test_colecao_com_nome_repetido_diz_colecao():
    ProjetoGeral.objects.create(nome="COLECAO REPETIDA")

    resp = _client().post("/api/projetos-gerais/", {"nome": "COLECAO REPETIDA"}, format="json")

    assert resp.status_code == 400, resp.data
    assert resp.data["errors"]["nome"] == ["Coleção com este nome já existe."]
