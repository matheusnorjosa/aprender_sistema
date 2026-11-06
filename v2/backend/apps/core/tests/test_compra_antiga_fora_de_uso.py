"""
A lista antiga de compras (`Compra`, tabela `core_compra`) foi apagada (G29; decisão do dono de 05/11/2026).

Etapa 1 (06/11/2026, #2178) tirou de uso as rotas que liam ou gravavam `Compra`. Etapa 2 apagou o model, a
tabela, o registro no admin e a policy `import_compras`. A lista atual é `DATCompra`
(`/api/dat/compras-materiais/`).

Este arquivo prova:
- as rotas antigas respondem 404, inclusive para o superusuário;
- o import pela tela que ficou no mesmo lugar (ações) segue gravando;
- o model, a tabela `core_compra` e o registro no admin não existem mais;
- `/api/me/policies/` não traz `import_compras`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient

import pytest

from apps.core.admin import admin_site
from apps.core.models import DATAcao
from apps.core.rbac.policies import PUBLIC_POLICY_KEYS
from apps.core.tests.factories import MunicipioFactory, ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db

CSV_DE_COMPRAS = b"codigo,produto,quant,municipio,uf,data,uso\nC1,X,10,Acarape,CE,2025-01-01,Formacao\n"

ROTAS_ANTIGAS: list[tuple[str, str]] = [
    ("get", "/api/compras/"),
    ("post", "/api/compras/"),
    ("get", "/api/compras/1/"),
    ("delete", "/api/compras/1/"),
    ("get", "/api/controle/compras/"),
    ("post", "/api/controle/import-compras/?dry_run=false"),
    ("post", "/api/import-compras/?dry_run=false"),
]


def _superusuario() -> APIClient:
    client = APIClient()
    client.force_authenticate(user=UsuarioFactory(superuser=True))
    return client


@pytest.mark.parametrize(("metodo", "rota"), ROTAS_ANTIGAS, ids=[f"{m} {r}" for m, r in ROTAS_ANTIGAS])
def test_rota_antiga_de_compra_responde_404(metodo: str, rota: str):
    arquivo = SimpleUploadedFile("compras.csv", CSV_DE_COMPRAS, content_type="text/csv")

    resposta = getattr(_superusuario(), metodo)(rota, {"file": arquivo}, format="multipart")

    assert resposta.status_code == 404, f"{metodo.upper()} {rota} respondeu {resposta.status_code}"


def test_import_de_acoes_que_ficou_segue_gravando():
    projeto = ProjetoFactory()
    MunicipioFactory(nome="Acarape", uf="CE")
    csv_de_acoes = "Município,Projeto,Coordenador,Data Entrega\nAcarape,{},,2025-01-15\n".format(projeto.nome)
    arquivo = SimpleUploadedFile("acoes.csv", csv_de_acoes.encode(), content_type="text/csv")

    resposta = _superusuario().post("/api/controle/import-acoes/?dry_run=false", {"file": arquivo}, format="multipart")

    assert resposta.status_code == 200, resposta.content
    assert DATAcao.objects.count() == 1


def test_model_compra_nao_existe_mais():
    with pytest.raises(LookupError):
        apps.get_model("core", "Compra")


def test_tabela_core_compra_nao_existe_mais():
    assert "core_compra" not in connection.introspection.table_names()
    assert "core_dat_compra" in connection.introspection.table_names()  # controle positivo: a lista atual fica


def test_admin_nao_registra_compra_antiga():
    registrados = {model._meta.label for model in admin_site._registry}

    assert "core.Compra" not in registrados
    assert "core.Deslocamento" in registrados  # controle positivo


def test_policies_nao_trazem_import_compras():
    resposta = _superusuario().get(reverse("core:me-policies"))

    assert resposta.status_code == 200
    assert "import_compras" not in resposta.json()
    assert "import_compras" not in PUBLIC_POLICY_KEYS
    assert "manage_purchases_and_materials" in resposta.json()  # controle positivo: a da lista atual fica
