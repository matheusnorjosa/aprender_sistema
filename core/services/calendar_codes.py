from collections import defaultdict
from datetime import date, datetime, time

from django.db.models import Q
from django.utils import timezone

from core.models import (
    Deslocamento,
    DisponibilidadeFormadores,
    Solicitacao,
    SolicitacaoStatus,
)


def _dia_range(dt: date):
    """Retorna o intervalo completo do dia (00:00 até 23:59)"""
    inicio = timezone.make_aware(datetime.combine(dt, time.min))
    fim = timezone.make_aware(datetime.combine(dt, time.max.replace(second=59)))
    return inicio, fim


def _tem_bloqueio(formador_id, dia: date, tipo: str):
    """Verifica bloqueios de forma case-insensitive"""
    return DisponibilidadeFormadores.objects.filter(
        usuario_id=formador_id, data_bloqueio=dia, tipo_bloqueio__iexact=tipo
    ).exists()


def _conta_eventos_no_dia(formador_id, dia: date) -> int:
    """Conta eventos que intersectam o dia (início <= dia <= fim)"""
    di, df = _dia_range(dia)
    return (
        Solicitacao.objects.filter(
            status="Aprovado",
            formadores=formador_id,
            data_inicio__lte=df,
            data_fim__gte=di,
        )
        .distinct()
        .count()
    )


def _tem_desloc_no_dia(formador_id, dia: date) -> bool:
    """Verifica deslocamentos de forma otimizada"""
    return Deslocamento.objects.filter(
        Q(pessoa_1_id=formador_id) | Q(pessoa_2_id=formador_id) | Q(pessoa_3_id=formador_id) |
        Q(pessoa_4_id=formador_id) | Q(pessoa_5_id=formador_id) | Q(pessoa_6_id=formador_id),
        data=dia
    ).exists()


def gerar_mapa_mensal_otimizado(formadores, dias):
    """
    Versão otimizada que busca todos os dados de uma vez e processa em memória.
    Reduz de N*M*4 consultas para apenas 4 consultas totais.
    """
    if not formadores or not dias:
        return {}

    # IDs dos formadores
    formador_ids = [f.id for f in formadores]

    # Data range do período
    dia_inicio = min(dias)
    dia_fim = max(dias)
    dt_inicio, dt_fim = _dia_range(dia_inicio)
    dt_inicio_periodo, dt_fim_periodo = _dia_range(dia_fim)

    # === BUSCAR TODOS OS DADOS DE UMA VEZ ===

    # 1. Todos os bloqueios do período
    # Mapear formador_ids para usuario_ids
    usuario_ids = [f.usuario.id for f in formadores if f.usuario]
    bloqueios = DisponibilidadeFormadores.objects.filter(
        usuario_id__in=usuario_ids,
        data_bloqueio__gte=dia_inicio,
        data_bloqueio__lte=dia_fim,
    ).select_related("usuario")

    # 2. Todos os deslocamentos do período
    from django.db.models import Q
    desloc_query = Q()
    for fid in formador_ids:
        desloc_query |= (
            Q(pessoa_1_id=fid) | Q(pessoa_2_id=fid) | Q(pessoa_3_id=fid) |
            Q(pessoa_4_id=fid) | Q(pessoa_5_id=fid) | Q(pessoa_6_id=fid)
        )
    
    deslocamentos = Deslocamento.objects.filter(
        desloc_query, data__gte=dia_inicio, data__lte=dia_fim
    ).select_related("pessoa_1", "pessoa_2", "pessoa_3", "pessoa_4", "pessoa_5", "pessoa_6")

    # 3. Todos os eventos aprovados que intersectam o período
    eventos = Solicitacao.objects.filter(
        status="Aprovado",
        formadores__in=formador_ids,
        data_inicio__lte=dt_fim_periodo,
        data_fim__gte=dt_inicio,
    ).prefetch_related("formadores")

    # === ORGANIZAR DADOS EM ESTRUTURAS RÁPIDAS ===

    # Bloqueios: {formador_id: {data: tipo}}
    bloqueios_map = defaultdict(dict)
    for bloq in bloqueios:
        # Mapear usuario_id para formador_id
        if hasattr(bloq.usuario, 'formador_profile') and bloq.usuario.formador_profile:
            formador_id = bloq.usuario.formador_profile.id
            bloqueios_map[formador_id][bloq.data_bloqueio] = bloq.tipo_bloqueio.lower()

    # Deslocamentos: {formador_id: {data: True}}
    desloc_map = defaultdict(set)
    for desloc in deslocamentos:
        for formador in desloc.pessoas:
            if formador:  # Verificar se não é None
                desloc_map[formador.id].add(desloc.data)

    # Eventos: {formador_id: {data: count}}
    eventos_map = defaultdict(lambda: defaultdict(int))
    for evento in eventos:
        # Para cada dia que o evento intersecta
        for dia in dias:
            di, df = _dia_range(dia)
            if evento.data_inicio <= df and evento.data_fim >= di:
                for formador in evento.formadores.all():
                    eventos_map[formador.id][dia] += 1

    # === GERAR MARCADORES OTIMIZADOS ===

    resultado = {}
    for formador in formadores:
        celulas = []
        for dia in dias:
            marcador = _marcador_otimizado(
                formador.id,
                dia,
                bloqueios_map[formador.id].get(dia),
                dia in desloc_map[formador.id],
                eventos_map[formador.id][dia],
            )
            celulas.append(marcador)
        resultado[formador.id] = celulas

    return resultado


def _marcador_otimizado(formador_id, dia, tipo_bloqueio, tem_desloc, qtd_eventos):
    """Lógica de marcador usando dados pré-carregados - baseado na planilha"""
    # Hierarquia de decisão baseada nos códigos da planilha
    if tipo_bloqueio == "total":
        return "X" if (qtd_eventos or tem_desloc) else "T"
    if tipo_bloqueio == "parcial":
        return "X" if (qtd_eventos or tem_desloc) else "P"
    if tipo_bloqueio == "conflito":
        return "X"  # Conflito com bloqueio
    if tipo_bloqueio == "evento":
        return "1" if qtd_eventos == 1 else str(qtd_eventos) if qtd_eventos > 1 else "1"
    if tipo_bloqueio == "multi_evento":
        return "2" if qtd_eventos >= 2 else str(qtd_eventos) if qtd_eventos > 0 else "2"
    if tipo_bloqueio == "desloc_evento":
        if tem_desloc and qtd_eventos > 0:
            return "D1"  # Deslocamento e evento
        elif tem_desloc:
            return "D"  # Apenas deslocamento
        elif qtd_eventos > 0:
            return str(qtd_eventos)  # Apenas evento
        else:
            return "D1"  # Fallback
    if tipo_bloqueio == "disponível":
        # Para disponível, mostrar eventos ou deslocamentos se existirem
        if tem_desloc and qtd_eventos > 0:
            return "D1"  # Deslocamento e evento
        elif tem_desloc:
            return "D"  # Apenas deslocamento
        elif qtd_eventos > 1:
            return "2"  # Mais de um evento
        elif qtd_eventos == 1:
            return "1"  # Um evento
        else:
            return "V"  # Disponível (célula vazia na planilha)
    
    # Fallback para casos não mapeados
    if tem_desloc and qtd_eventos > 0:
        return "D1"
    elif tem_desloc:
        return "D"
    elif qtd_eventos > 1:
        return "2"
    elif qtd_eventos == 1:
        return "1"
    else:
        return "-"


# === MANTER FUNÇÃO ORIGINAL PARA COMPATIBILIDADE ===
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
