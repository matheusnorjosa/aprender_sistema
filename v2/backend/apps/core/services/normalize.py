"""
Compat re-export wrapper for ``apps.core.imports``.

Implementations moved to the canonical namespace ``apps.core.imports.*`` in
PR for issue #1349 (after backfilling equivalence tests in #1350). This
module remains so existing imports keep working without code changes in
the callers (``controle_imports``, ``controle_acoes_import``,
``dat_cadastros_import``, ``views_lookup``).

Future cleanup: callers can migrate to ``apps.core.imports.*`` directly,
after which this wrapper can be removed.
"""

from __future__ import annotations

from apps.core.imports.hashing import hash_event_v2
from apps.core.imports.normalization import (
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

__all__ = [
    "hash_event_v2",
    "norm_text",
    "normalize_date_field",
    "normalize_email",
    "normalize_project_alias",
    "normalize_sector",
    "normalize_time_field",
    "parse_date_iso",
    "parse_time_iso",
    "split_municipios_super",
]
