"""
Service para importacao de Eventos (Solicitacao + Participation) via upload.

Padrao: dry_run + external_hash para idempotencia.

Colunas esperadas:
- municipio (obrigatorio): nome do municipio
- projeto (obrigatorio): nome do projeto
- tipo_evento (obrigatorio): nome do tipo de evento
- data (obrigatorio): data do evento
- hora_inicio (obrigatorio): hora de inicio
- hora_fim (obrigatorio): hora de fim (> hora_inicio)
- coordenador (obrigatorio): email ou nome do coordenador
- formador1-5 (opcional): email ou nome dos formadores
- encontro (opcional): numero do encontro
- segmento (opcional): segmento educacional
- local (opcional): local do evento

Regras de negocio (PA):
- Se projeto.fluxo == 'SUPER' e data >= hoje: status = 'pendente'
- Se projeto.fluxo == 'NAO_SUPER' ou data < hoje: status = 'aprovado'
- Criar Participation para coordenador (role='COORDENADOR')
- Criar Participation para cada formador1-5 (role='FORMADOR')
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

import hashlib
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

import pandas as pd

from apps.core.models import Participation, Solicitacao
from apps.core.services.resolvers import (
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
    resolve_user_by_name,
)

TZ = ZoneInfo("America/Fortaleza")


def import_eventos_from_file(*, path: str, dry_run: bool = True) -> dict[str, Any]:
    """
    Importa eventos de CSV/XLSX.

    Args:
        path: Caminho do arquivo CSV/XLSX
        dry_run: Se True, nao persiste (rollback)

    Returns:
        {
            "stats": {
                "solicitacoes": {"created": N, "updated": N, "unchanged": N},
                "participations": {"created": N, "updated": N},
                "skipped": {"municipio": N, "projeto": N, "tipo_evento": N,
                            "coordenador": N, "dates": N, "other": N}
            },
            "pendencias": {
                "municipios": [...], "projetos": [...], "tipos_evento": [...],
                "usuarios": [...], "dates": [...], "outros": [...]
            },
            "dry_run": bool,
            "file": str
        }
    """
    stats: dict[str, Any] = {
        "solicitacoes": {"created": 0, "updated": 0, "unchanged": 0},
        "participations": {"created": 0, "updated": 0},
        "skipped": {
            "municipio": 0,
            "projeto": 0,
            "tipo_evento": 0,
            "coordenador": 0,
            "dates": 0,
            "other": 0,
        },
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "municipios": [],
        "projetos": [],
        "tipos_evento": [],
        "usuarios": [],
        "dates": [],
        "outros": [],
    }

    # Data de referencia para status
    today = timezone.localdate()

    # Carregar arquivo
    rows = _load_file(path)

    # Processar linhas
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                _process_row(row, idx, stats, pendencias, today)
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

    # Municipio
    for key in ["município", "municipio", "cidade", "city"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["municipio"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["municipio"] = ""

    # Projeto
    for key in ["projeto", "project", "setor"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["projeto"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["projeto"] = ""

    # Tipo Evento
    for key in ["tipo_evento", "tipo", "type", "event_type"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["tipo_evento"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["tipo_evento"] = ""

    # Data
    for key in ["data", "date", "dia"]:
        if key in lower_map:
            normalized["data"] = lower_map[key]
            break
    else:
        normalized["data"] = None

    # Hora Inicio
    for key in ["hora_inicio", "hora_início", "inicio", "início", "start_time", "start"]:
        if key in lower_map:
            normalized["hora_inicio"] = lower_map[key]
            break
    else:
        normalized["hora_inicio"] = None

    # Hora Fim
    for key in ["hora_fim", "fim", "end_time", "end"]:
        if key in lower_map:
            normalized["hora_fim"] = lower_map[key]
            break
    else:
        normalized["hora_fim"] = None

    # Coordenador
    for key in ["coordenador", "coord", "coord_email", "coordinator"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["coordenador"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["coordenador"] = ""

    # Formadores 1-5
    for i in range(1, 6):
        for key in [f"formador{i}", f"formador_{i}", f"trainer{i}"]:
            if key in lower_map:
                val = lower_map[key]
                normalized[f"formador{i}"] = str(val).strip() if val and str(val) != "nan" else ""
                break
        else:
            normalized[f"formador{i}"] = ""

    # Encontro
    for key in ["encontro", "ef", "encounter", "meeting"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["encontro"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["encontro"] = ""

    # Segmento
    for key in ["segmento", "segment", "nivel"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["segmento"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["segmento"] = ""

    # Local
    for key in ["local", "location", "endereco", "endereço"]:
        if key in lower_map:
            val = lower_map[key]
            normalized["local"] = str(val).strip() if val and str(val) != "nan" else ""
            break
    else:
        normalized["local"] = ""

    return normalized


def _parse_date_flexible(value: Any) -> date | None:
    """Parse date flexivel (ISO, dd/mm/yyyy, Excel serial)."""
    if not value or str(value) == "nan":
        return None

    # Se ja e datetime
    if isinstance(value, datetime):
        return value.date()

    # Se e date
    if isinstance(value, date):
        return value

    # Se e numero (Excel serial)
    if isinstance(value, (int, float)):
        try:
            base_date = datetime(1899, 12, 30)
            return (base_date + timedelta(days=float(value))).date()
        except Exception:
            return None

    # Se e string
    value_str = str(value).strip()
    if not value_str:
        return None

    # Tentar ISO
    try:
        return datetime.fromisoformat(value_str).date()
    except ValueError:
        pass

    # Tentar dd/mm/yyyy
    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            pass

    return None


def _parse_time_flexible(value: Any) -> time | None:
    """Parse time flexivel (HH:MM, decimal hours, Excel serial)."""
    if not value or str(value) == "nan":
        return None

    # Se ja e datetime ou time
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value

    # Se e numero (Excel serial time ou decimal hours)
    if isinstance(value, (int, float)):
        try:
            # Excel serial time (fraction of day)
            if 0 <= float(value) < 1:
                total_seconds = float(value) * 24 * 3600
                hours = int(total_seconds // 3600)
                minutes = int((total_seconds % 3600) // 60)
                return time(hours, minutes)
            # Decimal hours (e.g., 8.5 = 08:30)
            elif 0 <= float(value) < 24:
                hours = int(float(value))
                minutes = int((float(value) - hours) * 60)
                return time(hours, minutes)
        except Exception:
            return None

    # Se e string
    value_str = str(value).strip()
    if not value_str:
        return None

    # Tentar HH:MM ou H:MM
    for fmt in ["%H:%M", "%H:%M:%S"]:
        try:
            return datetime.strptime(value_str, fmt).time()
        except ValueError:
            pass

    return None


def _compute_external_hash(
    municipio_id: int,
    projeto_id: int,
    tipo_evento_id: int,
    data_evento: date,
    hora_inicio: time,
    hora_fim: time,
) -> str:
    """
    Gera external_hash SHA1 para idempotencia.

    Hash: SHA1(municipio_id|projeto_id|tipo_id|data|hora_inicio|hora_fim)
    """
    parts = [
        str(municipio_id),
        str(projeto_id),
        str(tipo_evento_id),
        data_evento.isoformat(),
        hora_inicio.strftime("%H:%M"),
        hora_fim.strftime("%H:%M"),
    ]
    content = "|".join(parts)
    return hashlib.sha1(content.encode("utf-8"), usedforsecurity=False).hexdigest()


def _determine_status(projeto: Any, data_evento: date, today: date) -> str:
    """
    Determina status da solicitacao conforme regras PA:
    - data < hoje → aprovado
    - projeto.fluxo == 'SUPER' → pendente
    - projeto.fluxo == 'NAO_SUPER' → aprovado
    """
    if data_evento < today:
        return "aprovado"

    if projeto and projeto.fluxo == "SUPER":
        return "pendente"

    return "aprovado"


def _resolve_user(identifier: str) -> Any:
    """Resolve usuario por email ou nome."""
    if not identifier:
        return None

    # Tentar por email primeiro
    if "@" in identifier:
        user = resolve_user_by_email(identifier)
        if user:
            return user

    # Tentar por nome
    return resolve_user_by_name(identifier)


def _process_row(
    row: dict[str, Any],
    linha_num: int,
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    today: date,
) -> None:
    """Processa uma linha do arquivo."""
    # Resolver municipio
    municipio_nome = row.get("municipio", "").strip()
    if not municipio_nome:
        stats["skipped"]["municipio"] += 1
        return

    municipio = resolve_municipio(municipio_nome)
    if not municipio:
        stats["skipped"]["municipio"] += 1
        pendencias["municipios"].append(
            {
                "linha": linha_num,
                "nome": municipio_nome,
            }
        )
        return

    # Resolver projeto
    projeto_nome = row.get("projeto", "").strip()
    if not projeto_nome:
        stats["skipped"]["projeto"] += 1
        return

    projeto = resolve_projeto(projeto_nome)
    if not projeto:
        stats["skipped"]["projeto"] += 1
        pendencias["projetos"].append(
            {
                "linha": linha_num,
                "nome": projeto_nome,
            }
        )
        return

    # Resolver tipo_evento
    tipo_nome = row.get("tipo_evento", "").strip()
    if not tipo_nome:
        stats["skipped"]["tipo_evento"] += 1
        return

    tipo_evento = resolve_tipo_evento(tipo_nome)
    if not tipo_evento:
        stats["skipped"]["tipo_evento"] += 1
        pendencias["tipos_evento"].append(
            {
                "linha": linha_num,
                "nome": tipo_nome,
            }
        )
        return

    # Parse data e horas
    data_evento = _parse_date_flexible(row.get("data"))
    hora_inicio = _parse_time_flexible(row.get("hora_inicio"))
    hora_fim = _parse_time_flexible(row.get("hora_fim"))

    if not data_evento or not hora_inicio or not hora_fim:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "data": str(row.get("data")),
                "hora_inicio": str(row.get("hora_inicio")),
                "hora_fim": str(row.get("hora_fim")),
            }
        )
        return

    if hora_fim <= hora_inicio:
        stats["skipped"]["dates"] += 1
        pendencias["dates"].append(
            {
                "linha": linha_num,
                "data": str(data_evento),
                "hora_inicio": str(hora_inicio),
                "hora_fim": str(hora_fim),
                "erro": "hora_fim <= hora_inicio",
            }
        )
        return

    # Resolver coordenador (obrigatorio)
    coord_identifier = row.get("coordenador", "").strip()
    if not coord_identifier:
        stats["skipped"]["coordenador"] += 1
        return

    coordenador = _resolve_user(coord_identifier)
    if not coordenador:
        stats["skipped"]["coordenador"] += 1
        pendencias["usuarios"].append(
            {
                "linha": linha_num,
                "identificador": coord_identifier,
                "role": "COORDENADOR",
            }
        )
        return

    # Combinar data + hora timezone-aware
    inicio = datetime.combine(data_evento, hora_inicio)
    inicio = timezone.make_aware(inicio, TZ)
    fim = datetime.combine(data_evento, hora_fim)
    fim = timezone.make_aware(fim, TZ)

    # Determinar status (PA rules)
    status = _determine_status(projeto, data_evento, today)

    # Campos opcionais
    encontro = row.get("encontro", "").strip()
    segmento = row.get("segmento", "").strip()
    local = row.get("local", "").strip()

    # Montar observacoes
    observacoes_parts = []
    if encontro:
        observacoes_parts.append(f"Encontro: {encontro}")
    if segmento:
        observacoes_parts.append(f"Segmento: {segmento}")
    observacoes = " | ".join(observacoes_parts)

    # Compute external_hash para idempotencia
    external_hash = _compute_external_hash(
        municipio.id,  # pyright: ignore[reportAttributeAccessIssue]
        projeto.id,  # pyright: ignore[reportAttributeAccessIssue]
        tipo_evento.id,  # pyright: ignore[reportAttributeAccessIssue]
        data_evento,
        hora_inicio,
        hora_fim,
    )

    # Upsert Solicitacao
    solicitacao, created = Solicitacao.objects.update_or_create(
        external_hash=external_hash,
        defaults={
            "usuario": coordenador,
            "coordenador": coordenador,
            "municipio": municipio,
            "projeto": projeto,
            "tipo_evento": tipo_evento,
            "inicio": inicio,
            "fim": fim,
            "status": status,
            "observacoes": observacoes,
            "local": local,
            "encontro": encontro,
            "segmento": segmento,
        },
    )

    if created:
        stats["solicitacoes"]["created"] += 1
    else:
        # Verificar se houve mudanca
        changed = False
        if solicitacao.status != status:
            changed = True
        if solicitacao.inicio != inicio or solicitacao.fim != fim:
            changed = True
        if solicitacao.local != local:
            changed = True

        if changed:
            stats["solicitacoes"]["updated"] += 1
        else:
            stats["solicitacoes"]["unchanged"] += 1

    # Criar Participations
    _process_participations(solicitacao, coordenador, row, stats, pendencias, linha_num)


def _process_participations(
    solicitacao: Any,
    coordenador: Any,
    row: dict[str, Any],
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    linha_num: int,
) -> None:
    """Cria Participations para coordenador e formadores."""
    # Participation para coordenador
    _, created = Participation.objects.get_or_create(
        solicitacao=solicitacao,
        usuario=coordenador,
        role=Participation.Role.COORDENADOR,
    )
    if created:
        stats["participations"]["created"] += 1
    else:
        stats["participations"]["updated"] += 1

    # Participations para formadores (1-5)
    for i in range(1, 6):
        formador_id = row.get(f"formador{i}", "").strip()
        if not formador_id:
            continue

        formador = _resolve_user(formador_id)
        if not formador:
            pendencias["usuarios"].append(
                {
                    "linha": linha_num,
                    "identificador": formador_id,
                    "role": f"FORMADOR{i}",
                }
            )
            continue

        _, created = Participation.objects.get_or_create(
            solicitacao=solicitacao,
            usuario=formador,
            role=Participation.Role.FORMADOR,
        )
        if created:
            stats["participations"]["created"] += 1
        else:
            stats["participations"]["updated"] += 1
