# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false
"""
Regression tests for explicit boundary between core_compra and dat_compra domains.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from rest_framework.test import APIClient

import pytest

from apps.core.models import Compra, DATCompra, Municipio, Projeto, Usuario
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def controle_user() -> Usuario:
    user = UsuarioFactory(username="controle_boundary", password="test123", cpf="20000000001")
    group = GroupFactory(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def dat_user() -> Usuario:
    user = UsuarioFactory(username="dat_boundary", password="test123", cpf="20000000002")
    group = GroupFactory(name="DAT")
    user.groups.add(group)
    return user


@pytest.fixture
def municipio() -> Municipio:
    return MunicipioFactory(nome="Fortaleza", uf="CE")


@pytest.fixture
def projeto() -> Projeto:
    return ProjetoFactory(nome="Projeto Fronteira")


@pytest.fixture
def compra_core(municipio: Municipio, projeto: Projeto) -> Compra:
    return Compra.objects.create(
        codigo="CORE-001",
        projeto=projeto,
        municipio=municipio,
        quantidade=7,
        data=date(2026, 3, 1),
        uso="Libera solicitacao",
        external_hash="c" * 64,
    )


@pytest.fixture
def compra_dat(municipio: Municipio, projeto: Projeto, dat_user: Usuario) -> DATCompra:
    return DATCompra.objects.create(
        municipio=municipio,
        projeto=projeto,
        quantidade=20,
        quantidade_utilizada=5,
        valor_unitario=Decimal("12.34"),
        ano_uso=2026,
        created_by=dat_user,
    )


def _records(data):  # type: ignore[return-type]
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return list(data) if not isinstance(data, list) else data


def test_controle_endpoint_exposes_core_compra_contract(
    api_client: APIClient,
    controle_user: Usuario,
    compra_core: Compra,
    compra_dat: DATCompra,
) -> None:
    api_client.force_authenticate(user=controle_user)
    response = api_client.get("/api/controle/compras/", secure=True)

    assert response.status_code == 200
    records = _records(response.data)
    core_record = next(item for item in records if item["codigo"] == compra_core.codigo)

    assert core_record["quantidade"] == 7
    assert "valor" not in core_record
    assert core_record["municipio"] == compra_core.municipio.nome


def test_dat_endpoint_exposes_dat_compra_contract(
    api_client: APIClient,
    dat_user: Usuario,
    compra_dat: DATCompra,
) -> None:
    api_client.force_authenticate(user=dat_user)
    response = api_client.get("/api/dat/compras-materiais/", secure=True)

    assert response.status_code == 200
    records = _records(response.data)
    dat_record = next(item for item in records if item["id"] == compra_dat.id)

    assert dat_record["quantidade"] == 20
    assert "valor_unitario" in dat_record
    assert dat_record["municipio_nome"] == compra_dat.municipio.nome


def test_controle_user_can_access_dat_compra_domain(
    api_client: APIClient,
    controle_user: Usuario,
) -> None:
    """Issue #1220 (Epic 1): setor Controle tem `run_daily_operations` e
    agora acessa DAT Compras via composition OR. Antes (pré-Epic 1 realignment)
    era 403 porque DAT Compras exigia só `manage_admin_registries`."""
    api_client.force_authenticate(user=controle_user)
    response = api_client.get("/api/dat/compras-materiais/", secure=True)
    assert response.status_code == 200


def test_dat_user_cannot_access_controle_compra_domain(
    api_client: APIClient,
    dat_user: Usuario,
) -> None:
    api_client.force_authenticate(user=dat_user)
    response = api_client.get("/api/controle/compras/", secure=True)
    assert response.status_code == 403
