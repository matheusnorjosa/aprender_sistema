from django.db.models import Q
from datetime import datetime, date, time
from collections import defaultdict
from django.utils import timezone
from core.models import (
    DisponibilidadeFormadores, 
    Solicitacao, 
    SolicitacaoStatus,
    Deslocamento
)

def _dia_range(dt: date):
    """Retorna o intervalo completo do dia (00:00 até 23:59)"""
    inicio = timezone.make_aware(datetime.combine(dt, time.min))
    fim = timezone.make_aware(datetime.combine(dt, time.max.replace(second=59)))
    return inicio, fim

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
        status='Aprovado',
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
    bloqueios = DisponibilidadeFormadores.objects.filter(
        formador_id__in=formador_ids,
        data_bloqueio__gte=dia_inicio,
        data_bloqueio__lte=dia_fim
    ).select_related('formador')
    
    # 2. Todos os deslocamentos do período  
    deslocamentos = Deslocamento.objects.filter(
        formadores__in=formador_ids,
        data__gte=dia_inicio,
        data__lte=dia_fim
    ).prefetch_related('formadores')
    
    # 3. Todos os eventos aprovados que intersectam o período
    eventos = Solicitacao.objects.filter(
        status='Aprovado',
        formadores__in=formador_ids,
        data_inicio__lte=dt_fim_periodo,
        data_fim__gte=dt_inicio
    ).prefetch_related('formadores')
    
    # === ORGANIZAR DADOS EM ESTRUTURAS RÁPIDAS ===
    
    # Bloqueios: {formador_id: {data: tipo}}
    bloqueios_map = defaultdict(dict)
    for bloq in bloqueios:
        bloqueios_map[bloq.formador_id][bloq.data_bloqueio] = bloq.tipo_bloqueio.lower()
    
    # Deslocamentos: {formador_id: {data: True}}
    desloc_map = defaultdict(set)
    for desloc in deslocamentos:
        for formador in desloc.formadores.all():
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
                formador.id, dia,
                bloqueios_map[formador.id].get(dia),
                dia in desloc_map[formador.id],
                eventos_map[formador.id][dia]
            )
            celulas.append(marcador)
        resultado[formador.id] = celulas
    
    return resultado

def _marcador_otimizado(formador_id, dia, tipo_bloqueio, tem_desloc, qtd_eventos):
    """Lógica de marcador usando dados pré-carregados"""
    # Hierarquia de decisão
    if tipo_bloqueio == "total":
        return "X" if (qtd_eventos or tem_desloc) else "T"
    if tipo_bloqueio == "parcial":
        return "X" if (qtd_eventos or tem_desloc) else "P"
    if tem_desloc:
        return f"D{qtd_eventos}" if qtd_eventos else "D"
    return str(qtd_eventos) if qtd_eventos else "-"

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