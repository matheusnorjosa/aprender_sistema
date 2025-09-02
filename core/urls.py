# aprender_sistema/core/urls.py
from django.urls import path
from .views import (
    HomeView,  # Nova importação
    SolicitacaoCreateView, SolicitacaoOKView,
    AprovacoesPendentesView, AprovacaoDetailView,
    BloqueioCreateView, CustomLoginView, FormadorEventosView,
    GoogleCalendarMonitorView, AuditoriaLogView, ControleAPIStatusView,
    ControlePreAgendaView, CriarEventoGoogleCalendarView, RemoverEventoPreAgendaView,
    DiretoriaExecutiveDashboardView, DiretoriaRelatoriosView, DiretoriaAPIMetricsView,
    CoordenadorMeusEventosView, DashboardStatsAPIView,
    home  # Mantendo a função home também (opcional)
)
from .views_calendar import MapaMensalView, MapaMensalPageView
from django.views.generic import TemplateView

app_name = "core"

urlpatterns = [
    # Home - ambas as versões (você pode escolher uma ou manter ambas)
    path("", HomeView.as_view(), name="home"),  # Versão class-based
    # path("", home, name="home"),  # Versão function-based (mantenha se precisar)
    
    # Autenticação
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", TemplateView.as_view(template_name="core/logout.html"), name="logout"),
    
    # RF02
    path("solicitar/", SolicitacaoCreateView.as_view(), name="solicitar_evento"),
    path("solicitar/ok/", SolicitacaoOKView.as_view(), name="solicitacao_ok"),

    # RF04
    path("aprovacoes/pendentes/", AprovacoesPendentesView.as_view(), name="aprovacoes_pendentes"),
    path("aprovacoes/<uuid:pk>/", AprovacaoDetailView.as_view(), name="aprovacao_detail"),

    # Bloqueio de agenda
    path("bloqueios/novo/", BloqueioCreateView.as_view(), name="bloqueio_novo"),
    path("bloqueios/ok/", TemplateView.as_view(template_name="core/bloqueio_ok.html"), name="bloqueio_ok"),

    # Página do Formador
    path("formador/eventos/", FormadorEventosView.as_view(), name="formador_eventos"),
    
    # Perfil Coordenador - Gestão de Eventos
    path("coordenador/meus-eventos/", CoordenadorMeusEventosView.as_view(), name="coordenador_meus_eventos"),

    # Mapa mensal (JSON)
    path("mapa-mensal/", MapaMensalView.as_view(), name="mapa_mensal"),
    
    # Página visual (HTML)
    path("disponibilidade/", MapaMensalPageView.as_view(), name="mapa_mensal_page"),
    
    # Perfil Controle - Monitoramento e Auditoria
    path("controle/google-calendar/", GoogleCalendarMonitorView.as_view(), name="controle_google_calendar"),
    path("controle/auditoria/", AuditoriaLogView.as_view(), name="controle_auditoria"),
    path("controle/api/status/", ControleAPIStatusView.as_view(), name="controle_api_status"),
    
    # Perfil Controle - Pré-Agenda
    path("controle/pre-agenda/", ControlePreAgendaView.as_view(), name="controle_pre_agenda"),
    path("controle/pre-agenda/criar/<uuid:solicitacao_id>/", CriarEventoGoogleCalendarView.as_view(), name="controle_criar_evento"),
    path("controle/pre-agenda/remover/<uuid:solicitacao_id>/", RemoverEventoPreAgendaView.as_view(), name="controle_remover_evento"),
    
    # Perfil Diretoria - Visão Estratégica e Relatórios Executivos
    path("diretoria/dashboard/", DiretoriaExecutiveDashboardView.as_view(), name="diretoria_dashboard"),
    path("diretoria/relatorios/", DiretoriaRelatoriosView.as_view(), name="diretoria_relatorios"),
    path("diretoria/api/metrics/", DiretoriaAPIMetricsView.as_view(), name="diretoria_api_metrics"),
    
    # API para Dashboard Principal
    path("api/dashboard-stats/", DashboardStatsAPIView.as_view(), name="dashboard_stats_api"),
]