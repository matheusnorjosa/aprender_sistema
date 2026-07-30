"""
Tests for municipios import service side effects.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.core.cache import cache

import pytest

from apps.core.models import Municipio
from apps.core.services.municipios_import import import_municipios_from_file
from apps.core.services.options_cache import MUNICIPIOS_OPTIONS_CACHE_KEY

pytestmark = pytest.mark.django_db


def test_import_municipios_apply_invalidates_options_cache(tmp_path):
    csv_path = tmp_path / "municipios.csv"
    csv_path.write_text("nome,uf,ibge_code\nFortaleza,CE,2304400\n", encoding="utf-8")
    cache.set(MUNICIPIOS_OPTIONS_CACHE_KEY, [{"id": 999, "nome": "stale", "uf": "XX"}], timeout=300)

    report = import_municipios_from_file(path=str(csv_path), dry_run=False)

    assert report["stats"]["created"] == 1
    assert Municipio.objects.filter(nome="Fortaleza", uf="CE", ibge_code="2304400").exists()
    assert cache.get(MUNICIPIOS_OPTIONS_CACHE_KEY) is None


def test_unexpected_row_error_does_not_leak_exception_message(tmp_path, monkeypatch):
    """CodeQL py/stack-trace-exposure: a mensagem crua de uma excecao inesperada
    por linha nao pode voltar ao cliente no relatorio de pendencias.
    """
    import json

    from apps.core.imports.row_errors import MENSAGEM_ERRO_LINHA
    from apps.core.services import municipios_import

    sentinel = "LEAK_pg_UniqueViolation_municipio_pkey_SECRET_42"

    def _boom(*_args, **_kwargs):
        raise RuntimeError(sentinel)

    monkeypatch.setattr(municipios_import, "_process_row", _boom)

    csv_path = tmp_path / "municipios.csv"
    csv_path.write_text("nome,uf\nFortaleza,CE\n", encoding="utf-8")

    report = import_municipios_from_file(path=str(csv_path), dry_run=True)

    outros = report["pendencias"]["outros"]
    assert len(outros) == 1
    assert outros[0]["erro"] == MENSAGEM_ERRO_LINHA
    # a mensagem crua da excecao nao pode aparecer em nenhum campo do relatorio
    assert sentinel not in json.dumps(report, default=str)
