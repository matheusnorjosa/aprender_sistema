"""
Service para importacao de Deslocamentos via upload.

Padrao: dry_run + external_hash para idempotencia.

Colunas esperadas:
- usuario (obrigatorio): email ou nome do formador
- origem (obrigatorio): local de origem
- destino (obrigatorio): local de destino
- data_inicio (obrigatorio): date
- data_fim (obrigatorio): date (>= data_inicio)
- observacao (opcional): texto livre
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction

import pandas as pd

from apps.core.models import Deslocamento
from apps.dat_ingest.services.resolvers import resolve_user_by_email, resolve_user_by_name

TZ = ZoneInfo("America/Fortaleza")


def import_deslocamentos_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa deslocamentos de CSV/XLSX.

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
                _process_row(row, idx, stats, pendencias, dry_run)
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

    # Email (chaves claramente de email)
    for key in ["email", "e-mail", "mail"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["email"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["email"] = ""

    # Nome (chaves de nome)
    for key in ["name", "nome", "display_name", "usuario_nome"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["name"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["name"] = ""

    # Heuristica para "usuario"/"user": se tem "@" -> email, senao -> nome
    for key in ["usuario", "user", "usuário"]:
        if key in lower_map:
            value = str(lower_map[key]).strip() if lower_map[key] and str(lower_map[key]) != "nan" else ""
            if value:
                if "@" in value:
                    if not normalized["email"]:
                        normalized["email"] = value
                else:
                    if not normalized["name"]:
                        normalized["name"] = value
            break

    # Origem
    for key in ["origem", "origin", "de", "from"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["origem"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["origem"] = ""

    # Destino
    for key in ["destino", "destination", "dest", "para", "to"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["destino"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["destino"] = ""

    # Data inicio
    for key in ["data_inicio", "start", "start_date", "inicio", "início"]:
        if key in lower_map:
            normalized["data_inicio"] = lower_map[key]
            break
    else:
        normalized["data_inicio"] = None

    # Data fim
    for key in ["data_fim", "end", "end_date", "fim"]:
        if key in lower_map:
            normalized["data_fim"] = lower_map[key]
            break
    else:
        normalized["data_fim"] = None

    # Observacao
    for key in ["observacao", "observacoes", "observação", "obs", "notes", "nota"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["observacao"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["observacao"] = ""

    return normalized


def _parse_date_flexible(value: Any) -> date | None:
    """Parse date flexivel: ISO, dd/mm/yyyy, Excel serial."""
    if not value or str(value) == "nan":
        return None

    # Se ja e date
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    # Se e datetime
    if isinstance(value, datetime):
        return value.date()

    # Se e numero (Excel serial)
    if isinstance(value, (int, float)):
        try:
            base_date = datetime(1899, 12, 30)
            return (base_date + timedelta(days=int(value))).date()
        except Exception:
            return None

    # Se e string
    value_str = str(value).strip()
    if not value_str:
        return None

    # Tentar ISO (YYYY-MM-DD)
    try:
        return datetime.strptime(value_str, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Tentar dd/mm/yyyy
    try:
        return datetime.strptime(value_str, "%d/%m/%Y").date()
    except ValueError:
        pass

    # Tentar dd/mm/yy
    try:
        return datetime.strptime(value_str, "%d/%m/%y").date()
    except ValueError:
        pass

    # Tentar ISO com hora
    try:
        return datetime.fromisoformat(value_str).date()
    except ValueError:
        pass

    return None


def _compute_external_hash(usuario_id: int, origem: str, destino: str, start: date, end: date) -> str:
    """
    Gera external_hash SHA1 a partir de campos-chave.

    Formato: SHA1(usuario_id|origem|destino|start|end)
    """
    parts = [
        str(usuario_id),
        origem,
        destino,
        start.isoformat(),
        end.isoformat(),
    ]
    content = "|".join(parts)
    return hashlib.sha1(content.encode("utf-8")).hexdigest()


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    dry_run: bool,
) -> None:
    """Processa uma linha do arquivo."""
    # Resolver usuario (email > nome)
    email = row.get("email", "").strip()
    name = row.get("name", "").strip()

    usuario = None
    if email:
        usuario = resolve_user_by_email(email)

    if not usuario and name:
        usuario = resolve_user_by_name(name)

    if not usuario:
        stats["skipped"]["usuario"] += 1
        pendencias["usuarios"].append(
            {
                "linha": linha_num,
                "email": email,
                "nome": name,
            }
        )
        return

    # Origem/Destino
    origem = row.get("origem", "").strip()
    destino = row.get("destino", "").strip()

    if not origem or not destino:
        stats["skipped"]["other"] += 1
        pendencias["outros"].append(
            {
                "linha": linha_num,
                "erro": "origem_ou_destino_ausentes",
                "origem": origem,
                "destino": destino,
            }
        )
        return

    # Parse datas
    start_date = _parse_date_flexible(row.get("data_inicio"))
    end_date = _parse_date_flexible(row.get("data_fim"))

    if not start_date or not end_date:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "data_inicio": str(row.get("data_inicio")),
                "data_fim": str(row.get("data_fim")),
            }
        )
        return

    if end_date < start_date:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "data_inicio": str(start_date),
                "data_fim": str(end_date),
                "erro": "data_fim < data_inicio",
            }
        )
        return

    # Observacao
    observacao = row.get("observacao", "").strip()

    # Gerar external_hash para idempotencia
    external_hash = _compute_external_hash(usuario.id, origem, destino, start_date, end_date)

    # Verificar existencia
    existing = Deslocamento.objects.filter(external_hash=external_hash).first()

    if existing:
        # Verificar se precisa atualizar observacao
        if existing.observacao != (observacao if observacao else None) and observacao:
            if not dry_run:
                existing.observacao = observacao
                existing.save(update_fields=["observacao"])
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        if not dry_run:
            Deslocamento.objects.create(
                usuario=usuario,
                origem=origem,
                destino=destino,
                start_date=start_date,
                end_date=end_date,
                observacao=observacao if observacao else None,
                external_hash=external_hash,
            )
        stats["created"] += 1
