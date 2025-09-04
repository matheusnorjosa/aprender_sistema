"""
Serviço de Disponibilidade - Camada de integração do Motor E,M,D,P,T,X

Conecta o motor de disponibilidade com:
- Views Django (formulários de solicitação)
- Commands de migração
- APIs JSON (mapa mensal)
- Webhooks e notificações

Este serviço implementa a regra PA-01 (Sem auto-aprovação):
Uma Solicitacao NUNCA muda para "Aprovada" automaticamente.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.utils import timezone

from core.models import (
    DisponibilidadeFormadores,
    Formador,
    LogAuditoria,
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
)
from core.services.disponibilidade_engine import (
    AvailabilityCheck,
    ConflictInfo,
    DisponibilidadeEngine,
    create_availability_engine,
)


class AvailabilityService:
    """
    Serviço principal de disponibilidade
    Implementa regras de negócio e integração com o sistema
    """

    def __init__(self):
        self.engine = create_availability_engine()

    def validate_solicitacao(
        self,
        data_inicio: datetime,
        data_fim: datetime,
        formadores: QuerySet,
        municipio: Municipio,
        exclude_solicitacao: Optional[Solicitacao] = None,
        user: Optional[User] = None,
    ) -> Tuple[bool, AvailabilityCheck, List[str]]:
        """
        Valida uma solicitação de evento verificando disponibilidade

        Args:
            data_inicio: Data/hora início
            data_fim: Data/hora fim
            formadores: QuerySet de formadores
            municipio: Município do evento
            exclude_solicitacao: Solicitação a excluir (para edições)
            user: Usuário solicitante (para auditoria)

        Returns:
            Tuple[pode_solicitar, resultado_verificacao, mensagens_aviso]
        """
        # Verificar disponibilidade
        check_result = self.engine.check_availability(
            formadores, data_inicio, data_fim, municipio, exclude_solicitacao
        )

        # Regras de validação adicionais
        warnings = []
        can_request = True

        # Validação 1: Horário de funcionamento
        if not self._is_business_hours(data_inicio, data_fim):
            warnings.append("⚠️ Evento fora do horário comercial (8h-17h)")

        # Validação 2: Antecedência mínima
        min_notice = self._check_minimum_notice(data_inicio)
        if min_notice:
            warnings.append(f"⚠️ {min_notice}")

        # Validação 3: Final de semana
        if data_inicio.weekday() >= 5:  # Sábado ou Domingo
            warnings.append("⚠️ Evento agendado para final de semana")

        # Decisão final baseada em conflitos críticos
        critical_codes = ["T", "X"]  # Bloqueio total e conflitos de horário impedem
        has_critical = any(c.code in critical_codes for c in check_result.conflicts)

        if has_critical:
            can_request = False
            warnings.insert(
                0, "❌ Solicitação não pode ser criada devido a conflitos críticos"
            )
        elif check_result.conflicts:
            warnings.insert(
                0,
                "⚠️ Solicitação será criada com ressalvas - requer aprovação cuidadosa",
            )

        # Auditoria
        if user:
            self._log_validation_attempt(
                user,
                check_result,
                data_inicio,
                data_fim,
                formadores,
                municipio,
                can_request,
            )

        return can_request, check_result, warnings

    def create_solicitacao_with_validation(
        self,
        titulo: str,
        data_inicio: datetime,
        data_fim: datetime,
        formadores: QuerySet,
        municipio: Municipio,
        projeto: Projeto,
        tipo_evento: TipoEvento,
        observacoes: str = "",
        solicitante: Optional[User] = None,
    ) -> Tuple[Optional[Solicitacao], List[str], AvailabilityCheck]:
        """
        Cria solicitação após validação de disponibilidade

        IMPORTANTE: Implementa PA-01 - Nunca auto-aprova
        Status inicial SEMPRE é 'PENDENTE'

        Returns:
            Tuple[solicitacao_criada, mensagens, resultado_verificacao]
        """
        # Validar disponibilidade
        can_request, check_result, warnings = self.validate_solicitacao(
            data_inicio, data_fim, formadores, municipio, user=solicitante
        )

        if not can_request:
            return None, warnings, check_result

        # Criar solicitação com status PENDENTE (PA-01)
        try:
            # Criar uma solicitação e relacionar com múltiplos formadores via M2M
            solicitacao = Solicitacao.objects.create(
                titulo_evento=titulo,
                data_inicio=data_inicio,
                data_fim=data_fim,
                municipio=municipio,
                projeto=projeto,
                tipo_evento=tipo_evento,
                observacoes=observacoes,
                status="PENDENTE",  # PA-01: NUNCA auto-aprova
                usuario_solicitante=solicitante,
            )

            # Relacionar com formadores via M2M through
            from core.models import FormadoresSolicitacao

            for formador in formadores:
                FormadoresSolicitacao.objects.create(
                    solicitacao=solicitacao, formador=formador
                )

            # Log de auditoria
            if solicitante:
                LogAuditoria.objects.create(
                    usuario=solicitante,
                    acao="CREATE_SOLICITACAO",
                    entidade_afetada_id=solicitacao.id,
                    detalhes=f"Criação de solicitação: '{titulo}' para {municipio.nome} de {data_inicio.strftime('%d/%m/%Y %H:%M')} a {data_fim.strftime('%d/%m/%Y %H:%M')} - Formadores: {', '.join([f.nome for f in formadores])} - Status: PENDENTE - Resultado: {check_result.code} ({len(check_result.conflicts)} conflitos)",
                )

            success_msg = (
                f"✅ Solicitação criada com sucesso para {len(formadores)} formador(es)"
            )
            success_msg += f" - Status: PENDENTE (aguarda aprovação)"
            warnings.insert(0, success_msg)

            return solicitacao, warnings, check_result

        except Exception as e:
            error_msg = f"❌ Erro ao criar solicitação: {str(e)}"
            return None, [error_msg], check_result

    def get_availability_matrix(
        self, formadores: QuerySet, ano: int, mes: int
    ) -> Dict[str, Dict[str, Dict]]:
        """
        Gera matriz de disponibilidade para o mapa mensal
        Equivalente à planilha DISPONIBILIDADE original

        Returns:
            Dict[formador_nome][dia] = {
                'code': 'E'|'M'|'D'|'P'|'T'|'X',
                'events': [lista de eventos],
                'blocks': [lista de bloqueios],
                'color': 'green'|'yellow'|'red'|'gray'
            }
        """
        # Período do mês
        start_date = timezone.make_aware(
            datetime(ano, mes, 1, 8, 0), timezone.get_current_timezone()
        )

        # Último dia do mês
        if mes == 12:
            next_month = datetime(ano + 1, 1, 1)
        else:
            next_month = datetime(ano, mes + 1, 1)

        last_day = (next_month - timedelta(days=1)).day
        end_date = timezone.make_aware(
            datetime(ano, mes, last_day, 17, 0), timezone.get_current_timezone()
        )

        # Buscar dados do período
        events_data = self._get_period_events(formadores, start_date, end_date)
        blocks_data = self._get_period_blocks(formadores, start_date, end_date)

        # Montar matriz
        matrix = {}

        for formador in formadores:
            matrix[formador.nome] = {}

            for day in range(1, last_day + 1):
                day_date = date(ano, mes, day)
                day_start = timezone.make_aware(
                    datetime.combine(day_date, datetime.min.time().replace(hour=8)),
                    timezone.get_current_timezone(),
                )
                day_end = timezone.make_aware(
                    datetime.combine(day_date, datetime.min.time().replace(hour=17)),
                    timezone.get_current_timezone(),
                )

                # Eventos do dia
                day_events = [
                    e
                    for e in events_data.get(formador.id, [])
                    if e.data_inicio.date() == day_date
                ]

                # Bloqueios do dia
                day_blocks = [
                    b
                    for b in blocks_data.get(formador.id, [])
                    if b.data_bloqueio == day_date
                ]

                # Determinar código do dia
                if day_blocks and any(b.tipo_bloqueio == "T" for b in day_blocks):
                    code = "T"
                    color = "gray"
                elif day_blocks and any(b.tipo_bloqueio == "P" for b in day_blocks):
                    code = "P"
                    color = "yellow"
                elif len(day_events) == 0:
                    code = ""  # Disponível
                    color = "green"
                elif len(day_events) == 1:
                    code = "E"
                    color = "blue"
                else:  # Múltiplos eventos
                    code = "M"
                    color = "orange"

                # Verificar conflitos (X)
                if len(day_events) >= 2:
                    # Verificar sobreposição entre eventos
                    for i, event1 in enumerate(day_events):
                        for event2 in day_events[i + 1 :]:
                            if (
                                event1.data_inicio < event2.data_fim
                                and event2.data_inicio < event1.data_fim
                            ):
                                code = "X"
                                color = "red"
                                break
                        if code == "X":
                            break

                matrix[formador.nome][str(day)] = {
                    "code": code,
                    "events": [
                        {
                            "titulo": e.titulo_evento,
                            "inicio": e.data_inicio.strftime("%H:%M"),
                            "fim": e.data_fim.strftime("%H:%M"),
                            "municipio": e.municipio.nome if e.municipio else "",
                            "status": e.status,
                        }
                        for e in day_events
                    ],
                    "blocks": [
                        {
                            "tipo": b.tipo_bloqueio,
                            "motivo": b.motivo or "",
                            "inicio": b.hora_inicio.strftime("%H:%M"),
                            "fim": b.hora_fim.strftime("%H:%M"),
                        }
                        for b in day_blocks
                    ],
                    "color": color,
                }

        return matrix

    def suggest_alternative_slots(
        self,
        formadores: QuerySet,
        data_inicio: datetime,
        data_fim: datetime,
        municipio: Municipio,
        days_ahead: int = 30,
    ) -> List[Dict]:
        """
        Sugere horários alternativos quando há conflitos

        Returns:
            Lista de slots disponíveis: [{'inicio': datetime, 'fim': datetime, 'formadores_livres': QuerySet}]
        """
        suggestions = []
        duration = data_fim - data_inicio

        # Verificar próximos dias úteis
        current_date = data_inicio.date()

        for day_offset in range(1, days_ahead + 1):
            check_date = current_date + timedelta(days=day_offset)

            # Pular fins de semana
            if check_date.weekday() >= 5:
                continue

            # Verificar slots no dia
            for hour in range(8, 17):  # 8h às 17h
                slot_start = timezone.make_aware(
                    datetime.combine(
                        check_date, datetime.min.time().replace(hour=hour)
                    ),
                    timezone.get_current_timezone(),
                )
                slot_end = slot_start + duration

                # Não ultrapassar horário comercial
                if slot_end.hour > 17:
                    continue

                # Verificar disponibilidade
                check_result = self.engine.check_availability(
                    formadores, slot_start, slot_end, municipio
                )

                if check_result.available:
                    suggestions.append(
                        {
                            "inicio": slot_start,
                            "fim": slot_end,
                            "formadores_livres": formadores,
                            "confidence": "high",
                        }
                    )
                elif len(check_result.conflicts) <= 2:  # Conflitos menores
                    # Calcular formadores ainda disponíveis
                    conflicted_formadores = set(
                        c.formador.id for c in check_result.conflicts
                    )
                    free_formadores = formadores.exclude(id__in=conflicted_formadores)

                    if free_formadores.exists():
                        suggestions.append(
                            {
                                "inicio": slot_start,
                                "fim": slot_end,
                                "formadores_livres": free_formadores,
                                "confidence": "medium",
                                "notes": f"{len(conflicted_formadores)} formador(es) indisponível(eis)",
                            }
                        )

            # Parar se já encontrou sugestões suficientes
            if len(suggestions) >= 10:
                break

        return suggestions[:10]  # Retornar top 10

    def _is_business_hours(self, inicio: datetime, fim: datetime) -> bool:
        """Verifica se evento está dentro do horário comercial"""
        return 8 <= inicio.hour <= 17 and 8 <= fim.hour <= 17

    def _check_minimum_notice(self, data_evento: datetime) -> Optional[str]:
        """Verifica antecedência mínima"""
        now = timezone.now()
        notice = data_evento - now

        if notice.days < 1:
            return "Evento deve ser agendado com pelo menos 1 dia de antecedência"
        elif notice.days < 7:
            return "Recomendado agendar com pelo menos 7 dias de antecedência"

        return None

    def _get_period_events(
        self, formadores: QuerySet, start: datetime, end: datetime
    ) -> Dict[int, List]:
        """Busca eventos do período agrupados por formador"""
        events = (
            Solicitacao.objects.filter(
                formadores__in=formadores,
                status__in=["APROVADO"],
                data_inicio__lte=end,
                data_fim__gte=start,
            )
            .select_related("municipio")
            .prefetch_related("formadores")
        )

        grouped = {}
        for event in events:
            # Um evento pode ter múltiplos formadores
            for formador in event.formadores.all():
                if formador.id in [f.id for f in formadores]:
                    formador_id = formador.id
                    if formador_id not in grouped:
                        grouped[formador_id] = []
                    grouped[formador_id].append(event)

        return grouped

    def _get_period_blocks(
        self, formadores: QuerySet, start: datetime, end: datetime
    ) -> Dict[int, List]:
        """Busca bloqueios do período agrupados por formador"""
        blocks = DisponibilidadeFormadores.objects.filter(
            formador__in=formadores,
            data_bloqueio__gte=start.date(),
            data_bloqueio__lte=end.date(),
        ).select_related("formador")

        grouped = {}
        for block in blocks:
            formador_id = block.formador.id
            if formador_id not in grouped:
                grouped[formador_id] = []
            grouped[formador_id].append(block)

        return grouped

    def _log_validation_attempt(
        self,
        user: User,
        check_result: AvailabilityCheck,
        data_inicio: datetime,
        data_fim: datetime,
        formadores: QuerySet,
        municipio: Municipio,
        can_request: bool,
    ):
        """Log de tentativa de validação para auditoria"""
        LogAuditoria.objects.create(
            usuario=user,
            acao="VALIDATE_AVAILABILITY",
            detalhes=f"Validação de disponibilidade: {municipio.nome} de {data_inicio.strftime('%d/%m/%Y %H:%M')} a {data_fim.strftime('%d/%m/%Y %H:%M')} - Formadores: {', '.join([f.nome for f in formadores])} - Resultado: {check_result.code} ({'Pode solicitar' if can_request else 'Não pode solicitar'}) - {len(check_result.conflicts)} conflito(s)",
        )


# Instância global do serviço
availability_service = AvailabilityService()
