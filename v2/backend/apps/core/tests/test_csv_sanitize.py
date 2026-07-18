"""Testes unitários do helper de sanitização CSV (SEC-007).

Cobertura faltante para `apps.core.utils.csv_sanitize.sanitize_csv_value`, que
neutraliza formula injection prefixando `'` em valores que começam com um dos 7
gatilhos (`= + - @ TAB CR LF`) interpretados por Excel/LibreOffice/Sheets.
"""

from __future__ import annotations

import pytest

from apps.core.utils.csv_sanitize import sanitize_csv_value


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("=cmd", "'=cmd"),
        ("+1", "'+1"),
        ("-1", "'-1"),
        ("@x", "'@x"),
        ("\tfoo", "'\tfoo"),
        ("\rfoo", "'\rfoo"),
        ("\nfoo", "'\nfoo"),
    ],
)
def test_sanitiza_gatilhos_de_formula(raw: str, expected: str) -> None:
    assert sanitize_csv_value(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "Fulano de Tal",
        "a=b",  # '=' no meio não é gatilho (âncora ^)
        "email@dominio.com",  # '@' no meio é benigno
        "123",
        "",
    ],
)
def test_valores_benignos_inalterados(raw: str) -> None:
    assert sanitize_csv_value(raw) == raw


def test_none_vira_string_vazia() -> None:
    assert sanitize_csv_value(None) == ""


def test_numero_convertido_sem_prefixo() -> None:
    assert sanitize_csv_value(42) == "42"
