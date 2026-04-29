"""
Tests for the promote_municipios_referencia command.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from io import StringIO

from django.core.cache import cache
from django.core.management import call_command

import pytest

from apps.core.models import Municipio, MunicipioReferencia
from apps.core.services.options_cache import MUNICIPIOS_OPTIONS_CACHE_KEY

pytestmark = pytest.mark.django_db


def test_promote_municipios_referencia_dry_run_does_not_persist():
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", stdout=out)

    assert Municipio.objects.count() == 0
    text = out.getvalue()
    assert "would_create=1" in text
    assert "created=0" in text
    assert "updated=0" in text


def test_promote_municipios_referencia_apply_creates_rows_and_invalidates_cache():
    cache.set(MUNICIPIOS_OPTIONS_CACHE_KEY, [{"id": 999, "nome": "stale", "uf": "XX"}], timeout=300)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    municipio = Municipio.objects.get(nome="Fortaleza", uf="CE")
    assert municipio.ibge_code == "2304400"
    assert municipio.ativo is True
    assert cache.get(MUNICIPIOS_OPTIONS_CACHE_KEY) is None
    text = out.getvalue()
    assert "created=1" in text
    assert "cache_invalidated=1" in text


def test_promote_municipios_referencia_apply_is_idempotent():
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    first_out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=first_out)
    second_out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=second_out)

    assert Municipio.objects.filter(nome="Fortaleza", uf="CE", ibge_code="2304400").count() == 1
    assert "created=1" in first_out.getvalue()
    second_text = second_out.getvalue()
    assert "would_create=0" in second_text
    assert "would_update=0" in second_text
    assert "unchanged=1" in second_text
    assert "created=0" in second_text
    assert "updated=0" in second_text


def test_promote_municipios_referencia_apply_updates_existing_normalized_match():
    municipio = Municipio.objects.create(nome="Sao Paulo", uf="SP", ibge_code=None, ativo=False)
    MunicipioReferencia.objects.create(
        nome="Sao Paulo",
        uf="SP",
        codigo_externo="3550308",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    municipio.refresh_from_db()
    assert municipio.ibge_code == "3550308"
    assert municipio.ativo is True
    text = out.getvalue()
    assert "would_update=1" in text
    assert "updated=1" in text
    assert municipio.nome == "Sao Paulo"
    assert municipio.uf == "SP"


def test_promote_municipios_referencia_prefers_existing_ibge_code_match():
    Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304400", ativo=False)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    assert Municipio.objects.filter(ibge_code="2304400").count() == 1
    municipio = Municipio.objects.get(ibge_code="2304400")
    assert municipio.nome == "Fortaleza"
    assert municipio.ativo is True
    text = out.getvalue()
    assert "would_update=1" in text
    assert "updated=1" in text


def test_promote_municipios_referencia_does_not_match_by_name_without_uf():
    Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code=None, ativo=True)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="PI",
        codigo_externo="2203909",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    assert Municipio.objects.filter(nome="Fortaleza", uf="CE", ibge_code__isnull=True).exists()
    assert Municipio.objects.filter(nome="Fortaleza", uf="PI", ibge_code="2203909").exists()
    assert "created=1" in out.getvalue()


def test_promote_municipios_referencia_default_ignores_inactive_refs():
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=False,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", stdout=out)

    assert Municipio.objects.count() == 0
    text = out.getvalue()
    assert "referencias_lidas=0" in text
    assert "ignored_inactive_refs=1" in text
    assert "would_create=0" in text


def test_promote_municipios_referencia_include_inactive_refs_creates_inactive_rows():
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=False,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", "--include-inactive-ref", stdout=out)

    municipio = Municipio.objects.get(nome="Fortaleza", uf="CE")
    assert municipio.ibge_code == "2304400"
    assert municipio.ativo is False
    text = out.getvalue()
    assert "ignored_inactive_refs=0" in text
    assert "created=1" in text


def test_promote_municipios_referencia_apply_detects_code_owned_by_other():
    Municipio.objects.create(nome="Aquiraz", uf="CE", ibge_code="2301000", ativo=True)
    MunicipioReferencia.objects.create(
        nome="Eusebio",
        uf="CE",
        codigo_externo="2301000",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    assert not Municipio.objects.filter(nome="Eusebio", uf="CE").exists()
    text = out.getvalue()
    assert "conflicts_code_owned_by_other=1" in text
    assert "created=0" in text


def test_promote_municipios_referencia_apply_detects_ambiguous_existing_candidates():
    Municipio.objects.create(nome="Santo Antonio", uf="CE", ibge_code=None, ativo=True)
    Municipio.objects.create(nome="Santo Antônio", uf="CE", ibge_code=None, ativo=True)
    MunicipioReferencia.objects.create(
        nome="Santo Antonio",
        uf="CE",
        codigo_externo="2300001",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    assert Municipio.objects.filter(ibge_code="2300001").count() == 0
    text = out.getvalue()
    assert "conflicts_ambiguous_existing=1" in text


def test_promote_municipios_referencia_apply_detects_mismatched_existing_code():
    Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code="2304401", ativo=True)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("promote_municipios_referencia", "--apply", stdout=out)

    assert Municipio.objects.filter(ibge_code="2304400").count() == 0
    assert Municipio.objects.filter(nome="Fortaleza", uf="CE", ibge_code="2304401").exists()
    text = out.getvalue()
    assert "conflicts_mismatched_existing_code=1" in text
    assert "created=0" in text
    assert "updated=0" in text


def test_promote_municipios_referencia_apply_rolls_back_all_changes_on_failure(monkeypatch):
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )
    MunicipioReferencia.objects.create(
        nome="Caucaia",
        uf="CE",
        codigo_externo="2303709",
        fonte="ibge",
        ativo=True,
    )
    original_create = Municipio.objects.create

    def failing_bulk_create(objs, batch_size=None):
        first = objs[0]
        original_create(nome=first.nome, uf=first.uf, ibge_code=first.ibge_code, ativo=first.ativo)
        raise RuntimeError("forced failure")

    monkeypatch.setattr(Municipio.objects, "bulk_create", failing_bulk_create)

    with pytest.raises(RuntimeError, match="forced failure"):
        call_command("promote_municipios_referencia", "--apply", stdout=StringIO())

    assert Municipio.objects.count() == 0
