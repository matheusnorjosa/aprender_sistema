"""
Service para importacao de Colecoes via upload.

Padrao: dry_run + (nome, projeto) para idempotencia.

Colunas esperadas:
- nome (obrigatorio): nome da colecao
- projeto (obrigatorio): nome ou codigo do projeto vinculado
- descricao (opcional): descricao da colecao
- ativo (opcional): se a colecao esta ativa (default: True)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db import transaction

import pandas as pd

from apps.core.models import Colecao, Projeto
from apps.core.services.resolvers import resolve_projeto


def import_colecoes_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa colecoes de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {...}},
            "pendencias": {"nome_missing": [...], "projeto_missing": [...], "projeto_not_found": [...], "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"nome_missing": 0, "projeto_missing": 0, "projeto_not_found": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "nome_missing": [],
        "projeto_missing": [],
        "projeto_not_found": [],
        "outros": [],
    }

    rows = _load_file(path)

    # Cache de projetos ja resolvidos por nome informado
    projeto_cache: dict[str, Projeto | None] = {}

    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                _process_row(row, idx, stats, pendencias, projeto_cache)
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

    # Nome da colecao
    for key in ["nome", "colecao", "coleção", "nome_colecao", "nome_coleção"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["nome"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["nome"] = ""

    # Projeto
    for key in ["projeto", "project", "nome_projeto", "codigo_projeto"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["projeto"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["projeto"] = ""

    # Descricao
    for key in ["descricao", "description", "obs", "observacao", "detalhes"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["descricao"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["descricao"] = ""

    # Status ativo
    for key in ["ativo", "is_active", "active", "status"]:
        if key in lower_map:
            val = lower_map[key]
            val_str = str(val).strip().lower() if val and str(val) != "nan" else ""
            normalized["is_active"] = val_str not in ("nao", "não", "false", "0", "inativo", "n")
            break
    else:
        normalized["is_active"] = True

    return normalized


def _resolve_projeto_cached(nome: str, cache: dict[str, Projeto | None]) -> Projeto | None:
    """Resolve projeto com cache simples por nome informado."""
    if not nome:
        return None

    key = nome.strip().lower()
    if key in cache:
        return cache[key]

    projeto = resolve_projeto(nome)
    cache[key] = projeto
    return projeto


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    projeto_cache: dict[str, Projeto | None],
) -> None:
    """Processa um registro de colecao."""
    nome = row.get("nome", "").strip()
    projeto_nome = row.get("projeto", "").strip()
    descricao = row.get("descricao", "").strip()
    is_active = bool(row.get("is_active", True))

    if not nome:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append({"linha": linha_num, "erro": "Nome da colecao ausente"})
        return

    if not projeto_nome:
        stats["skipped"]["projeto_missing"] += 1
        pendencias["projeto_missing"].append({"linha": linha_num, "erro": "Projeto ausente", "colecao": nome})
        return

    projeto = _resolve_projeto_cached(projeto_nome, projeto_cache)
    if not projeto:
        stats["skipped"]["projeto_not_found"] += 1
        pendencias["projeto_not_found"].append(
            {"linha": linha_num, "erro": "Projeto nao encontrado", "projeto": projeto_nome, "colecao": nome}
        )
        return

    existing = Colecao.objects.filter(nome__iexact=nome, projeto=projeto).first()
    if not existing:
        Colecao.objects.create(
            nome=nome,
            projeto=projeto,
            descricao=descricao,
            ativo=is_active,
        )
        stats["created"] += 1
        return

    changed = False
    if descricao and existing.descricao != descricao:
        existing.descricao = descricao
        changed = True
    if existing.ativo != is_active:
        existing.ativo = is_active
        changed = True

    if changed:
        existing.save(update_fields=["descricao", "ativo", "updated_at"])
        stats["updated"] += 1
    else:
        stats["unchanged"] += 1
