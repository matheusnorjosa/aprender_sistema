"""
APIs para apoio ao grupo Controle na criação manual de eventos no Google Calendar.
SEMANA 3 - DIA 3: Integração Google Calendar + Google Meet

IMPORTANTE: Estas APIs apoiam o processo MANUAL do grupo Controle,
não criam eventos automaticamente.
"""

import json

from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from core.models import EventoGoogleCalendar, Solicitacao, SolicitacaoStatus
from core.services.google_calendar_automation import GoogleCalendarManagementService
from core.services.integrations.google_calendar import is_enabled as google_enabled


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.sync_calendar"), name="dispatch")
class ManualCreateEventAPI(View):
    """
    API para criação MANUAL de evento no Google Calendar
    pelo grupo Controle a partir de uma solicitação em PRE_AGENDA.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            solicitacao_id = data.get("solicitacao_id")

            if not solicitacao_id:
                return JsonResponse(
                    {"success": False, "error": "ID da solicitação é obrigatório"}
                )

            # Buscar solicitação
            solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

            # Verificar se está em status adequado
            if solicitacao.status != SolicitacaoStatus.PRE_AGENDA:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Solicitação deve estar em PRE_AGENDA (atual: {solicitacao.status})",
                    }
                )

            # Processar criação MANUAL pelo grupo Controle
            management_service = GoogleCalendarManagementService()
            result = management_service.create_event_for_controle(
                solicitacao, request.user
            )

            return JsonResponse(result)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.sync_calendar"), name="dispatch")
class BulkCreateEventsAPI(View):
    """
    API para criação em lote de eventos no Google Calendar
    para todas as solicitações em PRE_AGENDA.
    """

    def post(self, request):
        try:
            if not google_enabled():
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Integração com Google Calendar está desabilitada",
                    }
                )

            # Processar todas as solicitações em PRE_AGENDA MANUALMENTE
            management_service = GoogleCalendarManagementService()
            result = management_service.bulk_create_events_for_controle(request.user)

            return JsonResponse(result)

        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.sync_calendar"), name="dispatch")
class UpdateEventAPI(View):
    """
    API para atualização de evento existente no Google Calendar.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            solicitacao_id = data.get("solicitacao_id")

            if not solicitacao_id:
                return JsonResponse(
                    {"success": False, "error": "ID da solicitação é obrigatório"}
                )

            solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

            # Processar atualização MANUAL
            management_service = GoogleCalendarManagementService()
            result = management_service.update_calendar_event(solicitacao, request.user)

            return JsonResponse(result)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.sync_calendar"), name="dispatch")
class DeleteEventAPI(View):
    """
    API para remoção de evento do Google Calendar.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            solicitacao_id = data.get("solicitacao_id")

            if not solicitacao_id:
                return JsonResponse(
                    {"success": False, "error": "ID da solicitação é obrigatório"}
                )

            solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

            # Processar remoção MANUAL
            management_service = GoogleCalendarManagementService()
            result = management_service.delete_calendar_event(solicitacao, request.user)

            return JsonResponse(result)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.view_calendar"), name="dispatch")
class CalendarStatusAPI(View):
    """
    API para verificar status de integração com Google Calendar
    e listar eventos existentes.
    """

    def get(self, request):
        try:
            # Verificar status da integração
            integration_enabled = google_enabled()

            # Estatísticas básicas
            stats = {
                "total_solicitacoes_pre_agenda": Solicitacao.objects.filter(
                    status=SolicitacaoStatus.PRE_AGENDA
                ).count(),
                "total_eventos_criados": EventoGoogleCalendar.objects.count(),
                "eventos_com_meet": EventoGoogleCalendar.objects.exclude(
                    meet_link__isnull=True
                )
                .exclude(meet_link__exact="")
                .count(),
            }

            # Últimos eventos criados
            recent_events = []
            for evento_gc in EventoGoogleCalendar.objects.select_related("solicitacao")[
                :10
            ]:
                recent_events.append(
                    {
                        "id": str(evento_gc.id),
                        "solicitacao_titulo": evento_gc.solicitacao.titulo_evento,
                        "provider_event_id": evento_gc.provider_event_id,
                        "html_link": evento_gc.html_link,
                        "meet_link": evento_gc.meet_link,
                        "created_at": evento_gc.created_at.isoformat(),
                        "criado_por": (
                            evento_gc.criado_por.username
                            if evento_gc.criado_por
                            else None
                        ),
                    }
                )

            return JsonResponse(
                {
                    "success": True,
                    "integration_enabled": integration_enabled,
                    "stats": stats,
                    "recent_events": recent_events,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.view_calendar"), name="dispatch")
class EventDetailsAPI(View):
    """
    API para obter detalhes de um evento específico do Google Calendar.
    """

    def get(self, request, solicitacao_id):
        try:
            solicitacao = get_object_or_404(Solicitacao, pk=solicitacao_id)

            # Buscar evento do Google Calendar associado
            try:
                evento_gc = EventoGoogleCalendar.objects.get(solicitacao=solicitacao)

                return JsonResponse(
                    {
                        "success": True,
                        "has_calendar_event": True,
                        "event": {
                            "id": str(evento_gc.id),
                            "provider_event_id": evento_gc.provider_event_id,
                            "html_link": evento_gc.html_link,
                            "meet_link": evento_gc.meet_link,
                            "created_at": evento_gc.created_at.isoformat(),
                            "updated_at": evento_gc.updated_at.isoformat(),
                            "criado_por": (
                                evento_gc.criado_por.username
                                if evento_gc.criado_por
                                else None
                            ),
                        },
                        "solicitacao": {
                            "id": str(solicitacao.id),
                            "titulo": solicitacao.titulo_evento,
                            "status": solicitacao.status,
                            "data_inicio": (
                                solicitacao.data_inicio.isoformat()
                                if solicitacao.data_inicio
                                else None
                            ),
                            "data_fim": (
                                solicitacao.data_fim.isoformat()
                                if solicitacao.data_fim
                                else None
                            ),
                            "municipio": (
                                solicitacao.municipio.nome
                                if solicitacao.municipio
                                else None
                            ),
                            "formadores": [
                                f.nome for f in solicitacao.formadores.all()
                            ],
                        },
                    }
                )

            except EventoGoogleCalendar.DoesNotExist:
                return JsonResponse(
                    {
                        "success": True,
                        "has_calendar_event": False,
                        "solicitacao": {
                            "id": str(solicitacao.id),
                            "titulo": solicitacao.titulo_evento,
                            "status": solicitacao.status,
                            "data_inicio": (
                                solicitacao.data_inicio.isoformat()
                                if solicitacao.data_inicio
                                else None
                            ),
                            "data_fim": (
                                solicitacao.data_fim.isoformat()
                                if solicitacao.data_fim
                                else None
                            ),
                            "municipio": (
                                solicitacao.municipio.nome
                                if solicitacao.municipio
                                else None
                            ),
                            "formadores": [
                                f.nome for f in solicitacao.formadores.all()
                            ],
                        },
                    }
                )

        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("core.sync_calendar"), name="dispatch")
class AutoApprovalWithCalendarAPI(View):
    """
    API que combina aprovação de solicitação com criação automática
    de evento no Google Calendar em uma única operação.
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            solicitacao_ids = data.get("solicitacao_ids", [])
            create_calendar_events = data.get("create_calendar_events", True)

            if not solicitacao_ids:
                return JsonResponse(
                    {"success": False, "error": "IDs das solicitações são obrigatórios"}
                )

            results = []
            management_service = GoogleCalendarManagementService()

            with transaction.atomic():
                for sol_id in solicitacao_ids:
                    try:
                        solicitacao = get_object_or_404(Solicitacao, pk=sol_id)

                        if solicitacao.status != SolicitacaoStatus.PRE_AGENDA:
                            results.append(
                                {
                                    "solicitacao_id": sol_id,
                                    "success": False,
                                    "error": f"Status inválido: {solicitacao.status}",
                                }
                            )
                            continue

                        if create_calendar_events:
                            # Processar com criação MANUAL de evento pelo Controle
                            result = management_service.create_event_for_controle(
                                solicitacao, request.user
                            )
                        else:
                            # Apenas atualizar status (sem criar no calendário)
                            solicitacao.status = SolicitacaoStatus.APROVADO
                            solicitacao.save(update_fields=["status"])
                            result = {
                                "success": True,
                                "action": "approved_only",
                                "message": "Solicitação aprovada sem criar evento no calendário",
                            }

                        results.append(
                            {
                                "solicitacao_id": sol_id,
                                "titulo": solicitacao.titulo_evento,
                                **result,
                            }
                        )

                    except Exception as e:
                        results.append(
                            {
                                "solicitacao_id": sol_id,
                                "success": False,
                                "error": str(e),
                            }
                        )

            # Calcular estatísticas
            successful = len([r for r in results if r.get("success", False)])
            failed = len(results) - successful

            return JsonResponse(
                {
                    "success": failed == 0,
                    "processed": len(results),
                    "successful": successful,
                    "failed": failed,
                    "results": results,
                    "message": f"Processamento concluído: {successful} sucessos, {failed} falhas",
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Dados JSON inválidos"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Erro interno: {str(e)}"})
