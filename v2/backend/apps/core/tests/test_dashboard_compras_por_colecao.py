"""Dashboard de compras: "Coleções ativas" e "Quantidade por Coleção" contam a FAMÍLIA do projeto.

Regra do dono (P1, 05/10/2026): coleção é a obra, que no sistema é a família (`ProjetoGeral`). O
cadastro `Colecao` (vazio em produção) saiu; o dashboard, que lia `produto__colecao` e por isso só
mostrava "Sem coleção", passa a agrupar pela família do projeto da compra.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework import status

from apps.core.models import DATCompra, ProjetoGeral
from apps.core.tests.factories import ProjetoFactory
from apps.core.tests.test_dat_module import DATModuleAPITestCase

DASHBOARD_URL = "/api/dat/compras-materiais/dashboard/"


class DashboardComprasPorColecaoTests(DATModuleAPITestCase):
    def _compra(self, projeto, quantidade: int) -> None:
        DATCompra.objects.create(
            municipio=self.municipio,
            projeto=projeto,
            descricao_produto="Kit",
            quantidade=quantidade,
            ano_uso=2026,
            created_by=self.dat_user,
        )

    def test_agrupa_pela_familia_do_projeto_da_compra(self):
        catavento = ProjetoGeral.objects.create(nome="COLECAO CATAVENTO")
        acerta = ProjetoGeral.objects.create(nome="COLECAO ACERTA")
        # Duas séries da mesma coleção somam numa barra só.
        self._compra(ProjetoFactory(nome="Catavento 2", projeto_geral=catavento), 30)
        self._compra(ProjetoFactory(nome="Catavento 3", projeto_geral=catavento), 20)
        self._compra(ProjetoFactory(nome="ACerta Mat", projeto_geral=acerta), 40)
        self._compra(ProjetoFactory(nome="Avulso sem coleção", projeto_geral=None), 10)

        self.client.force_authenticate(user=self.dat_user)
        r = self.client.get(DASHBOARD_URL)

        assert r.status_code == status.HTTP_200_OK, r.status_code
        assert r.data["kpis"]["colecoes_diferentes"] == 2
        assert r.data["por_colecao"] == [
            {"colecao": "COLECAO CATAVENTO", "quantidade": 50, "percentual": 50.0},
            {"colecao": "COLECAO ACERTA", "quantidade": 40, "percentual": 40.0},
            {"colecao": "Sem coleção", "quantidade": 10, "percentual": 10.0},
        ]
