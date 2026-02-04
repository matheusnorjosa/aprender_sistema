"""
Service para importacao de Bloqueios (AvailabilityBlock) via upload.

Padrao: dry_run + external_hash para idempotencia.

Colunas esperadas:
- usuario (obrigatorio): nome do formador
- inicio (obrigatorio): datetime
- fim (obrigatorio): datetime (deve ser > inicio)
- tipo (obrigatorio): T=Total, P=Parcial
- motivo (opcional): observacao
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction

import pandas as pd

from apps.core.models import AvailabilityBlock
from apps.dat_ingest.services.resolvers import resolve_user_by_name

TZ = ZoneInfo("America/Fortaleza")


def import_bloqueios_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa bloqueios de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {...}},
            "pendencias": {"usuarios": [...], "dates": [...], "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"usuario": 0, "dates": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "usuarios": [],
        "dates": [],
        "outros": [],
    }

    # Carregar arquivo
    rows = _load_file(path)

    # Processar linhas
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
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
        df = pd.read_csv(file_path, dtype=str)
    else:
        df = pd.read_excel(file_path)

    df = df.dropna(how="all")

    rows = []
    for _, row in df.iterrows():
        normalized = _normalize_row(row)
        rows.append(normalized)

    return rows


def _normalize_row(row: Any) -> dict[str, Any]:
    """Normaliza headers do arquivo para padrao interno."""
    normalized: dict[str, Any] = {}

    # Criar mapa lower -> valor
    row_dict = row.to_dict()
    lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

    # Usuario
    for key in ["usuário", "usuario", "user", "formador", "nome"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["usuario"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["usuario"] = ""

    # Inicio
    for key in ["inicio", "início", "start", "data_inicio"]:
        if key in lower_map:
            normalized["inicio"] = lower_map[key]
            break
    else:
        normalized["inicio"] = None

    # Fim
    for key in ["fim", "end", "data_fim"]:
        if key in lower_map:
            normalized["fim"] = lower_map[key]
            break
    else:
        normalized["fim"] = None

    # Tipo
    for key in ["tipo", "type"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["tipo"] = str(val).strip() if val and str(val) != "nan" else "Total"
            break
    else:
        normalized["tipo"] = "Total"

    # Motivo
    for key in ["motivo", "obs", "observacao", "observação"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["motivo"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["motivo"] = ""

    return normalized


def _parse_datetime_flexible(value: Any) -> datetime | None:
    """Parse datetime flexivel (ISO, dd/mm/yyyy, Excel serial)."""
    if not value or str(value) == "nan":
        return None

    # Se ja e datetime
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=TZ)
        return value

    # Se e date
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=TZ)

    # Se e numero (Excel serial)
    if isinstance(value, (int, float)):
        try:
            base_date = datetime(1899, 12, 30, tzinfo=TZ)
            return base_date + timedelta(days=float(value))
        except Exception:
            return None

    # Se e string
    value_str = str(value).strip()
    if not value_str:
        return None

    # Tentar ISO
    try:
        dt = datetime.fromisoformat(value_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt
    except ValueError:
        pass

    # Tentar dd/mm/yyyy HH:MM
    for fmt in ["%d/%m/%Y %H:%M", "%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt.replace(tzinfo=TZ)
        except ValueError:
            pass

    return None


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
) -> None:
    """Processa uma linha do arquivo."""
    # Resolver usuario
    nome = row.get("usuario", "").strip()

    if not nome:
        stats["skipped"]["usuario"] += 1
        return

    usuario = resolve_user_by_name(nome)

    if not usuario:
        stats["skipped"]["usuario"] += 1
        pendencias["usuarios"].append(
            {
                "linha": linha_num,
                "nome": nome,
            }
        )
        return

    # Parse datas
    inicio = _parse_datetime_flexible(row.get("inicio"))
    fim = _parse_datetime_flexible(row.get("fim"))

    if not inicio or not fim:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "inicio": str(row.get("inicio")),
                "fim": str(row.get("fim")),
            }
        )
        return

    # Ajustar fim para fim do dia se for meia-noite
    if fim.hour == 0 and fim.minute == 0:
        fim = fim.replace(hour=23, minute=59, second=59)

    if fim <= inicio:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "inicio": str(inicio),
                "fim": str(fim),
                "erro": "fim <= inicio",
            }
        )
        return

    # Tipo
    tipo_raw = row.get("tipo", "Total").lower()
    if "parcial" in tipo_raw or tipo_raw == "p":
        tipo = "P"
    else:
        tipo = "T"

    # Motivo
    motivo = row.get("motivo", "").strip()

    # Verificar existencia (idempotencia)
    existing = AvailabilityBlock.objects.filter(
        usuario=usuario,
        inicio=inicio,
        fim=fim,
        tipo=tipo,
    ).first()

    if existing:
        # Verificar se precisa atualizar motivo
        if existing.motivo != motivo and motivo:
            existing.motivo = motivo
            existing.save(update_fields=["motivo"])
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        AvailabilityBlock.objects.create(
            usuario=usuario,
            inicio=inicio,
            fim=fim,
            tipo=tipo,
            motivo=motivo,
            status="aprovado",  # Auto-aprovado
        )
        stats["created"] += 1
