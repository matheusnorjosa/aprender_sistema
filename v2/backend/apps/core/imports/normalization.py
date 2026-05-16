"""
Pure normalization helpers shared by import services.

Every function here is byte-equivalent to the inline patterns previously
duplicated across the ``apps/core/services/*_import.py`` modules — the
helpers exist only to centralize identical logic, not to change behaviour.

Design rules:

* No I/O, no ORM, no Django dependencies.
* No mutation of inputs.
* Inputs may be ``None`` / ``"nan"`` (pandas NaN coerced to string) /
  arbitrary ``Any`` — handled defensively.
* Output types are concrete (``str``, ``bool``) — no ``Optional`` ever.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

from typing import Any

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
