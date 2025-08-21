# aprender_sistema/core/views.py

from datetime import timedelta, time
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
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
    EventoGoogleCalendar, Municipio, Projeto, TipoEvento
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


class IsDiretoriaMixin(UserPassesTestMixin):
    """Permite acesso ao perfil Diretoria - visão estratégica e relatórios executivos"""
    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (getattr(u, "papel", "") == "diretoria" or u.is_superuser)


# ----- RF02 -----


class SolicitacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = 'core.add_solicitacao'
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


class AprovacoesPendentesView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'core.view_aprovacao'
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


class AprovacaoDetailView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = 'core.add_aprovacao'
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
class BloqueioCreateView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    permission_required = 'core.add_disponibilidadeformadores'
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




class FormadorEventosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'core.view_solicitacao'  # Formadores podem ver solicitações onde participam
    template_name = "core/formador_eventos.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 🔑 MODO ADMIN: Superuser pode ver qualquer formador ou todos os eventos
        if user.is_superuser:
            admin_formador_id = self.request.GET.get('admin_formador_id')
            admin_mode = self.request.GET.get('admin_mode', 'geral')  # 'geral' ou 'formador'
            
            context['admin_mode'] = True
            context['admin_mode_type'] = admin_mode
            
            if admin_mode == 'formador' and admin_formador_id:
                # Simular formador específico
                try:
                    formador = Formador.objects.get(id=admin_formador_id, ativo=True)
                    context['admin_formador_simulado'] = formador
                except Formador.DoesNotExist:
                    formador = None
            else:
                # Modo admin geral - mostrar dados de exemplo/resumo
                formador = None
                context['formadores_disponiveis'] = Formador.objects.filter(ativo=True).order_by('nome')
        else:
            # 👤 MODO NORMAL: Encontrar formador pelo email
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
            # Sem formador específico - comportamento depende do modo
            if user.is_superuser and context.get('admin_mode'):
                # Modo admin: mostrar dados gerais ou seletor
                agora = timezone.now()
                
                # Estatísticas gerais para administradores
                total_formadores = Formador.objects.filter(ativo=True).count()
                eventos_admin_sample = (
                    Solicitacao.objects
                    .filter(status=SolicitacaoStatus.APROVADO, data_inicio__gte=agora)
                    .select_related("projeto", "municipio", "tipo_evento", "usuario_solicitante")
                    .prefetch_related("formadores")
                    .order_by("data_inicio")[:10]  # Amostra dos próximos eventos
                )
                
                context.update({
                    'formador': None,
                    'eventos_futuros': eventos_admin_sample,
                    'eventos_andamento': [],
                    'eventos_passados': [],
                    'eventos_pendentes': [],
                    'todos_eventos': list(eventos_admin_sample),
                    'total_eventos': eventos_admin_sample.count(),
                    'total_formadores': total_formadores,
                    'admin_message': f'Modo Admin: Visualizando dados gerais. {total_formadores} formadores disponíveis.',
                })
            else:
                # Usuário normal sem formador correspondente
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
class GoogleCalendarMonitorView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'core.sync_calendar'
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


class AuditoriaLogView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'core.view_logauditoria'
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


class ControleAPIStatusView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'core.sync_calendar'
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


# ----- Perfil Coordenador: Meus Eventos -----
class CoordenadorMeusEventosView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    permission_required = 'core.view_own_solicitacoes'  # Apenas coordenadores podem ver seus próprios eventos
    """Página para coordenador visualizar seus próprios eventos solicitados"""
    template_name = "core/coordenador/meus_eventos.html"
    model = Solicitacao
    context_object_name = "eventos"
    paginate_by = 15
    
    def get_queryset(self):
        # Mostrar apenas eventos criados pelo coordenador logado
        qs = (
            Solicitacao.objects
            .filter(usuario_solicitante=self.request.user)
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
        eventos_pendentes = user_eventos.filter(status=SolicitacaoStatus.PENDENTE).count()
        eventos_aprovados = user_eventos.filter(status=SolicitacaoStatus.APROVADO).count()
        eventos_reprovados = user_eventos.filter(status=SolicitacaoStatus.REPROVADO).count()
        
        # Taxa de aprovação
        taxa_aprovacao = round(
            (eventos_aprovados / total_solicitacoes * 100) 
            if total_solicitacoes > 0 else 0, 1
        )
        
        # Próximos eventos aprovados
        proximos_eventos = user_eventos.filter(
            status=SolicitacaoStatus.APROVADO,
            data_inicio__gte=timezone.now()
        ).order_by("data_inicio")[:5]
        
        # Opções para filtros
        projetos_opcoes = Projeto.objects.filter(ativo=True).order_by('nome')
        
        # Configurar filter_options para o template
        filter_options = {
            'status_choices': [
                ('PENDENTE', 'Pendente'),
                ('APROVADO', 'Aprovado'),
                ('REPROVADO', 'Reprovado'),
            ],
            'periodo_choices': [
                ('7', 'Últimos 7 dias'),
                ('30', 'Últimos 30 dias'),
                ('90', 'Últimos 3 meses'),
                ('365', 'Último ano'),
            ],
            'projetos': projetos_opcoes,
        }
        
        # Estatísticas para os cards
        stats = {
            'total_solicitacoes': total_solicitacoes,
            'eventos_pendentes': eventos_pendentes,
            'eventos_aprovados': eventos_aprovados,
            'eventos_reprovados': eventos_reprovados,
        }
        
        context.update({
            # Estatísticas
            'stats': stats,
            'taxa_aprovacao': taxa_aprovacao,
            'proximos_eventos': proximos_eventos,
            
            # Opções de filtro para o template
            'filter_options': filter_options,
            
            # Filtros ativos
            'status_filter': self.request.GET.get("status", ""),
            'periodo_filter': self.request.GET.get("periodo", ""),
            'projeto_filter': self.request.GET.get("projeto", ""),
            
        })
        
        return context


# ----- Perfil Diretoria: Visão Estratégica e Relatórios Executivos -----
class DiretoriaExecutiveDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'core.view_relatorios'
    """Dashboard executivo para perfil Diretoria com métricas estratégicas"""
    template_name = "core/diretoria/executive_dashboard.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Período de análise (últimos 12 meses)
        agora = timezone.now()
        data_inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        data_limite_trimestre = agora - timedelta(days=90)
        data_limite_mes = agora - timedelta(days=30)
        
        # === MÉTRICAS ESTRATÉGICAS ===
        
        # 1. Visão geral de solicitações no ano
        total_solicitacoes_ano = Solicitacao.objects.filter(data_solicitacao__gte=data_inicio_ano).count()
        solicitacoes_aprovadas_ano = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano,
            status=SolicitacaoStatus.APROVADO
        ).count()
        taxa_aprovacao_ano = round(
            (solicitacoes_aprovadas_ano / total_solicitacoes_ano * 100) 
            if total_solicitacoes_ano > 0 else 0, 1
        )
        
        # 2. Eventos por mês (últimos 12 meses)
        eventos_por_mes = []
        for i in range(12):
            data_ref = agora - timedelta(days=30*i)
            inicio_mes = data_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 11:
                fim_mes = data_inicio_ano
            else:
                proximo_mes = data_ref.replace(day=1) + timedelta(days=32)
                fim_mes = proximo_mes.replace(day=1)
            
            eventos_mes = Solicitacao.objects.filter(
                data_inicio__gte=inicio_mes,
                data_inicio__lt=fim_mes,
                status=SolicitacaoStatus.APROVADO
            ).count()
            
            eventos_por_mes.append({
                'mes': inicio_mes.strftime('%b/%Y'),
                'eventos': eventos_mes
            })
        eventos_por_mes.reverse()  # Ordem cronológica
        
        # 3. Performance dos formadores (top 10)
        formadores_performance = []
        for formador in Formador.objects.filter(ativo=True):
            eventos_participou = Solicitacao.objects.filter(
                formadores=formador,
                status=SolicitacaoStatus.APROVADO,
                data_inicio__gte=data_limite_trimestre
            ).count()
            
            if eventos_participou > 0:
                formadores_performance.append({
                    'nome': formador.nome,
                    'eventos': eventos_participou,
                    'area': formador.area_atuacao
                })
        
        formadores_performance.sort(key=lambda x: x['eventos'], reverse=True)
        top_formadores = formadores_performance[:10]
        
        # 4. Distribuição geográfica (municípios atendidos)
        municipios_atendidos = (
            Solicitacao.objects
            .filter(
                status=SolicitacaoStatus.APROVADO,
                data_inicio__gte=data_limite_trimestre
            )
            .values('municipio__nome', 'municipio__uf')
            .annotate(eventos=models.Count('id'))
            .order_by('-eventos')[:15]
        )
        
        # 5. Tipos de evento mais solicitados
        tipos_evento_stats = (
            Solicitacao.objects
            .filter(
                status=SolicitacaoStatus.APROVADO,
                data_inicio__gte=data_limite_trimestre
            )
            .values('tipo_evento__nome')
            .annotate(quantidade=models.Count('id'))
            .order_by('-quantidade')[:10]
        )
        
        # 6. Projetos com maior atividade
        projetos_stats = (
            Solicitacao.objects
            .filter(
                status=SolicitacaoStatus.APROVADO,
                data_inicio__gte=data_limite_trimestre
            )
            .values('projeto__nome')
            .annotate(eventos=models.Count('id'))
            .order_by('-eventos')[:10]
        )
        
        # 7. Métricas de sincronização Google Calendar
        total_sync = EventoGoogleCalendar.objects.count()
        sync_ok = EventoGoogleCalendar.objects.filter(status_sincronizacao="OK").count()
        taxa_sync_sucesso = round((sync_ok / total_sync * 100) if total_sync > 0 else 0, 1)
        
        # 8. Atividade recente do sistema (logs)
        atividade_recente = LogAuditoria.objects.filter(
            data_hora__gte=data_limite_mes
        ).count()
        
        context.update({
            # Métricas principais
            'total_solicitacoes_ano': total_solicitacoes_ano,
            'solicitacoes_aprovadas_ano': solicitacoes_aprovadas_ano,
            'taxa_aprovacao_ano': taxa_aprovacao_ano,
            'formadores_ativos': Formador.objects.filter(ativo=True).count(),
            'municipios_total': Municipio.objects.filter(ativo=True).count(),
            'projetos_ativos': Projeto.objects.filter(ativo=True).count(),
            
            # Dados para gráficos
            'eventos_por_mes': eventos_por_mes,
            'top_formadores': top_formadores,
            'municipios_atendidos': municipios_atendidos,
            'tipos_evento_stats': tipos_evento_stats,
            'projetos_stats': projetos_stats,
            
            # Métricas de sistema
            'taxa_sync_sucesso': taxa_sync_sucesso,
            'atividade_recente': atividade_recente,
            
            # Períodos para display
            'ano_atual': agora.year,
            'trimestre_atual': f"Q{((agora.month-1)//3)+1}/{agora.year}",
        })
        
        return context


class DiretoriaRelatoriosView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = 'core.view_relatorios'
    """Relatórios consolidados para perfil Diretoria"""
    template_name = "core/diretoria/relatorios.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtros da request
        periodo = self.request.GET.get('periodo', '30')  # dias
        projeto_id = self.request.GET.get('projeto')
        municipio_id = self.request.GET.get('municipio')
        
        try:
            dias = int(periodo)
        except (ValueError, TypeError):
            dias = 30
            
        data_limite = timezone.now() - timedelta(days=dias)
        
        # Query base
        qs = Solicitacao.objects.filter(
            data_solicitacao__gte=data_limite,
            status=SolicitacaoStatus.APROVADO
        )
        
        # Aplicar filtros
        if projeto_id:
            qs = qs.filter(projeto_id=projeto_id)
        if municipio_id:
            qs = qs.filter(municipio_id=municipio_id)
        
        # Estatísticas do período
        total_eventos = qs.count()
        total_formadores_envolvidos = qs.values('formadores').distinct().count()
        
        # Relatório por formador
        relatorio_formadores = []
        formadores_com_eventos = qs.values('formadores__nome', 'formadores__area_atuacao').annotate(
            eventos=models.Count('id')
        ).order_by('-eventos')
        
        for item in formadores_com_eventos:
            if item['formadores__nome']:  # Só se tem formador associado
                relatorio_formadores.append({
                    'nome': item['formadores__nome'],
                    'area': item['formadores__area_atuacao'],
                    'eventos': item['eventos']
                })
        
        # Relatório por município
        relatorio_municipios = list(
            qs.values('municipio__nome', 'municipio__uf')
            .annotate(eventos=models.Count('id'))
            .order_by('-eventos')
        )
        
        # Relatório por projeto  
        relatorio_projetos = list(
            qs.values('projeto__nome')
            .annotate(eventos=models.Count('id'))
            .order_by('-eventos')
        )
        
        # Opções para filtros
        projetos_opcoes = Projeto.objects.filter(ativo=True).order_by('nome')
        municipios_opcoes = Municipio.objects.filter(ativo=True).order_by('nome')
        
        context.update({
            'periodo_dias': dias,
            'projeto_selecionado': projeto_id,
            'municipio_selecionado': municipio_id,
            'total_eventos': total_eventos,
            'total_formadores_envolvidos': total_formadores_envolvidos,
            'relatorio_formadores': relatorio_formadores,
            'relatorio_municipios': relatorio_municipios,
            'relatorio_projetos': relatorio_projetos,
            'projetos_opcoes': projetos_opcoes,
            'municipios_opcoes': municipios_opcoes,
        })
        
        return context


class DashboardStatsAPIView(LoginRequiredMixin, View):
    """API endpoint para estatísticas do dashboard principal"""
    def get(self, request):
        agora = timezone.now()
        
        # Filtros da request
        periodo_dias = request.GET.get('periodo', '30')  # padrão: 30 dias
        projeto_id = request.GET.get('projeto')
        municipio_id = request.GET.get('municipio')
        
        try:
            dias = int(periodo_dias)
            if dias <= 0:
                dias = 30
        except (ValueError, TypeError):
            dias = 30
            
        # Calcular período baseado no filtro
        if dias == 30:
            # Mês atual
            data_limite = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            periodo_label = agora.strftime('%m/%Y')
        else:
            # Últimos N dias
            data_limite = agora - timedelta(days=dias)
            periodo_label = f"últimos {dias} dias"
        
        # Query base para eventos
        eventos_query = Solicitacao.objects.filter(
            data_inicio__gte=data_limite,
            status=SolicitacaoStatus.APROVADO
        )
        
        # Aplicar filtros opcionais
        if projeto_id:
            try:
                eventos_query = eventos_query.filter(projeto_id=projeto_id)
            except (ValueError, TypeError):
                pass
                
        if municipio_id:
            try:
                eventos_query = eventos_query.filter(municipio_id=municipio_id)
            except (ValueError, TypeError):
                pass
        
        # 1. Eventos no período (com filtros aplicados)
        eventos_periodo = eventos_query.count()
        
        # 2. Formadores ativos (sempre global)
        formadores_ativos = Formador.objects.filter(ativo=True).count()
        
        # 3. Solicitações pendentes (sempre global)
        solicitacoes_pendentes = Solicitacao.objects.filter(
            status=SolicitacaoStatus.PENDENTE
        ).count()
        
        # 4. Municípios atendidos no período (com filtros de projeto)
        municipios_query = Solicitacao.objects.filter(
            data_inicio__gte=data_limite,
            status=SolicitacaoStatus.APROVADO
        )
        if projeto_id:
            try:
                municipios_query = municipios_query.filter(projeto_id=projeto_id)
            except (ValueError, TypeError):
                pass
        
        municipios_atendidos = municipios_query.values('municipio').distinct().count()
        
        # Metadados dos filtros aplicados
        filtros_aplicados = []
        if projeto_id:
            try:
                projeto = Projeto.objects.get(id=projeto_id)
                filtros_aplicados.append(f"Projeto: {projeto.nome}")
            except Projeto.DoesNotExist:
                pass
                
        if municipio_id:
            try:
                municipio = Municipio.objects.get(id=municipio_id)
                filtros_aplicados.append(f"Município: {municipio.nome}")
            except Municipio.DoesNotExist:
                pass
        
        payload = {
            "timestamp": agora.isoformat(),
            "periodo_referencia": {
                "eventos_periodo": periodo_label,
                "municipios_periodo": periodo_label,
                "dias_filtro": dias
            },
            "filtros": {
                "periodo_dias": dias,
                "projeto_id": projeto_id,
                "municipio_id": municipio_id,
                "filtros_aplicados": filtros_aplicados
            },
            "estatisticas": {
                "eventos_periodo": eventos_periodo,
                "formadores_ativos": formadores_ativos,
                "solicitacoes_pendentes": solicitacoes_pendentes,
                "municipios_atendidos": municipios_atendidos
            },
            "meta": {
                "fonte": "dados_reais_banco",
                "cache_ttl": 300,  # 5 minutos
                "usuario": request.user.username,
                "com_filtros": bool(projeto_id or municipio_id or dias != 30)
            }
        }
        
        return JsonResponse(payload)


class DiretoriaAPIMetricsView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'core.view_relatorios'
    """API endpoint para métricas executivas da Diretoria"""
    def get(self, request):
        agora = timezone.now()
        data_inicio_ano = agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Métricas anuais
        eventos_aprovados_ano = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano,
            status=SolicitacaoStatus.APROVADO
        ).count()
        
        total_solicitacoes_ano = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano
        ).count()
        
        # Formadores ativos no ano
        formadores_utilizados = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano,
            status=SolicitacaoStatus.APROVADO
        ).values('formadores').distinct().count()
        
        # Municípios atendidos no ano
        municipios_atendidos = Solicitacao.objects.filter(
            data_solicitacao__gte=data_inicio_ano,
            status=SolicitacaoStatus.APROVADO
        ).values('municipio').distinct().count()
        
        # Crescimento mensal (últimos 6 meses)
        crescimento_mensal = []
        for i in range(6):
            data_ref = agora - timedelta(days=30*i)
            inicio_mes = data_ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if i == 5:
                fim_mes = data_inicio_ano
            else:
                proximo_mes = data_ref.replace(day=1) + timedelta(days=32)
                fim_mes = proximo_mes.replace(day=1)
            
            eventos = Solicitacao.objects.filter(
                data_inicio__gte=inicio_mes,
                data_inicio__lt=fim_mes,
                status=SolicitacaoStatus.APROVADO
            ).count()
            
            crescimento_mensal.append({
                'mes': inicio_mes.strftime('%Y-%m'),
                'eventos': eventos
            })
        
        crescimento_mensal.reverse()
        
        payload = {
            "timestamp": agora.isoformat(),
            "periodo": f"Ano {agora.year}",
            "metricas_executivas": {
                "eventos_realizados": eventos_aprovados_ano,
                "total_solicitacoes": total_solicitacoes_ano,
                "taxa_aprovacao": round(
                    (eventos_aprovados_ano / total_solicitacoes_ano * 100) 
                    if total_solicitacoes_ano > 0 else 0, 1
                ),
                "formadores_utilizados": formadores_utilizados,
                "municipios_atendidos": municipios_atendidos,
                "crescimento_mensal": crescimento_mensal
            },
            "recursos_sistema": {
                "formadores_cadastrados": Formador.objects.filter(ativo=True).count(),
                "municipios_cadastrados": Municipio.objects.filter(ativo=True).count(),
                "projetos_ativos": Projeto.objects.filter(ativo=True).count(),
                "tipos_evento": TipoEvento.objects.filter(ativo=True).count()
            }
        }
        
        return JsonResponse(payload)