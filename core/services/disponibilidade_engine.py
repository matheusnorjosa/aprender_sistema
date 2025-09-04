"""
Motor de Disponibilidade E,M,D,P,T,X
Replica a lógica das planilhas Google para validação automática de conflitos

Códigos de Disponibilidade:
- E → Evento confirmado (sem conflitos)
- M → Mais de um evento no mesmo dia
- D → Conflito de deslocamento entre municípios
- P → Bloqueio parcial impede o evento
- T → Bloqueio total impede o evento
- X → Conflito de sobreposição de horários

Regras de Negócio (RDs do CLAUDE.md):
- RD-01: Não-sobreposição de eventos
- RD-02: Bloqueio total (T) impede qualquer evento
- RD-03: Bloqueio parcial (P) impede eventos no subintervalo
- RD-04: Buffer de deslocamento entre municípios distintos
- RD-05: Capacidade diária limitada (M)
- RD-06: Timezone-aware (America/Fortaleza)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from django.db import models
from django.db.models import Q, QuerySet
from django.utils import timezone

from core.models import DisponibilidadeFormadores, Formador, Municipio, Solicitacao


@dataclass
class ConflictInfo:
    """Informações sobre um conflito detectado"""

    code: str  # E, M, D, P, T, X
    message: str
    formador: "Formador"
    start_time: datetime
    end_time: datetime
    conflicting_event: Optional["Solicitacao"] = None
    conflicting_block: Optional["DisponibilidadeFormadores"] = None


@dataclass
class AvailabilityCheck:
    """Resultado da verificação de disponibilidade"""

    available: bool
    code: str  # E, M, D, P, T, X
    conflicts: List[ConflictInfo]
    formadores_checked: List["Formador"]
    summary_message: str


class DisponibilidadeEngine:
    """
    Motor principal de verificação de disponibilidade
    Implementa todas as regras de negócio das planilhas originais
    """

    # Configurações padrão (podem ser sobrescritas)
    DEFAULT_TRAVEL_BUFFER_MINUTES = 90  # Buffer entre municípios diferentes
    DEFAULT_DAILY_HOUR_LIMIT = 8  # Máximo de horas por dia
    TIMEZONE = "America/Fortaleza"

    def __init__(self, travel_buffer_minutes: int = None, daily_hour_limit: int = None):
        """
        Inicializa o motor com configurações específicas

        Args:
            travel_buffer_minutes: Tempo mínimo entre eventos em municípios diferentes
            daily_hour_limit: Máximo de horas de eventos por dia por formador
        """
        self.travel_buffer_minutes = (
            travel_buffer_minutes or self.DEFAULT_TRAVEL_BUFFER_MINUTES
        )
        self.daily_hour_limit = daily_hour_limit or self.DEFAULT_DAILY_HOUR_LIMIT
        self.local_tz = timezone.get_current_timezone()

    def check_availability(
        self,
        formadores: QuerySet,
        data_inicio: datetime,
        data_fim: datetime,
        municipio: Municipio,
        exclude_solicitacao: Optional[Solicitacao] = None,
    ) -> AvailabilityCheck:
        """
        Verifica disponibilidade de formadores para um evento

        Args:
            formadores: QuerySet de formadores a verificar
            data_inicio: Data/hora de início do evento
            data_fim: Data/hora de fim do evento
            municipio: Município do evento
            exclude_solicitacao: Solicitação a excluir da verificação (para edições)

        Returns:
            AvailabilityCheck com resultado da verificação
        """
        # Garantir timezone-aware (RD-06)
        if timezone.is_naive(data_inicio):
            data_inicio = timezone.make_aware(data_inicio, self.local_tz)
        if timezone.is_naive(data_fim):
            data_fim = timezone.make_aware(data_fim, self.local_tz)

        all_conflicts = []
        formadores_ok = []
        formadores_conflict = []

        for formador in formadores:
            conflicts = self._check_formador_availability(
                formador, data_inicio, data_fim, municipio, exclude_solicitacao
            )

            if conflicts:
                all_conflicts.extend(conflicts)
                formadores_conflict.append(formador)
            else:
                formadores_ok.append(formador)

        # Determinar código principal e disponibilidade
        available = len(formadores_conflict) == 0
        code = self._determine_primary_code(
            all_conflicts, formadores_ok, data_inicio.date()
        )
        summary = self._build_summary_message(
            all_conflicts, formadores_ok, formadores_conflict
        )

        return AvailabilityCheck(
            available=available,
            code=code,
            conflicts=all_conflicts,
            formadores_checked=list(formadores),
            summary_message=summary,
        )

    def _check_formador_availability(
        self,
        formador: Formador,
        data_inicio: datetime,
        data_fim: datetime,
        municipio: Municipio,
        exclude_solicitacao: Optional[Solicitacao],
    ) -> List[ConflictInfo]:
        """
        Verifica disponibilidade de um formador específico
        Implementa todas as regras RD-01 a RD-05
        """
        conflicts = []

        # RD-02: Verificar bloqueios totais (T)
        # Buscar bloqueios do dia
        event_date = data_inicio.date()
        total_blocks = DisponibilidadeFormadores.objects.filter(
            formador=formador, tipo_bloqueio="T", data_bloqueio=event_date
        )

        for block in total_blocks:
            # Converter para datetime para comparação
            block_start = timezone.make_aware(
                datetime.combine(block.data_bloqueio, block.hora_inicio), self.local_tz
            )
            block_end = timezone.make_aware(
                datetime.combine(block.data_bloqueio, block.hora_fim), self.local_tz
            )

            # Verificar sobreposição
            if block_start <= data_fim and block_end >= data_inicio:
                conflicts.append(
                    ConflictInfo(
                        code="T",
                        message=f"Bloqueio total de {block_start.strftime('%d/%m %H:%M')} a {block_end.strftime('%d/%m %H:%M')}",
                        formador=formador,
                        start_time=block_start,
                        end_time=block_end,
                        conflicting_block=block,
                    )
                )

        # RD-03: Verificar bloqueios parciais (P)
        partial_blocks = DisponibilidadeFormadores.objects.filter(
            formador=formador, tipo_bloqueio="P", data_bloqueio=event_date
        )

        for block in partial_blocks:
            # Converter para datetime para comparação
            block_start = timezone.make_aware(
                datetime.combine(block.data_bloqueio, block.hora_inicio), self.local_tz
            )
            block_end = timezone.make_aware(
                datetime.combine(block.data_bloqueio, block.hora_fim), self.local_tz
            )

            # Verificar se há sobreposição real
            overlap_start = max(data_inicio, block_start)
            overlap_end = min(data_fim, block_end)

            if overlap_start < overlap_end:
                conflicts.append(
                    ConflictInfo(
                        code="P",
                        message=f"Bloqueio parcial de {overlap_start.strftime('%d/%m %H:%M')} a {overlap_end.strftime('%d/%m %H:%M')}",
                        formador=formador,
                        start_time=overlap_start,
                        end_time=overlap_end,
                        conflicting_block=block,
                    )
                )

        # RD-01: Verificar sobreposição com eventos existentes (X)
        existing_events = Solicitacao.objects.filter(
            formadores=formador,
            status__in=[
                "APROVADO"
            ],  # Usar apenas APROVADO baseado no SolicitacaoStatus
            data_inicio__lt=data_fim,
            data_fim__gt=data_inicio,
        )

        if exclude_solicitacao:
            existing_events = existing_events.exclude(id=exclude_solicitacao.id)

        for event in existing_events:
            # Verificar se não é adjacente (fim == início não conflita)
            if not (event.data_fim == data_inicio or event.data_inicio == data_fim):
                conflicts.append(
                    ConflictInfo(
                        code="X",
                        message=f"Conflito com '{event.titulo_evento}' de {event.data_inicio.strftime('%d/%m %H:%M')} a {event.data_fim.strftime('%d/%m %H:%M')}",
                        formador=formador,
                        start_time=max(data_inicio, event.data_inicio),
                        end_time=min(data_fim, event.data_fim),
                        conflicting_event=event,
                    )
                )

        # RD-04: Verificar buffer de deslocamento (D)
        travel_conflicts = self._check_travel_buffer(
            formador, data_inicio, data_fim, municipio, exclude_solicitacao
        )
        conflicts.extend(travel_conflicts)

        # RD-05: Verificar capacidade diária (M) - apenas se não houver outros conflitos
        if not conflicts:
            daily_conflicts = self._check_daily_capacity(
                formador, data_inicio, data_fim, exclude_solicitacao
            )
            conflicts.extend(daily_conflicts)

        return conflicts

    def _check_travel_buffer(
        self,
        formador: Formador,
        data_inicio: datetime,
        data_fim: datetime,
        municipio: Municipio,
        exclude_solicitacao: Optional[Solicitacao],
    ) -> List[ConflictInfo]:
        """
        RD-04: Verifica buffer de deslocamento entre municípios diferentes
        """
        conflicts = []
        buffer = timedelta(minutes=self.travel_buffer_minutes)

        # Buscar eventos próximos ao horário proposto
        buffer_start = data_inicio - buffer
        buffer_end = data_fim + buffer

        nearby_events = (
            Solicitacao.objects.filter(formadores=formador, status__in=["APROVADO"])
            .exclude(municipio=municipio)
            .filter(
                Q(data_inicio__gte=buffer_start, data_inicio__lte=buffer_end)
                | Q(data_fim__gte=buffer_start, data_fim__lte=buffer_end)
            )
        )

        if exclude_solicitacao:
            nearby_events = nearby_events.exclude(id=exclude_solicitacao.id)

        for event in nearby_events:
            # Calcular se precisa de buffer entre municípios diferentes
            time_between = None

            if event.data_fim <= data_inicio:  # Evento anterior
                time_between = data_inicio - event.data_fim
                direction = f"após evento em {event.municipio.nome}"
            elif event.data_inicio >= data_fim:  # Evento posterior
                time_between = event.data_inicio - data_fim
                direction = f"antes de evento em {event.municipio.nome}"

            if time_between and time_between < buffer:
                conflicts.append(
                    ConflictInfo(
                        code="D",
                        message=f"Deslocamento insuficiente {direction} - necessário {self.travel_buffer_minutes}min, disponível {int(time_between.total_seconds()/60)}min",
                        formador=formador,
                        start_time=data_inicio,
                        end_time=data_fim,
                        conflicting_event=event,
                    )
                )

        return conflicts

    def _check_daily_capacity(
        self,
        formador: Formador,
        data_inicio: datetime,
        data_fim: datetime,
        exclude_solicitacao: Optional[Solicitacao],
    ) -> List[ConflictInfo]:
        """
        RD-05: Verifica se o formador não excede capacidade diária
        """
        conflicts = []
        event_date = data_inicio.date()

        # Buscar eventos do mesmo dia
        daily_events = Solicitacao.objects.filter(
            formadores=formador, status__in=["APROVADO"], data_inicio__date=event_date
        )

        if exclude_solicitacao:
            daily_events = daily_events.exclude(id=exclude_solicitacao.id)

        # Calcular horas já ocupadas
        total_hours = 0
        for event in daily_events:
            duration = event.data_fim - event.data_inicio
            total_hours += duration.total_seconds() / 3600

        # Adicionar duração do evento proposto
        new_duration = data_fim - data_inicio
        new_hours = new_duration.total_seconds() / 3600
        total_with_new = total_hours + new_hours

        if total_with_new > self.daily_hour_limit:
            conflicts.append(
                ConflictInfo(
                    code="M",
                    message=f"Capacidade diária excedida: {total_with_new:.1f}h (máximo {self.daily_hour_limit}h)",
                    formador=formador,
                    start_time=data_inicio,
                    end_time=data_fim,
                )
            )

        return conflicts

    def _determine_primary_code(
        self, conflicts: List[ConflictInfo], formadores_ok: List[Formador], event_date
    ) -> str:
        """
        Determina o código principal baseado nos conflitos encontrados
        Prioridade: T > P > X > D > M > E
        """
        if not conflicts:
            # Verificar se há múltiplos eventos no dia (M)
            # Isso é verificado posteriormente para formadores OK
            return "E"  # Evento sem conflitos

        # Buscar códigos por prioridade
        codes = [c.code for c in conflicts]

        if "T" in codes:
            return "T"
        elif "P" in codes:
            return "P"
        elif "X" in codes:
            return "X"
        elif "D" in codes:
            return "D"
        elif "M" in codes:
            return "M"
        else:
            return "X"  # Default para qualquer conflito não mapeado

    def _build_summary_message(
        self,
        conflicts: List[ConflictInfo],
        formadores_ok: List[Formador],
        formadores_conflict: List[Formador],
    ) -> str:
        """
        Constrói mensagem resumo da verificação de disponibilidade
        """
        if not conflicts:
            return f"✅ Disponível para {len(formadores_ok)} formador(es)"

        # Agrupar conflitos por tipo
        conflicts_by_code = {}
        for conflict in conflicts:
            code = conflict.code
            if code not in conflicts_by_code:
                conflicts_by_code[code] = []
            conflicts_by_code[code].append(conflict)

        summary_parts = []

        for code, code_conflicts in conflicts_by_code.items():
            formadores_with_code = {c.formador.nome for c in code_conflicts}
            count = len(formadores_with_code)

            code_names = {
                "T": "Bloqueio Total",
                "P": "Bloqueio Parcial",
                "X": "Conflito de Horário",
                "D": "Conflito de Deslocamento",
                "M": "Capacidade Diária Excedida",
            }

            name = code_names.get(code, f"Conflito {code}")
            summary_parts.append(f"{name}: {count} formador(es)")

        summary = f"❌ Conflitos encontrados - {'; '.join(summary_parts)}"

        if formadores_ok:
            summary += f" | ✅ {len(formadores_ok)} formador(es) disponível(eis)"

        return summary

    def get_availability_matrix(
        self, formadores: QuerySet, start_date: datetime, end_date: datetime
    ) -> Dict[str, Dict[str, str]]:
        """
        Gera matriz de disponibilidade para período (equivalente ao mapa mensal)

        Returns:
            Dict[formador_nome][data_str] = código (E,M,D,P,T,X)
        """
        matrix = {}

        current_date = start_date.date()
        end = end_date.date()

        while current_date <= end:
            for formador in formadores:
                if formador.nome not in matrix:
                    matrix[formador.nome] = {}

                # Verificar status do dia inteiro para o formador
                day_start = timezone.make_aware(
                    datetime.combine(current_date, datetime.min.time().replace(hour=8)),
                    self.local_tz,
                )
                day_end = timezone.make_aware(
                    datetime.combine(
                        current_date, datetime.min.time().replace(hour=17)
                    ),
                    self.local_tz,
                )

                # Usar check_availability para determinar código do dia
                # Para matriz mensal, usar municipio genérico ou primeiro disponível
                default_municipio = Municipio.objects.first()

                check = self.check_availability(
                    formadores.filter(id=formador.id),
                    day_start,
                    day_end,
                    default_municipio,
                )

                matrix[formador.nome][current_date.strftime("%Y-%m-%d")] = check.code

            current_date += timedelta(days=1)

        return matrix


# Factory function para facilitar uso em views/commands
def create_availability_engine(**kwargs) -> DisponibilidadeEngine:
    """
    Cria instância do motor de disponibilidade com configurações padrão
    """
    return DisponibilidadeEngine(**kwargs)


# Função de conveniência para verificação rápida
def check_formador_availability(
    formador: Formador,
    data_inicio: datetime,
    data_fim: datetime,
    municipio: Municipio = None,
) -> AvailabilityCheck:
    """
    Função de conveniência para verificar disponibilidade de um formador
    """
    engine = create_availability_engine()
    # Usar municipio fornecido ou buscar um padrão
    target_municipio = municipio or Municipio.objects.first()
    return engine.check_availability(
        Formador.objects.filter(id=formador.id), data_inicio, data_fim, target_municipio
    )
