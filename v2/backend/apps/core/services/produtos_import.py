"""
Service para importacao de Produtos via upload.

Padrao: dry_run + codigo para idempotencia (campo unico).

Colunas esperadas:
- codigo (obrigatorio): codigo unico do produto (ex: NL-C1)
- nome (obrigatorio): nome do produto
- projeto (obrigatorio): nome ou codigo do projeto vinculado
- descricao (opcional): descricao do produto
- ativo (opcional): se o produto esta ativo (default: True)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.db import transaction

import pandas as pd

from apps.core.imports.normalization import normalize_active_flag, normalize_blank
from apps.core.models import Produto, Projeto
from apps.core.services.resolvers import _nfkd


def import_produtos_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa produtos de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)

    Returns:
        {
            "stats": {"created": N, "updated": N, "unchanged": N, "skipped": {...}},
            "pendencias": {"codigo_missing": [...], "nome_missing": [...], "projeto_not_found": [...], "outros": [...]},
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"codigo_missing": 0, "nome_missing": 0, "projeto_not_found": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "codigo_missing": [],
        "nome_missing": [],
        "projeto_not_found": [],
        "outros": [],
    }

    # Carregar arquivo
    rows = _load_file(path)

    # Construir cache de projetos
    projeto_cache = _build_projeto_cache()

    # Processar linhas.
    # ASQ-016: savepoint-per-row. Outer atomic still owns the dry-run
    # rollback; inner atomic isolates one bad row from the rest.
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():  # savepoint
                    _process_row(row, idx, stats, pendencias, projeto_cache, dry_run)
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
        df = pd.read_excel(file_path, dtype=str)

    df = df.fillna("")
    df = df.dropna(how="all")

    rows = []
    for _, row in df.iterrows():
        normalized = _normalize_row(row)
        rows.append(normalized)

    return rows


def _build_projeto_cache() -> dict[str, Projeto]:
    """
    Constroi cache de projetos por nome e codigo normalizados.

    Permite resolver projeto por nome fuzzy ou codigo exato.
    """
    cache: dict[str, Projeto] = {}

    for projeto in Projeto.objects.filter(ativo=True):
        # Por nome normalizado
        nome_norm = _nfkd(projeto.nome)
        if nome_norm:
            cache[nome_norm] = projeto

        # Por codigo normalizado (se tiver)
        if projeto.codigo:
            codigo_norm = _nfkd(projeto.codigo)
            if codigo_norm:
                cache[codigo_norm] = projeto

    return cache


def _normalize_row(row: Any) -> dict[str, Any]:
    """Normaliza headers do arquivo para padrao interno."""
    normalized: dict[str, Any] = {}

    # Criar mapa lower -> valor
    row_dict = row.to_dict()
    lower_map = {str(k).strip().lower(): v for k, v in row_dict.items()}

    # Codigo
    for key in ["codigo", "code", "cod", "sku", "codigo_produto"]:
        if key in lower_map:
            normalized["codigo"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["codigo"] = ""

    # Nome
    for key in ["nome", "name", "produto", "descricao_produto", "nome_produto"]:
        if key in lower_map:
            normalized["nome"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["nome"] = ""

    # Descricao
    for key in ["descricao", "description", "obs", "observacao", "detalhes"]:
        if key in lower_map:
            normalized["descricao"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["descricao"] = ""

    # Projeto
    for key in ["projeto", "project", "projeto_nome", "projeto_codigo"]:
        if key in lower_map:
            normalized["projeto"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["projeto"] = ""

    # Status ativo
    for key in ["ativo", "is_active", "active", "status"]:
        if key in lower_map:
            normalized["is_active"] = normalize_active_flag(lower_map[key])
            break
    else:
        normalized["is_active"] = True

    return normalized


def _resolve_projeto(nome_ou_codigo: str, cache: dict[str, Projeto]) -> Projeto | None:
    """
    Resolve projeto por nome ou codigo normalizado.

    Args:
        nome_ou_codigo: Nome ou codigo do projeto
        cache: Cache de projetos pre-construido

    Returns:
        Projeto encontrado ou None
    """
    if not nome_ou_codigo:
        return None

    normalized = _nfkd(nome_ou_codigo)
    return cache.get(normalized)


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    projeto_cache: dict[str, Projeto],
    dry_run: bool,
) -> None:
    """Processa uma linha do arquivo."""
    # Validar codigo
    codigo = row.get("codigo", "").strip()
    if not codigo:
        stats["skipped"]["codigo_missing"] += 1
        pendencias["codigo_missing"].append(
            {
                "linha": linha_num,
                "erro": "Codigo obrigatorio",
            }
        )
        return

    # Validar nome
    nome = row.get("nome", "").strip()
    if not nome:
        stats["skipped"]["nome_missing"] += 1
        pendencias["nome_missing"].append(
            {
                "linha": linha_num,
                "codigo": codigo,
                "erro": "Nome obrigatorio",
            }
        )
        return

    # Resolver projeto
    projeto_str = row.get("projeto", "").strip()
    projeto = _resolve_projeto(projeto_str, projeto_cache)

    if not projeto:
        stats["skipped"]["projeto_not_found"] += 1
        pendencias["projeto_not_found"].append(
            {
                "linha": linha_num,
                "codigo": codigo,
                "projeto": projeto_str,
                "erro": f"Projeto '{projeto_str}' nao encontrado",
            }
        )
        return

    descricao = row.get("descricao", "").strip()
    is_active = row.get("is_active", True)

    # Verificar existencia por codigo (idempotencia)
    existing = Produto.objects.filter(codigo=codigo).first()

    if existing:
        # Atualizar campos se houver mudancas
        updated = False
        update_fields = []

        if existing.nome != nome:
            existing.nome = nome
            updated = True
            update_fields.append("nome")

        if descricao and existing.descricao != descricao:
            existing.descricao = descricao
            updated = True
            update_fields.append("descricao")

        if existing.projeto_id != projeto.id:
            existing.projeto = projeto
            updated = True
            update_fields.append("projeto")

        if existing.ativo != is_active:
            existing.ativo = is_active
            updated = True
            update_fields.append("ativo")

        if updated:
            if not dry_run:
                existing.save(update_fields=update_fields)
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        # Criar novo produto
        if not dry_run:
            Produto.objects.create(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                projeto=projeto,
                ativo=is_active,
            )
        stats["created"] += 1
