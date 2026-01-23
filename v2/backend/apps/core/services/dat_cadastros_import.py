"""
Serviço de import para AcaoDAT.

Lê CSV/XLSX e cria/atualiza AcaoDAT por external_hash único.

Regras de negócio:
- Município/Projeto resolvidos por nome (norm_text)
- Responsável resolvido por email > nome
- Datas parseadas: ISO, dd/mm/yyyy, dd/mm/yy, Excel serial
- Idempotência: SHA1(municipio_id|projeto_id|tipo_acao|responsavel_id)
  - external_hash baseado em identidade estável
  - Dados variáveis (data_registro/obs) atualizam o mesmo registro
- Relatório em out_etl/import_dat_cadastros_report.json
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.core.models import AcaoDAT, Municipio, Projeto, Usuario
from apps.core.services.normalize import norm_text
from apps.core.services.resolvers import resolve_user_by_email, resolve_user_by_name
from apps.core.types import ExternalHash

OUT_DIR: Path = Path(settings.BASE_DIR) / "out_etl"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def import_dat_cadastros(file_path: str, dry_run: bool = False) -> dict[str, Any]:
    """
    Importa cadastros DAT de CSV/XLSX.

    Args:
        file_path: Caminho do arquivo
        dry_run: Se True, simula sem gravar

    Returns:
        Dict com stats e pendências
    """
    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"municipio": 0, "projeto": 0, "responsavel": 0, "tipo_acao": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "municipios": [],
        "projetos": [],
        "responsaveis": [],
        "tipo_acao": [],
        "outros": [],
    }

    # Carregar arquivo
    rows: list[dict[str, Any]] = _load_file(file_path)

    # Processar linhas
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                result: str | None = _process_row(row, idx, stats, pendencias)
                if result == "skip":
                    continue
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append(
                    {
                        "linha": idx,
                        "erro": str(e),
                        "row": row,
                    }
                )

        if dry_run:
            transaction.set_rollback(True)

    # Gerar relatório
    report: dict[str, Any] = {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": file_path,
    }
    report_path: Path = OUT_DIR / "import_dat_cadastros_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    return report


def _load_file(file_path: str) -> list[dict[str, Any]]:
    """
    Carrega CSV ou XLSX em memória.

    Headers flexíveis (case-insensitive):
    - municipio/município
    - projeto
    - tipo_acao/tipo acao/tipo de acao
    - responsavel/responsável
    - observacao/observação
    - data_registro/data registro
    """
    ext: str = Path(file_path).suffix.lower()

    if ext == ".csv":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)
    elif ext in [".xlsx", ".xls"]:
        import openpyxl

        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.active
        rows: list[tuple[Any, ...]] = list(ws.iter_rows(values_only=True))
        headers: tuple[Any, ...] = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    else:
        raise ValueError(f"Formato não suportado: {ext}")


def _normalize_headers(row: dict[str, Any]) -> dict[str, str | None]:
    """
    Normaliza headers do CSV/XLSX para padrão interno.

    Retorna dict com chaves: municipio, projeto, tipo_acao, responsavel,
    observacao, data_registro.
    """
    lower_map: dict[str, str] = {k.lower(): k for k in row.keys() if k}
    normalized: dict[str, str | None] = {
        "municipio": None,
        "projeto": None,
        "tipo_acao": None,
        "responsavel": None,
        "observacao": None,
        "data_registro": None,
    }

    # Município
    for key in ["municipio", "município"]:
        if key in lower_map:
            normalized["municipio"] = str(row[lower_map[key]]).strip()
            break

    # Projeto
    if "projeto" in lower_map:
        normalized["projeto"] = str(row[lower_map["projeto"]]).strip()

    # Tipo de ação
    for key in ["tipo_acao", "tipo acao", "tipo de acao", "tipo_ação", "tipo ação", "tipo de ação", "tipo"]:
        if key in lower_map:
            val: str = str(row[lower_map[key]]).strip()
            if val:
                normalized["tipo_acao"] = val
                break

    # Responsável (email ou nome)
    for key in ["responsavel", "responsável", "email"]:
        if key in lower_map:
            val_resp: str = str(row[lower_map[key]]).strip()
            if val_resp:
                normalized["responsavel"] = val_resp
                break

    # Data de registro
    for key in ["data_registro", "data registro", "data"]:
        if key in lower_map:
            normalized["data_registro"] = row[lower_map[key]]
            break

    # Observação
    for key in ["observacao", "observação", "obs"]:
        if key in lower_map:
            val_obs: Any = row[lower_map[key]]
            normalized["observacao"] = str(val_obs).strip() if val_obs else None
            break

    return normalized


def _process_row(
    row: dict[str, Any], idx: int, stats: dict[str, Any], pendencias: dict[str, list[dict[str, Any]]]
) -> str | None:
    """
    Processa uma linha do CSV/XLSX.

    Returns:
        "skip" se linha deve ser pulada, None caso contrário
    """
    norm: dict[str, str | None] = _normalize_headers(row)

    # Resolver município
    municipio_nome: str | None = norm["municipio"]
    if not municipio_nome:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": None})
        return "skip"

    municipio: Municipio | None = Municipio.objects.filter(nome__iexact=norm_text(municipio_nome)).first()
    if not municipio:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": municipio_nome})
        return "skip"

    # Resolver projeto
    projeto_nome: str | None = norm["projeto"]
    if not projeto_nome:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": None})
        return "skip"

    projeto: Projeto | None = Projeto.objects.filter(nome__iexact=norm_text(projeto_nome)).first()
    if not projeto:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": projeto_nome})
        return "skip"

    # Tipo de ação (obrigatório)
    tipo_acao: str | None = norm["tipo_acao"]
    if not tipo_acao:
        stats["skipped"]["tipo_acao"] += 1
        pendencias["tipo_acao"].append({"linha": idx, "valor": None})
        return "skip"

    # Resolver responsável (opcional)
    responsavel: Usuario | None = None
    responsavel_val: str | None = norm["responsavel"]
    if responsavel_val:
        if "@" in responsavel_val:
            responsavel = resolve_user_by_email(responsavel_val)
        else:
            responsavel = resolve_user_by_name(responsavel_val)

        if not responsavel:
            stats["skipped"]["responsavel"] += 1
            pendencias["responsaveis"].append({"linha": idx, "valor": responsavel_val})
            # Não retorna skip, responsável é opcional

    # Parsear data de registro
    data_registro: date | None = _parse_date(norm["data_registro"])

    # Normalizar tipo_acao para hash consistente
    tipo_norm: str = norm_text(tipo_acao)

    # Criar external_hash (baseado em identidade estável)
    # external_hash baseado em identidade (município, projeto, tipo_acao, responsável).
    # Dados variáveis (data_registro/obs) atualizam o mesmo registro.
    resp_id: int | str = getattr(responsavel, "id", "NA")
    hash_key: str = f"{municipio.id}|{projeto.id}|{tipo_norm}|{resp_id}"
    external_hash: ExternalHash = hashlib.sha1(hash_key.encode()).hexdigest()

    # Verificar se já existe registro com este external_hash
    existing: AcaoDAT | None = AcaoDAT.objects.filter(external_hash=external_hash).first()

    # Preparar campos para criação/atualização
    defaults: dict[str, Any] = {
        "municipio": municipio,
        "projeto": projeto,
        "tipo_acao": tipo_acao,
        "responsavel": responsavel,
        "observacao": norm["observacao"],
        "data_registro": data_registro,
    }

    if existing:
        # Detectar mudanças comparando campos
        changed: bool = any(getattr(existing, k) != v for k, v in defaults.items())

        if changed:
            # Atualizar campos modificados
            for k, v in defaults.items():
                setattr(existing, k, v)
            existing.save(update_fields=list(defaults.keys()))
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        # Criar novo registro
        AcaoDAT.objects.create(external_hash=external_hash, **defaults)
        stats["created"] += 1

    return None


def _parse_date(val: Any) -> date | None:
    """
    Tenta parsear data de múltiplos formatos (robusto).

    Suporta:
    - None/vazio → None
    - date object → retorna direto
    - datetime object → .date()
    - int/float (Excel serial) → conversão
    - str numérica (Excel serial) → conversão
    - str ISO → yyyy-mm-dd[THH:MM:SS]
    - str BR → dd/mm/yyyy ou dd/mm/yy
    """
    if val is None:
        return None

    # date object (não datetime)
    if isinstance(val, date) and not isinstance(val, datetime):
        return val

    # datetime object
    if isinstance(val, datetime):
        return val.date()

    # String
    s: str = str(val).strip()
    if not s:
        return None

    # ISO (YYYY-MM-DD[THH:MM:SS])
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        pass

    # dd/mm/YYYY ou dd/mm/YY
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass

    # Excel serial (float ou string numérica)
    try:
        n: float = float(s)
        base: datetime = datetime(1899, 12, 30)
        return (base + timedelta(days=int(n))).date()
    except Exception:
        return None
