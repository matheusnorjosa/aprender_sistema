"""
Equivalence tests for ``apps.core.imports.hashing``.

These tests guard against accidental change of the SHA-1 idempotency
contract used for ``external_hash`` columns. Any divergence here would
silently break deduplication of imports on the next ETL run.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

import hashlib

import pytest

from apps.core.imports.hashing import stable_import_hash


def _legacy_sha1(content: str) -> str:
    """Original inline call repeated across import services."""
    return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()


class TestStableImportHash:
    def test_single_part_matches_sha1_of_string(self):
        assert stable_import_hash("foo") == _legacy_sha1("foo")

    def test_multiple_parts_use_pipe_delimiter(self):
        assert stable_import_hash("a", "b", "c") == _legacy_sha1("a|b|c")

    def test_empty_part_preserved(self):
        # "a", "b", "" → "a|b|" (trailing pipe, NOT collapsed)
        assert stable_import_hash("a", "b", "") == _legacy_sha1("a|b|")

    def test_leading_empty_part_preserved(self):
        assert stable_import_hash("", "b", "c") == _legacy_sha1("|b|c")

    def test_zero_parts_is_sha1_of_empty_string(self):
        # SHA1 of "" is a well-known constant
        expected = "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        assert stable_import_hash() == expected
        assert stable_import_hash() == _legacy_sha1("")

    def test_output_is_40_char_hex(self):
        digest = stable_import_hash("anything")
        assert len(digest) == 40
        assert all(c in "0123456789abcdef" for c in digest)

    def test_deterministic_for_same_input(self):
        assert stable_import_hash("x", "y") == stable_import_hash("x", "y")

    def test_order_sensitive(self):
        assert stable_import_hash("a", "b") != stable_import_hash("b", "a")

    @pytest.mark.parametrize(
        "parts",
        [
            ("123", "São Paulo", "SP"),
            ("a", "b", "c", "d", "e"),
            ("emoji 🚀", "ascii"),
            ("with\nnewline", "x"),
        ],
    )
    def test_byte_equivalence_with_pipe_join(self, parts):
        assert stable_import_hash(*parts) == _legacy_sha1("|".join(parts))


class TestDeslocamentoExternalHashEquivalence:
    """
    Snapshot test pinning the exact digest produced by
    ``deslocamentos_import._compute_external_hash`` so the migration to
    ``stable_import_hash`` cannot silently change ``Deslocamento.external_hash``.

    Replicates the legacy call:

        parts = [str(usuario_id), origem, destino, start.isoformat(), end.isoformat()]
        content = "|".join(parts)
        return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()
    """

    def test_byte_equivalence_for_representative_row(self):
        from datetime import date

        usuario_id = 42
        origem = "Fortaleza"
        destino = "Sobral"
        start = date(2026, 5, 16)
        end = date(2026, 5, 18)

        legacy = _legacy_sha1(
            "|".join(
                [
                    str(usuario_id),
                    origem,
                    destino,
                    start.isoformat(),
                    end.isoformat(),
                ]
            )
        )

        new = stable_import_hash(
            str(usuario_id),
            origem,
            destino,
            start.isoformat(),
            end.isoformat(),
        )

        assert new == legacy


class TestSha1StrWrapperEquivalence:
    """
    ``apps.core.services.controle_imports.sha1_str`` is migrated to a thin
    wrapper around ``stable_import_hash``. This test pins byte-equivalence
    so historical ``Compra.external_hash`` values stay valid.
    """

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "a",
            "a|b|c",
            "1|2|3|São Paulo|SP",
            "x" * 1000,
        ],
    )
    def test_sha1_str_matches_stable_import_hash_single_arg(self, value):
        from apps.core.services.controle_imports import sha1_str

        assert sha1_str(value) == stable_import_hash(value)
        assert sha1_str(value) == _legacy_sha1(value)
