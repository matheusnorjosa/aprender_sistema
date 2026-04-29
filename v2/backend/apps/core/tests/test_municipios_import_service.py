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
