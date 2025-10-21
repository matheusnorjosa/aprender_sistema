"""
Serviço de importação de Compras a partir de CSV/XLSX.

Importa Compras da aba "🟥 COMPRAS" da Planilha de Controle.
- Idempotência por external_hash determinístico
- Dry-run mode para preview
- Relatório JSON em out_etl/import_compras_report.json
"""

from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List
from datetime import datetime, date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.models import Compra
from apps.dat_ingest.services.resolvers import resolve_municipio, resolve_projeto
from apps.dat_ingest.services.acompanhamento_normalize import norm_text


OUT_DIR = Path(settings.BASE_DIR) / "out_etl"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def sha1_str(s: str) -> str:
    """Gera SHA1 hex digest de uma string."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def parse_date_flexible(v: str | None) -> date | None:
    """
    Parse de data flexível: YYYY-MM-DD, DD/MM/YYYY ou serial Excel.

    Excel armazena datas como número de dias desde 1899-12-30.
    """
    if not v:
        return None

    s = str(v).strip()

    # Formato ISO: YYYY-MM-DD
    try:
        if "-" in s:
            return datetime.fromisoformat(s).date()
    except Exception:
        pass

    # Formato brasileiro: DD/MM/YYYY
    try:
        if "/" in s:
            parts = s.split("/")
            if len(parts) == 3:
                d, m, a = parts
                return date(int(a), int(m), int(d))
    except Exception:
        pass

    # Serial Excel (número)
    try:
        n = float(s)
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=n)).date()
    except Exception:
        return None

    return None


@dataclass
class ImportStats:
    """Estatísticas de importação."""
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0


@dataclass
class ImportPendencias:
    """Pendências encontradas durante importação."""
    municipios: List[Dict[str, Any]] = field(default_factory=list)
    projetos: List[Dict[str, Any]] = field(default_factory=list)
    linhas_invalidas: List[Dict[str, Any]] = field(default_factory=list)


def import_compras_from_file(*, path: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Importa Compras de CSV/XLSX.

    Args:
        path: Caminho para arquivo CSV/XLSX
        dry_run: Se True, não persiste (apenas simula)

    Returns:
        Relatório com stats, pendências e IDs criados

    Raises:
        FileNotFoundError: Se arquivo não existe
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    # Ler CSV ou XLSX
    rows: List[Dict[str, Any]] = []
    if p.suffix.lower() == ".csv":
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        from openpyxl import load_workbook
        wb = load_workbook(p, data_only=True, read_only=True)
        ws = wb.active
        headers = [
            str(c.value).strip() if c.value is not None else ""
            for c in next(ws.iter_rows(min_row=1, max_row=1))
        ]
        for row in ws.iter_rows(min_row=2):
            rec = {}
            for j, cell in enumerate(row):
                key = headers[j] if j < len(headers) else f"col{j}"
                rec[key] = cell.value
            rows.append(rec)
        wb.close()

    stats = ImportStats()
    pendencias = ImportPendencias()

    def normalize_row(r: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza uma linha do arquivo."""
        codigo = str(r.get("CÓD") or r.get("COD") or r.get("Cód") or "").strip()
        produto = str(r.get("Produto") or "").strip()
        produto_norm = norm_text(produto)
        quant_raw = r.get("Quant.") or r.get("Quant") or r.get("Quantidade")
        municipio = str(r.get("Município") or r.get("Municipio") or "").strip()
        uf = str(r.get("UF") or "").strip().upper()
        data_raw = r.get("Data")
        uso = str(r.get("Uso das coleções") or r.get("Uso") or "").strip()

        try:
            quantidade = int(float(quant_raw or 0))
        except Exception:
            quantidade = None

        data = parse_date_flexible(str(data_raw) if data_raw is not None else "")

        return {
            "codigo": codigo,
            "produto": produto,
            "produto_norm": produto_norm,
            "quantidade": quantidade,
            "municipio": municipio,
            "uf": uf[:2] if uf else "",
            "data": data,
            "uso_norm": norm_text(uso),
        }

    normalized = [normalize_row(r) for r in rows]

    # Resolver municípios e projetos
    resolved: List[Dict[str, Any]] = []
    for i, r in enumerate(normalized, start=2):
        # Validar campos obrigatórios
        if not r["municipio"] or r["quantidade"] is None or not r["codigo"]:
            stats.skipped += 1
            pendencias.linhas_invalidas.append({
                "row": i,
                "motivo": "municipio/quantidade/codigo inválidos",
                "dados": {
                    "municipio": r["municipio"],
                    "quantidade": r["quantidade"],
                    "codigo": r["codigo"],
                }
            })
            continue

        # Resolver município
        mun_obj = resolve_municipio(r["municipio"])
        if not mun_obj:
            stats.skipped += 1
            pendencias.municipios.append({
                "row": i,
                "municipio": r["municipio"],
                "uf": r["uf"]
            })
            continue

        # Resolver projeto (obrigatório)
        proj_obj = _infer_projeto_from_produto(r["produto_norm"])
        if not proj_obj:
            stats.skipped += 1
            pendencias.projetos.append({
                "row": i,
                "produto": r["produto"],
                "produto_norm": r["produto_norm"]
            })
            continue

        resolved.append({**r, "municipio_obj": mun_obj, "projeto_obj": proj_obj})

    # Persistir ou simular
    created_ids: List[int] = []
    if not dry_run:
        with transaction.atomic():
            for r in resolved:
                # Gerar external_hash determinístico
                ext_key = "|".join([
                    str(r["municipio_obj"].id),
                    str(r["projeto_obj"].id),
                    r["codigo"],
                    r["produto_norm"],
                    str(r["quantidade"]),
                    str(r["data"]),
                    r["uso_norm"],
                ])
                ext_hash = sha1_str(ext_key)

                defaults = dict(
                    municipio=r["municipio_obj"],
                    projeto=r["projeto_obj"],
                    codigo=r["codigo"],
                    quantidade=r["quantidade"],
                    data=r["data"],
                    uso=r["uso_norm"],
                )

                obj, created = Compra.objects.update_or_create(
                    external_hash=ext_hash,
                    defaults=defaults
                )

                if created:
                    stats.created += 1
                    created_ids.append(obj.id)
                else:
                    # Verificar se houve mudança
                    changed = any(getattr(obj, k) != v for k, v in defaults.items())
                    if changed:
                        stats.updated += 1
                    else:
                        stats.skipped += 1
    else:
        # Simulação: verificar se já existe sem persistir
        for r in resolved:
            ext_key = "|".join([
                str(r["municipio_obj"].id),
                str(r["projeto_obj"].id),
                r["codigo"],
                r["produto_norm"],
                str(r["quantidade"]),
                str(r["data"]),
                r["uso_norm"],
            ])
            ext_hash = sha1_str(ext_key)
            exists = Compra.objects.filter(external_hash=ext_hash).exists()
            if exists:
                stats.updated += 1
            else:
                stats.created += 1

    # Gerar relatório
    report = {
        "path": str(p),
        "dry_run": dry_run,
        "stats": vars(stats),
        "pendencias": {
            "municipios": pendencias.municipios,
            "projetos": pendencias.projetos,
            "linhas_invalidas": pendencias.linhas_invalidas,
        },
        "created_ids": created_ids if not dry_run else [],
        "ts": timezone.now().isoformat(),
    }

    # Salvar relatório em arquivo
    report_path = OUT_DIR / "import_compras_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return report


def _infer_projeto_from_produto(produto_norm: str):
    """
    Infere projeto a partir do nome do produto normalizado.

    Heurísticas:
    - "NOVO LENDO" → resolve_projeto("Novo Lendo")
    - "GESTAO ESCOLAR" | "GESTÃO ESCOLAR" → resolve_projeto("Gestão Escolar")
    """
    if not produto_norm:
        return None

    key = produto_norm.upper()

    try:
        if "NOVO LENDO" in key:
            return resolve_projeto("Novo Lendo")
        if "GESTAO ESCOLAR" in key or "GESTÃO ESCOLAR" in key:
            return resolve_projeto("Gestão Escolar")
    except Exception:
        return None

    return None
