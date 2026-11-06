"""
A lista antiga de compras (`Compra`, tabela `core_compra`) saiu de uso (G29, etapa 1; decisão do dono de 05/11/2026).

A lista atual é `DATCompra` (`/api/dat/compras-materiais/`). As rotas que liam ou gravavam `Compra` saíram;
a tabela e o model ficam até a etapa 2 (apagar a tabela, depois de backup e OK do dono). No Django admin o
registro fica só para consulta.

Este arquivo prova:
- as rotas antigas respondem 404, inclusive para o superusuário;
- o import pela tela que ficou no mesmo lugar (ações) não grava em `Compra`;
- o admin do `Compra` não cria, não altera e não apaga.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from rest_framework.test import APIClient

import pytest

from apps.core.admin import admin_site
from apps.core.models import Compra, DATAcao
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CSV_DE_COMPRAS = b"codigo,produto,quant,municipio,uf,data,uso\nC1,X,10,Acarape,CE,2025-01-01,Formacao\n"

ROTAS_ANTIGAS: list[tuple[str, str]] = [
    ("get", "/api/compras/"),
    ("post", "/api/compras/"),
    ("get", "/api/compras/{id}/"),
    ("delete", "/api/compras/{id}/"),
    ("get", "/api/controle/compras/"),
    ("post", "/api/controle/import-compras/?dry_run=false"),
    ("post", "/api/import-compras/?dry_run=false"),
]


def _superusuario() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


def _compra_antiga() -> Compra:
    return Compra.objects.create(
        codigo="ANTIGA-1",
        projeto=ProjetoFactory(),
        municipio=MunicipioFactory(),
        quantidade=5,
        data=date(2026, 7, 3),
        uso="Formação",
        external_hash="hash-compra-antiga-1",
    )


@pytest.mark.parametrize(("metodo", "rota"), ROTAS_ANTIGAS, ids=[f"{m} {r}" for m, r in ROTAS_ANTIGAS])
def test_rota_antiga_de_compra_responde_404(metodo: str, rota: str):
    rota = rota.format(id=_compra_antiga().pk)
    arquivo = SimpleUploadedFile("compras.csv", CSV_DE_COMPRAS, content_type="text/csv")

    resposta = getattr(_superusuario(), metodo)(rota, {"file": arquivo}, format="multipart")

    assert resposta.status_code == 404, f"{metodo.upper()} {rota} respondeu {resposta.status_code}"
    assert Compra.objects.count() == 1  # a linha antiga continua lá: nada apagado, nada gravado


def test_import_de_acoes_que_ficou_nao_grava_em_compra():
    antiga = _compra_antiga()
    antes = list(Compra.objects.values_list("id", "codigo", "quantidade", "updated_at"))
    MunicipioFactory(nome="Acarape", uf="CE")
    csv_de_acoes = "Município,Projeto,Coordenador,Data Entrega\nAcarape,{},,2025-01-15\n".format(antiga.projeto.nome)
    arquivo = SimpleUploadedFile("acoes.csv", csv_de_acoes.encode(), content_type="text/csv")

    resposta = _superusuario().post("/api/controle/import-acoes/?dry_run=false", {"file": arquivo}, format="multipart")

    assert resposta.status_code == 200, resposta.content
    assert DATAcao.objects.count() == 1  # controle positivo: o import gravou, só não foi em Compra
    assert list(Compra.objects.values_list("id", "codigo", "quantidade", "updated_at")) == antes


def test_admin_do_compra_e_so_leitura():
    model_admin = admin_site._registry[Compra]
    request = RequestFactory().get("/admin/core/compra/")
    request.user = UsuarioFactory(superuser=True)
    compra = _compra_antiga()

    assert model_admin.has_view_permission(request, compra) is True
    assert model_admin.has_add_permission(request) is False
    assert model_admin.has_change_permission(request, compra) is False
    assert model_admin.has_delete_permission(request, compra) is False
