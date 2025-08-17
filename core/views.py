# aprender_sistema/core/views.py

from datetime import timedelta, time
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, ListView, FormView
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from core.forms import SolicitacaoForm, AprovacaoDecisionForm, BloqueioAgendaForm
from core.models import (
    Solicitacao, SolicitacaoStatus, Aprovacao, AprovacaoStatus, LogAuditoria,
)


def home(request):
    """
    Renderiza a página inicial do sistema.
    """
    return render(request, "core/home.html")


class HomeView(TemplateView):
    template_name = "core/home.html"


# ----- RF02 -----
class IsCoordenadorMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "coordenador" or u.is_superuser)


class SolicitacaoCreateView(LoginRequiredMixin, IsCoordenadorMixin, CreateView):
    model = Solicitacao
    form_class = SolicitacaoForm
    template_name = "core/solicitacao_form.html"
    success_url = reverse_lazy("core:solicitacao_ok")

    def form_valid(self, form):
        form.instance.usuario_solicitante = self.request.user
        messages.success(self.request, "Solicitação registrada com sucesso.")
        return super().form_valid(form)


class SolicitacaoOKView(LoginRequiredMixin, TemplateView):
    template_name = "core/solicitacao_ok.html"


# ----- RF04 -----
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
            return redirect("core:aprovacoes_pendentes")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sol"] = self.solicitacao
        ctx["formadores"] = self.solicitacao.formadores.all()
        return ctx

    def form_valid(self, form):
        decisao = form.cleaned_data["decisao"]
        justificativa = form.cleaned_data.get("justificativa", "").strip()

        Aprovacao.objects.create(
            solicitacao=self.solicitacao,
            usuario_aprovador=self.request.user,
            status_decisao=decisao,
            justificativa=justificativa or "",
        )
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

        LogAuditoria.objects.create(
            usuario=self.request.user,
            acao=f"RF04: {decisao} solicitação",
            entidade_afetada_id=self.solicitacao.id,
            detalhes=f"Solicitação '{self.solicitacao.titulo_evento}' ({self.solicitacao.id})"
                     f" — decisão: {decisao}; justificativa: {justificativa or '-'}"
        )

        messages.success(self.request, f"Solicitação {decisao.lower()} com sucesso.")
        return redirect("core:aprovacoes_pendentes")


# ----- Bloqueio de agenda (Apps Script -> Django) -----
class BloqueioCreateView(LoginRequiredMixin, FormView):
    template_name = "core/bloqueio_form.html"
    form_class = BloqueioAgendaForm
    success_url = reverse_lazy("bloqueio_ok")

    def form_valid(self, form):
        from core.models import DisponibilidadeFormadores
        formador = form.cleaned_data["formador"]
        inicio = form.cleaned_data["inicio"]
        fim = form.cleaned_data["fim"]
        tipo = form.cleaned_data["tipo"]

        hora_ini = time(0,0) if tipo == "Total" else time(8,0)
        hora_fim = time(23,59) if tipo == "Total" else time(17,0)

        atual = inicio
        criados = 0
        while atual <= fim:
            obj, created = DisponibilidadeFormadores.objects.get_or_create(
                formador=formador,
                data_bloqueio=atual,
                hora_inicio=hora_ini,
                hora_fim=hora_fim,
                defaults={"tipo_bloqueio": tipo, "motivo": ""},
            )
            if not created:
                obj.tipo_bloqueio = tipo
                obj.save(update_fields=["tipo_bloqueio"])
            else:
                criados += 1
            atual += timedelta(days=1)

        try:
            send_mail(
                "Confirmação de Bloqueio de Agenda",
                (
                    f"Olá, {formador.nome}.\n\n"
                    f"Seu bloqueio foi registrado:\n"
                    f" - Início: {inicio.strftime('%d/%m/%Y')}\n"
                    f" - Fim: {fim.strftime('%d/%m/%Y')}\n"
                    f" - Tipo: {tipo}\n"
                    f"Total de dias afetados: {criados}\n\n"
                    f"Equipe DAT"
                ),
                settings.DEFAULT_FROM_EMAIL,
                [formador.email],
                fail_silently=True,
            )
        except Exception:
            pass

        messages.success(self.request, "Bloqueio registrado e e‑mail enviado (console em dev).")
        return super().form_valid(form)


# ----- Autenticação customizada -----
class CustomLoginView(LoginView):
    template_name = "core/login.html"
    redirect_authenticated_user = True
    
    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:home')
    
    def form_valid(self, form):
        messages.success(self.request, f"Bem-vindo(a), {form.get_user().get_full_name() or form.get_user().username}!")
        return super().form_valid(form)