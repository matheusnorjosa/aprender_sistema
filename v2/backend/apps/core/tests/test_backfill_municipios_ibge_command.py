"""
Testes do comando backfill_municipios_ibge.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from io import StringIO

from django.core.management import call_command

import pytest

from apps.core.models import Municipio, MunicipioReferencia

pytestmark = pytest.mark.django_db


def test_backfill_municipios_ibge_dry_run_does_not_persist():
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code=None)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("backfill_municipios_ibge", stdout=out)

    municipio.refresh_from_db()
    assert municipio.ibge_code is None
    text = out.getvalue()
    assert "would_update=1" in text
    assert "updated=0" in text


def test_backfill_municipios_ibge_apply_persists_unique_match():
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ibge_code=None)
    MunicipioReferencia.objects.create(
        nome="Fortaleza",
        uf="CE",
        codigo_externo="2304400",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("backfill_municipios_ibge", "--apply", stdout=out)

    municipio.refresh_from_db()
    assert municipio.ibge_code == "2304400"
    text = out.getvalue()
    assert "match_unico=1" in text
    assert "updated=1" in text


def test_backfill_municipios_ibge_apply_detects_ambiguous_normalized_names():
    municipio = Municipio.objects.create(nome="Santo Antonio", uf="CE", ibge_code=None)
    MunicipioReferencia.objects.create(
        nome="Santo Antônio",
        uf="CE",
        codigo_externo="2300001",
        fonte="ibge",
        ativo=True,
    )
    MunicipioReferencia.objects.create(
        nome="Santo Antonio",
        uf="CE",
        codigo_externo="2300002",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("backfill_municipios_ibge", "--apply", stdout=out)

    municipio.refresh_from_db()
    assert municipio.ibge_code is None
    text = out.getvalue()
    assert "ambiguos=1" in text
    assert "updated=0" in text


def test_backfill_municipios_ibge_apply_detects_conflict_with_existing_code():
    Municipio.objects.create(nome="Aquiraz", uf="CE", ibge_code="2301000")
    target = Municipio.objects.create(nome="Eusébio", uf="CE", ibge_code=None)
    MunicipioReferencia.objects.create(
        nome="Eusébio",
        uf="CE",
        codigo_externo="2301000",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("backfill_municipios_ibge", "--apply", stdout=out)

    target.refresh_from_db()
    assert target.ibge_code is None
    text = out.getvalue()
    assert "conflitos_codigo_existente=1" in text
    assert "updated=0" in text


def test_backfill_municipios_ibge_apply_matches_without_accents():
    target = Municipio.objects.create(nome="Sao Paulo", uf="SP", ibge_code=None)
    MunicipioReferencia.objects.create(
        nome="São Paulo",
        uf="SP",
        codigo_externo="3550308",
        fonte="ibge",
        ativo=True,
    )

    out = StringIO()
    call_command("backfill_municipios_ibge", "--apply", stdout=out)

    target.refresh_from_db()
    assert target.ibge_code == "3550308"
