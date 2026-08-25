"""Opção A #1837 · Wave 2 — CR-03: separar APPLIABLE de IMPLEMENTED.

`--allow-entity` que aponta uma entidade classificável mas NÃO-escrivível (ex.: `produto`,
`gerencia` — em IMPLEMENTED, sem apply → grava 0 calado) deve levantar CommandError, em vez de
mentir "applied=0" (fecha M17-09/M18-09/M19-10/M22-06).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.core.services.export_contract_importer import APPLIABLE, IMPLEMENTED


def _empty_export(tmp_path) -> str:
    d = tmp_path / "e"
    d.mkdir()
    (d / "manifest.json").write_text('{"entities": {}}', encoding="utf-8")
    return str(d)


def test_appliable_subset_of_implemented():
    # produto/gerencia classificam mas não têm apply → fora de APPLIABLE; dat_coordenador entrou.
    assert APPLIABLE <= IMPLEMENTED
    assert "produto" in IMPLEMENTED and "produto" not in APPLIABLE
    assert "gerencia" in IMPLEMENTED and "gerencia" not in APPLIABLE
    assert "dat_coordenador" in APPLIABLE


def test_allow_nonappliable_raises(tmp_path):
    with pytest.raises(CommandError):
        call_command(
            "import_export_contract", "--path", _empty_export(tmp_path), "--apply", "--allow-entity", "produto"
        )


def test_allow_appliable_does_not_raise_command_error(tmp_path):
    # dat_area é escrivível → o CR-03 não barra (a validação roda antes de tocar arquivos).
    try:
        call_command(
            "import_export_contract", "--path", _empty_export(tmp_path), "--apply", "--allow-entity", "dat_area"
        )
    except CommandError as exc:  # não pode ser o erro do CR-03
        assert "não-escrivível" not in str(exc)
