# aprender_sistema/core/services/conflicts.py
from datetime import datetime
from django.db.models import Q
from core.models import DisponibilidadeFormadores, Solicitacao, SolicitacaoStatus, Formador

def intervals_overlap(a_start, a_end, b_start, b_end):
    return a_start < b_end and b_start < a_end

def check_conflicts(formadores_qs, dt_inicio, dt_fim):
    """
    Retorna dict com conflitos:
      - 'bloqueios': indisponibilidades (DisponibilidadeFormadores)
      - 'solicitacoes': solicitações aprovadas que se sobrepõem
    """
    result = {"bloqueios": [], "solicitacoes": []}
    formadores_ids = list(formadores_qs.values_list("id", flat=True))

    # 1) Bloqueios de disponibilidade no mesmo dia; depois filtra por hora na mão
    bloqueios = DisponibilidadeFormadores.objects.filter(
        formador_id__in=formadores_ids,
        data_bloqueio__range=[dt_inicio.date(), dt_fim.date()],
    ).select_related("formador")

    for b in bloqueios:
        # montar dois datetimes do bloqueio naquele dia
        from django.utils import timezone as tz
        b_start = datetime.combine(b.data_bloqueio, b.hora_inicio)
        b_end = datetime.combine(b.data_bloqueio, b.hora_fim)
        
        # Converter para timezone-aware se necessário
        if tz.is_aware(dt_inicio):
            b_start = tz.make_aware(b_start) if tz.is_naive(b_start) else b_start
            b_end = tz.make_aware(b_end) if tz.is_naive(b_end) else b_end
        else:
            b_start = tz.make_naive(b_start) if tz.is_aware(b_start) else b_start
            b_end = tz.make_naive(b_end) if tz.is_aware(b_end) else b_end
            
        if intervals_overlap(dt_inicio, dt_fim, b_start, b_end):
            result["bloqueios"].append(b)

    # 2) Solicitações aprovadas já existentes (por formador) que se sobrepõem
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
