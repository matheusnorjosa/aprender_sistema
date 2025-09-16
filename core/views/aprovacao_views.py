"""
Views relacionadas ao sistema de aprovações de solicitações.
"""

from django.db import transaction

from core.mixins import SuperintendenciaSetorRequiredMixin
from .base import *


class AprovacoesPendentesView(LoginRequiredMixin, SuperintendenciaSetorRequiredMixin, ListView):
    template_name = "core/aprovacoes_pendentes_enhanced.html"
    model = Solicitacao
    context_object_name = "pendentes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE)
            .select_related(
                "projeto",
                "municipio",
                "tipo_evento",
                "usuario_solicitante",
                "projeto__setor",
            )
            .prefetch_related("formadores")
            .order_by("data_inicio")
        )

        # FILTRO POR SETOR - baseado no usuário logado
        if not self.request.user.is_superuser:
            user_setor = self.request.user.setor

            if user_setor:
                if user_setor.vinculado_superintendencia:
                    # Gerentes da Superintendência: veem apenas solicitações de projetos da superintendência
                    qs = qs.filter(projeto__setor__vinculado_superintendencia=True)
                else:
                    # Gerentes de outros setores: veem apenas solicitações do seu próprio setor
                    qs = qs.filter(projeto__setor=user_setor)
            else:
                # Usuário sem setor definido - não vê nenhuma solicitação
                qs = qs.none()

        # Filtro de busca por termo
        termo = self.request.GET.get("q")
        if termo:
            qs = qs.filter(titulo_evento__icontains=termo)

        return qs


class AprovacaoDetailView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = "core.add_aprovacao"
    template_name = "core/aprovacao_detail.html"
    form_class = AprovacaoDecisionForm

    def dispatch(self, request, *args, **kwargs):
        self.solicitacao = get_object_or_404(Solicitacao, pk=kwargs["pk"])
        if self.solicitacao.status != SolicitacaoStatus.PENDENTE:
            messages.warning(request, "Esta solicitação já foi decidida.")
            return redirect("core:aprovacoes_pendentes")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sol"] = self.solicitacao
        ctx["formadores"] = self.solicitacao.formadores.all()
        return ctx

    @transaction.atomic
    def form_valid(self, form):
        """
        Processa a decisão de aprovação/reprovação usando transação atômica.
        Garante que todas as operações sejam executadas ou nenhuma.
        """
        decisao = form.cleaned_data["decisao"]
        justificativa = form.cleaned_data.get("justificativa", "")

        try:
            # Usar savepoint para controle granular de rollback
            with transaction.atomic():
                # 1. Criar registro de aprovação
                aprovacao = Aprovacao.objects.create(
                    solicitacao=self.solicitacao,
                    usuario_aprovador=self.request.user,
                    status_decisao=decisao,
                    justificativa=justificativa,
                )

                # 2. Atualizar status da solicitação
                self.solicitacao.status = (
                    SolicitacaoStatus.PRE_AGENDA
                    if decisao == AprovacaoStatus.APROVADO
                    else SolicitacaoStatus.REPROVADO
                )
                self.solicitacao.usuario_aprovador = self.request.user
                self.solicitacao.data_aprovacao_rejeicao = timezone.now()
                self.solicitacao.save(
                    update_fields=[
                        "status",
                        "usuario_aprovador",
                        "data_aprovacao_rejeicao",
                    ]
                )

                # 3. Registrar auditoria
                LogAuditoria.objects.create(
                    usuario=self.request.user,
                    acao=f"RF04: {decisao} solicitação",
                    entidade_afetada_id=self.solicitacao.id,
                    detalhes=f"Solicitação '{self.solicitacao.titulo_evento}' ({self.solicitacao.id}) "
                    f"— decisão: {decisao}"
                    f"{f' — justificativa: {justificativa}' if justificativa else ''}",
                )

                # 4. Validar integridade dos dados
                if not aprovacao.pk:
                    raise ValueError("Falha ao criar registro de aprovação")

                if self.solicitacao.status not in [
                    SolicitacaoStatus.PRE_AGENDA,
                    SolicitacaoStatus.REPROVADO,
                ]:
                    raise ValueError("Status da solicitação inválido após atualização")

        except Exception as e:
            # Log do erro e re-raise para o Django tratar
            LogAuditoria.objects.create(
                usuario=self.request.user,
                acao="RF04: ERRO na aprovação",
                entidade_afetada_id=self.solicitacao.id,
                detalhes=f"ERRO ao processar aprovação: {str(e)}",
            )
            messages.error(self.request, f"Erro ao processar aprovação: {str(e)}")
            return redirect("core:aprovacao_detail", pk=self.solicitacao.pk)

        # 5. Mensagens de sucesso
        if self.solicitacao.status == SolicitacaoStatus.PRE_AGENDA:
            messages.success(
                self.request,
                "Solicitação aprovada e enviada para pré-agenda. "
                "O grupo Controle criará o evento no Google Calendar.",
            )
        else:
            messages.success(
                self.request, f"Solicitação {decisao.lower()} com sucesso."
            )

        return redirect("core:aprovacoes_pendentes")
