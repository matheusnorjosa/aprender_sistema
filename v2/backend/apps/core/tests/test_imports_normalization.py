"""
Equivalence tests for ``apps.core.imports.normalization``.

Each test pins the helper output against the legacy inline pattern that it
replaces, so any future change that breaks byte-equivalence fails CI.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import re

import pytest

from apps.core.imports.normalization import (
    normalize_active_flag,
    normalize_blank,
    normalize_cpf_digits,
    normalize_uf,
)

# ---------------------------------------------------------------------------
# normalize_blank
# ---------------------------------------------------------------------------


def _legacy_blank(val):
    """Inline pattern previously repeated ~80x across services."""
    return str(val).strip() if val and str(val) != "nan" else ""


class TestNormalizeBlank:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, ""),
            ("", ""),
            (0, ""),
            (0.0, ""),
            (False, ""),
            ("nan", ""),
            (" x ", "x"),
            ("x", "x"),
            (123, "123"),
            ("0", "0"),
            ("False", "False"),
            ("\tabc\n", "abc"),
            ("  hello world  ", "hello world"),
        ],
    )
    def test_matches_expected(self, val, expected):
        assert normalize_blank(val) == expected

    @pytest.mark.parametrize(
        "val",
        [None, "", 0, 0.0, False, "nan", " x ", "x", 123, "0", "False", "\tabc\n"],
    )
    def test_byte_equivalent_to_legacy_pattern(self, val):
        assert normalize_blank(val) == _legacy_blank(val)


# ---------------------------------------------------------------------------
# normalize_active_flag
# ---------------------------------------------------------------------------


def _legacy_active(val):
    """Inline pattern previously repeated 5x across services."""
    val_str = str(val).strip().lower() if val and str(val) != "nan" else ""
    return val_str not in ("nao", "não", "false", "0", "inativo", "n")


class TestNormalizeActiveFlag:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, True),
            ("", True),
            ("nan", True),
            ("sim", True),
            ("Sim", True),
            ("YES", True),
            ("True", True),
            ("1", True),
            ("ativo", True),
            ("nao", False),
            ("Não", False),
            ("NAO", False),
            ("false", False),
            ("False", False),
            ("0", False),
            ("inativo", False),
            ("n", False),
            ("N", False),
        ],
    )
    def test_matches_expected(self, val, expected):
        assert normalize_active_flag(val) is expected

    @pytest.mark.parametrize(
        "val",
        [None, "", "nan", "sim", "Sim", "YES", "True", "ativo", "nao", "Não", "false", "0", "inativo", "N"],
    )
    def test_byte_equivalent_to_legacy_pattern(self, val):
        assert normalize_active_flag(val) is _legacy_active(val)

    def test_default_false_when_blank(self):
        assert normalize_active_flag(None, default=False) is False
        assert normalize_active_flag("", default=False) is False
        # Non-blank still resolves on its own merits regardless of default
        assert normalize_active_flag("nao", default=True) is False
        assert normalize_active_flag("sim", default=False) is True


# ---------------------------------------------------------------------------
# normalize_uf
# ---------------------------------------------------------------------------


def _legacy_uf(val):
    """Inline pattern previously used in municipios_import."""
    return str(val).strip().upper() if val and str(val) != "nan" else ""


class TestNormalizeUf:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("ce", "CE"),
            (" CE ", "CE"),
            ("sp", "SP"),
            (None, ""),
            ("", ""),
            ("nan", ""),
            ("Ceará", "CEARÁ"),  # No truncation — caller's concern
        ],
    )
    def test_matches_expected(self, val, expected):
        assert normalize_uf(val) == expected

    @pytest.mark.parametrize("val", ["ce", " CE ", "sp", None, "", "nan", "Ceará"])
    def test_byte_equivalent_to_legacy_pattern(self, val):
        assert normalize_uf(val) == _legacy_uf(val)


# ---------------------------------------------------------------------------
# normalize_cpf_digits
# ---------------------------------------------------------------------------


def _legacy_cpf_regex(cpf):
    """Pattern from usuarios_import._clean_cpf."""
    return re.sub(r"[^\d]", "", cpf)


def _legacy_cpf_isdigit(cpf):
    """Pattern from equipe_gerencia_import._resolve_usuario / _resolve_usuario_from_value."""
    return "".join([c for c in cpf if c.isdigit()])


class TestNormalizeCpfDigits:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("123.456.789-00", "12345678900"),
            ("12345678900", "12345678900"),
            ("abc12345", "12345"),
            ("", ""),
            ("   ", ""),
            ("---", ""),
            (None, ""),
            (12345, "12345"),  # Defensive: int passed through
        ],
    )
    def test_matches_expected(self, val, expected):
        assert normalize_cpf_digits(val) == expected

    @pytest.mark.parametrize(
        "val",
        ["123.456.789-00", "12345678900", "abc12345", "", "---"],
    )
    def test_byte_equivalent_to_both_legacy_patterns(self, val):
        result = normalize_cpf_digits(val)
        assert result == _legacy_cpf_regex(val)
        assert result == _legacy_cpf_isdigit(val)
