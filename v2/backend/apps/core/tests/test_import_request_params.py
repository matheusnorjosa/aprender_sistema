"""Testes do parse fail-closed de ``dry_run`` (issue #1649 / achado M04-05).

Contrato: dry-run (preview) é o padrão seguro; só um token de apply EXPLÍCITO
libera a escrita. Qualquer valor desconhecido (typo, lixo, vazio) permanece em
dry-run — um erro de digitação nunca deve disparar APPLY silencioso.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false

import pytest

from apps.core.imports.request_params import parse_dry_run


class TestParseDryRun:
    """Matriz do contrato de ``parse_dry_run``."""

    @pytest.mark.parametrize("raw", ["false", "0", "no", "n", "f", "off", "FALSE", " False "])
    def test_explicit_apply_tokens_disable_dry_run(self, raw: str) -> None:
        """Só tokens de apply explícitos desligam o dry-run."""
        assert parse_dry_run(raw) is False

    @pytest.mark.parametrize("raw", ["true", "1", "t", "yes", "y", "on", "TRUE", " True "])
    def test_recognized_preview_tokens_keep_dry_run(self, raw: str) -> None:
        """Tokens de preview reconhecidos mantêm o dry-run."""
        assert parse_dry_run(raw) is True

    @pytest.mark.parametrize("raw", ["treu", "tru", "yess", "sim", "maybe", "apply", "xyz", "2"])
    def test_unknown_values_fail_closed_to_dry_run(self, raw: str) -> None:
        """Regressão M04-05/#1649: valor desconhecido NUNCA vira APPLY."""
        assert parse_dry_run(raw) is True

    def test_none_uses_default(self) -> None:
        assert parse_dry_run(None) is True
        assert parse_dry_run(None, default=False) is False

    def test_empty_string_uses_default(self) -> None:
        assert parse_dry_run("") is True
        assert parse_dry_run("   ", default=False) is False
