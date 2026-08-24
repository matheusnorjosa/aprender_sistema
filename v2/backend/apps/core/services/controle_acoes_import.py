"""
Serviço de import de Ações → DATAcao (modelo operacional).

Onda 1 do programa de imports órfãos (v2/docs/plans/PLANO_IMPORTS_ORFAOS.md):
o import foi redirecionado do legacy ``AcaoControle`` (que nenhuma tela lê) para
``DATAcao``, lido pela AcoesPage em ``/dat/acoes-ciclo/``.

Regras de negócio:
- Município/Projeto resolvidos por nome (resolvers accent/alias-insensitive)
- Coordenador da origem (email/nome) → DATCoordenador (email → nome → null)
- Datas parseadas: ISO, dd/mm/yyyy, dd/mm/yy, Excel serial
- Mapa de datas: data_carta→data_carta, contato_inicial→data_contato,
  data_reuniao→data_reuniao, data_entrega→data_entrega
- Status por etapa DERIVADO: etapa com data preenchida → "concluído"; senão "pendente".
  (Inserção manual pela tela constrói a linha do tempo passo a passo; o import
  apenas reflete o que a data já indica.)
- observacao única da origem → observacao_carta (1ª etapa)
- created_by OBRIGATÓRIO (DATAcao.created_by é NOT NULL) — o endpoint passa request.user
- Idempotência: chave natural (municipio, projeto) via upsert
- Relatório em out_etl/import_acoes_controle_report.json
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q

from apps.core.imports.row_errors import registrar_erro_import
from apps.core.models import DATAcao, DATCoordenador, Municipio, Projeto, Usuario
from apps.core.services.resolvers import resolve_municipio, resolve_projeto

OUT_DIR: Path = Path(settings.BASE_DIR) / "out_etl"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def import_acoes_controle(
    file_path: str, dry_run: bool = False, *, created_by: Usuario | None = None
) -> dict[str, Any]:
    """
    Importa ações de CSV/XLSX para ``DATAcao``.

    Args:
        file_path: Caminho do arquivo
        dry_run: Se True, simula sem gravar (rollback)
        created_by: Usuário responsável pela importação (obrigatório —
            ``DATAcao.created_by`` é NOT NULL). O endpoint passa ``request.user``.

    Returns:
        Dict com stats e pendências

    Raises:
        ValueError: se ``created_by`` não for informado.
    """
    if created_by is None:
        raise ValueError("created_by é obrigatório (DATAcao.created_by é NOT NULL; o endpoint passa request.user).")

    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "skipped": {"municipio": 0, "projeto": 0, "coordenador": 0, "dates": 0, "other": 0},
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "municipios": [],
        "projetos": [],
        "coordenadores": [],
        "dates": [],
        "outros": [],
    }

    # Carregar arquivo
    rows: list[dict[str, Any]] = _load_file(file_path)

    # Processar linhas.
    # ASQ-016: savepoint-per-row. Outer atomic still owns the dry-run
    # rollback; inner atomic isolates one bad row from the rest.
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():  # savepoint
                    result: str | None = _process_row(row, idx, stats, pendencias, created_by)
                    if result == "skip":
                        continue
            except Exception:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append(
                    {
                        "linha": idx,
                        "erro": registrar_erro_import(importer="controle_acoes", linha=idx),
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
    report_path: Path = OUT_DIR / "import_acoes_controle_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    return report


def _load_file(file_path: str) -> list[dict[str, Any]]:
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


def _normalize_headers(row: dict[str, Any]) -> dict[str, str | None]:
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


def _resolve_dat_coordenador(value: str) -> DATCoordenador | None:
    """Mapeia o coordenador da origem (email ou nome) para um DATCoordenador.

    Ordem: email (principal ou alternativo) → nome → None. Coordenador é
    opcional em DATAcao (SET_NULL), então não-encontrado devolve None.
    """
    v = value.strip()
    if not v:
        return None
    if "@" in v:
        qs = DATCoordenador.objects.filter(Q(email__iexact=v) | Q(email_alternativo__iexact=v))
    else:
        qs = DATCoordenador.objects.filter(nome__iexact=v)
    # Guard de ambiguidade (#1837): email de coordenador é chave de CARGO (migra de dono); `.first()`
    # atrelaria a ação ao ocupante ATUAL da caixa. 1 match inequívoco → resolve; 0 ou 2+ → None.
    ids = list(qs.values_list("id", flat=True)[:2])
    if len(ids) == 1:
        return DATCoordenador.objects.get(pk=ids[0])
    return None


def _derive_status(data_etapa: date | None) -> str:
    """Deriva o status de uma etapa: tem data → concluído; senão pendente."""
    return DATAcao.StatusEtapa.CONCLUIDO if data_etapa else DATAcao.StatusEtapa.PENDENTE


def _process_row(
    row: dict[str, Any],
    idx: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    created_by: Usuario,
) -> str | None:
    """
    Processa uma linha do CSV/XLSX, gravando em ``DATAcao``.

    Returns:
        "skip" se linha deve ser pulada, None caso contrário
    """
    norm: dict[str, str | None] = _normalize_headers(row)

    # Resolver município (obrigatório)
    municipio_nome: str | None = norm["municipio"]
    if not municipio_nome:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": None})
        return "skip"

    # `resolve_municipio` é accent-insensitive (fallback NFKD) e parseia
    # formatos "Cidade - UF" / "Cidade/UF".
    municipio: Municipio | None = resolve_municipio(municipio_nome)
    if not municipio:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append({"linha": idx, "nome": municipio_nome})
        return "skip"

    # Resolver projeto (obrigatório)
    projeto_nome: str | None = norm["projeto"]
    if not projeto_nome:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": None})
        return "skip"

    projeto: Projeto | None = resolve_projeto(projeto_nome)
    if not projeto:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append({"linha": idx, "nome": projeto_nome})
        return "skip"

    # Resolver coordenador (opcional) → DATCoordenador
    coordenador: DATCoordenador | None = None
    coordenador_val: str | None = norm["coordenador"]
    if coordenador_val:
        coordenador = _resolve_dat_coordenador(coordenador_val)
        if not coordenador:
            stats["skipped"]["coordenador"] += 1
            pendencias["coordenadores"].append({"linha": idx, "valor": coordenador_val})
            # Não retorna skip — coordenador é opcional (SET_NULL)

    # Parsear datas (mapa AcaoControle → DATAcao)
    data_carta: date | None = _parse_date(norm["data_carta"])
    data_contato: date | None = _parse_date(norm["contato_inicial"])
    data_reuniao: date | None = _parse_date(norm["data_reuniao"])
    data_entrega: date | None = _parse_date(norm["data_entrega"])

    # observacao única da origem → observacao_carta (respeita max_length=500)
    observacao: str = (norm["observacao"] or "")[:500]

    # Campos operacionais (mutáveis) — base da detecção de mudança no upsert
    defaults: dict[str, Any] = {
        "coordenador": coordenador,
        "status_carta": _derive_status(data_carta),
        "data_carta": data_carta,
        "status_contato": _derive_status(data_contato),
        "data_contato": data_contato,
        "status_reuniao": _derive_status(data_reuniao),
        "data_reuniao": data_reuniao,
        "status_entrega": _derive_status(data_entrega),
        "data_entrega": data_entrega,
        "observacao_carta": observacao,
    }

    # Upsert idempotente pela chave natural (municipio, projeto)
    existing: DATAcao | None = DATAcao.objects.filter(municipio=municipio, projeto=projeto).first()

    if existing:
        changed: bool = any(getattr(existing, k) != v for k, v in defaults.items())
        if changed:
            for k, v in defaults.items():
                setattr(existing, k, v)
            existing.updated_by = created_by
            existing.save(update_fields=[*defaults.keys(), "updated_by"])
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
    else:
        DATAcao.objects.create(municipio=municipio, projeto=projeto, created_by=created_by, **defaults)
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
