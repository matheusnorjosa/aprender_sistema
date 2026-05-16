"""
Deterministic hash helpers for idempotency keys used by import services.

These hashes are NOT cryptographic — they exist solely as stable identifiers
to detect already-imported rows. The SHA-1 digest with
``usedforsecurity=False`` is required by PEP 644 to silence weak-crypto
linters. Migrating to SHA-256 would break historical ``external_hash``
values stored in ``Compra``, ``Solicitacao``, ``Deslocamento``,
``AcaoControle``, ``AcaoDAT`` and is therefore forbidden.
"""

# pyright: reportMissingParameterType=false

from __future__ import annotations

import hashlib


def stable_import_hash(*parts: str) -> str:
    """
    Compute a deterministic SHA-1 hex digest of pipe-joined parts.

    Equivalent to:

        ``hashlib.sha1("|".join(parts).encode("utf-8"), usedforsecurity=False).hexdigest()``

    Used as idempotency key for ``external_hash`` columns. DO NOT change
    the digest algorithm, encoding, or delimiter — historical values stored
    in the database rely on this exact byte-level definition.

    Examples (verified byte-equivalent to legacy callers):

    * ``stable_import_hash("foo")`` →
      same as ``hashlib.sha1(b"foo", usedforsecurity=False).hexdigest()``.
    * ``stable_import_hash("a", "b", "")`` →
      same as ``hashlib.sha1(b"a|b|", usedforsecurity=False).hexdigest()``.
    * ``stable_import_hash()`` →
      same as ``hashlib.sha1(b"", usedforsecurity=False).hexdigest()`` =
      ``"da39a3ee5e6b4b0d3255bfef95601890afd80709"``.
    """
    content = "|".join(parts)
    return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()
