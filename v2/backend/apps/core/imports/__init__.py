"""
``apps.core.imports`` — canonical namespace for shared import helpers.

This package is the SSOT (single source of truth) for utility helpers
shared across the import services in ``apps.core.services.*_import``.

Submodules:

* :mod:`apps.core.imports.normalization` — pure string normalization helpers
  (``normalize_blank``, ``normalize_active_flag``, ``normalize_uf``,
  ``normalize_cpf_digits``).
* :mod:`apps.core.imports.hashing` — deterministic SHA-1 idempotency-key
  generation (``stable_import_hash``). Not cryptographic.

See ``README.md`` next to this file for the migration policy regarding
``apps.core.services.normalize`` (legacy module pending test backfill).
"""

from __future__ import annotations
