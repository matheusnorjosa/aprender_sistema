"""
Decisão do dono (2026-09-14, diretriz da onda #2): todo campo que o sistema IMPORTA
deve ter home de cadastro DIRETO (write serializer + form), não só o importer.

Produto tem FK `colecao` (nullable), mas o `ProdutoSerializer` (usado no CRUD do
`ProdutoViewSet`) NÃO expunha `colecao` em Meta.fields — logo não havia como
cadastrar/editar a coleção de um produto pela UI. (O import de produto ainda é
not_implemented no export-contract; quando for, gravará colecao — este é o home
de cadastro direto forward-looking.) Aqui a coleção passa a ser cadastrável
diretamente (write) e exibível (`colecao_nome`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import Colecao, Produto
from apps.core.tests.factories import ProjetoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


def _dat_admin() -> object:
    """Superuser: bypassa o gate de CRUD de Produto (o foco do teste é o serializer)."""
    return UsuarioFactory(superuser=True)


class TestProdutoColecaoCadastroDireto:
    def test_criar_produto_persiste_colecao(self):
        projeto = ProjetoFactory(nome="Projeto Colecao", codigo="PCOL")
        colecao = Colecao.objects.create(nome="Coleção A", projeto=projeto)

        client = APIClient()
        client.force_authenticate(_dat_admin())
        resp = client.post(
            "/api/produtos/",
            {"codigo": "TST-COL-1", "nome": "Produto Teste", "projeto": projeto.id, "colecao": colecao.id},
            format="json",
        )

        assert resp.status_code == 201, resp.data
        prod = Produto.objects.get(codigo="TST-COL-1")
        assert prod.colecao_id == colecao.id
        assert resp.data["colecao"] == colecao.id
        assert resp.data["colecao_nome"] == "Coleção A"

    def test_editar_colecao_do_produto(self):
        projeto = ProjetoFactory(nome="Projeto Colecao2", codigo="PCOL2")
        colecao = Colecao.objects.create(nome="Coleção B", projeto=projeto)
        prod = Produto.objects.create(codigo="TST-COL-2", nome="Produto Sem Colecao", projeto=projeto)

        client = APIClient()
        client.force_authenticate(_dat_admin())
        resp = client.patch(f"/api/produtos/{prod.id}/", {"colecao": colecao.id}, format="json")

        assert resp.status_code == 200, resp.data
        prod.refresh_from_db()
        assert prod.colecao_id == colecao.id

    def test_remover_colecao_do_produto(self):
        projeto = ProjetoFactory(nome="Projeto Colecao3", codigo="PCOL3")
        colecao = Colecao.objects.create(nome="Coleção C", projeto=projeto)
        prod = Produto.objects.create(codigo="TST-COL-3", nome="Produto Com Colecao", projeto=projeto, colecao=colecao)

        client = APIClient()
        client.force_authenticate(_dat_admin())
        resp = client.patch(f"/api/produtos/{prod.id}/", {"colecao": None}, format="json")

        assert resp.status_code == 200, resp.data
        prod.refresh_from_db()
        assert prod.colecao_id is None

    def test_options_colecoes_filtra_por_projeto(self):
        projeto_a = ProjetoFactory(nome="Familia A", codigo="FAMA")
        projeto_b = ProjetoFactory(nome="Familia B", codigo="FAMB")
        col_a = Colecao.objects.create(nome="Col A1", projeto=projeto_a)
        Colecao.objects.create(nome="Col B1", projeto=projeto_b)

        client = APIClient()
        client.force_authenticate(UsuarioFactory(username="opt_user", cpf="95000000009"))
        resp = client.get(f"/api/options/colecoes/?projeto={projeto_a.id}")

        assert resp.status_code == 200, resp.data
        ids = {c["id"] for c in resp.data}
        assert ids == {col_a.id}
        assert resp.data[0]["projeto"] == projeto_a.id
