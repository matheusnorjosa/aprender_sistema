"""
Scan de segurança 16/10/2026 — F3: `/api/availability/check-many/` sem teto.

`usuarios_ids` tem teto de 50 (400 acima), cada item tem de ser inteiro positivo (400 se não for),
os ids repetidos contam uma vez e as contas vêm numa consulta só (`filter(pk__in=...)`).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

URL = "/api/availability/check-many/"


@pytest.fixture
def cliente(db) -> APIClient:
    """Superusuário: alcance global, para o teste olhar só a forma da lista (F3), não o escopo (F4)."""
    client = APIClient()
    client.force_authenticate(UsuarioFactory(is_superuser=True))
    return client


def _corpo(ids: Any) -> dict[str, Any]:
    inicio = timezone.now() + timedelta(days=5)
    return {"usuarios_ids": ids, "inicio": inicio.isoformat(), "fim": (inicio + timedelta(hours=2)).isoformat()}


@pytest.mark.django_db
class TestListaDeIds:
    def test_acima_do_teto_da_400(self, cliente):
        resp = cliente.post(URL, _corpo(list(range(1, 52))), format="json")
        assert resp.status_code == 400

    def test_no_teto_passa(self, cliente):
        resp = cliente.post(URL, _corpo(list(range(10_000_001, 10_000_051))), format="json")
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 50

    def test_repeticao_conta_uma_vez_antes_do_teto(self, cliente):
        """200 mil vezes o mesmo id era o ataque; repetido não passa do teto mesmo deduplicado depois."""
        resp = cliente.post(URL, _corpo([1] * 51), format="json")
        assert resp.status_code == 400

    @pytest.mark.parametrize("item", ["12", None, {"id": 1}, [1], True, 1.5, 0, -3])
    def test_item_que_nao_e_inteiro_positivo_da_400(self, cliente, item):
        resp = cliente.post(URL, _corpo([item]), format="json")
        assert resp.status_code == 400, resp.content

    def test_ids_repetidos_dao_um_resultado(self, cliente):
        alvo = UsuarioFactory()
        resp = cliente.post(URL, _corpo([alvo.id, alvo.id, alvo.id]), format="json")
        assert resp.status_code == 200
        assert [r["usuario_id"] for r in resp.json()["results"]] == [alvo.id]

    def test_inexistentes_custam_uma_consulta(self, cliente):
        """As contas vêm num `filter(pk__in=...)`, não num `get` por item."""

        def _contar(ids: list[int]) -> int:
            with CaptureQueriesContext(connection) as ctx:
                resp = cliente.post(URL, _corpo(ids), format="json")
            assert resp.status_code == 200
            assert all(r["conflicts"][0]["code"] == "X" for r in resp.json()["results"])
            return len(ctx.captured_queries)

        _contar([20_000_000])  # aquece caches
        assert _contar(list(range(20_000_001, 20_000_041))) == _contar([20_000_000])
