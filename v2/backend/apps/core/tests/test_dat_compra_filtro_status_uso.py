"""G17 (P#26/P#30, B#32): o filtro de status e a ordenação da lista de compras.

A tela mandava ``?status=`` (que o servidor ignora: a lista voltava inteira) e
``ordering=-updated_at`` (fora de ``ordering_fields``: ignorado também). Estes testes fixam o que
o servidor aceita: ``status_uso`` filtra e ``-created_at`` ordena.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from apps.core.models import DATCompra
from apps.core.tests.test_dat_module import DATModuleAPITestCase

COMPRAS_URL = "/api/dat/compras-materiais/"


def _ids(response) -> list[int]:
    data = response.data
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return [r["id"] for r in rows]


class DATCompraFiltroStatusUsoTests(DATModuleAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        agora = timezone.now()
        # status_uso é recalculado no save(): esgotado = tudo usado; em_uso = parte; disponível = nada.
        cls.esgotada = DATCompra.objects.create(
            municipio=cls.municipio,
            projeto=cls.projeto,
            descricao_produto="Esgotada",
            quantidade=10,
            quantidade_utilizada=10,
            ano_uso=2026,
            created_by=cls.dat_user,
            created_at=agora - timedelta(days=2),
        )
        cls.em_uso = DATCompra.objects.create(
            municipio=cls.municipio,
            projeto=cls.projeto,
            descricao_produto="Em uso",
            quantidade=10,
            quantidade_utilizada=4,
            ano_uso=2026,
            created_by=cls.dat_user,
            created_at=agora - timedelta(days=1),
        )
        cls.disponivel = DATCompra.objects.create(
            municipio=cls.municipio,
            projeto=cls.projeto,
            descricao_produto="Disponível",
            quantidade=10,
            quantidade_utilizada=0,
            ano_uso=2026,
            created_by=cls.dat_user,
            created_at=agora,
        )

    def test_status_uso_esgotado_filtra(self):
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.get(COMPRAS_URL, {"status_uso": "esgotado", "municipio_id": self.municipio.id})
        assert r.status_code == status.HTTP_200_OK
        assert _ids(r) == [self.esgotada.id]

    def test_parametro_status_e_ignorado(self):
        # Prova de por que a tela precisa mandar status_uso: ?status= não filtra nada.
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.get(COMPRAS_URL, {"status": "esgotado", "municipio_id": self.municipio.id})
        assert r.status_code == status.HTTP_200_OK
        assert sorted(_ids(r)) == sorted([self.esgotada.id, self.em_uso.id, self.disponivel.id])

    def test_ordering_menos_created_at_traz_a_mais_nova_primeiro(self):
        self.client.force_authenticate(user=self.dat_user)
        r = self.client.get(COMPRAS_URL, {"ordering": "-created_at", "municipio_id": self.municipio.id})
        assert r.status_code == status.HTTP_200_OK
        assert _ids(r) == [self.disponivel.id, self.em_uso.id, self.esgotada.id]
