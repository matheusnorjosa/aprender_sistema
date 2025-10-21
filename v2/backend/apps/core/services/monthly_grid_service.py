"""
Service para compor grade mensal de disponibilidade.

Retorna uma grade mensal (ano/mês) com códigos por dia/pessoa:
- E: 1 evento
- 2: ≥2 eventos
- P: bloqueio parcial (sem evento)
- T: bloqueio total (sem evento)
- X: evento + bloqueio

Calcula CH mês/ano, ranking por CH mês (denso).
Details_index para dias com E/2/X (lista de eventos).
"""

from datetime import date, datetime, timedelta
from typing import Optional
from django.utils import timezone
from django.db.models import Q, Prefetch

from apps.core.models import Usuario, Solicitacao, AvailabilityBlock, Participation


def build_monthly_grid(
    *,
    year: int,
    month: int,
    role: str,
    sector: Optional[str] = None,
    q: Optional[str] = None,
) -> dict:
    """
    Compõe grade mensal de disponibilidade por pessoa (role).

    Args:
        year: Ano (YYYY)
        month: Mês (1..12)
        role: "FORMADOR" ou "COORDENADOR"
        sector: Filtro opcional por setor (projeto.nome)
        q: Filtro opcional por nome/email (icontains)

    Returns:
        {
            "days": int (número de dias do mês),
            "legend": {...},
            "people": [{"id", "name", "email", "ch_month", "ch_year", "position_month"}],
            "cells": {user_id: {day: code}},
            "details_index": {user_id: {day: [{event_data}]}}
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
    month_start = timezone.make_aware(
        datetime.combine(first_day, datetime.min.time()), tz
    )
    month_end = timezone.make_aware(
        datetime.combine(last_day, datetime.max.time()), tz
    )

    # Converter para datetime aware (início/fim do ano)
    year_start_dt = timezone.make_aware(
        datetime.combine(year_start, datetime.min.time()), tz
    )
    year_end_dt = timezone.make_aware(
        datetime.combine(year_end, datetime.max.time()), tz
    )

    # 1. Pessoas (via Participation)
    participations_qs = Participation.objects.filter(role=role)

    if q and q.strip():
        q_lower = q.strip().lower()
        participations_qs = participations_qs.filter(
            Q(usuario__first_name__icontains=q_lower)
            | Q(usuario__last_name__icontains=q_lower)
            | Q(usuario__email__icontains=q_lower)
        )

    # Get distinct user IDs
    user_ids = list(set(participations_qs.values_list("usuario_id", flat=True)))

    if not user_ids:
        # Sem usuários, retorna vazio
        return {
            "days": days_in_month,
            "legend": _build_legend(),
            "people": [],
            "cells": {},
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

    # Prefetch participations do role específico
    events_q = events_q.prefetch_related(
        Prefetch(
            "participations",
            queryset=Participation.objects.filter(
                role=role, usuario_id__in=user_ids
            ).select_related("usuario"),
        )
    ).select_related("municipio", "tipo_evento")

    events = list(events_q)

    # 3. Bloqueios aprovados
    blocks = list(
        AvailabilityBlock.objects.filter(
            status="aprovado",
            usuario_id__in=user_ids,
            inicio__lt=month_end,
            fim__gt=month_start,
        ).select_related("usuario")
    )

    # 4. Estruturas para acumular dados por user_id
    user_data = {uid: _init_user_data(year, month, days_in_month) for uid in user_ids}

    # 5. Distribuir eventos por dia/pessoa
    for event in events:
        # Converter para TZ local
        event_start_local = event.inicio.astimezone(tz)
        event_end_local = event.fim.astimezone(tz)

        # Dias tocados pelo evento (loop por dias)
        current = event_start_local.date()
        end_date = event_end_local.date()

        # Encontrar usuários desse evento com o role específico
        event_users = [
            p.usuario_id for p in event.participations.all() if p.role == role
        ]

        while current <= end_date:
            day_num = current.day

            # Verificar se o dia está dentro do mês atual
            if current.month == month and current.year == year:
                for uid in event_users:
                    if uid in user_data:
                        user_data[uid]["events_by_day"][day_num].append(event)

            current += timedelta(days=1)

        # Calcular CH mês/ano para este evento
        for uid in event_users:
            if uid not in user_data:
                continue

            # CH mês: interseção com mês
            ch_month_hours = _calc_hours_in_range(
                event.inicio, event.fim, month_start, month_end
            )
            user_data[uid]["ch_month"] += ch_month_hours

            # CH ano: interseção com ano
            ch_year_hours = _calc_hours_in_range(
                event.inicio, event.fim, year_start_dt, year_end_dt
            )
            user_data[uid]["ch_year"] += ch_year_hours

    # 6. Distribuir bloqueios por dia/pessoa
    for block in blocks:
        uid = block.usuario_id
        if uid not in user_data:
            continue

        # Converter para TZ local
        block_start_local = block.inicio.astimezone(tz)
        block_end_local = block.fim.astimezone(tz)

        # Dias tocados pelo bloqueio
        current = block_start_local.date()
        end_date = block_end_local.date()

        while current <= end_date:
            day_num = current.day

            # Verificar se o dia está dentro do mês atual
            if current.month == month and current.year == year:
                user_data[uid]["blocks_by_day"][day_num].append(block)

            current += timedelta(days=1)

    # 7. Gerar códigos por dia/pessoa (precedência)
    cells = {}
    details_index = {}

    for uid, data in user_data.items():
        cells[uid] = {}
        details_index[uid] = {}

        for day_num in range(1, days_in_month + 1):
            events_day = data["events_by_day"][day_num]
            blocks_day = data["blocks_by_day"][day_num]

            has_event = len(events_day) > 0
            has_block = len(blocks_day) > 0

            code = ""
            if has_event and has_block:
                code = "X"
            elif len(events_day) >= 2:
                code = "2"
            elif len(events_day) == 1:
                code = "E"
            elif has_block:
                # Verificar se é T ou P
                # Se qualquer bloqueio for T, código é T; senão P
                has_total = any(b.tipo == "T" for b in blocks_day)
                code = "T" if has_total else "P"

            cells[uid][day_num] = code

            # Details para E/2/X
            if code in ["E", "2", "X"]:
                details_index[uid][day_num] = [
                    _event_to_detail(e, tz) for e in events_day
                ]

    # 8. People com CH mês/ano e ranking
    users = Usuario.objects.filter(id__in=user_ids)
    user_map = {u.id: u for u in users}

    people = []
    for uid in user_ids:
        user = user_map.get(uid)
        if not user:
            continue

        people.append(
            {
                "id": uid,
                "name": user.get_full_name() or user.username,
                "email": user.email,
                "ch_month": round(user_data[uid]["ch_month"], 2),
                "ch_year": round(user_data[uid]["ch_year"], 2),
            }
        )

    # Ordenar por nome
    people.sort(key=lambda p: p["name"])

    # Ranking denso por CH mês (desc)
    people_sorted_by_ch = sorted(people, key=lambda p: p["ch_month"], reverse=True)
    rank = 0
    last_ch = None
    for p in people_sorted_by_ch:
        if p["ch_month"] != last_ch:
            rank += 1
            last_ch = p["ch_month"]
        p["position_month"] = rank

    # Re-indexar por id para facilitar lookup
    for p in people:
        for p2 in people_sorted_by_ch:
            if p["id"] == p2["id"]:
                p["position_month"] = p2["position_month"]
                break

    return {
        "days": days_in_month,
        "legend": _build_legend(),
        "people": people,
        "cells": cells,
        "details_index": details_index,
    }


def _init_user_data(year: int, month: int, days_in_month: int) -> dict:
    """Inicializa estrutura de dados por usuário."""
    return {
        "ch_month": 0.0,
        "ch_year": 0.0,
        "events_by_day": {day: [] for day in range(1, days_in_month + 1)},
        "blocks_by_day": {day: [] for day in range(1, days_in_month + 1)},
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


def _event_to_detail(event: Solicitacao, tz) -> dict:
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


def _build_legend() -> dict:
    """Constrói legenda de códigos."""
    return {
        "E": "1 evento",
        "2": "≥2 eventos",
        "P": "Bloqueio parcial",
        "T": "Bloqueio total",
        "X": "Evento + bloqueio",
    }
