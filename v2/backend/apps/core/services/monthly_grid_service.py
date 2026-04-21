"""
Service para compor grade mensal de disponibilidade.

Retorna uma grade mensal (ano/mês) com códigos por dia/pessoa:
- E: 1 evento
- 2: ≥2 eventos
- P: bloqueio parcial (sem evento, sem deslocamento)
- T: bloqueio total (sem evento, sem deslocamento)
- X: evento + bloqueio (com ou sem deslocamento)
- D: deslocamento apenas (sem eventos, sem bloqueios)
- D1: evento + deslocamento (sem bloqueio)

Precedência: X > D1 > 2 > E > T/P > D

Calcula CH mês/ano, ranking por CH mês (denso).
Details_index para dias com E/2/X/D1 (lista de eventos).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import Q
from django.utils import timezone

from apps.core.models import AvailabilityBlock, Deslocamento, EquipeGerencia, Participation, Solicitacao, Usuario
from apps.core.types import UserId


def build_monthly_grid(
    *,
    year: int,
    month: int,
    role: str,
    gerencia_id: int | None = None,
    sector: str | None = None,
    q: str | None = None,
    allowed_user_ids: list[UserId] | None = None,
) -> dict[str, Any]:
    """
    Compõe grade mensal de disponibilidade por pessoa (role).

    Args:
        year: Ano (YYYY)
        month: Mês (1..12)
        role: "FORMADOR" ou "COORDENADOR"
        gerencia_id: ID da gerência para filtrar. Quando especificado, filtra
            participações e eventos apenas dessa gerência. Quando None, mantém
            comportamento legado (apenas fluxo SUPER).
        sector: Filtro opcional por setor (projeto.nome)
        q: Filtro opcional por nome/email (icontains)
        allowed_user_ids: Lista de IDs de usuários permitidos (None = todos)

    Returns:
        {
            "days": [1, 2, 3, ..., ND] (lista de dias do mês),
            "legend": {...},
            "people": [{"id", "name", "email", "ch_month", "ch_year", "position_month"}],
            "cells": [[code_row0_day1, ...], [code_row1_day1, ...]] (matriz 2D),
            "details_index": {"row:day": [{event_data}]}
        }
    """
    tz = timezone.get_current_timezone()

    # Limites do mês em TZ local
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    days_in_month = last_day.day

    # Limites do ano em TZ local
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)

    # Converter para datetime aware (início/fim do mês)
    month_start = timezone.make_aware(datetime.combine(first_day, datetime.min.time()), tz)
    month_end = timezone.make_aware(datetime.combine(last_day, datetime.max.time()), tz)

    # Converter para datetime aware (início/fim do ano)
    year_start_dt = timezone.make_aware(datetime.combine(year_start, datetime.min.time()), tz)
    year_end_dt = timezone.make_aware(datetime.combine(year_end, datetime.max.time()), tz)

    # 1. Pessoas - estratégia depende de gerencia_id
    if gerencia_id is not None:
        # Quando gerencia_id especificado: buscar membros da equipe via EquipeGerencia
        # Mapear role para papel no EquipeGerencia
        papel_map = {"FORMADOR": "FORMADOR", "COORDENADOR": "COORDENADOR"}
        papel = papel_map.get(role, role)

        equipe_qs = EquipeGerencia.objects.filter(
            gerencia_id=gerencia_id,
            papel=papel,
            ativo=True,
        )

        if q and q.strip():
            q_lower = q.strip().lower()
            equipe_qs = equipe_qs.filter(
                Q(usuario__first_name__icontains=q_lower)
                | Q(usuario__last_name__icontains=q_lower)
                | Q(usuario__email__icontains=q_lower)
            )

        user_ids = list(set(equipe_qs.values_list("usuario_id", flat=True)))
    else:
        # Fallback para comportamento anterior (via Participation, apenas fluxo SUPER)
        participations_qs = Participation.objects.filter(role=role)
        participations_qs = participations_qs.filter(solicitacao__projeto__fluxo="SUPER")

        if q and q.strip():
            q_lower = q.strip().lower()
            participations_qs = participations_qs.filter(
                Q(usuario__first_name__icontains=q_lower)
                | Q(usuario__last_name__icontains=q_lower)
                | Q(usuario__email__icontains=q_lower)
            )

        user_ids = list(set(participations_qs.values_list("usuario_id", flat=True)))

    # Filtrar por IDs permitidos (se fornecido). Converter para set torna a
    # intersecção O(U) ao invés de O(U × len(allowed)).
    if allowed_user_ids is not None:
        allowed_set = set(allowed_user_ids)
        user_ids = [uid for uid in user_ids if uid in allowed_set]

    if not user_ids:
        # Sem usuários, retorna vazio
        return {
            "days": list(range(1, days_in_month + 1)),
            "legend": _build_legend(),
            "people": [],
            "cells": [],
            "details_index": {},
        }

    # 2. Eventos aprovados do mês (por pessoa)
    events_q = Solicitacao.objects.filter(
        status="aprovado",
        participations__role=role,
        participations__usuario_id__in=user_ids,
    ).filter(
        # Interseção com o mês: evento.inicio < month_end AND evento.fim > month_start
        inicio__lt=month_end,
        fim__gt=month_start,
    )

    if sector and sector.strip():
        events_q = events_q.filter(projeto__nome__iexact=sector.strip())

    # Nota: NÃO filtrar eventos por gerência aqui.
    # Quando gerencia_id é especificado, mostramos os MEMBROS daquela gerência,
    # mas exibimos TODOS os seus eventos (de qualquer projeto) para ter visão
    # completa da disponibilidade.

    # Select FKs directly but skip prefetch of Participations. We will
    # fetch participant ids in a single batched values_list query below,
    # which is cheaper than materializing the RelatedManager for each
    # event (#777 phase 2).
    events_q = events_q.select_related("municipio", "tipo_evento")
    events = list(events_q)

    # Batch fetch participants for every event in one query. Returns a flat
    # list of (solicitacao_id, usuario_id) tuples, indexed below.
    event_ids = [e.id for e in events]
    event_to_users: dict[int, list[int]] = defaultdict(list)
    if event_ids:
        for sol_id, uid in Participation.objects.filter(
            solicitacao_id__in=event_ids,
            role=role,
            usuario_id__in=user_ids,
        ).values_list("solicitacao_id", "usuario_id"):
            event_to_users[sol_id].append(uid)

    # 3. Bloqueios aprovados
    blocks = list(
        AvailabilityBlock.objects.filter(
            status="aprovado",
            usuario_id__in=user_ids,
            inicio__lt=month_end,
            fim__gt=month_start,
        ).select_related("usuario")
    )

    # 3.5. Deslocamentos do mês
    deslocamentos = list(
        Deslocamento.objects.filter(
            usuario_id__in=user_ids,
            start_date__lte=last_day,
            end_date__gte=first_day,
        ).select_related("usuario")
    )

    # 4. Acumuladores — dicts flat, chaveados por (uid, day_num). Cheaper
    # than triple-nested dict access, especially on hot paths (#777 phase 2).
    user_ids_set = set(user_ids)
    events_by_user_day: dict[tuple[int, int], list[Any]] = defaultdict(list)
    blocks_by_user_day: dict[tuple[int, int], list[Any]] = defaultdict(list)
    desloc_by_user_day: dict[tuple[int, int], list[Any]] = defaultdict(list)
    ch_month_by_user: dict[int, float] = defaultdict(float)
    ch_year_by_user: dict[int, float] = defaultdict(float)

    month_last_day = last_day  # local date, end-of-month clamp

    # 5. Distribuir eventos por dia/pessoa. Pré-filtramos o intervalo por dia
    # para o mês corrente uma única vez, eliminando o `if current.month == month`
    # do inner loop.
    for event in events:
        event_start_local = event.inicio.astimezone(tz).date()
        event_end_local = event.fim.astimezone(tz).date()

        # Clamp no intervalo do mês.
        day_start = event_start_local if event_start_local > first_day else first_day
        day_end = event_end_local if event_end_local < month_last_day else month_last_day
        if day_start > day_end:
            # Evento que toca apenas meses adjacentes — sem distribuição.
            continue

        event_users = event_to_users.get(event.id, ())
        current = day_start
        while current <= day_end:
            day_num = current.day
            for uid in event_users:
                events_by_user_day[(uid, day_num)].append(event)
            current += timedelta(days=1)

        # CH mês/ano por usuário. Calcula uma vez por evento e soma pra
        # cada participant.
        ch_month_hours = _calc_hours_in_range(event.inicio, event.fim, month_start, month_end)
        ch_year_hours = _calc_hours_in_range(event.inicio, event.fim, year_start_dt, year_end_dt)
        for uid in event_users:
            if uid in user_ids_set:
                ch_month_by_user[uid] += ch_month_hours
                ch_year_by_user[uid] += ch_year_hours

    # 6. Distribuir bloqueios por dia/pessoa
    for block in blocks:
        uid = block.usuario_id
        if uid not in user_ids_set:
            continue

        block_start_local = block.inicio.astimezone(tz).date()
        block_end_local = block.fim.astimezone(tz).date()

        day_start = block_start_local if block_start_local > first_day else first_day
        day_end = block_end_local if block_end_local < month_last_day else month_last_day
        if day_start > day_end:
            continue

        current = day_start
        while current <= day_end:
            blocks_by_user_day[(uid, current.day)].append(block)
            current += timedelta(days=1)

    # 6.5. Distribuir deslocamentos por dia/pessoa
    for desloc in deslocamentos:
        uid = desloc.usuario_id
        if uid not in user_ids_set:
            continue

        day_start = desloc.start_date if desloc.start_date > first_day else first_day
        day_end = desloc.end_date if desloc.end_date < month_last_day else month_last_day
        if day_start > day_end:
            continue

        current = day_start
        while current <= day_end:
            desloc_by_user_day[(uid, current.day)].append(desloc)
            current += timedelta(days=1)

    # 7. People com CH mês/ano. Usar values() evita hidratação completa do
    # modelo Usuario (os únicos campos usados são nome/email).
    user_rows = Usuario.objects.filter(id__in=user_ids).values("id", "first_name", "last_name", "email", "username")

    people = []
    for row in user_rows:
        uid = row["id"]
        # Replica get_full_name(): join de first+last, com fallback no username.
        full = f"{row['first_name']} {row['last_name']}".strip()
        name = full or row["username"]
        people.append(
            {
                "id": uid,
                "name": name,
                "email": row["email"],
                "ch_month": round(ch_month_by_user.get(uid, 0.0), 2),
                "ch_year": round(ch_year_by_user.get(uid, 0.0), 2),
            }
        )

    # Ordenar por nome (DETERMINÍSTICO)
    people.sort(key=lambda p: p["name"])

    # 8. Derivar user_id_to_row DE people (já ordenado)
    user_id_to_row = {p["id"]: idx for idx, p in enumerate(people)}

    # 9. Gerar códigos por dia/pessoa (precedência) - MATRIZ 2D.
    # Iteramos somente sobre os users que efetivamente têm algum evento/bloqueio/
    # deslocamento naquele dia; o resto permanece "" (já pré-alocado).
    num_rows = len(people)
    cells: list[list[str]] = [["" for _ in range(days_in_month)] for _ in range(num_rows)]
    details_index: dict[str, Any] = {}

    for p in people:
        uid = p["id"]
        row_idx = user_id_to_row[uid]

        for day_num in range(1, days_in_month + 1):
            events_day = events_by_user_day.get((uid, day_num), [])
            blocks_day = blocks_by_user_day.get((uid, day_num), [])
            deslocamentos_day = desloc_by_user_day.get((uid, day_num), [])

            n_events = len(events_day)
            has_event = n_events > 0
            has_block = bool(blocks_day)
            has_desloc = bool(deslocamentos_day)

            # Precedência: X > D1 > 2 > E > T/P > D
            if has_event and has_block:
                code = "X"
            elif has_event and has_desloc:
                code = "D1"
            elif n_events >= 2:
                code = "2"
            elif n_events == 1:
                code = "E"
            elif has_block:
                code = "T" if any(b.tipo == "T" for b in blocks_day) else "P"
            elif has_desloc:
                code = "D"
            else:
                continue  # cell already ""

            col_idx = day_num - 1
            cells[row_idx][col_idx] = code

            if code in ("E", "2", "X", "D1"):
                details_index[f"{row_idx}:{col_idx}"] = [_event_to_detail(e, tz) for e in events_day]

    # 10. Ranking denso por CH mês (desc).
    # `sorted()` retorna os mesmos objetos dict — a atribuição abaixo já mutua
    # os dicts referenciados por `people`, então não precisamos re-aplicar o
    # rank num segundo loop O(U²) (ASQ-004).
    people_sorted_by_ch = sorted(people, key=lambda p: p["ch_month"], reverse=True)
    rank = 0
    last_ch = None
    for p in people_sorted_by_ch:
        if p["ch_month"] != last_ch:
            rank += 1
            last_ch = p["ch_month"]
        p["position_month"] = rank

    return {
        "days": list(range(1, days_in_month + 1)),
        "legend": _build_legend(),
        "people": people,
        "cells": cells,
        "details_index": details_index,
    }


def _calc_hours_in_range(
    event_start: datetime, event_end: datetime, range_start: datetime, range_end: datetime
) -> float:
    """
    Calcula horas de interseção entre evento e intervalo.

    Args:
        event_start: Início do evento (aware)
        event_end: Fim do evento (aware)
        range_start: Início do intervalo (aware)
        range_end: Fim do intervalo (aware)

    Returns:
        Horas decimais (interseção)
    """
    # Interseção
    start = max(event_start, range_start)
    end = min(event_end, range_end)

    if start >= end:
        return 0.0

    delta = end - start
    hours = delta.total_seconds() / 3600.0
    return hours


def _event_to_detail(event: Solicitacao, tz) -> dict[str, Any]:
    """
    Converte evento para formato de detalhe.

    Args:
        event: Solicitacao
        tz: Timezone local

    Returns:
        {
            "id": int,
            "municipio": str,
            "data": str (YYYY-MM-DD local),
            "inicio": str (HH:MM local),
            "fim": str (HH:MM local),
            "tipo": str
        }
    """
    start_local = event.inicio.astimezone(tz)
    end_local = event.fim.astimezone(tz)

    return {
        "id": event.id,
        "municipio": event.municipio.nome if event.municipio else "",
        "data": start_local.strftime("%Y-%m-%d"),
        "inicio": start_local.strftime("%H:%M"),
        "fim": end_local.strftime("%H:%M"),
        "tipo": event.tipo_evento.nome,
    }


def _build_legend() -> dict[str, Any]:
    """Constrói legenda de códigos."""
    return {
        "E": "1 evento",
        "2": "≥2 eventos",
        "P": "Bloqueio parcial",
        "T": "Bloqueio total",
        "X": "Evento + bloqueio",
        "D": "Deslocamento",
        "D1": "Evento + deslocamento",
    }
