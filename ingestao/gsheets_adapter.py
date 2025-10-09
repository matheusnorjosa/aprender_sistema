"""
Adaptador para Google Sheets com fallback para CSV local.

Fornece funções para buscar dados de planilhas Google Sheets usando
Service Account, com fallback automático para CSV local se a credencial
não estiver disponível.
"""

from __future__ import annotations

import csv
import io
import os
from typing import Dict, List, Tuple

from django.conf import settings


def _have_sa() -> bool:
    """Verifica se temos Service Account configurada."""
    p = getattr(settings, "GSHEETS_SA_PATH", "/app/creds/gsheet_sa.json")
    return os.path.exists(p) and os.path.getsize(p) > 0


def fetch_sheet_csv(sheet_id: str, gid: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Busca dados de uma aba específica do Google Sheets.

    Args:
        sheet_id: ID da planilha Google Sheets
        gid: ID da aba específica (worksheet ID)

    Returns:
        Tupla com (headers, rows) onde rows é lista de dicionários

    Raises:
        RuntimeError: Se Service Account não estiver configurada ou aba não existir
    """
    if not _have_sa():
        raise RuntimeError(
            "Service Account ausente: configure GOOGLE_APPLICATION_CREDENTIALS "
            "ou /app/creds/gsheet_sa.json"
        )

    import gspread
    from google.oauth2.service_account import Credentials

    creds = Credentials.from_service_account_file(
        settings.GSHEETS_SA_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    # Encontrar worksheet pelo GID
    ws = next((w for w in sh.worksheets() if str(w.id) == str(gid)), None)
    if not ws:
        raise RuntimeError(f"Aba gid={gid} não encontrada em {sheet_id}")

    rows = ws.get_all_records()
    headers = list(rows[0].keys()) if rows else [c for c in ws.row_values(1) if c]

    # Normalizar dicionários (trim keys e values)
    norm = []
    for r in rows:
        norm.append(
            {
                (k or "").strip(): (str(v).strip() if v is not None else "")
                for k, v in r.items()
            }
        )

    return headers, norm


def read_local_csv(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    Lê CSV local e retorna no mesmo formato que fetch_sheet_csv.

    Args:
        path: Caminho para arquivo CSV local

    Returns:
        Tupla com (headers, rows) onde rows é lista de dicionários
    """
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        headers = rdr.fieldnames or []
        rows = [
            {(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in rdr
        ]
    return headers, rows
