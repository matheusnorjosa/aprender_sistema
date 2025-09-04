"""
Sistema de APOIO à criação manual de eventos no Google Calendar pelo grupo Controle.
SEMANA 3 - DIA 3: Integração Google Calendar + Google Meet

IMPORTANTE: Este sistema não cria eventos automaticamente.
Fornece ferramentas para o grupo Controle criar manualmente os eventos,
respeitando o fluxo de negócio onde o Controle tem autonomia sobre a criação.
"""

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.models import (
    EventoGoogleCalendar,
    LogAuditoria,
    Solicitacao,
    SolicitacaoStatus,
)
from core.services.integrations.calendar_mapper import map_solicitacao_to_google_event
from core.services.integrations.google_calendar import (
    GoogleCalendarService,
)
from core.services.integrations.google_calendar import is_enabled as google_enabled

logger = logging.getLogger(__name__)


class GoogleCalendarManagementService:
    """
    Serviço de apoio ao grupo Controle para criação manual de eventos
    no Google Calendar. Fornece ferramentas para facilitar o processo manual.
    """

    def __init__(self):
        self.calendar_service = GoogleCalendarService()

    @transaction.atomic
    def create_event_for_controle(
        self, solicitacao: Solicitacao, user
    ) -> Dict[str, Any]:
        """
        CRIAÇÃO MANUAL pelo grupo Controle.

        Este método é chamado quando um usuário do grupo Controle
        decide criar manualmente um evento para uma solicitação em PRE_AGENDA.

        Args:
            solicitacao: Solicitação em PRE_AGENDA
            user: Usuário do grupo Controle

        Returns:
            Dict com resultado da operação manual
        """
        if not google_enabled():
            return {
                "success": False,
                "action": "integration_disabled",
                "reason": "Google Calendar integration disabled",
                "message": "Integração com Google Calendar está desabilitada",
            }

        if solicitacao.status != SolicitacaoStatus.PRE_AGENDA:
            return {
                "success": False,
                "action": "invalid_status",
                "reason": f"Status atual: {solicitacao.status}",
                "message": "Solicitação deve estar em status PRE_AGENDA para criação manual",
            }

        # Verificar se já existe evento para esta solicitação
        existing_event = EventoGoogleCalendar.objects.filter(
            solicitacao=solicitacao
        ).first()

        if existing_event:
            return {
                "success": False,
                "action": "duplicate",
                "reason": "Event already exists",
                "message": f"Evento já existe no Google Calendar: {existing_event.provider_event_id}",
                "event_id": existing_event.provider_event_id,
                "html_link": existing_event.html_link,
                "meet_link": existing_event.meet_link,
            }

        try:
            # Criar evento no Google Calendar via ação manual do Controle
            result = self._create_calendar_event_manual(solicitacao, user)

            if result["success"]:
                # Atualizar status para APROVADO após criação manual
                solicitacao.status = SolicitacaoStatus.APROVADO
                solicitacao.save(update_fields=["status"])

                return {
                    "success": True,
                    "action": "created_manually",
                    "event_id": result["event_id"],
                    "html_link": result["html_link"],
                    "meet_link": result["meet_link"],
                    "message": "Evento criado manualmente pelo grupo Controle no Google Calendar",
                }
            else:
                return result

        except Exception as e:
            logger.error(
                f"Erro na criação manual pelo Controle - solicitação {solicitacao.id}: {e}"
            )

            # Registrar erro na auditoria
            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: ERRO criação manual",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"ERRO na criação manual pelo Controle: {str(e)}",
            )

            return {
                "success": False,
                "action": "error",
                "reason": str(e),
                "message": f"Erro na criação manual: {str(e)}",
            }

    def _create_calendar_event_manual(
        self, solicitacao: Solicitacao, user
    ) -> Dict[str, Any]:
        """Cria evento no Google Calendar e registra no banco de dados"""
        try:
            # Converter solicitação para formato Google Event
            gevent = map_solicitacao_to_google_event(solicitacao)

            # Criar evento via API
            api_result = self.calendar_service.create_event(gevent)

            # Salvar referência no banco
            evento_gc = EventoGoogleCalendar.objects.create(
                solicitacao=solicitacao,
                provider_event_id=api_result["id"],
                html_link=api_result.get("htmlLink", ""),
                meet_link=api_result.get("hangoutLink", ""),
                criado_por=user,
            )

            # Registrar auditoria da criação manual
            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: Controle criou evento manual",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento '{solicitacao.titulo_evento}' criado manualmente pelo Controle "
                f"— ID: {api_result['id']} "
                f"— Meet: {'Sim' if api_result.get('hangoutLink') else 'Não'}",
            )

            # Enviar notificações sobre evento criado (SEMANA 3 - DIA 4)
            from core.services.notifications_simplified import notify_event_created

            try:
                notify_result = notify_event_created(solicitacao, evento_gc, user)
                if notify_result["success"]:
                    LogAuditoria.objects.create(
                        usuario=user,
                        acao="RF07: Notificações de evento criado enviadas",
                        entidade_afetada_id=solicitacao.id,
                        detalhes=f"Notificações enviadas: {notify_result['notifications_sent']}",
                    )
            except Exception as e:
                # Erro nas notificações não deve interromper o processo
                LogAuditoria.objects.create(
                    usuario=user,
                    acao="RF07: Erro em notificações de evento criado",
                    entidade_afetada_id=solicitacao.id,
                    detalhes=f"Erro: {str(e)}",
                )

            logger.info(
                f"Evento criado com sucesso para solicitação {solicitacao.id}: {api_result['id']}"
            )

            return {
                "success": True,
                "event_id": api_result["id"],
                "html_link": api_result.get("htmlLink", ""),
                "meet_link": api_result.get("hangoutLink", ""),
                "db_event_id": evento_gc.id,
            }

        except Exception as e:
            logger.error(
                f"Erro ao criar evento no calendar para solicitação {solicitacao.id}: {e}"
            )
            raise

    @transaction.atomic
    def update_calendar_event(self, solicitacao: Solicitacao, user) -> Dict[str, Any]:
        """
        Atualiza evento existente no Google Calendar quando solicitação é modificada.
        """
        if not google_enabled():
            return {
                "success": True,
                "action": "skipped",
                "reason": "Google Calendar integration disabled",
            }

        try:
            evento_gc = EventoGoogleCalendar.objects.get(solicitacao=solicitacao)
        except EventoGoogleCalendar.DoesNotExist:
            return {
                "success": False,
                "action": "not_found",
                "reason": "No Google Calendar event found for this solicitacao",
            }

        try:
            # Converter solicitação atualizada
            gevent = map_solicitacao_to_google_event(solicitacao)

            # Atualizar via API
            api_result = self.calendar_service.update_event(
                evento_gc.provider_event_id, gevent
            )

            # Atualizar referência no banco
            evento_gc.html_link = api_result.get("htmlLink", evento_gc.html_link)
            evento_gc.meet_link = api_result.get("hangoutLink", evento_gc.meet_link)
            evento_gc.save(update_fields=["html_link", "meet_link"])

            # Registrar auditoria
            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: Atualizar evento Google Calendar",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento '{solicitacao.titulo_evento}' atualizado no Google Calendar "
                f"— ID: {evento_gc.provider_event_id}",
            )

            return {
                "success": True,
                "action": "updated",
                "event_id": evento_gc.provider_event_id,
                "html_link": api_result.get("htmlLink", ""),
                "meet_link": api_result.get("hangoutLink", ""),
            }

        except Exception as e:
            logger.error(
                f"Erro ao atualizar evento para solicitação {solicitacao.id}: {e}"
            )

            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: ERRO atualização evento",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"ERRO ao atualizar evento: {str(e)}",
            )

            return {"success": False, "action": "error", "reason": str(e)}

    @transaction.atomic
    def delete_calendar_event(self, solicitacao: Solicitacao, user) -> Dict[str, Any]:
        """
        Remove evento do Google Calendar quando solicitação é cancelada/rejeitada.
        """
        if not google_enabled():
            return {
                "success": True,
                "action": "skipped",
                "reason": "Google Calendar integration disabled",
            }

        try:
            evento_gc = EventoGoogleCalendar.objects.get(solicitacao=solicitacao)
        except EventoGoogleCalendar.DoesNotExist:
            return {
                "success": True,
                "action": "not_found",
                "reason": "No Google Calendar event to delete",
            }

        try:
            # Deletar via API
            self.calendar_service.delete_event(evento_gc.provider_event_id)

            # Registrar auditoria antes de deletar o registro
            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: Deletar evento Google Calendar",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento '{solicitacao.titulo_evento}' removido do Google Calendar "
                f"— ID: {evento_gc.provider_event_id}",
            )

            # Remover referência do banco
            evento_gc.delete()

            return {
                "success": True,
                "action": "deleted",
                "event_id": evento_gc.provider_event_id,
            }

        except Exception as e:
            logger.error(
                f"Erro ao deletar evento para solicitação {solicitacao.id}: {e}"
            )

            LogAuditoria.objects.create(
                usuario=user,
                acao="RF05: ERRO remoção evento",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"ERRO ao remover evento: {str(e)}",
            )

            return {"success": False, "action": "error", "reason": str(e)}

    @transaction.atomic
    def bulk_create_events_for_controle(self, user) -> Dict[str, Any]:
        """
        Criação em lote MANUAL de eventos pelo grupo Controle.

        Processa todas as solicitações em PRE_AGENDA que ainda não têm eventos
        criados no Google Calendar e permite ao Controle criar todos de uma vez.

        Args:
            user: Usuário do grupo Controle

        Returns:
            Dict com resultado da operação em lote
        """
        if not google_enabled():
            return {
                "success": False,
                "action": "integration_disabled",
                "message": "Integração com Google Calendar está desabilitada",
            }

        # Buscar solicitações PRE_AGENDA sem evento criado
        solicitacoes_pendentes = []
        for solicitacao in Solicitacao.objects.filter(
            status=SolicitacaoStatus.PRE_AGENDA
        ):
            if not EventoGoogleCalendar.objects.filter(
                solicitacao=solicitacao
            ).exists():
                solicitacoes_pendentes.append(solicitacao)

        if not solicitacoes_pendentes:
            return {
                "success": True,
                "action": "no_events_to_create",
                "message": "Não há eventos pendentes para criação",
                "processed": 0,
                "successful": 0,
                "failed": 0,
            }

        results = []
        successful = 0
        failed = 0

        for solicitacao in solicitacoes_pendentes:
            try:
                result = self.create_event_for_controle(solicitacao, user)
                if result["success"]:
                    successful += 1
                else:
                    failed += 1

                results.append(
                    {
                        "solicitacao_id": str(solicitacao.id),
                        "titulo": solicitacao.titulo_evento,
                        "success": result["success"],
                        "message": result.get("message", ""),
                        "event_id": result.get("event_id", ""),
                        "html_link": result.get("html_link", ""),
                        "meet_link": result.get("meet_link", ""),
                    }
                )

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "solicitacao_id": str(solicitacao.id),
                        "titulo": solicitacao.titulo_evento,
                        "success": False,
                        "error": str(e),
                    }
                )

                logger.error(
                    f"Erro na criação em lote - solicitação {solicitacao.id}: {e}"
                )

        # Log de auditoria da operação em lote
        LogAuditoria.objects.create(
            usuario=user,
            acao="RF05: Controle - Criação em lote de eventos",
            detalhes=f"Processadas {len(solicitacoes_pendentes)} solicitações "
            f"— {successful} sucessos, {failed} falhas",
        )

        return {
            "success": failed == 0,
            "action": "bulk_create_completed",
            "processed": len(solicitacoes_pendentes),
            "successful": successful,
            "failed": failed,
            "results": results,
            "message": f"Criação em lote concluída: {successful} sucessos, {failed} falhas",
        }

    def get_pre_agenda_summary(self) -> Dict[str, Any]:
        """
        Retorna resumo das solicitações em PRE_AGENDA para o grupo Controle.
        Ferramenta de apoio para visualização e organização.
        """
        solicitacoes_pre_agenda = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PRE_AGENDA
        ).select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")

        # Verificar quais já têm eventos criados
        solicitacoes_com_evento = []
        solicitacoes_sem_evento = []

        for solicitacao in solicitacoes_pre_agenda:
            has_calendar_event = EventoGoogleCalendar.objects.filter(
                solicitacao=solicitacao
            ).exists()

            solicitacao_data = {
                "id": str(solicitacao.id),
                "titulo": solicitacao.titulo_evento,
                "projeto": solicitacao.projeto.nome if solicitacao.projeto else "",
                "municipio": (
                    solicitacao.municipio.nome if solicitacao.municipio else ""
                ),
                "data_inicio": (
                    solicitacao.data_inicio.isoformat()
                    if solicitacao.data_inicio
                    else None
                ),
                "formadores": [f.nome for f in solicitacao.formadores.all()],
                "solicitante": (
                    solicitacao.usuario_solicitante.username
                    if solicitacao.usuario_solicitante
                    else ""
                ),
            }

            if has_calendar_event:
                solicitacoes_com_evento.append(solicitacao_data)
            else:
                solicitacoes_sem_evento.append(solicitacao_data)

        return {
            "total_pre_agenda": len(solicitacoes_pre_agenda),
            "com_evento_criado": len(solicitacoes_com_evento),
            "sem_evento_criado": len(solicitacoes_sem_evento),
            "solicitacoes_sem_evento": solicitacoes_sem_evento,
            "solicitacoes_com_evento": solicitacoes_com_evento,
            "integration_enabled": google_enabled(),
        }


# Funções de conveniência para uso pelos views do grupo Controle
def manual_create_calendar_event(solicitacao: Solicitacao, user) -> Dict[str, Any]:
    """
    Função de conveniência para criar evento manualmente pelo grupo Controle.
    Usada quando o Controle decide criar um evento para uma solicitação em PRE_AGENDA.
    """
    service = GoogleCalendarManagementService()
    return service.create_event_for_controle(solicitacao, user)


def manual_update_calendar_event(solicitacao: Solicitacao, user) -> Dict[str, Any]:
    """
    Função de conveniência para atualizar evento manualmente.
    Usada quando o Controle precisa atualizar um evento já criado.
    """
    service = GoogleCalendarManagementService()
    return service.update_calendar_event(solicitacao, user)


def manual_delete_calendar_event(solicitacao: Solicitacao, user) -> Dict[str, Any]:
    """
    Função de conveniência para deletar evento manualmente.
    Usada quando o Controle precisa cancelar um evento.
    """
    service = GoogleCalendarManagementService()
    return service.delete_calendar_event(solicitacao, user)


def get_controle_dashboard_data() -> Dict[str, Any]:
    """
    Função de conveniência para obter dados do dashboard do Controle.
    Retorna resumo das solicitações pendentes de criação manual.
    """
    service = GoogleCalendarManagementService()
    return service.get_pre_agenda_summary()
