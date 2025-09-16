"""
Views para pré-agenda do grupo Controle.
Permite que o grupo Controle visualize eventos aprovados e crie manualmente no Google Calendar.
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from core.mixins import SuperintendenciaSetorRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from core.models import (
    EventoGoogleCalendar,
    Formador,
    LogAuditoria,
    Projeto,
    Solicitacao,
    SolicitacaoStatus,
)


class ControlePreAgendaView(LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, ListView):
    """
    Página principal de pré-agenda para o grupo Controle.
    Lista todos os eventos com status PRE_AGENDA para criação manual no Google Calendar.
    """

    permission_required = "core.sync_calendar"
    template_name = "core/controle/pre_agenda.html"
    model = Solicitacao
    context_object_name = "eventos_pre_agenda"
    paginate_by = 20

    def get_queryset(self):
        """Busca eventos em pré-agenda ordenados por data de início."""
        qs = (
            Solicitacao.objects.filter(status=SolicitacaoStatus.PRE_AGENDA)
            .select_related(
                "projeto", "municipio", "tipo_evento", "usuario_solicitante"
            )
            .prefetch_related("formadores")
            .order_by("data_inicio")
        )

        # Filtros opcionais
        projeto_id = self.request.GET.get("projeto")
        if projeto_id:
            try:
                qs = qs.filter(projeto_id=int(projeto_id))
            except (ValueError, TypeError):
                pass

        formador_id = self.request.GET.get("formador")
        if formador_id:
            try:
                qs = qs.filter(formadores__id=formador_id)
            except (ValueError, TypeError):
                pass

        # Filtro por período
        periodo = self.request.GET.get("periodo")
        if periodo:
            try:
                dias = int(periodo)
                if dias > 0:
                    data_limite = timezone.now() - timedelta(days=dias)
                    qs = qs.filter(data_solicitacao__gte=data_limite)
            except (ValueError, TypeError):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas para cards
        total_pre_agenda = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PRE_AGENDA
        ).count()

        eventos_hoje = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PRE_AGENDA, data_inicio__date=timezone.now().date()
        ).count()

        eventos_semana = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PRE_AGENDA,
            data_inicio__date__gte=timezone.now().date(),
            data_inicio__date__lte=timezone.now().date() + timedelta(days=7),
        ).count()

        # Eventos já sincronizados (para comparação)
        eventos_sincronizados = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="OK"
        ).count()

        context.update(
            {
                "total_pre_agenda": total_pre_agenda,
                "eventos_hoje": eventos_hoje,
                "eventos_semana": eventos_semana,
                "eventos_sincronizados": eventos_sincronizados,
                # Opções para filtros
                "projetos_filter": Projeto.objects.filter(ativo=True).order_by("nome"),
                "formadores_filter": Formador.objects.filter(ativo=True).order_by(
                    "nome"
                ),
                # Filtros ativos
                "projeto_filter": self.request.GET.get("projeto", ""),
                "formador_filter": self.request.GET.get("formador", ""),
                "periodo_filter": self.request.GET.get("periodo", ""),
            }
        )

        return context


class CriarEventoGoogleCalendarView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    API endpoint para criar evento no Google Calendar manualmente.
    Usado pelos usuários do grupo Controle através da interface de pré-agenda.
    """

    permission_required = "core.sync_calendar"

    def post(self, request, solicitacao_id):
        """Cria evento no Google Calendar e atualiza status da solicitação."""
        try:
            # Buscar solicitação
            solicitacao = get_object_or_404(
                Solicitacao, id=solicitacao_id, status=SolicitacaoStatus.PRE_AGENDA
            )

            # Verificar se já não foi criado
            if EventoGoogleCalendar.objects.filter(solicitacao=solicitacao).exists():
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Evento já foi criado no Google Calendar",
                    },
                    status=400,
                )

            # Criar evento no Google Calendar
            from django.conf import settings

            from core.services.integrations.calendar_mapper import (
                map_solicitacao_to_google_event,
            )
            from core.services.integrations.google_calendar import GoogleCalendarService

            if not settings.FEATURE_GOOGLE_SYNC:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Sincronização com Google Calendar está desabilitada",
                    },
                    status=400,
                )

            # Mapear solicitação para evento Google
            gevent = map_solicitacao_to_google_event(solicitacao)

            # Criar evento via serviço real
            service = GoogleCalendarService()
            result = service.create_event(gevent)

            if result.get("id"):
                # Salvar evento no banco
                evento_gc = EventoGoogleCalendar.objects.create(
                    solicitacao=solicitacao,
                    usuario_criador=request.user,
                    provider_event_id=result["id"],
                    html_link=result.get("htmlLink", ""),
                    meet_link=result.get("hangoutLink", ""),
                    raw_payload=result,
                    status_sincronizacao=EventoGoogleCalendar.SincronizacaoStatus.OK,
                )

                # Atualizar status da solicitação para APROVADO
                solicitacao.status = SolicitacaoStatus.APROVADO
                solicitacao.save(update_fields=["status"])

                # Log de auditoria
                LogAuditoria.objects.create(
                    usuario=request.user,
                    acao="Controle: Evento criado no Google Calendar",
                    entidade_afetada_id=solicitacao.id,
                    detalhes=f"Evento '{solicitacao.titulo_evento}' criado manualmente pelo controle. ID: {result.get('id')}",
                )

                return JsonResponse(
                    {
                        "success": True,
                        "message": "Evento criado com sucesso no Google Calendar",
                        "google_event_id": result["id"],
                        "html_link": result.get("htmlLink", ""),
                        "meet_link": result.get("hangoutLink", ""),
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Falha ao criar evento no Google Calendar",
                    },
                    status=500,
                )

        except Exception as e:
            # Log do erro
            LogAuditoria.objects.create(
                usuario=request.user,
                acao="Controle: Erro ao criar evento no Google Calendar",
                entidade_afetada_id=solicitacao_id,
                detalhes=f"Erro: {str(e)}",
            )

            return JsonResponse(
                {"success": False, "error": f"Erro interno: {str(e)}"}, status=500
            )


class RemoverEventoPreAgendaView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    API endpoint para remover evento da pré-agenda (rejeitar criação).
    """

    permission_required = "core.sync_calendar"

    def post(self, request, solicitacao_id):
        """Remove evento da pré-agenda (marca como reprovado pelo controle)."""
        try:
            solicitacao = get_object_or_404(
                Solicitacao, id=solicitacao_id, status=SolicitacaoStatus.PRE_AGENDA
            )

            # Verificar motivo (opcional)
            motivo = request.POST.get("motivo", "Removido pelo controle")

            # Atualizar status para reprovado
            solicitacao.status = SolicitacaoStatus.REPROVADO
            solicitacao.save(update_fields=["status"])

            # Log de auditoria
            LogAuditoria.objects.create(
                usuario=request.user,
                acao="Controle: Evento removido da pré-agenda",
                entidade_afetada_id=solicitacao.id,
                detalhes=f"Evento '{solicitacao.titulo_evento}' removido da pré-agenda. Motivo: {motivo}",
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "Evento removido da pré-agenda com sucesso",
                }
            )

        except Exception as e:
            return JsonResponse(
                {"success": False, "error": f"Erro interno: {str(e)}"}, status=500
            )
