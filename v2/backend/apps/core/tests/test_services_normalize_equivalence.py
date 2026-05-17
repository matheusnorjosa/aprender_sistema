"""
Equivalence / snapshot tests for ``apps.core.services.normalize``.

This module is the **legacy** normalization helper still used by:

* ``apps.core.services.controle_imports``
* ``apps.core.services.controle_acoes_import``
* ``apps.core.services.dat_cadastros_import``
* ``apps.core.views_lookup``

Per the migration policy in
``apps/core/imports/README.md``, these helpers will eventually move to the
canonical namespace ``apps.core.imports.*``. This test module pins the
**current** behavior of every public function so the future move can
prove byte-for-byte equivalence.

Diretriz (issue #1345): congelar comportamento atual, NÃO corrigir bugs
encontrados. Anomalias observadas estão documentadas em
``# NOTE:`` comments — qualquer mudança de comportamento deve quebrar
estes testes propositalmente em PR dedicada.

Refs #1345 — prepares #1349.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportArgumentType=false

from __future__ import annotations

from datetime import date, time

import pytest

from apps.core.services.normalize import (
    hash_event_v2,
    norm_text,
    normalize_date_field,
    normalize_email,
    normalize_project_alias,
    normalize_sector,
    normalize_time_field,
    parse_date_iso,
    parse_time_iso,
    split_municipios_super,
)

# ---------------------------------------------------------------------------
# norm_text — trim, collapse whitespace, NFKD, lowercase
# ---------------------------------------------------------------------------


class TestNormTextSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("  Test  ", "test"),
            ("São Paulo", "sao paulo"),
            ("AÇÚCAR", "acucar"),
            ("", ""),
            ("multi  space", "multi space"),
            ("multi   spaces", "multi spaces"),
            ("già", "gia"),
            ("mañana", "manana"),
            ("\tabc\n", "abc"),
            ("ALREADY lower", "already lower"),
        ],
    )
    def test_current_behavior(self, val, expected):
        assert norm_text(val) == expected

    def test_none_returns_empty_string(self):
        # NOTE: defensive None handling — current implementation returns ""
        # via the `if not s` early-out. Tests pin this so we don't lose it.
        assert norm_text(None) == ""


# ---------------------------------------------------------------------------
# normalize_sector — sheet/project mapping
# ---------------------------------------------------------------------------


class TestNormalizeSectorSnapshot:
    @pytest.mark.parametrize(
        ("sheet", "projeto", "expected"),
        [
            # Sheets with canonical name
            ("ACerta", "", "ACerta"),
            ("Brincando", "", "Brincando"),
            ("Vidas", "", "Vidas"),
            ("Super", "", "Super"),
            # Case + whitespace insensitivity on sheet name
            ("  acerta  ", "", "ACerta"),
            ("ACERTA", "", "ACerta"),
            # Unknown sheet falls back to "Outros"
            ("Unknown", "", "Outros"),
            # Sheet "Outros" maps by project keyword
            ("Outros", "IDEB10", "Gestão Escolar"),
            ("Outros", "Vidas L", "Vida & Linguagem"),
            ("Outros", "Vidas M", "Vida & Matemática"),
            ("Outros", "Vidas C", "Vida & Ciências"),
            ("Outros", "qualquer", "Outros"),
            # Lowercase sheet "outros" also resolves via project
            ("outros", "gestao escolar", "Gestão Escolar"),
            ("outros", "linguagem", "Vida & Linguagem"),
            ("outros", "matematica", "Vida & Matemática"),
            ("outros", "ciencias", "Vida & Ciências"),
        ],
    )
    def test_current_behavior(self, sheet, projeto, expected):
        assert normalize_sector(sheet, projeto) == expected


# ---------------------------------------------------------------------------
# normalize_project_alias — IDEB/Gestão Escolar alias
# ---------------------------------------------------------------------------


class TestNormalizeProjectAliasSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("IDEB10", "Gestão Escolar"),
            ("IDEB", "Gestão Escolar"),
            ("Gestão Escolar", "Gestão Escolar"),
            ("gestao escolar", "Gestão Escolar"),
            ("Novo Lendo", "Novo Lendo"),
            ("", ""),
        ],
    )
    def test_current_behavior(self, val, expected):
        assert normalize_project_alias(val) == expected


# ---------------------------------------------------------------------------
# split_municipios_super — split by ; , / |
# ---------------------------------------------------------------------------


class TestSplitMunicipiosSuperSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("", []),
            ("Fortaleza", ["Fortaleza"]),
            ("Fortaleza; Caucaia", ["Fortaleza", "Caucaia"]),
            ("A; B, C / D | E", ["A", "B", "C", "D", "E"]),
            ("  A  ;  B  ", ["A", "B"]),
        ],
    )
    def test_current_behavior(self, val, expected):
        assert split_municipios_super(val) == expected

    def test_nan_string_is_not_filtered(self):
        # NOTE: legacy quirk — the literal "nan" string is NOT filtered.
        # Callers that expect pandas-NaN handling must filter externally.
        # Frozen here so future refactors don't silently change this.
        assert split_municipios_super("nan") == ["nan"]


# ---------------------------------------------------------------------------
# parse_date_iso — YYYY-MM-DD only
# ---------------------------------------------------------------------------


class TestParseDateIsoSnapshot:
    def test_valid_iso_returns_date(self):
        assert parse_date_iso("2026-05-17") == date(2026, 5, 17)

    @pytest.mark.parametrize(
        "val",
        [
            "",
            "abc",
            "2026/05/17",  # NOTE: rejects slashes — use normalize_date_field for BR
            "17-05-2026",  # NOTE: rejects DD-MM-YYYY
            "2026-13-01",  # invalid month
        ],
    )
    def test_invalid_returns_none(self, val):
        assert parse_date_iso(val) is None


# ---------------------------------------------------------------------------
# parse_time_iso — HH:MM or HH:MM:SS
# ---------------------------------------------------------------------------


class TestParseTimeIsoSnapshot:
    def test_hh_mm(self):
        assert parse_time_iso("08:30") == time(8, 30)

    def test_hh_mm_ss(self):
        assert parse_time_iso("08:30:45") == time(8, 30, 45)

    @pytest.mark.parametrize(
        "val",
        [
            "",
            "abc",
            "08",  # NOTE: requires colon separator
        ],
    )
    def test_invalid_returns_none(self, val):
        assert parse_time_iso(val) is None


# ---------------------------------------------------------------------------
# normalize_email — lowercase + strip (NO format validation)
# ---------------------------------------------------------------------------


class TestNormalizeEmailSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("  X@Y.COM  ", "x@y.com"),
            ("a@b.com", "a@b.com"),
            ("", ""),
        ],
    )
    def test_current_behavior(self, val, expected):
        assert normalize_email(val) == expected

    def test_invalid_format_is_passed_through_lowercased(self):
        # NOTE: function does NOT validate format — it just lowercases/strips.
        # Frozen here to document existing behavior.
        assert normalize_email("inválido sem arroba") == "inválido sem arroba"


# ---------------------------------------------------------------------------
# normalize_date_field — ISO or DD/MM/YYYY → YYYY-MM-DD
# ---------------------------------------------------------------------------


class TestNormalizeDateFieldSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("", ""),
            ("2026-05-17", "2026-05-17"),  # ISO pass-through
            ("17/05/2026", "2026-05-17"),  # BR → ISO
            ("2026/05/17", ""),  # NOTE: slashes-as-ISO rejected
            ("abc", ""),
            ("17-05-2026", ""),  # NOTE: DD-MM-YYYY rejected
        ],
    )
    def test_current_behavior(self, val, expected):
        assert normalize_date_field(val) == expected


# ---------------------------------------------------------------------------
# normalize_time_field — any HH:MM-ish → HH:MM (truncates seconds)
# ---------------------------------------------------------------------------


class TestNormalizeTimeFieldSnapshot:
    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("", ""),
            ("8:30", "08:30"),  # zfill applied
            ("08:30", "08:30"),
            ("08:30:45", "08:30"),  # seconds truncated
            ("abc", ""),
            ("8", ""),  # NOTE: requires colon separator
        ],
    )
    def test_current_behavior(self, val, expected):
        assert normalize_time_field(val) == expected


# ---------------------------------------------------------------------------
# hash_event_v2 — the most critical helper (Acompanhamento idempotency)
# ---------------------------------------------------------------------------


# Canonical row used as snapshot baseline. DO NOT modify these field values
# without recomputing the expected hash — these snapshots pin idempotency.
ROW_ACERTA_CANONICAL: dict[str, str] = {
    "source_sheet": "ACerta",
    "projeto": "ACerta",
    "municipio": "Fortaleza",
    "encontro": "1",
    "tipo": "Presencial",
    "data": "2026-01-15",
    "hora_inicio": "08:00",
    "hora_fim": "12:00",
    "segmento": "EI",
    "coord_acompanha": "sim",
    "coordenador": "coord@example.com",
    "formador1": "form1@example.com",
    "formador2": "",
    "formador3": "",
    "formador4": "",
    "formador5": "",
    "aprovacao": "",
}

EXPECTED_HASH_ACERTA = "a1df0e51fec2e0d5e0d812e383eb50b2f5162258"
EXPECTED_HASH_SUPER_APROVADO = "d023304360d8a08fa1d158fc9c6b02b23ec21052"
EXPECTED_HASH_WITH_FORMADOR3 = "abc852382ac6cbf05afc79cd87eedd8c94a1dfa8"
EXPECTED_HASH_BRINCANDO_MINIMAL = "6c566f21d3f9b60d47ddbea2d065be9676dbec92"
EXPECTED_HASH_OUTROS_IDEB10 = "6c14fbc4ebf34421954e19175292458c544aa5ec"


class TestHashEventV2Snapshot:
    """
    Snapshot tests for ``hash_event_v2`` — guards Acompanhamento
    ``external_hash`` idempotency. Changing any expected digest is a
    breaking change requiring re-import or migration.
    """

    def test_baseline_acerta_row(self):
        assert hash_event_v2(ROW_ACERTA_CANONICAL) == EXPECTED_HASH_ACERTA

    def test_super_with_aprovacao_changes_hash(self):
        row = dict(ROW_ACERTA_CANONICAL)
        row["source_sheet"] = "Super"
        row["aprovacao"] = "aprovado"
        assert hash_event_v2(row) == EXPECTED_HASH_SUPER_APROVADO
        assert hash_event_v2(row) != EXPECTED_HASH_ACERTA

    def test_adding_formador3_changes_hash(self):
        row = dict(ROW_ACERTA_CANONICAL)
        row["formador3"] = "form3@example.com"
        assert hash_event_v2(row) == EXPECTED_HASH_WITH_FORMADOR3
        assert hash_event_v2(row) != EXPECTED_HASH_ACERTA

    def test_brincando_minimal_row(self):
        row: dict[str, str] = {
            "source_sheet": "Brincando",
            "projeto": "Brincando",
            "municipio": "Sobral",
            "encontro": "2",
            "tipo": "Online",
            "data": "2026-02-20",
            "hora_inicio": "14:00",
            "hora_fim": "17:30",
            "segmento": "EF",
            "coord_acompanha": "",
            "coordenador": "Maria Silva",  # name, no @
            "formador1": "",
            "formador2": "",
            "formador3": "",
            "formador4": "",
            "formador5": "",
            "aprovacao": "",
        }
        assert hash_event_v2(row) == EXPECTED_HASH_BRINCANDO_MINIMAL

    def test_ideb10_normalized_to_gestao_escolar(self):
        """
        IDEB10 in sheet=Outros must be normalized to 'Gestão Escolar' for
        hashing — both versions produce identical digest.
        """
        row_ideb = dict(ROW_ACERTA_CANONICAL)
        row_ideb["source_sheet"] = "Outros"
        row_ideb["projeto"] = "IDEB10"

        row_explicit = dict(ROW_ACERTA_CANONICAL)
        row_explicit["source_sheet"] = "Outros"
        row_explicit["projeto"] = "Gestão Escolar"

        assert hash_event_v2(row_ideb) == EXPECTED_HASH_OUTROS_IDEB10
        assert hash_event_v2(row_ideb) == hash_event_v2(row_explicit)

    def test_aprovacao_ignored_in_non_super_sector(self):
        """
        ``aprovacao`` only contributes to the hash when sector is ``Super``.
        Setting it in ACerta must NOT change the hash.
        """
        row = dict(ROW_ACERTA_CANONICAL)
        row["aprovacao"] = "aprovado"
        # sector remains 'ACerta' (not Super)
        assert hash_event_v2(row) == EXPECTED_HASH_ACERTA

    def test_date_format_normalized_before_hashing(self):
        """
        ``17/05/2026`` and ``2026-05-17`` produce the same hash because the
        date is normalized via ``normalize_date_field`` before hashing.
        """
        row_br = dict(ROW_ACERTA_CANONICAL)
        row_br["data"] = "15/01/2026"
        assert hash_event_v2(row_br) == EXPECTED_HASH_ACERTA

    def test_deterministic(self):
        h1 = hash_event_v2(ROW_ACERTA_CANONICAL)
        h2 = hash_event_v2(ROW_ACERTA_CANONICAL)
        assert h1 == h2

    def test_output_is_40_char_sha1_hex(self):
        digest = hash_event_v2(ROW_ACERTA_CANONICAL)
        assert len(digest) == 40
        assert all(c in "0123456789abcdef" for c in digest)
