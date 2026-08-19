"""
M01-07 (#1612) — /usuarios-admin/ honra ?page_size (não capa em 100).

O `UsuarioAdminViewSet` herdava o paginador global (`PageNumberPagination`,
PAGE_SIZE=100, SEM page_size_query_param) — `?page_size=1000` era ignorado e a
lista capava em 100. A tela de grupos deriva a membership da lista de usuários e
salva por full-replace (`sync-members`); com a lista truncada, membros além dos
100 primeiros (por username) eram revogados em silêncio ao salvar o grupo.

Fix: `pagination_class = LargePagination` (page_size_query_param, max 1000) —
o frontend já pede ?page_size=1000, agora recebe todos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

BULK = 130  # > 100 (cap do paginador global) para provar que o teto foi removido


@pytest.fixture
def superuser():
    return UsuarioFactory(username="zz_su_1612", superuser=True)


@pytest.fixture
def bulk_users():
    return [UsuarioFactory(username=f"bulk_{i:04d}") for i in range(BULK)]


class TestUsuariosAdminPagination:
    def test_page_size_1000_retorna_todos(self, superuser, bulk_users):
        """RED: paginador global ignora ?page_size e capa em 100."""
        client = APIClient()
        client.force_authenticate(superuser)
        resp = client.get("/api/usuarios-admin/?page_size=1000", secure=True)
        assert resp.status_code == 200
        returned = [u for u in resp.data["results"] if u["username"].startswith("bulk_")]
        assert len(returned) == BULK, f"esperado {BULK} bulk, veio {len(returned)}"

    def test_ultimo_membro_por_username_presente(self, superuser, bulk_users):
        """O membro que ordena por último (bulk_0129) precisa aparecer — é ele que
        era truncado e revogado no save do grupo."""
        client = APIClient()
        client.force_authenticate(superuser)
        resp = client.get("/api/usuarios-admin/?page_size=1000", secure=True)
        usernames = {u["username"] for u in resp.data["results"]}
        assert f"bulk_{BULK - 1:04d}" in usernames
