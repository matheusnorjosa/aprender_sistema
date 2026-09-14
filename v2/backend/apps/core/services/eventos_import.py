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

Regras de negocio (PA-01/PA-04):
- Status inicial decidido por resolve_initial_status (mesma regra da API):
  - projeto.fluxo == 'SUPER'      -> 'pendente' (PA-01: SUPER NUNCA auto-aprova)
  - projeto.fluxo == 'NAO_SUPER'  -> 'aprovado'
  - A data do evento NAO influencia o STATUS (passado/futuro irrelevante).
- Criar Participation para coordenador (role='COORDENADOR')
- Criar Participation para cada formador1-5 (role='FORMADOR')

Disponibilidade e reimport (#1620/M08-12 e #1628/M10-07):
- Gate RD-01..08 (check_solicitacao_availability): so p/ evento FUTURO. Evento futuro em
  conflito NAO e gravado -> pendencia `availability`. Historico (data passada) entra sem checar.
- Reimport NUNCA sobrescreve decisao humana: se um campo protegido (status/usuario/
  coordenador/local) divergir da linha existente -> pendencia `protected`, sem escrita.
  Sem divergencia, atualiza so observacoes/encontro (diff real em `updated`/`unchanged`).
- Participante ocupante que sumiu da planilha no reimport e REPORTADO em `orfaos`, nunca removido.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

import pandas as pd

from apps.core.imports.hashing import stable_import_hash
from apps.core.imports.normalization import normalize_blank
from apps.core.imports.row_errors import registrar_erro_import
from apps.core.models import Participation, Solicitacao
from apps.core.services.availability_service import ENFORCED_ROLES
from apps.core.services.resolvers import (
    resolve_municipio,
    resolve_projeto,
    resolve_tipo_evento,
    resolve_user_by_email,
    resolve_user_by_name,
)
from apps.core.services.solicitacao_availability import check_solicitacao_availability
from apps.core.services.solicitacao_create import resolve_initial_status

TZ = ZoneInfo("America/Fortaleza")

# Campos que carregam DECISAO ou EDICAO humana: o reimport NUNCA os sobrescreve (#1628/M10-07).
# `inicio`/`fim`/`segmento` nao entram porque fazem parte do external_hash (mesma chave => mesmos
# valores), logo nunca divergem para a mesma linha.
_PROTECTED_FIELDS: tuple[str, ...] = ("status", "usuario_id", "coordenador_id", "local")


class _AvailabilityConflict(Exception):
    """Evento FUTURO importado conflita com a disponibilidade (RD-01..08) de um participante.

    Levantada DENTRO do savepoint-per-row, DEPOIS de a Solicitacao+Participation terem sido
    gravadas (o gate le os participantes ja persistidos) e ANTES de qualquer contagem em `stats`
    (increment de dict nao volta no rollback). O laco principal a converte na pendencia
    `availability`. So se aplica a evento futuro — historico entra sem checar (#1620/M08-12).
    """

    def __init__(self, detail: dict[str, Any]) -> None:
        super().__init__("availability_conflict")
        self.detail = detail


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
            "availability": 0,
            "protected": 0,
            "other": 0,
        },
    }
    pendencias: dict[str, list[dict[str, Any]]] = {
        "municipios": [],
        "projetos": [],
        "tipos_evento": [],
        "usuarios": [],
        "dates": [],
        "availability": [],
        "protected": [],
        "orfaos": [],
        "outros": [],
    }

    # Carregar arquivo
    rows = _load_file(path)

    # Processar linhas.
    # ASQ-016: savepoint-per-row. Outer atomic still owns the dry-run
    # rollback; inner atomic isolates one bad row from the rest.
    with transaction.atomic():
        for idx, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():  # savepoint
                    _process_row(row, idx, stats, pendencias)
            except _AvailabilityConflict as exc:
                # Evento futuro em conflito: o savepoint ja desfez a Solicitacao/Participation.
                # `stats` ainda nao foi tocado (contagem so acontece apos o gate passar).
                stats["skipped"]["availability"] += 1
                pendencias["availability"].append(exc.detail)
            except Exception:
                stats["skipped"]["other"] += 1
                pendencias["outros"].append(
                    {
                        "linha": idx,
                        "erro": registrar_erro_import(importer="eventos", linha=idx),
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
            normalized["municipio"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["municipio"] = ""

    # Projeto
    for key in ["projeto", "project", "setor"]:
        if key in lower_map:
            normalized["projeto"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["projeto"] = ""

    # Tipo Evento
    for key in ["tipo_evento", "tipo", "type", "event_type"]:
        if key in lower_map:
            normalized["tipo_evento"] = normalize_blank(lower_map[key])
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
            normalized["coordenador"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["coordenador"] = ""

    # Formadores 1-5
    for i in range(1, 6):
        for key in [f"formador{i}", f"formador_{i}", f"trainer{i}"]:
            if key in lower_map:
                normalized[f"formador{i}"] = normalize_blank(lower_map[key])
                break
        else:
            normalized[f"formador{i}"] = ""

    # Encontro
    for key in ["encontro", "ef", "encounter", "meeting"]:
        if key in lower_map:
            normalized["encontro"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["encontro"] = ""

    # Segmento
    for key in ["segmento", "segment", "nivel"]:
        if key in lower_map:
            normalized["segmento"] = normalize_blank(lower_map[key])
            break
    else:
        normalized["segmento"] = ""

    # Local
    for key in ["local", "location", "endereco", "endereço"]:
        if key in lower_map:
            normalized["local"] = normalize_blank(lower_map[key])
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
    segmento: str,
) -> str:
    """
    Gera external_hash SHA1 para idempotencia.

    Hash: SHA1(municipio_id|projeto_id|tipo_id|data|hora_inicio|hora_fim|segmento)

    O `segmento` faz parte da CHAVE NATURAL do evento (#1915): duas turmas no mesmo
    slot (municipio/projeto/tipo/data/hora) diferindo so no segmento sao eventos
    DISTINTOS; sem o segmento na chave o hash colidia e o `update_or_create` sobrescrevia
    o primeiro em silencio. Usa o segmento BRUTO (so `.strip()`, feito no chamador) — mais
    discriminacao e o lado seguro para um bug de sub-discriminacao. ADR-012 congela o
    ALGORITMO (SHA-1/encoding), nao a composicao de campos; por isso a migracao 0101
    re-chaveia as linhas ja persistidas. Limite inerente: eventos com segmento vazio
    permanecem indistinguiveis e ainda podem colapsar (nao ha campo que os separe).
    """
    parts = [
        str(municipio_id),
        str(projeto_id),
        str(tipo_evento_id),
        data_evento.isoformat(),
        hora_inicio.strftime("%H:%M"),
        hora_fim.strftime("%H:%M"),
        segmento,
    ]
    return stable_import_hash(*parts)


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

    # Determinar status inicial (PA-01/PA-04) — mesma regra da API.
    # SUPER -> pendente, NAO_SUPER -> aprovado. A data do evento NAO decide.
    status = resolve_initial_status(projeto=projeto).status

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
        segmento,
    )

    # Idempotencia + protecao (#1628/M10-07): buscar a linha existente COM lock. select_for_update
    # fecha o lost-update (leitura->escrita concorrente) e serializa reimports da mesma linha.
    existing = Solicitacao.objects.select_for_update().filter(external_hash=external_hash).first()

    if existing is not None:
        _reimport_existing(
            existing, coordenador, status, local, observacoes, encontro, row, stats, pendencias, linha_num
        )
        return

    # Linha NOVA: cria, popula participacoes e (so p/ evento futuro) checa disponibilidade
    # ANTES de contabilizar. As contagens ficam para o fim porque increment de dict nao volta
    # no rollback do savepoint disparado por _AvailabilityConflict.
    solicitacao = Solicitacao.objects.create(
        external_hash=external_hash,
        usuario=coordenador,
        coordenador=coordenador,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=inicio,
        fim=fim,
        status=status,
        observacoes=observacoes,
        local=local,
        encontro=encontro,
        segmento=segmento,
    )
    part = _sync_participations(solicitacao, coordenador, row, linha_num)

    # #1620/M08-12: gate RD-01..08 so p/ evento FUTURO. Historico (data passada) entra sem
    # checar — ja aconteceu; bloquear reescreveria o passado. Futuro em conflito NAO grava.
    if inicio > timezone.now():
        guard = check_solicitacao_availability(solicitacao)
        if not guard.ok:
            raise _AvailabilityConflict(
                {
                    "linha": linha_num,
                    "motivo": "conflito de disponibilidade (evento futuro)",
                    "participantes": [{"usuario_id": p.usuario_id, "nome": p.usuario_nome} for p in guard.blocked],
                }
            )

    # Passou (ou historico): agora contabiliza (o savepoint desta linha vai commitar).
    stats["solicitacoes"]["created"] += 1
    _apply_participation_result(part, stats, pendencias)


def _reimport_existing(
    existing: Any,
    coordenador: Any,
    status: str,
    local: str,
    observacoes: str,
    encontro: str,
    row: dict[str, Any],
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
    linha_num: int,
) -> None:
    """Reimport de linha existente: protege decisao humana, atualiza so o descritivo (#1628).

    Se um campo PROTEGIDO divergir (status decidido por humano, reatribuicao de dono, ou edicao
    manual de local), a linha NAO e sobrescrita — vira pendencia `protected` p/ decisao humana.
    Sem divergencia protegida, atualiza apenas observacoes/encontro e reporta o diff REAL (o
    `updated` deixa de ser codigo morto: antes comparava a instancia JA mutada pelo upsert).
    """
    would_be: dict[str, Any] = {
        "status": status,
        "usuario_id": coordenador.pk,
        "coordenador_id": coordenador.pk,
        "local": local,
    }
    divergences = [f for f in _PROTECTED_FIELDS if getattr(existing, f) != would_be[f]]
    if divergences:
        stats["skipped"]["protected"] += 1
        pendencias["protected"].append({"linha": linha_num, "solicitacao_id": existing.pk, "campos": divergences})
        return

    changed_fields: list[str] = []
    if existing.observacoes != observacoes:
        existing.observacoes = observacoes
        changed_fields.append("observacoes")
    if existing.encontro != encontro:
        existing.encontro = encontro
        changed_fields.append("encontro")

    if changed_fields:
        existing.save(update_fields=changed_fields)
        stats["solicitacoes"]["updated"] += 1
    else:
        stats["solicitacoes"]["unchanged"] += 1

    _apply_participation_result(_sync_participations(existing, coordenador, row, linha_num), stats, pendencias)


def _sync_participations(
    solicitacao: Any,
    coordenador: Any,
    row: dict[str, Any],
    linha_num: int,
) -> dict[str, Any]:
    """Grava as Participations (coordenador + formadores) e detecta orfaos, SEM tocar `stats`.

    Devolve contagens/pendencias para o chamador aplicar: no caminho de evento novo a
    contabilizacao so pode acontecer DEPOIS do gate de disponibilidade (senao um evento
    revertido no rollback contaria). Orfao — participante ocupante que sumiu da planilha — e
    REPORTADO, nunca removido (decisao do dono 2026-09-14, #1628 item 4).
    """
    result: dict[str, Any] = {"created": 0, "updated": 0, "orfaos": [], "unresolved": []}
    sheet_usuario_ids: set[int] = {coordenador.pk}

    _, created = Participation.objects.get_or_create(
        solicitacao=solicitacao,
        usuario=coordenador,
        role=Participation.Role.COORDENADOR,
    )
    result["created" if created else "updated"] += 1

    for i in range(1, 6):
        formador_id = row.get(f"formador{i}", "").strip()
        if not formador_id:
            continue

        formador = _resolve_user(formador_id)
        if not formador:
            result["unresolved"].append({"linha": linha_num, "identificador": formador_id, "role": f"FORMADOR{i}"})
            continue

        _, created = Participation.objects.get_or_create(
            solicitacao=solicitacao,
            usuario=formador,
            role=Participation.Role.FORMADOR,
        )
        sheet_usuario_ids.add(formador.pk)
        result["created" if created else "updated"] += 1

    # Orfao: participante ocupante (ENFORCED_ROLES) que nao consta mais da planilha.
    orfaos = (
        Participation.objects.filter(solicitacao=solicitacao, role__in=ENFORCED_ROLES)
        .exclude(usuario_id__in=sheet_usuario_ids)
        .select_related("usuario")
    )
    for p in orfaos:
        result["orfaos"].append(
            {
                "linha": linha_num,
                "solicitacao_id": solicitacao.pk,
                "usuario_id": p.usuario_id,
                "nome": (str(p.usuario.get_full_name() or p.usuario.username) if p.usuario else None),
                "role": p.role,
            }
        )

    return result


def _apply_participation_result(
    result: dict[str, Any],
    stats: dict[str, Any],
    pendencias: dict[str, list[dict[str, Any]]],
) -> None:
    """Aplica a `stats`/`pendencias` o resultado de _sync_participations (apos o gate passar)."""
    stats["participations"]["created"] += result["created"]
    stats["participations"]["updated"] += result["updated"]
    pendencias["usuarios"].extend(result["unresolved"])
    pendencias["orfaos"].extend(result["orfaos"])
