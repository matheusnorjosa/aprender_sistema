"""
Pure normalization helpers shared by import services.

This module is the canonical SSOT for normalization used by the
``apps/core/services/*_import.py`` modules. It is split in two sections:

1. **Modern helpers** (introduced in PR #1344) — small pure functions that
   replaced patterns previously inlined ~80 times across import services.
2. **Legacy import-specific helpers** (migrated from
   ``apps.core.services.normalize`` in PR for issue #1349). Behaviour is
   byte-equivalent to the original module — the legacy module is kept as
   a compat re-export wrapper. Snapshots in
   ``apps/core/tests/test_services_normalize_equivalence.py`` pin the
   current behaviour, including documented quirks (NaN handling, ISO-only
   date parsing, etc.).

Design rules:

* No I/O, no ORM, no Django dependencies.
* No mutation of inputs.
* Inputs may be ``None`` / ``"nan"`` (pandas NaN coerced to string) /
  arbitrary ``Any`` — handled defensively.
* Output types are concrete (``str``, ``bool``) — no ``Optional`` ever
  for the modern helpers; legacy helpers preserve their original return
  types including ``Optional``.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import re
import unicodedata
from datetime import date, time
from typing import Any

# ============================================================================
# Modern helpers (PR #1344) — used by produtos/colecoes/municipios/
# deslocamentos imports plus future callers.
# ============================================================================


# Values treated as falsy when parsing "ativo/active" columns. The mixed-case
# variants come from spreadsheets where users type "Nao", "NAO", "não", etc.
# Normalization is performed via ``.lower()`` before membership test.
_NEGATIVE_ACTIVE_FLAGS: frozenset[str] = frozenset({"nao", "não", "false", "0", "inativo", "n"})


def normalize_blank(val: Any) -> str:
    """
    Return ``str(val).strip()`` unless ``val`` is falsy or the literal
    ``"nan"`` (pandas NaN coerced to string), in which case return ``""``.

    Byte-equivalent to the pattern:

        ``str(val).strip() if val and str(val) != "nan" else ""``

    repeated ~80 times across the legacy ``_normalize_row`` functions.
    """
    if not val:
        return ""
    s = str(val)
    if s == "nan":
        return ""
    return s.strip()


def normalize_active_flag(val: Any, default: bool = True) -> bool:
    """
    Parse an "active/inactive" flag from a free-form spreadsheet column.

    Returns ``default`` when ``val`` is blank/None/"nan". Otherwise returns
    ``False`` only for explicitly negative tokens (``nao``, ``não``,
    ``false``, ``0``, ``inativo``, ``n`` — case-insensitive). Anything else
    is treated as truthy.

    Byte-equivalent to the pattern:

        ``val_str = str(val).strip().lower() if val and str(val) != "nan" else ""``
        ``is_active = val_str not in ("nao", "não", "false", "0", "inativo", "n")``

    repeated 5x across user/produto/colecao/municipio/equipe_gerencia imports.
    The ``default`` argument matches the implicit ``True`` of the old pattern
    (because an empty string is never in ``_NEGATIVE_ACTIVE_FLAGS``).
    """
    raw = normalize_blank(val).lower()
    if not raw:
        return default
    return raw not in _NEGATIVE_ACTIVE_FLAGS


def normalize_uf(val: Any) -> str:
    """
    Return uppercase-stripped UF code, or ``""`` for blank/nan/None.

    Byte-equivalent to the pattern:

        ``str(val).strip().upper() if val and str(val) != "nan" else ""``

    used in ``municipios_import._normalize_row`` and ``_process_row``.

    NOTE: does NOT enforce 2-character length. Callers that need to clamp
    (e.g. ``uf[:2]``) must do so explicitly — that concern is validation,
    not normalization.
    """
    return normalize_blank(val).upper()


def normalize_cpf_digits(val: Any) -> str:
    """
    Return only the digit characters of ``val``, or ``""`` if ``val`` is
    ``None``.

    Behaviourally equivalent to both legacy patterns:

    * ``re.sub(r"[^\\d]", "", cpf)`` (usuarios_import)
    * ``"".join([c for c in cpf if c.isdigit()])`` (equipe_gerencia_import)

    For ASCII CPF inputs the output matches both. Additionally tolerates
    ``None`` and non-string inputs (``int``) without raising, matching the
    defensive expectation when columns come from heterogeneous spreadsheets.
    """
    if val is None:
        return ""
    return "".join(c for c in str(val) if c.isdigit())


# ============================================================================
# Legacy helpers (migrated from apps.core.services.normalize in #1349).
#
# Behaviour is FROZEN by test_services_normalize_equivalence.py — including
# documented quirks. DO NOT "fix" these here:
#
# * split_municipios_super: literal "nan" string is NOT filtered.
# * parse_date_iso: rejects DD/MM/YYYY and slash variants.
# * parse_time_iso: rejects "08" (requires colon separator).
# * normalize_email: no format validation, only lowercase/strip.
# * norm_text: accepts None defensively despite ``s: str`` signature.
# ============================================================================


def norm_text(s: str) -> str:
    """
    Normaliza texto: trim, collapse espaços, remover acentos (NFKD).

    Args:
        s: String para normalizar

    Returns:
        String normalizada (minúsculas, sem acentos, espaços colapsados)
    """
    if not s:
        return ""

    # Trim
    s = s.strip()

    # Collapse espaços múltiplos
    s = re.sub(r"\s+", " ", s)

    # Remover acentos (NFKD decomposition)
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Lowercase
    s = s.lower()

    return s


def normalize_sector(sheet_name: str, projeto_value: str) -> str:
    """
    Mapeia setor a partir da aba e valor do Projeto.

    Regras:
    - ACerta → "ACerta"
    - Brincando → "Brincando"
    - Vidas → "Vidas"
    - Outros:
      - IDEB/IDEB10 → "Gestão Escolar"
      - Vidas L → "Vida & Linguagem"
      - Vidas M → "Vida & Matemática"
      - Vidas C → "Vida & Ciências"
      - Outros → "Outros"
    - Super → "Super"

    Args:
        sheet_name: Nome da aba (ACerta, Brincando, Vidas, Outros, Super)
        projeto_value: Valor do campo Projeto

    Returns:
        Setor normalizado
    """
    sheet_norm = norm_text(sheet_name)
    projeto_norm = norm_text(projeto_value) if projeto_value else ""

    if sheet_norm == "acerta":
        return "ACerta"
    elif sheet_norm == "brincando":
        return "Brincando"
    elif sheet_norm == "vidas":
        return "Vidas"
    elif sheet_norm == "super":
        return "Super"
    elif sheet_norm == "outros":
        # Map por Projeto
        if "ideb" in projeto_norm or ("gestao" in projeto_norm and "escolar" in projeto_norm):
            return "Gestão Escolar"
        elif "vidas l" in projeto_norm or "linguagem" in projeto_norm:
            return "Vida & Linguagem"
        elif "vidas m" in projeto_norm or "matematica" in projeto_norm:
            return "Vida & Matemática"
        elif "vidas c" in projeto_norm or "ciencias" in projeto_norm:
            return "Vida & Ciências"
        else:
            return "Outros"
    else:
        return "Outros"


def normalize_project_alias(projeto: str) -> str:
    """
    Normaliza nome do projeto aplicando aliases (IDEB/IDEB10 → Gestão Escolar).

    Args:
        projeto: Nome do projeto

    Returns:
        Nome normalizado com aliases aplicados
    """
    projeto_norm = norm_text(projeto) if projeto else ""

    # Aplicar aliases IDEB
    if "ideb" in projeto_norm or ("gestao" in projeto_norm and "escolar" in projeto_norm):
        return "Gestão Escolar"

    # Retornar original se não houver alias
    return projeto.strip() if projeto else ""


def split_municipios_super(value: str) -> list[str]:
    """
    Split múltiplos municípios separados por ; , / |

    Args:
        value: String com municípios (ex: "Fortaleza; Caucaia")

    Returns:
        Lista de municípios normalizados
    """
    if not value:
        return []

    # Split por delimitadores
    municipios = re.split(r"[;,/|]", value)

    # Trim e filtrar vazios
    municipios = [m.strip() for m in municipios if m.strip()]

    return municipios


def parse_date_iso(s: str) -> date | None:
    """
    Parse data no formato YYYY-MM-DD.

    Args:
        s: String de data

    Returns:
        objeto date ou None se inválido
    """
    if not s:
        return None

    try:
        parts = s.split("-")
        if len(parts) != 3:
            return None

        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_time_iso(s: str) -> time | None:
    """
    Parse hora no formato HH:MM ou HH:MM:SS.

    Args:
        s: String de hora

    Returns:
        objeto time ou None se inválido
    """
    if not s:
        return None

    try:
        parts = s.split(":")
        if len(parts) < 2:
            return None

        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) > 2 else 0

        return time(hour, minute, second)
    except (ValueError, IndexError):
        return None


def normalize_email(s: str) -> str:
    """
    Normaliza email para lowercase (sem acentos removidos).

    Args:
        s: Email string

    Returns:
        Email em lowercase, trimmed
    """
    if not s:
        return ""

    return s.strip().lower()


def normalize_date_field(s: str) -> str:
    """
    Normaliza campo de data para formato YYYY-MM-DD.

    Args:
        s: String de data (pode ser YYYY-MM-DD ou DD/MM/YYYY)

    Returns:
        Data em formato YYYY-MM-DD ou string vazia se inválido
    """
    if not s:
        return ""

    s = s.strip()

    # Já está em formato ISO
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s

    # Converter DD/MM/YYYY para YYYY-MM-DD
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"

    return ""


def normalize_time_field(s: str) -> str:
    """
    Normaliza campo de hora para formato HH:MM.

    Args:
        s: String de hora (pode incluir segundos)

    Returns:
        Hora em formato HH:MM ou string vazia se inválido
    """
    if not s:
        return ""

    s = s.strip()

    # Remove segundos se presente
    parts = s.split(":")
    if len(parts) >= 2:
        hour = parts[0].zfill(2)
        minute = parts[1].zfill(2)
        return f"{hour}:{minute}"

    return ""
