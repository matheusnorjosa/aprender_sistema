# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false
"""
Regression tests for the dat_compra domain contract.

A lista antiga (`core_compra`) saiu de uso em 06/11/2026 (G29): `/api/controle/compras/` e `/api/compras/`
saíram; a prova das rotas antigas = 404 está em `test_compra_antiga_fora_de_uso.py`.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework.test import APIClient

import pytest

from apps.core.models import DATCompra, Municipio, Projeto, Usuario
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    UsuarioFactory,
    com_pacote_do_controle,
    com_pacote_do_dat,
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
    com_pacote_do_controle(user)
    return user


@pytest.fixture
def dat_user() -> Usuario:
    user = UsuarioFactory(username="dat_boundary", password="test123", cpf="20000000002")
    group = GroupFactory(name="DAT")
    user.groups.add(group)
    com_pacote_do_dat(user)
    return user


@pytest.fixture
def municipio() -> Municipio:
    return MunicipioFactory(nome="Fortaleza", uf="CE")


@pytest.fixture
def projeto() -> Projeto:
    return ProjetoFactory(nome="Projeto Fronteira")


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
    # #1637: codigo do produto e' espelho read-only (source="produto.codigo"), nao coluna
    # gravavel por-compra. Deve estar no contrato do DAT (a coluna "Cod:" da tabela o consome).
    assert "codigo_produto" in dat_record
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
