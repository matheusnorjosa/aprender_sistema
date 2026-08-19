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


def test_dat_user_cannot_access_controle_compra_domain(
    api_client: APIClient,
    dat_user: Usuario,
) -> None:
    api_client.force_authenticate(user=dat_user)
    response = api_client.get("/api/controle/compras/", secure=True)
    assert response.status_code == 403


# ===================================================================
# M15-03 (#1633) — external_hash imutável no PATCH + quantidade > 0
# ===================================================================


def _errs(response):
    """Dict de erros de campo — a API embrulha validação em {code, detail, errors: {...}}."""
    data = response.data
    if isinstance(data, dict) and "errors" in data and isinstance(data["errors"], dict):
        return data["errors"]
    return data


def test_patch_nao_reescreve_external_hash(
    api_client: APIClient,
    dat_user: Usuario,
    compra_core: Compra,
) -> None:
    """M15-03 (#1633): external_hash é a chave de idempotência de import — imutável após
    a criação. Um PATCH não pode reescrevê-la (quebraria a idempotência de imports futuros).

    RED: hoje o PATCH reescreve o hash e retorna 200 com o valor forjado.
    """
    api_client.force_authenticate(user=dat_user)
    original = compra_core.external_hash
    response = api_client.patch(
        f"/api/compras/{compra_core.id}/", {"external_hash": "f" * 64}, format="json", secure=True
    )
    assert response.status_code == 200
    compra_core.refresh_from_db()
    assert compra_core.external_hash == original  # RED: virava "f"*64


def test_post_quantidade_zero_retorna_400(
    api_client: APIClient,
    dat_user: Usuario,
    municipio: Municipio,
    projeto: Projeto,
) -> None:
    """M15-03: compra de estoque zero é inválida (habilitava solicitação com estoque zerado).

    RED: hoje quantidade=0 é aceito com 201 (validate_quantidade só barra negativo).
    """
    api_client.force_authenticate(user=dat_user)
    payload = {
        "codigo": "ZERO-001",
        "projeto": projeto.id,
        "municipio": municipio.id,
        "quantidade": 0,
        "data": "2026-03-01",
        "uso": "teste",
        "external_hash": "a" * 64,
    }
    response = api_client.post("/api/compras/", payload, format="json", secure=True)
    assert response.status_code == 400, f"aceito com {response.status_code}"
    assert "quantidade" in _errs(response)


def test_patch_campo_normal_ok_hash_intacto(
    api_client: APIClient,
    dat_user: Usuario,
    compra_core: Compra,
) -> None:
    """Não-regressão: PATCH de campo normal funciona e o external_hash fica intacto."""
    api_client.force_authenticate(user=dat_user)
    original = compra_core.external_hash
    response = api_client.patch(f"/api/compras/{compra_core.id}/", {"quantidade": 9}, format="json", secure=True)
    assert response.status_code == 200
    compra_core.refresh_from_db()
    assert compra_core.quantidade == 9
    assert compra_core.external_hash == original
