"""
Deterministic hash helpers for idempotency keys used by import services.

These hashes are NOT cryptographic — they exist solely as stable identifiers
to detect already-imported rows. The SHA-1 digest with
``usedforsecurity=False`` is required by PEP 644 to silence weak-crypto
linters. Migrating to SHA-256 would break historical ``external_hash``
values stored in ``Compra``, ``Solicitacao``, ``Deslocamento``,
``AcaoControle``, ``AcaoDAT``, ``Acompanhamento`` and is therefore
forbidden.

This module is split in two sections:

1. **Modern helper** (PR #1344) — ``stable_import_hash`` for pipe-joined
   composite keys.
2. **Legacy helper** (migrated from ``apps.core.services.normalize`` in
   PR for issue #1349) — ``hash_event_v2`` for the Acompanhamento ETL
   17-field hash. Behaviour is FROZEN by snapshots in
   ``apps/core/tests/test_services_normalize_equivalence.py``.
"""

# pyright: reportMissingParameterType=false

from __future__ import annotations

import hashlib

from apps.core.imports.normalization import (
    norm_text,
    normalize_date_field,
    normalize_email,
    normalize_sector,
    normalize_time_field,
)


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


def hash_event_v2(row: dict[str, str]) -> str:
    """
    Gera external_hash v2 (SHA1) a partir de 17 campos normalizados.

    Esta função implementa o critério de "duplicata real" usado na auditoria,
    com normalização completa de todos os campos.

    Campos (todos normalizados):
    1. sector (aba ou mapeado em "Outros" via Projeto com alias IDEB→Gestão Escolar)
    2. municipio
    3. encontro
    4. tipo_evento
    5. data (formato YYYY-MM-DD)
    6. hora_inicio (formato HH:MM)
    7. hora_fim (formato HH:MM)
    8. projeto
    9. segmento
    10. coord_acompanha
    11. coordenador
    12. formador1
    13. formador2
    14. formador3
    15. formador4
    16. formador5
    17. aprovacao (apenas para "Super"; vazio nos demais)

    Normalização aplicada:
    - Textos: trim, collapse spaces, sem acentos, casefold
    - Emails: lowercase (sem remoção de acentos)
    - Datas: YYYY-MM-DD
    - Horas: HH:MM

    Args:
        row: Dicionário com campos normalizados do evento

    Returns:
        Hash SHA1 (40 caracteres hex)
    """
    # 1. sector - mapear de aba + projeto (com alias IDEB)
    sector = normalize_sector(row.get("source_sheet", ""), row.get("projeto", ""))
    sector_norm = norm_text(sector)

    # 2. municipio
    municipio_norm = norm_text(row.get("municipio", ""))

    # 3. encontro
    encontro_norm = norm_text(row.get("encontro", ""))

    # 4. tipo_evento
    tipo_norm = norm_text(row.get("tipo", ""))

    # 5. data (YYYY-MM-DD)
    data_norm = normalize_date_field(row.get("data", ""))

    # 6. hora_inicio (HH:MM)
    hora_inicio_norm = normalize_time_field(row.get("hora_inicio", ""))

    # 7. hora_fim (HH:MM)
    hora_fim_norm = normalize_time_field(row.get("hora_fim", ""))

    # 8. projeto - aplicar aliases IDEB→Gestão Escolar para consistência
    projeto_raw = row.get("projeto", "")
    projeto_lower = norm_text(projeto_raw)
    # Aplicar mesmo mapeamento de aliases que normalize_sector
    if "ideb" in projeto_lower or ("gestao" in projeto_lower and "escolar" in projeto_lower):
        projeto_norm = norm_text("Gestão Escolar")
    else:
        projeto_norm = projeto_lower

    # 9. segmento
    segmento_norm = norm_text(row.get("segmento", ""))

    # 10. coord_acompanha
    coord_acompanha_norm = norm_text(row.get("coord_acompanha", ""))

    # 11. coordenador (email ou nome)
    coordenador = row.get("coordenador", "")
    if "@" in coordenador:
        coordenador_norm = normalize_email(coordenador)
    else:
        coordenador_norm = norm_text(coordenador)

    # 12-16. formadores (emails ou nomes)
    formadores_norm: list[str] = []
    for i in range(1, 6):
        formador = row.get(f"formador{i}", "")
        if "@" in formador:
            formadores_norm.append(normalize_email(formador))
        else:
            formadores_norm.append(norm_text(formador))

    # 17. aprovacao (apenas para Super; vazio nos demais)
    aprovacao = row.get("aprovacao", "")
    if sector_norm == "super":
        aprovacao_norm = norm_text(aprovacao)
    else:
        aprovacao_norm = ""

    # Construir string canônica
    parts = [
        sector_norm,  # 1
        municipio_norm,  # 2
        encontro_norm,  # 3
        tipo_norm,  # 4
        data_norm,  # 5
        hora_inicio_norm,  # 6
        hora_fim_norm,  # 7
        projeto_norm,  # 8
        segmento_norm,  # 9
        coord_acompanha_norm,  # 10
        coordenador_norm,  # 11
        formadores_norm[0],  # 12 (formador1)
        formadores_norm[1],  # 13 (formador2)
        formadores_norm[2],  # 14 (formador3)
        formadores_norm[3],  # 15 (formador4)
        formadores_norm[4],  # 16 (formador5)
        aprovacao_norm,  # 17
    ]

    # Join com pipe delimiter
    content = "|".join(parts)

    # SHA1 hash
    hash_obj = hashlib.sha1(content.encode("utf-8"), usedforsecurity=False)
    return hash_obj.hexdigest()
