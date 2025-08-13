# aprender_sistema/core/services/calendar_codes.py
from datetime import datetime, date, time
from core.models import DisponibilidadeFormadores, Solicitacao, SolicitacaoStatus, Deslocamento, Formador

def _dia_range(dt: date):
    return datetime.combine(dt, time(0,0,0)), datetime.combine(dt, time(23,59,59))

def _tem_bloqueio(formador_id, dia: date, tipo: str):
    return DisponibilidadeFormadores.objects.filter(
        formador_id=formador_id,
        tipo_bloqueio__iexact=tipo,
        data_bloqueio=dia,
    ).exists()

def _conta_eventos_no_dia(formador_id, dia: date) -> int:
    di, df = _dia_range(dia)
    return (
        Solicitacao.objects.filter(
            status=SolicitacaoStatus.APROVADO,
            data_inicio__gte=di, data_inicio__lte=df,
            formadores=formador_id
        ).distinct().count()
    )

def _tem_desloc_no_dia(formador_id, dia: date) -> int:
    return Deslocamento.objects.filter(data=dia, formadores=formador_id).distinct().count()

def marcador_do_dia(formador: Formador, dia: date) -> str:
    if not formador:
        return ""
    bloqT = _tem_bloqueio(formador.id, dia, "Total")
    bloqP = _tem_bloqueio(formador.id, dia, "Parcial")
    eventos = _conta_eventos_no_dia(formador.id, dia)
    deslocs = _tem_desloc_no_dia(formador.id, dia)

    if bloqT and (eventos + deslocs) > 0:
        return "X"
    if bloqT:
        return "T"
    if bloqP:
        return "X" if (eventos + deslocs) > 0 else "P"
    if deslocs > 0:
        return f"D{eventos}" if eventos > 0 else "D"
    if eventos > 0:
        return str(eventos)
    return "-"
