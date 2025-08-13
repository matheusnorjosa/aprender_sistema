from django.shortcuts import render

# Create your views here.
# aprender_sistema/core/views.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.contrib import messages
from core.forms import SolicitacaoForm
from core.models import Solicitacao

class IsCoordenadorMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "coordenador" or u.is_superuser)

class SolicitacaoCreateView(LoginRequiredMixin, IsCoordenadorMixin, CreateView):
    model = Solicitacao
    form_class = SolicitacaoForm
    template_name = "core/solicitacao_form.html"
    success_url = reverse_lazy("solicitacao_ok")

    def form_valid(self, form):
        form.instance.usuario_solicitante = self.request.user
        messages.success(self.request, "Solicitação registrada com sucesso.")
        return super().form_valid(form)

class SolicitacaoOKView(LoginRequiredMixin, TemplateView):
    template_name = "core/solicitacao_ok.html"

# === RF04: Superintendência aprova/reprova ===
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import ListView, FormView
from django.contrib import messages
from django.utils import timezone

from core.models import (
    Solicitacao, SolicitacaoStatus, Aprovacao, AprovacaoStatus, LogAuditoria
)
from core.forms import AprovacaoDecisionForm

class IsSuperintendenciaMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "superintendencia" or u.is_superuser)


class AprovacoesPendentesView(LoginRequiredMixin, IsSuperintendenciaMixin, ListView):
    template_name = "core/aprovacoes_pendentes.html"
    model = Solicitacao
    context_object_name = "pendentes"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Solicitacao.objects
            .filter(status=SolicitacaoStatus.PENDENTE)
            .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
            .prefetch_related("formadores")
            .order_by("data_inicio")
        )
        # filtros simples opcionais
        termo = self.request.GET.get("q")
        if termo:
            qs = qs.filter(titulo_evento__icontains=termo)
        return qs


class AprovacaoDetailView(LoginRequiredMixin, IsSuperintendenciaMixin, FormView):
    template_name = "core/aprovacao_detail.html"
    form_class = AprovacaoDecisionForm

    def dispatch(self, request, *args, **kwargs):
        self.solicitacao = get_object_or_404(Solicitacao, pk=kwargs["pk"])
        if self.solicitacao.status != SolicitacaoStatus.PENDENTE:
            messages.warning(request, "Esta solicitação já foi decidida.")
            return redirect("aprovacoes_pendentes")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sol"] = self.solicitacao
        ctx["formadores"] = self.solicitacao.formadores.all()
        return ctx

    def form_valid(self, form):
        decisao = form.cleaned_data["decisao"]
        justificativa = form.cleaned_data.get("justificativa", "").strip()

        with transaction.atomic():
            # 1) cria registro de Aprovacao
            Aprovacao.objects.create(
                solicitacao=self.solicitacao,
                usuario_aprovador=self.request.user,
                status_decisao=decisao,
                justificativa=justificativa or "",
            )
            # 2) atualiza Solicitacao
            self.solicitacao.status = (
                SolicitacaoStatus.APROVADO if decisao == AprovacaoStatus.APROVADO
                else SolicitacaoStatus.REPROVADO
            )
            self.solicitacao.usuario_aprovador = self.request.user
            self.solicitacao.data_aprovacao_rejeicao = timezone.now()
            if decisao == AprovacaoStatus.REPROVADO:
                self.solicitacao.justificativa_rejeicao = justificativa
            self.solicitacao.save(update_fields=[
                "status","usuario_aprovador","data_aprovacao_rejeicao","justificativa_rejeicao"
            ])

            # 3) log de auditoria
            LogAuditoria.objects.create(
                usuario=self.request.user,
                acao=f"RF04: {decisao} solicitação",
                entidade_afetada_id=self.solicitacao.id,
                detalhes=f"Solicitação '{self.solicitacao.titulo_evento}' ({self.solicitacao.id})"
                         f" — decisão: {decisao}; justificativa: {justificativa or '-'}"
            )

        messages.success(self.request, f"Solicitação {decisao.lower()} com sucesso.")
        return redirect("aprovacoes_pendentes")

