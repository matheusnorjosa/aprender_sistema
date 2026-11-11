"""ISS-1658 (fila do #2210): a tela de municípios e o upload não criam a cópia que só muda acento ou caixa.

O importador da virada para a carga inteira quando o cadastro tem a mesma chave (nome sem acento e sem caixa,
UF em caixa alta) com ids diferentes (#2210). Os outros dois caminhos que gravam município (o CRUD da tela,
`MunicipioSerializer`, e o upload, `municipios_import`) conferiam só `nome`/`nome__iexact`: deixavam entrar
"Acarau"/CE ao lado de "Acaraú"/CE, e o CRUD aceitava UF em minúsculas.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import Municipio
from apps.core.services.municipios_import import import_municipios_from_file
from apps.core.tests.factories import MunicipioFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(groups=["DAT"]))
    return client


def _acarau_ce() -> int:
    return Municipio.objects.filter(uf="CE", nome__in=["Acaraú", "Acarau", "ACARAU", "acaraú"]).count()


@pytest.mark.parametrize("nome,uf", [("Acarau", "CE"), ("ACARAÚ", "CE"), ("acaraú", "ce")])
def test_crud_recusa_a_copia_que_so_muda_acento_ou_caixa(api, nome, uf):
    MunicipioFactory(nome="Acaraú", uf="CE")

    resp = api.post("/api/municipios/", {"nome": nome, "uf": uf, "ativo": True}, format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
    assert "nome" in resp.data["errors"]
    assert _acarau_ce() == 1


def test_crud_recusa_renomear_para_a_chave_de_outro(api):
    MunicipioFactory(nome="Acaraú", uf="CE")
    outro = MunicipioFactory(nome="Outro Lugar", uf="CE")

    resp = api.patch(f"/api/municipios/{outro.id}/", {"nome": "ACARAU"}, format="json")

    assert resp.status_code == status.HTTP_400_BAD_REQUEST, resp.data
    outro.refresh_from_db()
    assert outro.nome == "Outro Lugar"


def test_crud_editar_o_proprio_e_homonimo_de_outra_uf_seguem_valendo(api):
    acarau = MunicipioFactory(nome="Acaraú", uf="CE")

    assert api.patch(f"/api/municipios/{acarau.id}/", {"ativo": False}, format="json").status_code == 200
    assert api.patch(f"/api/municipios/{acarau.id}/", {"nome": "ACARAÚ"}, format="json").status_code == 200
    novo = api.post("/api/municipios/", {"nome": "Acaraú", "uf": "PI", "ativo": True}, format="json")
    assert novo.status_code == status.HTTP_201_CREATED, novo.data


def test_crud_grava_a_uf_em_caixa_alta(api):
    resp = api.post("/api/municipios/", {"nome": "Lugar Ficticio", "uf": "pi", "ativo": True}, format="json")

    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    assert Municipio.objects.get(pk=resp.data["id"]).uf == "PI"


def test_upload_reconhece_a_grafia_sem_acento_e_nao_cria_copia(tmp_path):
    MunicipioFactory(nome="Acaraú", uf="CE", ativo=True)
    csv_path = tmp_path / "municipios.csv"
    csv_path.write_text("nome,uf,ibge_code\nAcarau,CE,\n", encoding="utf-8")

    report = import_municipios_from_file(path=str(csv_path), dry_run=False)

    assert report["stats"]["created"] == 0
    assert _acarau_ce() == 1
