"""
Tests for municipio cache invalidation through the admin API.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.services.options_cache import MUNICIPIOS_OPTIONS_CACHE_KEY
from apps.core.tests.factories import MunicipioFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def usuario_dat():
    return UsuarioFactory(groups=["DAT"])


def test_dat_create_municipio_invalidates_options_cache(api_client, usuario_dat):
    cache.set(MUNICIPIOS_OPTIONS_CACHE_KEY, [{"id": 1, "nome": "stale", "uf": "XX"}], timeout=300)

    api_client.force_authenticate(user=usuario_dat)
    payload = {"nome": "Caucaia", "uf": "CE", "ibge_code": "2303709", "ativo": True}
    response = api_client.post("/api/municipios/", payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert cache.get(MUNICIPIOS_OPTIONS_CACHE_KEY) is None


def test_dat_update_municipio_invalidates_options_cache(api_client, usuario_dat):
    municipio = MunicipioFactory(nome="Caucaia", uf="CE", ibge_code="2303709", ativo=True)
    cache.set(MUNICIPIOS_OPTIONS_CACHE_KEY, [{"id": municipio.id, "nome": "stale", "uf": "CE"}], timeout=300)

    api_client.force_authenticate(user=usuario_dat)
    response = api_client.patch(f"/api/municipios/{municipio.id}/", {"ativo": False}, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert cache.get(MUNICIPIOS_OPTIONS_CACHE_KEY) is None


def test_dat_delete_municipio_invalidates_options_cache(api_client, usuario_dat):
    municipio = MunicipioFactory(nome="Caucaia", uf="CE", ibge_code="2303709", ativo=True)
    cache.set(MUNICIPIOS_OPTIONS_CACHE_KEY, [{"id": municipio.id, "nome": "stale", "uf": "CE"}], timeout=300)

    api_client.force_authenticate(user=usuario_dat)
    response = api_client.delete(f"/api/municipios/{municipio.id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert cache.get(MUNICIPIOS_OPTIONS_CACHE_KEY) is None
