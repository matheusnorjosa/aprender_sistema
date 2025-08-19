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
from django.db import models
from django.http import JsonResponse
from django.views import View

from core.forms import SolicitacaoForm, AprovacaoDecisionForm, BloqueioAgendaForm
from core.models import (
    Solicitacao, SolicitacaoStatus, Aprovacao, AprovacaoStatus, LogAuditoria, Formador,
    EventoGoogleCalendar
)


def home(request):
    """
    Renderiza a página inicial do sistema.
    """
    return render(request, "core/home.html")


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "core/home.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # PA-06: Garantir que o contexto do usuário esteja disponível no template
        context['user'] = self.request.user
        return context


# ----- Mixins de Segurança -----
class IsCoordenadorMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "coordenador" or u.is_superuser)


class IsSuperintendenciaMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "superintendencia" or u.is_superuser)


class IsFormadorMixin(UserPassesTestMixin):
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and getattr(u, "papel", "") == "formador"


class IsFormadorOrAdminMixin(UserPassesTestMixin):
    """Permite acesso a formadores e administradores apenas"""
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") in ["formador", "admin"] or u.is_superuser)


class CanViewCalendarMixin(UserPassesTestMixin):
    """Permite visualizar calendário: superintendência, diretoria, controle e admin"""
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (
            getattr(u, "papel", "") in ["superintendencia", "diretoria", "controle", "admin"] 
            or u.is_superuser
        )


class IsControleMixin(UserPassesTestMixin):
    """Permite acesso ao perfil Controle - monitoramento e auditoria"""
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "controle" or u.is_superuser)


# ----- RF02 -----


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

        # RF05: Hook para sincronização com Google Calendar (apenas se APROVADO)
        if self.solicitacao.status == SolicitacaoStatus.APROVADO:
            # PA-03 garantida: só aqui damos follow-up
            from django.conf import settings
            from core.services.integrations.calendar_mapper import map_solicitacao_to_google_event
            from core.services.integrations.calendar_stub import GoogleCalendarServiceStub
            from core.models import EventoGoogleCalendar
            
            if settings.FEATURE_GOOGLE_SYNC:
                try:
                    gevent = map_solicitacao_to_google_event(self.solicitacao)
                    svc = GoogleCalendarServiceStub()
                    result = svc.create_event(gevent)

                    if result.get("id"):
                        EventoGoogleCalendar.objects.create(
                            solicitacao=self.solicitacao,
                            usuario_criador=self.request.user,
                            provider_event_id=result["id"],
                            html_link=result.get("htmlLink", ""),
                            meet_link=result.get("hangoutLink", ""),
                            raw_payload=result,
                            status_sincronizacao=EventoGoogleCalendar.SincronizacaoStatus.OK
                        )
                        LogAuditoria.objects.create(
                            usuario=self.request.user,
                            acao="RF05: Evento sincronizado com Google Calendar",
                            entidade_afetada_id=self.solicitacao.id,
                            detalhes=f"Evento criado no Google Calendar: {result.get('id')}"
                        )
                    else:
                        # Log que não foi possível criar
                        LogAuditoria.objects.create(
                            usuario=self.request.user,
                            acao="RF05: Falha ao sincronizar com Google Calendar",
                            entidade_afetada_id=self.solicitacao.id,
                            detalhes=f"Resposta: {result}"
                        )
                except Exception as e:
                    # Log de erro sem quebrar o fluxo principal
                    LogAuditoria.objects.create(
                        usuario=self.request.user,
                        acao="RF05: Erro na sincronização com Google Calendar",
                        entidade_afetada_id=self.solicitacao.id,
                        detalhes=f"Erro: {str(e)}"
                    )
            # Se flag OFF, não faz nada (PA-03 respeitada)

        messages.success(self.request, f"Solicitação {decisao.lower()} com sucesso.")
        return redirect("core:aprovacoes_pendentes")


# ----- Bloqueio de agenda (Apps Script -> Django) -----
class BloqueioCreateView(LoginRequiredMixin, IsFormadorOrAdminMixin, FormView):
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




class FormadorEventosView(LoginRequiredMixin, IsFormadorMixin, TemplateView):
    template_name = "core/formador_eventos.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Encontrar o formador associado ao usuário logado
        # Apenas o email do usuário logado é usado - sem bypass para outros formadores
        try:
            formador = Formador.objects.get(email=user.email, ativo=True)
        except Formador.DoesNotExist:
            formador = None
        
        if formador:
            # Buscar solicitações onde o formador está participando
            agora = timezone.now()
            
            # Eventos futuros (aprovados)
            eventos_futuros = (
                Solicitacao.objects
                .filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_inicio__gt=agora
                )
                .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
                .order_by("data_inicio")
            )
            
            # Eventos em andamento (aprovados e dentro do período)
            eventos_andamento = (
                Solicitacao.objects
                .filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_inicio__lte=agora,
                    data_fim__gte=agora
                )
                .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
                .order_by("data_inicio")
            )
            
            # Eventos passados (últimos 30 dias)
            ultimos_30_dias = agora - timedelta(days=30)
            eventos_passados = (
                Solicitacao.objects
                .filter(
                    formadores=formador,
                    status=SolicitacaoStatus.APROVADO,
                    data_fim__lt=agora,
                    data_fim__gte=ultimos_30_dias
                )
                .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
                .order_by("-data_inicio")
            )
            
            # Eventos pendentes (ainda não aprovados/reprovados)
            eventos_pendentes = (
                Solicitacao.objects
                .filter(
                    formadores=formador,
                    status=SolicitacaoStatus.PENDENTE
                )
                .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
                .order_by("data_inicio")
            )
            
            # Criar uma lista única com todos os eventos para a tabela
            todos_eventos = list(eventos_andamento) + list(eventos_futuros) + list(eventos_pendentes) + list(eventos_passados)
            
            context.update({
                'formador': formador,
                'eventos_futuros': eventos_futuros,
                'eventos_andamento': eventos_andamento,
                'eventos_passados': eventos_passados,
                'eventos_pendentes': eventos_pendentes,
                'todos_eventos': todos_eventos,
                'total_eventos': len(todos_eventos),
            })
        else:
            context.update({
                'formador': None,
                'eventos_futuros': [],
                'eventos_andamento': [],
                'eventos_passados': [],
                'eventos_pendentes': [],
                'todos_eventos': [],
                'total_eventos': 0,
                'erro': 'Formador não encontrado. Verifique se seu email está registrado no sistema.',
            })
            
        return context


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


# ----- Perfil Controle: Monitoramento e Auditoria -----
class GoogleCalendarMonitorView(LoginRequiredMixin, IsControleMixin, ListView):
    """Monitor de sincronização com Google Calendar para perfil Controle"""
    template_name = "core/controle/google_calendar_monitor.html"
    model = EventoGoogleCalendar
    context_object_name = "eventos_sync"
    paginate_by = 25
    
    def get_queryset(self):
        qs = (
            EventoGoogleCalendar.objects
            .select_related("solicitacao", "usuario_criador")
            .order_by("-data_criacao")
        )
        
        # Filtros por status
        status = self.request.GET.get("status")
        if status and status in ["OK", "Erro", "Pendente"]:
            qs = qs.filter(status_sincronizacao=status)
        
        # Filtro por período
        periodo = self.request.GET.get("periodo", "7")  # últimos 7 dias por padrão
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
        eventos_ok = EventoGoogleCalendar.objects.filter(status_sincronizacao="OK").count()
        eventos_erro = EventoGoogleCalendar.objects.filter(status_sincronizacao="Erro").count()
        eventos_pendentes = EventoGoogleCalendar.objects.filter(status_sincronizacao="Pendente").count()
        
        context.update({
            'total_eventos': total_eventos,
            'eventos_ok': eventos_ok,
            'eventos_erro': eventos_erro,
            'eventos_pendentes': eventos_pendentes,
            'taxa_sucesso': round((eventos_ok / total_eventos * 100) if total_eventos > 0 else 0, 1),
            'status_filter': self.request.GET.get("status", ""),
            'periodo_filter': self.request.GET.get("periodo", "7"),
        })
        return context


class AuditoriaLogView(LoginRequiredMixin, IsControleMixin, ListView):
    """Dashboard de auditoria para perfil Controle"""
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
        periodo = self.request.GET.get("periodo", "7")  # últimos 7 dias por padrão
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
            LogAuditoria.objects
            .filter(data_hora__gte=data_limite)
            .values("acao")
            .annotate(count=models.Count("acao"))
            .order_by("-count")[:10]
        )
        
        # Usuários mais ativos (últimos 30 dias)
        usuarios_ativos = (
            LogAuditoria.objects
            .filter(data_hora__gte=data_limite)
            .values("usuario__username")
            .annotate(count=models.Count("usuario"))
            .order_by("-count")[:10]
        )
        
        context.update({
            'total_logs': total_logs,
            'logs_hoje': logs_hoje,
            'acoes_frequentes': acoes_frequentes,
            'usuarios_ativos': usuarios_ativos,
            'acao_filter': self.request.GET.get("acao", ""),
            'usuario_filter': self.request.GET.get("usuario", ""),
            'periodo_filter': self.request.GET.get("periodo", "7"),
        })
        return context


class ControleAPIStatusView(LoginRequiredMixin, IsControleMixin, View):
    """API endpoint para status do sistema para perfil Controle"""
    def get(self, request):
        # Coleta de métricas do sistema
        agora = timezone.now()
        data_limite_24h = agora - timedelta(hours=24)
        data_limite_7d = agora - timedelta(days=7)
        
        # Métricas de solicitações
        solicitacoes_pendentes = Solicitacao.objects.filter(status=SolicitacaoStatus.PENDENTE).count()
        solicitacoes_24h = Solicitacao.objects.filter(data_criacao__gte=data_limite_24h).count()
        
        # Métricas de sincronização Google Calendar
        sync_ok_24h = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="OK", data_criacao__gte=data_limite_24h
        ).count()
        sync_erro_24h = EventoGoogleCalendar.objects.filter(
            status_sincronizacao="Erro", data_criacao__gte=data_limite_24h
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
                    "ultimas_24h": solicitacoes_24h
                },
                "google_calendar": {
                    "sync_ok_24h": sync_ok_24h,
                    "sync_erro_24h": sync_erro_24h,
                    "taxa_sucesso_24h": round(
                        (sync_ok_24h / (sync_ok_24h + sync_erro_24h) * 100) 
                        if (sync_ok_24h + sync_erro_24h) > 0 else 100, 1
                    )
                },
                "auditoria": {
                    "logs_24h": logs_24h,
                    "logs_7d": logs_7d
                },
                "formadores_ativos": formadores_ativos
            }
        }
        
        return JsonResponse(payload)