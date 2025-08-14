from django.db.models import Q
from datetime import datetime, date, time
from core.models import (
    DisponibilidadeFormadores, 
    Solicitacao, 
    SolicitacaoStatus,
    Deslocamento
)

def _dia_range(dt: date):
    """Retorna o intervalo completo do dia (00:00 até 23:59)"""
    return datetime.combine(dt, time.min), datetime.combine(dt, time.max.replace(second=59))

def _tem_bloqueio(formador_id, dia: date, tipo: str):
    """Verifica bloqueios de forma case-insensitive"""
    return DisponibilidadeFormadores.objects.filter(
        formador_id=formador_id,
        data_bloqueio=dia,
        tipo_bloqueio__iexact=tipo
    ).exists()

def _conta_eventos_no_dia(formador_id, dia: date) -> int:
    """Conta eventos que intersectam o dia (início <= dia <= fim)"""
    di, df = _dia_range(dia)
    return Solicitacao.objects.filter(
        status=SolicitacaoStatus.APROVADO,
        formadores=formador_id,
        data_inicio__lte=df,
        data_fim__gte=di
    ).distinct().count()

def _tem_desloc_no_dia(formador_id, dia: date) -> bool:
    """Verifica deslocamentos de forma otimizada"""
    return Deslocamento.objects.filter(
        formadores=formador_id,
        data=dia
    ).exists()

def marcador_do_dia(formador, dia) -> str:
    """Lógica prioritária: Bloqueios > Deslocamentos > Eventos > Disponível"""
    if not formador or not dia:
        return "-"

    # Consultas otimizadas
    bloq_total = _tem_bloqueio(formador.id, dia, "Total")
    bloq_parcial = _tem_bloqueio(formador.id, dia, "Parcial")
    tem_desloc = _tem_desloc_no_dia(formador.id, dia)
    qtd_eventos = _conta_eventos_no_dia(formador.id, dia)

    # Hierarquia de decisão
    if bloq_total:
        return "X" if (qtd_eventos or tem_desloc) else "T"
    if bloq_parcial:
        return "X" if (qtd_eventos or tem_desloc) else "P"
    if tem_desloc:
        return f"D{qtd_eventos}" if qtd_eventos else "D"
    return str(qtd_eventos) if qtd_eventos else "-"