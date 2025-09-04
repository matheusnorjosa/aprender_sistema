"""
Views relacionadas ao perfil de Diretoria (visão executiva e relatórios).
"""

from .base import *


class DiretoriaExecutiveDashboardView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = "core.view_relatorios"
    template_name = "core/diretoria/executive_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agora = timezone.now()
        data_inicio_ano = agora.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        data_limite_trimestre = agora - timedelta(days=90)

        # Métricas principais
        total_solicitacoes_ano = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano
        ).count()
        solicitacoes_aprovadas_ano = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano, status=SolicitacaoStatus.APROVADO
        ).count()
        taxa_aprovacao_ano = round(
            (
                (solicitacoes_aprovadas_ano / total_solicitacoes_ano * 100)
                if total_solicitacoes_ano > 0
                else 0
            ),
            1,
        )

        context.update(
            {
                "total_solicitacoes_ano": total_solicitacoes_ano,
                "solicitacoes_aprovadas_ano": solicitacoes_aprovadas_ano,
                "taxa_aprovacao_ano": taxa_aprovacao_ano,
                "formadores_ativos": Formador.objects.filter(ativo=True).count(),
                "municipios_total": Municipio.objects.filter(ativo=True).count(),
                "projetos_ativos": Projeto.objects.filter(ativo=True).count(),
                "ano_atual": agora.year,
            }
        )
        return context


class DiretoriaRelatoriosView(
    LoginRequiredMixin, PermissionRequiredMixin, TemplateView
):
    permission_required = "core.view_relatorios"
    template_name = "core/diretoria/relatorios.html"


class DashboardStatsAPIView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.view_relatorios"

    def get(self, request):
        # Estatísticas básicas para o dashboard
        stats = {
            "total_solicitacoes": Solicitacao.objects.count(),
            "formadores_ativos": Formador.objects.filter(ativo=True).count(),
            "eventos_hoje": Solicitacao.objects.filter(
                data_inicio__date=timezone.now().date(),
                status=SolicitacaoStatus.APROVADO,
            ).count(),
        }
        return JsonResponse(stats)


class DiretoriaAPIMetricsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "core.view_relatorios"

    def get(self, request):
        agora = timezone.now()
        data_limite = agora - timedelta(days=30)

        metrics = {
            "solicitacoes_mes": Solicitacao.objects.filter(
                data_solicitacao__gte=data_limite
            ).count(),
            "aprovacoes_mes": Solicitacao.objects.filter(
                data_solicitacao__gte=data_limite, status=SolicitacaoStatus.APROVADO
            ).count(),
        }
        return JsonResponse(metrics)
