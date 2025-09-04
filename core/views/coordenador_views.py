"""
Views relacionadas ao perfil de Coordenador.
"""

from .base import *


class CoordenadorMeusEventosView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = "core.view_own_solicitacoes"
    template_name = "core/coordenador/meus_eventos.html"
    model = Solicitacao
    context_object_name = "eventos"
    paginate_by = 15

    def get_queryset(self):
        qs = (
            Solicitacao.objects.filter(usuario_solicitante=self.request.user)
            .select_related("projeto", "municipio", "tipo_evento", "usuario_aprovador")
            .prefetch_related("formadores")
            .order_by("-data_solicitacao")
        )

        # Filtro por status
        status = self.request.GET.get("status")
        if status and status in ["PENDENTE", "APROVADO", "REPROVADO"]:
            qs = qs.filter(status=status)

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

        # Filtro por projeto
        projeto_id = self.request.GET.get("projeto")
        if projeto_id:
            try:
                qs = qs.filter(projeto_id=int(projeto_id))
            except (ValueError, TypeError):
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Estatísticas do coordenador
        user_eventos = Solicitacao.objects.filter(usuario_solicitante=self.request.user)

        total_solicitacoes = user_eventos.count()
        eventos_pendentes = user_eventos.filter(
            status=SolicitacaoStatus.PENDENTE
        ).count()
        eventos_aprovados = user_eventos.filter(
            status=SolicitacaoStatus.APROVADO
        ).count()
        eventos_reprovados = user_eventos.filter(
            status=SolicitacaoStatus.REPROVADO
        ).count()

        # Taxa de aprovação
        taxa_aprovacao = round(
            (
                (eventos_aprovados / total_solicitacoes * 100)
                if total_solicitacoes > 0
                else 0
            ),
            1,
        )

        # Próximos eventos aprovados
        proximos_eventos = user_eventos.filter(
            status=SolicitacaoStatus.APROVADO, data_inicio__gte=timezone.now()
        ).order_by("data_inicio")[:5]

        # Opções para filtros
        projetos_opcoes = Projeto.objects.filter(ativo=True).order_by("nome")

        filter_options = {
            "status_choices": [
                ("PENDENTE", "Pendente"),
                ("APROVADO", "Aprovado"),
                ("REPROVADO", "Reprovado"),
            ],
            "periodo_choices": [
                ("7", "Últimos 7 dias"),
                ("30", "Últimos 30 dias"),
                ("90", "Últimos 3 meses"),
                ("365", "Último ano"),
            ],
            "projetos": projetos_opcoes,
        }

        stats = {
            "total_solicitacoes": total_solicitacoes,
            "eventos_pendentes": eventos_pendentes,
            "eventos_aprovados": eventos_aprovados,
            "eventos_reprovados": eventos_reprovados,
        }

        context.update(
            {
                "stats": stats,
                "taxa_aprovacao": taxa_aprovacao,
                "proximos_eventos": proximos_eventos,
                "filter_options": filter_options,
                "status_filter": self.request.GET.get("status", ""),
                "periodo_filter": self.request.GET.get("periodo", ""),
                "projeto_filter": self.request.GET.get("projeto", ""),
            }
        )

        return context
