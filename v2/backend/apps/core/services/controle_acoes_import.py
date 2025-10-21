"""
Serviço de import para AcaoControle.

Lê CSV/XLSX e cria/atualiza AcaoControle por external_hash único.

Regras de negócio:
- Município/Projeto resolvidos por nome (norm_text)
- Coordenador resolvido por email > nome
- Datas parseadas: ISO, dd/mm/yyyy, dd/mm/yy, Excel serial
- Idempotência: SHA1(municipio_id|projeto_id|coordenador_id)
  - external_hash baseado em identidade estável
  - Dados variáveis (datas/obs) atualizam o mesmo registro
- Relatório em out_etl/import_acoes_controle_report.json
"""

import csv
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import transaction

from apps.core.models import AcaoControle, Municipio, Projeto
from apps.dat_ingest.services.acompanhamento_normalize import norm_text
from apps.dat_ingest.services.resolvers import (
    resolve_user_by_email,
    resolve_user_by_name,
)

OUT_DIR = Path(settings.BASE_DIR) / "out_etl"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def import_acoes_controle(file_path: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Importa ações de controle de CSV/XLSX.

    Args:
        file_path: Caminho do arquivo
        dry_run: Se True, simula sem gravar

    Returns:
        Dict com stats e pendências
    """
    stats = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"municipio": 0, "projeto": 0, "coordenador": 0, "dates": 0, "other": 0},
    }
    pendencias = {
        "municipios": [],
        "projetos": [],
        "coordenadores": [],
        "dates": [],
        "outros": [],
    }

    # Carregar arquivo
    rows = _load_file(file_path)

    # Processar linhas
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                result = _process_row(row, idx, stats, pendencias)
                if result == "skip":
                    continue
            except Exception as e:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append({
                    "linha": idx,
                    "erro": str(e),
                    "row": row,
                })

        if dry_run:
            transaction.set_rollback(True)

    # Gerar relatório
    report = {
        "stats": stats,
        "pendencias": pendencias,
        "dry_run": dry_run,
        "file": file_path,
    }
    report_path = OUT_DIR / "import_acoes_controle_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    return report


def _load_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Carrega CSV ou XLSX em memória.

    Headers flexíveis (case-insensitive):
    - municipio/município
    - projeto
    - coordenador
    - data_entrega/data entrega
    - data_carta/data carta
    - contato_inicial/contato inicial
    - data_reuniao/data_reunião/data reunião
    - observacao/observação
    """
    ext = Path(file_path).suffix.lower()

    if ext == ".csv":
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return list(reader)
    elif ext in [".xlsx", ".xls"]:
        import openpyxl
        wb = openpyxl.load_workbook(file_path, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = rows[0]
        return [dict(zip(headers, row)) for row in rows[1:]]
    else:
        raise ValueError(f"Formato não suportado: {ext}")


def _normalize_headers(row: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Normaliza headers do CSV/XLSX para padrão interno.

    Retorna dict com chaves: municipio, projeto, coordenador, data_entrega,
    data_carta, contato_inicial, data_reuniao, observacao.
    """
    lower_map = {k.lower(): k for k in row.keys() if k}
    normalized = {
        "municipio": None,
        "projeto": None,
        "coordenador": None,
        "data_entrega": None,
        "data_carta": None,
        "contato_inicial": None,
        "data_reuniao": None,
        "observacao": None,
    }

    # Município
    for key in ["municipio", "município"]:
        if key in lower_map:
            normalized["municipio"] = str(row[lower_map[key]]).strip()
            break

    # Projeto
    if "projeto" in lower_map:
        normalized["projeto"] = str(row[lower_map["projeto"]]).strip()

    # Coordenador (email ou nome)
    for key in ["coordenador", "email", "responsavel", "responsável"]:
        if key in lower_map:
            val = str(row[lower_map[key]]).strip()
            if val:
                normalized["coordenador"] = val
                break

    # Datas
    for key in ["data_entrega", "data entrega"]:
        if key in lower_map:
            normalized["data_entrega"] = row[lower_map[key]]
            break

    for key in ["data_carta", "data carta"]:
        if key in lower_map:
            normalized["data_carta"] = row[lower_map[key]]
            break

    for key in ["contato_inicial", "contato inicial"]:
        if key in lower_map:
            normalized["contato_inicial"] = row[lower_map[key]]
            break

    for key in ["data_reuniao", "data_reunião", "data reunião"]:
        if key in lower_map:
            normalized["data_reuniao"] = row[lower_map[key]]
            break

    # Observação
    for key in ["observacao", "observação", "obs"]:
        if key in lower_map:
            val = row[lower_map[key]]
            normalized["observacao"] = str(val).strip() if val else None
            break

    return normalized


def _process_row(row: Dict[str, Any], idx: int, stats: dict, pendencias: dict) -> Optional[str]:
    """
    Processa uma linha do CSV/XLSX.

    Returns:
        "skip" se linha deve ser pulada, None caso contrário
    """
    norm = _normalize_headers(row)

    # Resolver município
    municipio_nome = norm["municipio"]
    if not municipio_nome:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": None})
        return "skip"

    municipio = Municipio.objects.filter(nome__iexact=norm_text(municipio_nome)).first()
    if not municipio:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": municipio_nome})
        return "skip"

    # Resolver projeto
    projeto_nome = norm["projeto"]
    if not projeto_nome:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": None})
        return "skip"

    projeto = Projeto.objects.filter(nome__iexact=norm_text(projeto_nome)).first()
    if not projeto:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": projeto_nome})
        return "skip"

    # Resolver coordenador (opcional)
    coordenador = None
    coordenador_val = norm["coordenador"]
    if coordenador_val:
        if "@" in coordenador_val:
            coordenador = resolve_user_by_email(coordenador_val)
        else:
            coordenador = resolve_user_by_name(coordenador_val)

        if not coordenador:
            stats["skipped"]["coordenador"] += 1
            pendencias["coordenadores"].append({"linha": idx, "valor": coordenador_val})
            # Não retorna skip, coordenador é opcional

    # Parsear datas
    data_entrega = _parse_date(norm["data_entrega"])
    data_carta = _parse_date(norm["data_carta"])
    contato_inicial = _parse_date(norm["contato_inicial"])
    data_reuniao = _parse_date(norm["data_reuniao"])

    # Criar external_hash (baseado em identidade estável)
    # external_hash baseado em identidade (município, projeto, coordenador).
    # Dados variáveis (datas/obs) atualizam o mesmo registro.
    coord_id = getattr(coordenador, "id", "NA")
    hash_key = f"{municipio.id}|{projeto.id}|{coord_id}"
    external_hash = hashlib.sha1(hash_key.encode()).hexdigest()

    # Verificar se já existe registro com este external_hash
    existing = AcaoControle.objects.filter(external_hash=external_hash).first()

    # Preparar campos para criação/atualização
    defaults = {
        "municipio": municipio,
        "projeto": projeto,
        "coordenador": coordenador,
        "data_entrega": data_entrega,
        "data_carta": data_carta,
        "contato_inicial": contato_inicial,
        "data_reuniao": data_reuniao,
        "observacao": norm["observacao"],
    }

    if existing:
        # Detectar mudanças comparando campos
        changed = any(getattr(existing, k) != v for k, v in defaults.items())

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
        AcaoControle.objects.create(external_hash=external_hash, **defaults)
        stats["created"] += 1

    return None


def _parse_date(val: Any) -> Optional[date]:
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
    s = str(val).strip()
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
        n = float(s)
        base = datetime(1899, 12, 30)
        return (base + timedelta(days=int(n))).date()
    except Exception:
        return None
