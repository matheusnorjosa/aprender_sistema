"""M15-02 (#1632): invariantes de DATCompra + paridade agregação-x-property do dashboard.

Cobre a FATIA de aplicação (serializer + dashboard) — não as CheckConstraints do banco
(item 2/5, que exigem levantamento + datafix em prod) nem a decisão sobre quantidade=0
(item 3, decisão do dono). Ver o issue #1632.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import uuid
from decimal import Decimal

from rest_framework import status

from apps.core.models import DATCompra
from apps.core.models.organizacao import Produto
from apps.core.tests.factories import ProjetoFactory
from apps.core.tests.test_dat_module import DATModuleAPITestCase

COMPRAS_URL = "/api/dat/compras-materiais/"
DASHBOARD_URL = "/api/dat/compras-materiais/dashboard/"


def _errs(response):
    """Dict de erros de campo — a API embrulha validação em {code, detail, errors: {...}}."""
    data = response.data
    if isinstance(data, dict) and "errors" in data and isinstance(data["errors"], dict):
        return data["errors"]
    return data


class DATCompraInvariantesAPITests(DATModuleAPITestCase):
    """POSTs inválidos devem retornar 400 (não 201) por campo, e o dashboard deve
    concordar com a soma das linhas (clamp por linha)."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        uid = uuid.uuid4().hex[:6]
        cls.produto = Produto.objects.create(codigo=f"INV-{uid}", nome="Produto Inv", projeto=cls.projeto)
        cls.projeto_outro = ProjetoFactory(nome=f"Outro Proj {uid}", codigo=f"OP{uid[:4]}", fluxo="NAO_SUPER")
        cls.produto_outro_projeto = Produto.objects.create(
            codigo=f"OUT-{uid}", nome="Produto Outro", projeto=cls.projeto_outro
        )

    def _payload(self, **overrides):
        base = {
            "municipio": self.municipio.id,
            "projeto": self.projeto.id,
            "produto": self.produto.id,
            "quantidade": 10,
            "quantidade_utilizada": 0,
            "valor_unitario": "5.00",
            "ano_uso": 2026,
        }
        base.update(overrides)
        return base

    def test_post_sobreuso_retorna_400(self):
        """quantidade_utilizada > quantidade → 400 no campo quantidade_utilizada."""
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(COMPRAS_URL, self._payload(quantidade=10, quantidade_utilizada=999), format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, f"aceito com {r.status_code}"
        assert "quantidade_utilizada" in _errs(r)

    def test_post_valor_negativo_retorna_400(self):
        """valor_unitario < 0 → 400 no campo valor_unitario."""
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(COMPRAS_URL, self._payload(valor_unitario="-100.00"), format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, f"aceito com {r.status_code}"
        assert "valor_unitario" in _errs(r)

    def test_post_item_vazio_retorna_400(self):
        """produto None E descricao_produto vazio → 400 (não identifica material)."""
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(COMPRAS_URL, self._payload(produto=None, descricao_produto=""), format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, f"aceito com {r.status_code}"
        assert "descricao_produto" in _errs(r)

    def test_post_produto_de_outro_projeto_retorna_400(self):
        """produto.projeto != projeto da compra → 400 no campo produto."""
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(COMPRAS_URL, self._payload(produto=self.produto_outro_projeto.id), format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST, f"aceito com {r.status_code}"
        assert "produto" in _errs(r)

    def test_post_valido_ainda_passa(self):
        """Não-regressão: payload válido continua 201."""
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(COMPRAS_URL, self._payload(quantidade=10, quantidade_utilizada=3), format="json")
        assert r.status_code == status.HTTP_201_CREATED, f"rejeitou válido: {r.data}"

    def test_dashboard_disponivel_igual_soma_das_linhas(self):
        """O KPI total_disponivel deve bater com a soma das .disponivel.

        Cobre uma linha esgotada (utilizada == quantidade → disponível 0) além da normal.
        Sobreuso (utilizada > quantidade) deixou de ser representável: a CheckConstraint
        `dat_compra_utilizada_lte_quantidade` (M15-02/#1632) o barra no banco.
        """
        # Linha normal: disponível = 10 - 3 = 7
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            produto=self.produto,
            quantidade=10,
            quantidade_utilizada=3,
            valor_unitario=Decimal("5.00"),
            ano_uso=2026,
            created_by=self.dat_user,
        )
        # Linha esgotada: disponível = max(0, 10 - 10) = 0 (utilizada == quantidade)
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=self.projeto,
            produto=self.produto,
            quantidade=10,
            quantidade_utilizada=10,
            valor_unitario=Decimal("1.00"),
            ano_uso=2026,
            created_by=self.dat_user,
        )

        self.client.force_authenticate(user=self.dat_user)
        r = self.client.get(DASHBOARD_URL)
        assert r.status_code == status.HTTP_200_OK, f"dashboard {r.status_code}"

        soma_linhas = sum(c.disponivel for c in DATCompra.objects.all())
        assert (
            r.data["kpis"]["total_disponivel"] == soma_linhas
        ), f"dashboard={r.data['kpis']['total_disponivel']} != soma_das_linhas={soma_linhas}"


class DATCompraProdutoDaMesmaColecaoTests(DATModuleAPITestCase):
    """#1632 (lote E1): a compra ligada a produto de OUTRO livro da MESMA coleção é legítima.

    Em produção (07/11) 1.902 das 2.041 compras com produto estão assim (o import liga o produto
    só pelo código). A validação exigia produto.projeto == compra.projeto e, como valida o estado
    efetivo, recusava com 400 qualquer edição dessas compras pela tela.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from apps.core.models import ProjetoGeral

        uid = uuid.uuid4().hex[:6]
        cls.colecao = ProjetoGeral.objects.create(nome=f"Colecao E1 {uid}")
        cls.colecao_outra = ProjetoGeral.objects.create(nome=f"Colecao E1 outra {uid}")
        cls.livro1 = ProjetoFactory(nome=f"Livro 1 {uid}", codigo=f"L1{uid[:4]}", fluxo="NAO_SUPER")
        cls.livro2 = ProjetoFactory(nome=f"Livro 2 {uid}", codigo=f"L2{uid[:4]}", fluxo="NAO_SUPER")
        cls.livro_outra = ProjetoFactory(nome=f"Livro X {uid}", codigo=f"LX{uid[:4]}", fluxo="NAO_SUPER")
        for p, c in ((cls.livro1, cls.colecao), (cls.livro2, cls.colecao), (cls.livro_outra, cls.colecao_outra)):
            p.projeto_geral = c
            p.save(update_fields=["projeto_geral"])
        cls.produto_livro2 = Produto.objects.create(codigo=f"E1-{uid}", nome="Produto Livro 2", projeto=cls.livro2)
        cls.produto_outra = Produto.objects.create(codigo=f"E1X-{uid}", nome="Produto Outra", projeto=cls.livro_outra)

    def _compra(self, produto):
        return DATCompra.objects.create(
            municipio=self.municipio, projeto=self.livro1, produto=produto,
            quantidade=10, quantidade_utilizada=0, valor_unitario=Decimal("5.00"), ano_uso=2026,
            created_by=self.dat_user,
        )

    def test_patch_de_compra_com_produto_da_mesma_colecao_passa(self):
        """Editar só a quantidade utilizada de uma compra assim deve dar 200 (antes: 400)."""
        compra = self._compra(self.produto_livro2)
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.patch(f"{COMPRAS_URL}{compra.id}/", {"quantidade_utilizada": 2}, format="json")
        assert r.status_code == status.HTTP_200_OK, f"recusou: {r.status_code} {r.data}"
        compra.refresh_from_db()
        assert compra.quantidade_utilizada == 2

    def test_post_com_produto_da_mesma_colecao_passa(self):
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(
            COMPRAS_URL,
            {"municipio": self.municipio.id, "projeto": self.livro1.id, "produto": self.produto_livro2.id,
             "quantidade": 10, "quantidade_utilizada": 0, "valor_unitario": "5.00", "ano_uso": 2026},
            format="json",
        )
        assert r.status_code == status.HTTP_201_CREATED, f"recusou: {r.data}"

    def test_post_com_produto_de_outra_colecao_continua_400(self):
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.post(
            COMPRAS_URL,
            {"municipio": self.municipio.id, "projeto": self.livro1.id, "produto": self.produto_outra.id,
             "quantidade": 10, "quantidade_utilizada": 0, "valor_unitario": "5.00", "ano_uso": 2026},
            format="json",
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "produto" in _errs(r)
