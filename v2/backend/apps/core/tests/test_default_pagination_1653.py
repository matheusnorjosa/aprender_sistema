# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportArgumentType=false, reportCallIssue=false, reportIndexIssue=false, reportMissingTypeArgument=false, reportOptionalCall=false

"""
#1653: o DEFAULT_PAGINATION_CLASS global deve honrar `?page_size` (com teto),
sem mudar a resposta sem o parâmetro.

Antes era `rest_framework.pagination.PageNumberPagination` cru, que ignorava
`?page_size` e truncava TODA listagem em `PAGE_SIZE` (100). A troca para
`apps.core.pagination.StandardPagination` é aditiva: mesmo default de 100,
mas `?page_size` passa a ser respeitado até `max_page_size=500`.
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.settings import api_settings
from rest_framework.test import APIClient, APIRequestFactory

import pytest

from apps.core.pagination import StandardPagination
from apps.core.tests.factories import MunicipioFactory, UsuarioFactory


def test_default_pagination_honra_page_size_query_param():
    """Sentinela: o default global aceita `?page_size` e tem teto."""
    pager = api_settings.DEFAULT_PAGINATION_CLASS()
    assert pager.page_size_query_param == "page_size"
    assert pager.max_page_size is not None
    # Aditivo: mesmo default de 100 por página (resposta sem-param inalterada).
    assert pager.page_size == api_settings.PAGE_SIZE == 100


def test_standard_pagination_limita_ao_max_page_size():
    """`?page_size` acima do teto é limitado a `max_page_size` (500)."""
    req = Request(APIRequestFactory().get("/", {"page_size": "99999"}))
    assert StandardPagination().get_page_size(req) == 500


@pytest.mark.django_db
def test_list_endpoint_respeita_page_size():
    """Um list endpoint que herda o default passa a devolver `?page_size` itens.

    Antes (PageNumberPagination cru) truncava em 100 ignorando o parâmetro.
    """
    admin = UsuarioFactory(superuser=True)
    for i in range(150):
        MunicipioFactory(nome=f"Cidade Paginacao {i:03d}", uf="CE", ativo=True)

    client = APIClient()
    client.force_authenticate(user=admin)

    # Sem parâmetro: comportamento inalterado (100 por página).
    default_resp = client.get("/api/municipios/")
    assert default_resp.status_code == 200
    assert len(default_resp.data["results"]) == 100

    # Com `?page_size`: honrado (150), não truncado em 100.
    resp = client.get("/api/municipios/?page_size=150")
    assert resp.status_code == 200
    assert len(resp.data["results"]) == 150
