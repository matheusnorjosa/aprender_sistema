"""
Serviço de detecção de conflitos de agenda
Implementa as regras de disponibilidade definidas no CLAUDE.md
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from django.db.models import Q
from django.utils import timezone

from core.models import (
    Deslocamento,
    DisponibilidadeFormadores,
    Formador,
    Solicitacao,
    SolicitacaoStatus,
)


class ConflictType:
    """Tipos de conflito baseados nas planilhas originais"""

    OVERLAP = "E"  # Evento sobreposto (Existing)
    MULTIPLE = "M"  # Mais de um evento no dia
    TRAVEL = "D"  # Deslocamento necessário
    PARTIAL_BLOCK = "P"  # Bloqueio parcial
    TOTAL_BLOCK = "T"  # Bloqueio total
    CONFLICT = "X"  # Conflito geral


class ConflictDetector:
    """
    Detector de conflitos seguindo as regras de negócio das planilhas
    Baseado nas Regras de Disponibilidade RD-01 a RD-08
    """

    def __init__(self, buffer_deslocamento_minutos: int = 120):
        """
        Args:
            buffer_deslocamento_minutos: Tempo mínimo entre eventos em municípios diferentes
        """
        self.buffer_deslocamento = timedelta(minutes=buffer_deslocamento_minutos)

    def detect_conflicts(
        self, solicitacao: Solicitacao, formadores: List[Formador]
    ) -> Dict[str, List[Dict]]:
        """
        Detecta todos os conflitos para uma solicitação com lista de formadores

        Returns:
            Dict com conflitos por formador: {
                'formador_id': [{'type': 'E', 'message': '...', 'details': {...}}]
            }
        """
        conflicts = {}

        for formador in formadores:
            formador_conflicts = self._check_formador_conflicts(solicitacao, formador)
            if formador_conflicts:
                conflicts[str(formador.id)] = formador_conflicts

        return conflicts

    def _check_formador_conflicts(
        self, solicitacao: Solicitacao, formador: Formador
    ) -> List[Dict]:
        """Verifica conflitos para um formador específico"""
        conflicts = []

        # RD-02 e RD-03: Verificar bloqueios (total e parcial)
        block_conflicts = self._check_availability_blocks(solicitacao, formador)
        conflicts.extend(block_conflicts)

        # RD-01: Verificar sobreposição de eventos
        overlap_conflicts = self._check_event_overlaps(solicitacao, formador)
        conflicts.extend(overlap_conflicts)

        # RD-04: Verificar buffer de deslocamento
        travel_conflicts = self._check_travel_buffer(solicitacao, formador)
        conflicts.extend(travel_conflicts)

        # RD-05: Verificar capacidade diária
        capacity_conflicts = self._check_daily_capacity(solicitacao, formador)
        conflicts.extend(capacity_conflicts)

        return conflicts

    def _check_availability_blocks(
        self, solicitacao: Solicitacao, formador: Formador
    ) -> List[Dict]:
        """RD-02 e RD-03: Verificar bloqueios de disponibilidade"""
        conflicts = []

        # Buscar bloqueios que se sobreponham com a solicitação
        data_evento = solicitacao.data_inicio.date()
        hora_inicio = solicitacao.data_inicio.time()
        hora_fim = solicitacao.data_fim.time()

        bloqueios = DisponibilidadeFormadores.objects.filter(
            formador=formador, data_bloqueio=data_evento
        )

        for bloqueio in bloqueios:
            # RD-02: Bloqueio total
            if bloqueio.tipo_bloqueio.upper() in ["T", "TOTAL", "BLOQUEIO TOTAL"]:
                conflicts.append(
                    {
                        "type": ConflictType.TOTAL_BLOCK,
                        "message": f'Bloqueio total em {data_evento.strftime("%d/%m/%Y")}',
                        "details": {
                            "formador": (
                                formador.usuario.get_full_name()
                                if formador.usuario
                                else formador.nome
                            ),
                            "data": data_evento,
                            "tipo_bloqueio": bloqueio.tipo_bloqueio,
                            "motivo": bloqueio.motivo,
                        },
                    }
                )
                continue

            # RD-03: Bloqueio parcial - verificar sobreposição
            if self._time_ranges_overlap(
                (hora_inicio, hora_fim), (bloqueio.hora_inicio, bloqueio.hora_fim)
            ):
                conflicts.append(
                    {
                        "type": ConflictType.PARTIAL_BLOCK,
                        "message": f'Bloqueio parcial {bloqueio.hora_inicio}-{bloqueio.hora_fim} em {data_evento.strftime("%d/%m/%Y")}',
                        "details": {
                            "formador": (
                                formador.usuario.get_full_name()
                                if formador.usuario
                                else formador.nome
                            ),
                            "data": data_evento,
                            "horario_bloqueio": f"{bloqueio.hora_inicio}-{bloqueio.hora_fim}",
                            "tipo_bloqueio": bloqueio.tipo_bloqueio,
                            "motivo": bloqueio.motivo,
                        },
                    }
                )

        return conflicts

    def _check_event_overlaps(
        self, solicitacao: Solicitacao, formador: Formador
    ) -> List[Dict]:
        """RD-01: Verificar sobreposição com eventos existentes"""
        conflicts = []

        # Buscar eventos aprovados que se sobreponham
        eventos_existentes = Solicitacao.objects.filter(
            status__in=[SolicitacaoStatus.APROVADO, SolicitacaoStatus.PRE_AGENDA],
            formadores=formador,
        ).exclude(id=solicitacao.id)

        for evento in eventos_existentes:
            # RD-01: Verificar overlap (borda: fim == início não conflita)
            if self._datetime_ranges_overlap(
                (solicitacao.data_inicio, solicitacao.data_fim),
                (evento.data_inicio, evento.data_fim),
                allow_adjacent=True,  # fim == início não conflita
            ):
                conflicts.append(
                    {
                        "type": ConflictType.OVERLAP,
                        "message": f'Sobreposição com "{evento.titulo_evento}" em {evento.data_inicio.strftime("%d/%m/%Y %H:%M")}',
                        "details": {
                            "formador": (
                                formador.usuario.get_full_name()
                                if formador.usuario
                                else formador.nome
                            ),
                            "evento_conflitante": evento.titulo_evento,
                            "data_conflito": evento.data_inicio,
                            "horario_conflito": f'{evento.data_inicio.strftime("%H:%M")}-{evento.data_fim.strftime("%H:%M")}',
                            "municipio_conflito": evento.municipio.nome,
                        },
                    }
                )

        return conflicts

    def _check_travel_buffer(
        self, solicitacao: Solicitacao, formador: Formador
    ) -> List[Dict]:
        """RD-04: Verificar buffer de deslocamento entre municípios"""
        conflicts = []

        # Buscar eventos no mesmo dia ou próximos em outros municípios
        data_inicio = solicitacao.data_inicio
        data_fim = solicitacao.data_fim

        # Janela de verificação: 4 horas antes e depois
        janela_inicio = data_inicio - timedelta(hours=4)
        janela_fim = data_fim + timedelta(hours=4)

        eventos_proximos = (
            Solicitacao.objects.filter(
                status__in=[SolicitacaoStatus.APROVADO, SolicitacaoStatus.PRE_AGENDA],
                formadores=formador,
                data_inicio__range=(janela_inicio, janela_fim),
            )
            .exclude(id=solicitacao.id)
            .exclude(
                municipio=solicitacao.municipio  # Mesmo município não precisa buffer
            )
        )

        for evento in eventos_proximos:
            # Calcular tempo entre eventos
            if evento.data_fim <= data_inicio:
                # Evento anterior
                tempo_entre = data_inicio - evento.data_fim
            elif evento.data_inicio >= data_fim:
                # Evento posterior
                tempo_entre = evento.data_inicio - data_fim
            else:
                # Sobreposição (já detectada em outro método)
                continue

            if tempo_entre < self.buffer_deslocamento:
                conflicts.append(
                    {
                        "type": ConflictType.TRAVEL,
                        "message": f"Deslocamento {evento.municipio.nome} → {solicitacao.municipio.nome} requer {self.buffer_deslocamento.total_seconds()//60:.0f}min",
                        "details": {
                            "formador": (
                                formador.usuario.get_full_name()
                                if formador.usuario
                                else formador.nome
                            ),
                            "municipio_origem": evento.municipio.nome,
                            "municipio_destino": solicitacao.municipio.nome,
                            "tempo_disponivel_minutos": int(
                                tempo_entre.total_seconds() // 60
                            ),
                            "tempo_necessario_minutos": int(
                                self.buffer_deslocamento.total_seconds() // 60
                            ),
                            "evento_anterior": evento.titulo_evento,
                        },
                    }
                )

        return conflicts

    def _check_daily_capacity(
        self, solicitacao: Solicitacao, formador: Formador, max_horas_dia: int = 10
    ) -> List[Dict]:
        """RD-05: Verificar capacidade diária máxima"""
        conflicts = []

        data_evento = solicitacao.data_inicio.date()

        # Buscar eventos no mesmo dia
        eventos_no_dia = Solicitacao.objects.filter(
            status__in=[SolicitacaoStatus.APROVADO, SolicitacaoStatus.PRE_AGENDA],
            formadores=formador,
            data_inicio__date=data_evento,
        ).exclude(id=solicitacao.id)

        # Calcular horas totais
        duracao_nova = (
            solicitacao.data_fim - solicitacao.data_inicio
        ).total_seconds() / 3600
        total_horas = duracao_nova

        for evento in eventos_no_dia:
            duracao = (evento.data_fim - evento.data_inicio).total_seconds() / 3600
            total_horas += duracao

        if total_horas > max_horas_dia:
            conflicts.append(
                {
                    "type": ConflictType.MULTIPLE,
                    "message": f'Capacidade diária excedida: {total_horas:.1f}h > {max_horas_dia}h em {data_evento.strftime("%d/%m/%Y")}',
                    "details": {
                        "formador": (
                            formador.usuario.get_full_name()
                            if formador.usuario
                            else formador.nome
                        ),
                        "data": data_evento,
                        "horas_total": total_horas,
                        "horas_limite": max_horas_dia,
                        "eventos_no_dia": len(eventos_no_dia) + 1,
                    },
                }
            )

        return conflicts

    def _time_ranges_overlap(self, range1: Tuple, range2: Tuple) -> bool:
        """Verifica sobreposição entre dois intervalos de tempo"""
        start1, end1 = range1
        start2, end2 = range2
        return start1 < end2 and start2 < end1

    def _datetime_ranges_overlap(
        self, range1: Tuple, range2: Tuple, allow_adjacent: bool = False
    ) -> bool:
        """
        Verifica sobreposição entre dois intervalos de datetime

        Args:
            allow_adjacent: Se True, fim == início não é considerado conflito
        """
        start1, end1 = range1
        start2, end2 = range2

        if allow_adjacent:
            # RD-01: Se fim == início, não conflita
            return start1 < end2 and start2 < end1
        else:
            return start1 <= end2 and start2 <= end1

    def get_conflict_summary(self, conflicts: Dict[str, List[Dict]]) -> Dict[str, int]:
        """
        Gera resumo dos conflitos encontrados

        Returns:
            {'total': 5, 'E': 2, 'M': 1, 'D': 1, 'P': 1}
        """
        summary = {"total": 0}

        for formador_id, formador_conflicts in conflicts.items():
            for conflict in formador_conflicts:
                conflict_type = conflict["type"]
                summary[conflict_type] = summary.get(conflict_type, 0) + 1
                summary["total"] += 1

        return summary

    def format_conflicts_for_display(
        self, conflicts: Dict[str, List[Dict]]
    ) -> List[str]:
        """
        Formata conflitos para exibição amigável

        Returns:
            Lista de mensagens formatadas
        """
        messages = []

        for formador_id, formador_conflicts in conflicts.items():
            for conflict in formador_conflicts:
                tipo = conflict["type"]
                msg = conflict["message"]
                messages.append(f"[{tipo}] {msg}")

        return messages


# Instância global para uso fácil
conflict_detector = ConflictDetector()
