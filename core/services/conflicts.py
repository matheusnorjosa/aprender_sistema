# aprender_sistema/core/services/conflicts.py
from datetime import datetime, time
from django.db.models import Q
from core.models import DisponibilidadeFormadores, Solicitacao, SolicitacaoStatus, Formador

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
    if bloqueio.tipo_bloqueio.upper() == 'T' or bloqueio.tipo_bloqueio.lower() == 'total':
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

def check_conflicts(formadores_qs, dt_inicio, dt_fim):
    """
    Retorna dict com conflitos seguindo RD-07 (ordem de prioridade):
    1. Bloqueios (T, P)
    2. Conflitos por eventos aprovados (sobreposição)
    3. Buffer de deslocamento (D) - TODO: próxima fase
    4. Limite diário (M) - TODO: próxima fase
    
    Args:
        formadores_qs: QuerySet de Formador ou lista de objetos Formador
    """
    result = {"bloqueios": [], "solicitacoes": []}
    
    # Suporte tanto para QuerySet quanto para lista
    if hasattr(formadores_qs, 'values_list'):
        # É um QuerySet
        formadores_ids = list(formadores_qs.values_list("id", flat=True))
    else:
        # É uma lista de objetos Formador
        formadores_ids = [f.id for f in formadores_qs]

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
    
    return result
