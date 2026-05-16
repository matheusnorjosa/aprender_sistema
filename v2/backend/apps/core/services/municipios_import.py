"""
Service para importacao de Municipios via upload.

Padrao: dry_run + (nome, uf) para idempotencia.

Colunas esperadas:
- nome (obrigatorio): nome do municipio
- uf (obrigatorio): UF (2 letras)
- ibge_code (opcional): codigo IBGE
- ativo (opcional): se o municipio esta ativo (default: True)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db import transaction

import pandas as pd

from apps.core.imports.normalization import normalize_active_flag, normalize_blank, normalize_uf
from apps.core.models import Municipio
from apps.core.services.options_cache import invalidate_municipios_options_cache


def import_municipios_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa municipios de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {...}},
            "pendencias": {"nome_missing": [...], "uf_missing": [...], "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"nome_missing": 0, "uf_missing": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "nome_missing": [],
        "uf_missing": [],
        "outros": [],
    }

    rows = _load_file(path)

    # ASQ-016: savepoint-per-row. Outer atomic still owns the dry-run
    # rollback; inner atomic isolates one bad row from the rest.
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():  # savepoint
                    _process_row(row, idx, stats, pendencias)
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append(
                    {
                        "linha": idx,
                        "erro": str(e),
                        "row": str(row),
                    }
                )

        if dry_run:
            transaction.set_rollback(True)
        elif stats["created"] or stats["updated"]:
            transaction.on_commit(invalidate_municipios_options_cache)

    return {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": path,
    }


def _load_file(path: str) -> list[dict[str, Any]]:
    """Carrega CSV ou XLSX com headers flexiveis."""
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(file_path, dtype=str, encoding="utf-8-sig")
    else:
        df = pd.read_excel(file_path, dtype=str)

    df = df.fillna("")
    df = df.dropna(how="all")

    rows = []
    for _, row in df.iterrows():
        normalized = _normalize_row(row)
        rows.append(normalized)

    return rows


def _normalize_row(row: Any) -> dict[str, Any]:
    """Normaliza headers do arquivo para padrao interno."""
    normalized: dict[str, Any] = {}

    row_dict = row.to_dict()
    lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

    # Nome do municipio
    for key in ["nome", "municipio", "município", "cidade"]:
        if key in lower_map:
            normalized["nome"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["nome"] = ""

    # UF
    for key in ["uf", "estado"]:
        if key in lower_map:
            normalized["uf"] = normalize_uf(lower_map[key])
            break
    else:
        normalized["uf"] = ""

    # IBGE code
    for key in ["ibge_code", "ibge", "codigo_ibge", "código_ibge"]:
        if key in lower_map:
            normalized["ibge_code"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["ibge_code"] = ""

    # Status ativo
    for key in ["ativo", "is_active", "active", "status"]:
        if key in lower_map:
            normalized["is_active"] = normalize_active_flag(lower_map[key])
            break
    else:
        normalized["is_active"] = True

    # Heuristica: se UF nao veio, tentar parsear "Cidade - UF"
    if not normalized["uf"] and normalized["nome"]:
        nome_raw = normalized["nome"]
        if " - " in nome_raw:
            parts = [p.strip() for p in nome_raw.split(" - ") if p.strip()]
            if len(parts) >= 2 and len(parts[-1]) == 2:
                normalized["nome"] = " - ".join(parts[:-1]).strip()
                normalized["uf"] = parts[-1].upper()

    return normalized


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
) -> None:
    """Processa um registro de municipio."""
    nome = row.get("nome", "").strip()
    uf = row.get("uf", "").strip().upper()
    ibge_code = row.get("ibge_code", "").strip()
    is_active = bool(row.get("is_active", True))

    if not nome:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append({"linha": linha_num, "erro": "Nome do municipio ausente"})
        return

    if not uf:
        stats["skipped"]["uf_missing"] += 1
        pendencias["uf_missing"].append({"linha": linha_num, "erro": "UF ausente", "municipio": nome})
        return

    existing = Municipio.objects.filter(nome__iexact=nome, uf=uf).first()
    if not existing:
        Municipio.objects.create(
            nome=nome,
            uf=uf,
            ibge_code=ibge_code or None,
            ativo=is_active,
        )
        stats["created"] += 1
        return

    changed = False
    if ibge_code and existing.ibge_code != ibge_code:
        existing.ibge_code = ibge_code
        changed = True
    if existing.ativo != is_active:
        existing.ativo = is_active
        changed = True

    if changed:
        existing.save(update_fields=["ibge_code", "ativo"])
        stats["updated"] += 1
    else:
        stats["unchanged"] += 1
