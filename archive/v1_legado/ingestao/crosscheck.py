"""
Cross-check entre dados do Google Sheets e CSV local.

Verifica consistência entre dados baixados de planilhas e arquivos CSV locais,
gerando métricas de cobertura e diferenças.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List

from .gsheets_adapter import fetch_sheet_csv


def sha1_row(row: Dict[str, str]) -> str:
    """
    Gera hash SHA1 canônico de uma linha (dicionário).

    Args:
        row: Dicionário representando uma linha de dados

    Returns:
        Hash SHA1 hexadecimal (40 caracteres)
    """
    # Normalizar: trim keys e values, ordenar keys
    normalized = {k.strip(): (row.get(k, "") or "").strip() for k in sorted(row)}
    blob = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha1(blob).hexdigest()


def crosscheck_sheet(sheet_id: str, gid: str, local_rows: List[Dict[str, str]]) -> Dict:
    """
    Compara dados locais com dados do Google Sheets.

    Args:
        sheet_id: ID da planilha Google Sheets
        gid: ID da aba (worksheet)
        local_rows: Lista de dicionários com dados locais

    Returns:
        Dicionário com métricas de comparação:
        - local_rows: quantidade de linhas locais
        - sheet_rows: quantidade de linhas no Sheets
        - intersection: linhas presentes em ambos
        - coverage_local_in_sheet_pct: % de linhas locais que existem no Sheets
        - coverage_sheet_in_local_pct: % de linhas do Sheets que existem localmente
        - missing_in_sheet: linhas que só existem localmente
        - missing_in_local: linhas que só existem no Sheets
    """
    _, sheet_rows = fetch_sheet_csv(sheet_id, gid)

    # Calcular hashes
    loc = {sha1_row(r) for r in local_rows}
    rem = {sha1_row(r) for r in sheet_rows}
    inter = loc & rem

    return {
        "local_rows": len(local_rows),
        "sheet_rows": len(sheet_rows),
        "intersection": len(inter),
        "coverage_local_in_sheet_pct": (
            round((len(inter) / len(local_rows)) * 100, 2) if local_rows else 0.0
        ),
        "coverage_sheet_in_local_pct": (
            round((len(inter) / len(sheet_rows)) * 100, 2) if sheet_rows else 0.0
        ),
        "missing_in_sheet": len(loc - rem),
        "missing_in_local": len(rem - loc),
    }
