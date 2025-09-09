"""
Views relacionadas ao perfil de Controle (monitoramento e auditoria).
"""

from .base import *


class GoogleCalendarMonitorView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "core.sync_calendar"
    template_name = "core/controle/google_calendar_monitor.html"
    model = EventoGoogleCalendar
    context_object_name = "eventos_sync"
    paginate_by = 25

    def get_queryset(self):
        qs = EventoGoogleCalendar.objects.select_related(
            "solicitacao", "usuario_criador"
        ).order_by("-data_criacao")

        # Filtros por status
        status = self.request.GET.get("status")
        if status and status in ["OK", "Erro", "Pendente"]:
            qs = qs.filter(status_sincronizacao=status)

        # Filtro por período
        periodo = self.request.GET.get("periodo", "7")
        try:
            dias = int(periodo)
            if dias > 0:
                data_limite = timezone.now() - timedelta(days=dias)
                qs = qs.filter(data_criacao__gte=data_limite)
        except ValueError:
            pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas de sincronização
        total_eventos = EventoGoogleCalendar.objects.count()
        eventos_ok = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="OK"
        ).count()
        eventos_erro = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="Erro"
        ).count()
        eventos_pendentes = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="Pendente"
        ).count()

        context.update(
            {
                "total_eventos": total_eventos,
                "eventos_ok": eventos_ok,
                "eventos_erro": eventos_erro,
                "eventos_pendentes": eventos_pendentes,
                "taxa_sucesso": round(
                    (eventos_ok / total_eventos * 100) if total_eventos > 0 else 0, 1
                ),
                "status_filter": self.request.GET.get("status", ""),
                "periodo_filter": self.request.GET.get("periodo", "7"),
            }
        )
        return context


class AuditoriaLogView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "core.view_logauditoria"
    template_name = "core/controle/auditoria_log.html"
    model = LogAuditoria
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        qs = LogAuditoria.objects.select_related("usuario").order_by("-data_hora")

        # Filtro por tipo de ação
        acao = self.request.GET.get("acao")
        if acao:
            qs = qs.filter(acao__icontains=acao)

        # Filtro por usuário
        usuario = self.request.GET.get("usuario")
        if usuario:
            qs = qs.filter(usuario__username__icontains=usuario)

        # Filtro por período
        periodo = self.request.GET.get("periodo", "7")
        try:
            dias = int(periodo)
            if dias > 0:
                data_limite = timezone.now() - timedelta(days=dias)
                qs = qs.filter(data_hora__gte=data_limite)
        except ValueError:
            pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas de auditoria
        total_logs = LogAuditoria.objects.count()
        logs_hoje = LogAuditoria.objects.filter(
            data_hora__date=timezone.now().date()
        ).count()

        # Ações mais frequentes (últimos 30 dias)
        data_limite = timezone.now() - timedelta(days=30)
        acoes_frequentes = (
            LogAuditoria.objects.filter(data_hora__gte=data_limite)
            .values("acao")
            .annotate(count=models.Count("acao"))
            .order_by("-count")[:10]
        )

        # Usuários mais ativos (últimos 30 dias)
        usuarios_ativos = (
            LogAuditoria.objects.filter(data_hora__gte=data_limite)
            .values("usuario__username")
            .annotate(count=models.Count("usuario"))
            .order_by("-count")[:10]
        )

        context.update(
            {
                "total_logs": total_logs,
                "logs_hoje": logs_hoje,
                "acoes_frequentes": acoes_frequentes,
                "usuarios_ativos": usuarios_ativos,
                "acao_filter": self.request.GET.get("acao", ""),
                "usuario_filter": self.request.GET.get("usuario", ""),
                "periodo_filter": self.request.GET.get("periodo", "7"),
            }
        )
        return context


class ControleAPIStatusView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.sync_calendar"

    def get(self, request):
        agora = timezone.now()
        data_limite_24h = agora - timedelta(hours=24)
        data_limite_7d = agora - timedelta(days=7)

        # Métricas de solicitações
        solicitacoes_pendentes = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PENDENTE
        ).count()
        solicitacoes_24h = Solicitacao.objects.filter(
            data_solicitacao__gte=data_limite_24h
        ).count()

        # Métricas de sincronização Google Calendar
        sync_ok_24h = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="OK", data_solicitacao__gte=data_limite_24h
        ).count()
        sync_erro_24h = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="Erro", data_solicitacao__gte=data_limite_24h
        ).count()

        # Métricas de auditoria
        logs_24h = LogAuditoria.objects.filter(data_hora__gte=data_limite_24h).count()
        logs_7d = LogAuditoria.objects.filter(data_hora__gte=data_limite_7d).count()

        # Formadores ativos
        formadores_ativos = Formador.objects.filter(ativo=True).count()

        payload = {
            "timestamp": agora.isoformat(),
            "sistema_status": "OK",
            "metricas": {
                "solicitacoes": {
                    "pendentes": solicitacoes_pendentes,
                    "ultimas_24h": solicitacoes_24h,
                },
                "google_calendar": {
                    "sync_ok_24h": sync_ok_24h,
                    "sync_erro_24h": sync_erro_24h,
                    "taxa_sucesso_24h": round(
                        (
                            (sync_ok_24h / (sync_ok_24h + sync_erro_24h) * 100)
                            if (sync_ok_24h + sync_erro_24h) > 0
                            else 100
                        ),
                        1,
                    ),
                },
                "auditoria": {"logs_24h": logs_24h, "logs_7d": logs_7d},
                "formadores_ativos": formadores_ativos,
            },
        }

        return JsonResponse(payload)
