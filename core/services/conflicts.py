# aprender_sistema/core/services/conflicts.py
from datetime import datetime, time

from django.db.models import Q

from core.models import (
    DisponibilidadeFormadores,
    Formador,
    Solicitacao,
    SolicitacaoStatus,
)


def intervals_overlap(a_start, a_end, b_start, b_end):
    """RD-01: Verifica sobreposição. Se fim == início → não conflita"""
    return a_start < b_end and b_start < a_end


def check_bloqueio_conflict(bloqueio, dt_inicio, dt_fim):
    """
    RD-02/RD-03: Verifica conflito com bloqueio Total(T) ou Parcial(P)

    - T (Total): impede qualquer evento no dia inteiro
    - P (Parcial): impede apenas no subintervalo bloqueado
    """
    from django.utils import timezone as tz

    # Determinar intervalo do bloqueio
    if (
        bloqueio.tipo_bloqueio.upper() == "T"
        or bloqueio.tipo_bloqueio.lower() == "total"
    ):
        # RD-02: Bloqueio total = dia inteiro (00:00 às 23:59)
        b_start = datetime.combine(bloqueio.data_bloqueio, time(0, 0))
        b_end = datetime.combine(bloqueio.data_bloqueio, time(23, 59, 59))
    else:
        # RD-03: Bloqueio parcial = apenas no subintervalo específico
        b_start = datetime.combine(bloqueio.data_bloqueio, bloqueio.hora_inicio)
        b_end = datetime.combine(bloqueio.data_bloqueio, bloqueio.hora_fim)

    # Converter para timezone-aware se necessário (RD-06)
    if tz.is_aware(dt_inicio):
        b_start = tz.make_aware(b_start) if tz.is_naive(b_start) else b_start
        b_end = tz.make_aware(b_end) if tz.is_naive(b_end) else b_end
    else:
        b_start = tz.make_naive(b_start) if tz.is_aware(b_start) else b_start
        b_end = tz.make_naive(b_end) if tz.is_aware(b_end) else b_end

    return intervals_overlap(dt_inicio, dt_fim, b_start, b_end)


def check_travel_buffer_conflict(formador, municipio_evento, dt_inicio, dt_fim):
    """
    RD-04: Verifica conflito de buffer de deslocamento

    Entre municípios distintos, exigir tempo mínimo de deslocamento.
    Para eventos no mesmo município, buffer pode ser zero.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone as tz

    buffer_minutes = getattr(settings, "TRAVEL_BUFFER_MINUTES", 90)

    # Buscar solicitações aprovadas do mesmo formador próximas no tempo
    conflitos_buffer = []

    # Intervalo de busca: buffer antes e depois do evento
    search_start = dt_inicio - timedelta(minutes=buffer_minutes)
    search_end = dt_fim + timedelta(minutes=buffer_minutes)

    # Buscar todas as solicitações aprovadas do formador para calcular gaps
    solicitacoes_proximas = (
        Solicitacao.objects.filter(
            status=SolicitacaoStatus.APROVADO,
            formadores=formador,
        )
        .exclude(
            # Excluir o próprio evento se estiver editando
            data_inicio=dt_inicio,
            data_fim=dt_fim,
        )
        .select_related("municipio")
    )

    for sol in solicitacoes_proximas:
        # Verificar se são municípios diferentes
        if sol.municipio.id != municipio_evento.id:
            # Calcular tempo entre eventos
            if sol.data_fim <= dt_inicio:
                # Evento anterior: verificar tempo entre fim do anterior e início do novo
                gap = dt_inicio - sol.data_fim
            elif sol.data_inicio >= dt_fim:
                # Evento posterior: verificar tempo entre fim do novo e início do posterior
                gap = sol.data_inicio - dt_fim
            else:
                # Eventos se sobrepõem (será detectado em RD-01)
                continue

            if gap.total_seconds() < (buffer_minutes * 60):
                conflitos_buffer.append(
                    {
                        "solicitacao": sol,
                        "gap_minutes": gap.total_seconds() / 60,
                        "required_minutes": buffer_minutes,
                        "tipo_conflito": "D",  # Deslocamento
                    }
                )

    return conflitos_buffer


def check_daily_capacity_conflict(formador, dt_inicio, dt_fim):
    """
    RD-05: Verifica se o formador excederia a capacidade diária máxima

    Retorna dict com informações sobre a violação de capacidade, se houver.
    """
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone as tz

    max_daily_hours = getattr(settings, "MAX_DAILY_HOURS", 8)

    # Calcular duração do novo evento em horas
    duracao_novo_evento = (dt_fim - dt_inicio).total_seconds() / 3600

    # Buscar todos os eventos aprovados do formador no mesmo dia
    data_evento = dt_inicio.date()

    eventos_do_dia = Solicitacao.objects.filter(
        status=SolicitacaoStatus.APROVADO,
        formadores=formador,
        data_inicio__date=data_evento,
    ).exclude(
        # Excluir o próprio evento se estiver editando
        data_inicio=dt_inicio,
        data_fim=dt_fim,
    )

    # Calcular total de horas já ocupadas no dia
    horas_ocupadas = 0
    for evento in eventos_do_dia:
        duracao = (evento.data_fim - evento.data_inicio).total_seconds() / 3600
        horas_ocupadas += duracao

    # Verificar se novo evento excederia o limite
    total_com_novo = horas_ocupadas + duracao_novo_evento

    if total_com_novo > max_daily_hours:
        return {
            "formador": formador,
            "data": data_evento,
            "horas_ocupadas": horas_ocupadas,
            "duracao_novo_evento": duracao_novo_evento,
            "total_com_novo": total_com_novo,
            "limite_diario": max_daily_hours,
            "excesso": total_com_novo - max_daily_hours,
            "tipo_conflito": "M",  # Mais de um evento (excesso de capacidade)
            "eventos_do_dia": list(eventos_do_dia),
        }

    return None


def check_conflicts(formadores_qs, dt_inicio, dt_fim, municipio_evento=None):
    """
    Retorna dict com conflitos seguindo RD-07 (ordem de prioridade):
    1. Bloqueios (T, P)
    2. Conflitos por eventos aprovados (sobreposição)
    3. Buffer de deslocamento (D)
    4. Limite diário (M)

    Args:
        formadores_qs: QuerySet de Formador ou lista de objetos Formador
        municipio_evento: Municipio do evento (para RD-04)
    """
    result = {
        "bloqueios": [],
        "solicitacoes": [],
        "deslocamentos": [],
        "capacidade_diaria": [],
    }

    # Suporte tanto para QuerySet quanto para lista
    if hasattr(formadores_qs, "values_list"):
        # É um QuerySet
        formadores_ids = list(formadores_qs.values_list("id", flat=True))
        formadores_objs = list(formadores_qs)
    else:
        # É uma lista de objetos Formador
        formadores_ids = [f.id for f in formadores_qs]
        formadores_objs = formadores_qs

    # RD-07.1: Prioridade 1 - Bloqueios de disponibilidade (RD-02/RD-03)
    bloqueios = DisponibilidadeFormadores.objects.filter(
        formador_id__in=formadores_ids,
        data_bloqueio__range=[dt_inicio.date(), dt_fim.date()],
    ).select_related("formador")

    for b in bloqueios:
        if check_bloqueio_conflict(b, dt_inicio, dt_fim):
            result["bloqueios"].append(b)

    # RD-07.2: Prioridade 2 - Conflitos por eventos aprovados (RD-01)
    if formadores_ids:  # Só procurar se houver formadores
        solicitacoes = (
            Solicitacao.objects.filter(
                status=SolicitacaoStatus.APROVADO,
                data_inicio__lt=dt_fim,
                data_fim__gt=dt_inicio,
                formadores__id__in=formadores_ids,  # Usar id explicitamente
            )
            .select_related("projeto", "municipio", "tipo_evento")
            .prefetch_related("formadores")
            .distinct()
        )
        result["solicitacoes"].extend(list(solicitacoes))

    # RD-07.3: Prioridade 3 - Buffer de deslocamento (RD-04)
    if municipio_evento:
        for formador in formadores_objs:
            conflitos_buffer = check_travel_buffer_conflict(
                formador, municipio_evento, dt_inicio, dt_fim
            )
            result["deslocamentos"].extend(conflitos_buffer)

    # RD-07.4: Prioridade 4 - Limite diário (RD-05)
    for formador in formadores_objs:
        conflito_capacidade = check_daily_capacity_conflict(formador, dt_inicio, dt_fim)
        if conflito_capacidade:
            result["capacidade_diaria"].append(conflito_capacidade)

    return result
