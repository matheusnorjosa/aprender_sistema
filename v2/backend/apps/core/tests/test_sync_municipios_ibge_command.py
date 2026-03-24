"""
Testes do comando sync_municipios_ibge.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import gzip
import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command

import pytest

from apps.core.models import MunicipioReferencia

pytestmark = pytest.mark.django_db


class _FakeHTTPResponse:
    def __init__(self, payload: list[dict[str, object]], *, gzip_enabled: bool = True):
        raw = json.dumps(payload).encode("utf-8")
        if gzip_enabled:
            self._raw = gzip.compress(raw)
            self.headers = {"Content-Encoding": "gzip"}
        else:
            self._raw = raw
            self.headers = {"Content-Encoding": ""}

    def read(self) -> bytes:
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _payload_nivelado() -> list[dict[str, object]]:
    return [
        {"municipio-id": 2304400, "municipio-nome": "Fortaleza", "UF-sigla": "CE"},
        {"municipio-id": 2303709, "municipio-nome": "Caucaia", "UF-sigla": "CE"},
    ]


@patch("apps.core.management.commands.sync_municipios_ibge.urlopen")
def test_sync_municipios_ibge_dry_run_does_not_persist(mock_urlopen):
    mock_urlopen.return_value = _FakeHTTPResponse(_payload_nivelado())

    out = StringIO()
    call_command("sync_municipios_ibge", stdout=out)

    assert MunicipioReferencia.objects.filter(fonte="ibge").count() == 0
    text = out.getvalue()
    assert "[DRY-RUN]" in text
    assert "created=2" in text
    assert "total_db_source=0" in text


@patch("apps.core.management.commands.sync_municipios_ibge.urlopen")
def test_sync_municipios_ibge_apply_creates_rows(mock_urlopen):
    mock_urlopen.return_value = _FakeHTTPResponse(_payload_nivelado())

    out = StringIO()
    call_command("sync_municipios_ibge", "--apply", stdout=out)

    assert MunicipioReferencia.objects.filter(fonte="ibge").count() == 2
    assert MunicipioReferencia.objects.filter(fonte="ibge", codigo_externo="2304400", nome="Fortaleza").exists()
    text = out.getvalue()
    assert "[APPLY]" in text
    assert "created=2" in text


@patch("apps.core.management.commands.sync_municipios_ibge.urlopen")
def test_sync_municipios_ibge_apply_updates_existing_row(mock_urlopen):
    MunicipioReferencia.objects.create(
        fonte="ibge",
        codigo_externo="2304400",
        nome="Fortaleza Velha",
        uf="CE",
        ativo=False,
    )
    mock_urlopen.return_value = _FakeHTTPResponse(
        [{"municipio-id": 2304400, "municipio-nome": "Fortaleza", "UF-sigla": "CE"}]
    )

    out = StringIO()
    call_command("sync_municipios_ibge", "--apply", stdout=out)

    ref = MunicipioReferencia.objects.get(fonte="ibge", codigo_externo="2304400")
    assert ref.nome == "Fortaleza"
    assert ref.ativo is True
    text = out.getvalue()
    assert "updated=1" in text


@patch("apps.core.management.commands.sync_municipios_ibge.urlopen")
def test_sync_municipios_ibge_ignores_invalid_rows(mock_urlopen):
    mock_urlopen.return_value = _FakeHTTPResponse(
        [
            {"municipio-id": 2304400, "municipio-nome": "Fortaleza", "UF-sigla": "CE"},
            {"municipio-id": "ABC", "municipio-nome": "Invalido", "UF-sigla": "CE"},
            {"municipio-id": 2300001, "municipio-nome": "Sem UF"},
        ]
    )

    out = StringIO()
    call_command("sync_municipios_ibge", "--apply", stdout=out)

    assert MunicipioReferencia.objects.filter(fonte="ibge").count() == 1
    text = out.getvalue()
    assert "invalid_rows=2" in text
    assert "created=1" in text


@patch("apps.core.management.commands.sync_municipios_ibge.urlopen")
def test_sync_municipios_ibge_supports_legacy_payload(mock_urlopen):
    mock_urlopen.return_value = _FakeHTTPResponse(
        [
            {
                "id": 3550308,
                "nome": "São Paulo",
                "microrregiao": {"mesorregiao": {"UF": {"sigla": "SP"}}},
            }
        ],
        gzip_enabled=False,
    )

    out = StringIO()
    call_command("sync_municipios_ibge", "--apply", stdout=out)

    assert MunicipioReferencia.objects.filter(
        fonte="ibge", codigo_externo="3550308", nome="São Paulo", uf="SP"
    ).exists()
    text = out.getvalue()
    assert "created=1" in text
