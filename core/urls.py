# aprender_sistema/core/urls.py
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import TemplateView

from .views import HomeView  # Nova importação
from .views import home  # Mantendo a função home também (opcional)
from .views.health import health_check, health_detailed, health_ready, health_live, health_metrics
# Removido: views não existem no módulo core.api.dashboard.views
from .views import (
    AprovacaoDetailView,
    AprovacoesPendentesView,
    AuditoriaLogView,
    BloqueioCreateView,
    ControleAPIStatusView,
    ControlePreAgendaView,
    CoordenadorMeusEventosView,
    CriarEventoGoogleCalendarView,
    CustomLoginView,
    DashboardStatsAPIView,
    DiretoriaAPIMetricsView,
    DiretoriaExecutiveDashboardView,
    DiretoriaRelatoriosView,
    FormadorEventosView,
    GoogleCalendarMonitorView,
    RemoverEventoPreAgendaView,
    SolicitacaoCreateView,
    SolicitacaoOKView,
    TestMapView,
    TestMapSimpleView,
    TestMapFinalView,
    TestMapAdvancedView,
)
from .views.mapa_views import MapaDadosAPIView, MapaEstatisticasAPIView
from .views.mapa_realtime_views import MapaRealtimeAPIView, MapaStatusAPIView, MapaWebhookView
from .views.diretoria_views import DashboardChartsAPIView, DiretoriaDebugView, DiretoriaIntegratedDashboardView, DashboardCursosAPIView, DashboardCoordenadoresAPIView
from .views.admin_views import CommunicationLogsView
from .views.gestao_views import (
    GestaoDashboardView,
    FormadorListView, FormadorCreateView, FormadorUpdateView, FormadorDeleteView,
    MunicipioListView, MunicipioCreateView, MunicipioUpdateView, MunicipioDeleteView,
    ProjetoListView, ProjetoCreateView, ProjetoUpdateView, ProjetoDeleteView,
    TipoEventoListView, TipoEventoCreateView, TipoEventoUpdateView, TipoEventoDeleteView
)
from .views.api_approval import (
    BulkApprovalAPI,
    SolicitacaoConflictsAPI,
    SolicitacoesPendentesAPI,
)
from .views.api_availability import CheckAvailabilityAPI, FormadorDetailsAPI, FormadoresSuperintendenciaAPI
from .views.api_notifications import (
    CommunicationLogsAPI,
    CommunicationStatsAPI,
    MarkAllNotificationsReadAPI,
    MarkNotificationReadAPI,
    NotificationCountAPI,
    RealtimeNotificationsAPI,
    UserNotificationsAPI,
)
from .views_calendar import MapaMensalPageView, MapaMensalView, FormadoresSuperintendenciaView
from .views.deslocamento_views import (
    DeslocamentoListView,
    DeslocamentoCreateView,
    DeslocamentoUpdateView,
    DeslocamentoDeleteView,
    DeslocamentoAPI,
)

app_name = "core"

urlpatterns = [
    # Health check endpoints
    path("health/", health_check, name="health_check"),
    path("health/detailed/", health_detailed, name="health_detailed"),
    path("health/ready/", health_ready, name="health_ready"),
    path("health/live/", health_live, name="health_live"),
    path("health/metrics/", health_metrics, name="health_metrics"),
    # Home - ambas as versões (você pode escolher uma ou manter ambas)
    path("", HomeView.as_view(), name="home"),  # Versão class-based
    # path("", home, name="home"),  # Versão function-based (mantenha se precisar)
    # Autenticação
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    # RF02
    path("solicitar/", SolicitacaoCreateView.as_view(), name="solicitar_evento"),
    path("solicitar/ok/", SolicitacaoOKView.as_view(), name="solicitacao_ok"),
    # RF04
    path(
        "aprovacoes/pendentes/",
        AprovacoesPendentesView.as_view(),
        name="aprovacoes_pendentes",
    ),
    path(
        "aprovacoes/<uuid:pk>/", AprovacaoDetailView.as_view(), name="aprovacao_detail"
    ),
    # Bloqueio de agenda
    path("bloqueios/novo/", BloqueioCreateView.as_view(), name="bloqueio_novo"),
    path(
        "bloqueios/ok/",
        TemplateView.as_view(template_name="core/bloqueio_ok.html"),
        name="bloqueio_ok",
    ),
    # Página do Formador
    path("formador/eventos/", FormadorEventosView.as_view(), name="formador_eventos"),
    # Perfil Coordenador - Gestão de Eventos
    path(
        "coordenador/meus-eventos/",
        CoordenadorMeusEventosView.as_view(),
        name="coordenador_meus_eventos",
    ),
    # Mapa mensal (JSON)
    path("mapa-mensal/", MapaMensalView.as_view(), name="mapa_mensal"),
    # Página visual (HTML)
    path("disponibilidade/", MapaMensalPageView.as_view(), name="mapa_mensal_page"),
    # Perfil Controle - Monitoramento e Auditoria
    path(
        "controle/google-calendar/",
        GoogleCalendarMonitorView.as_view(),
        name="controle_google_calendar",
    ),
    path("controle/auditoria/", AuditoriaLogView.as_view(), name="controle_auditoria"),
    path(
        "controle/api/status/",
        ControleAPIStatusView.as_view(),
        name="controle_api_status",
    ),
    # Perfil Controle - Pré-Agenda
    path(
        "controle/pre-agenda/",
        ControlePreAgendaView.as_view(),
        name="controle_pre_agenda",
    ),
    path(
        "controle/pre-agenda/criar/<uuid:solicitacao_id>/",
        CriarEventoGoogleCalendarView.as_view(),
        name="controle_criar_evento",
    ),
    path(
        "controle/pre-agenda/remover/<uuid:solicitacao_id>/",
        RemoverEventoPreAgendaView.as_view(),
        name="controle_remover_evento",
    ),
    # Perfil Diretoria - Visão Estratégica e Relatórios Executivos
    path(
        "diretoria/dashboard/",
        DiretoriaExecutiveDashboardView.as_view(),
        name="diretoria_dashboard",
    ),
    path(
        "diretoria/dashboard/integrado/",
        DiretoriaIntegratedDashboardView.as_view(),
        name="diretoria_dashboard_integrado",
    ),
    path(
        "diretoria/test-map/",
        TestMapView.as_view(),
        name="diretoria_test_map",
    ),
    path(
        "diretoria/test-map-simple/",
        TestMapSimpleView.as_view(),
        name="diretoria_test_map_simple",
    ),
    path(
        "diretoria/test-map-final/",
        TestMapFinalView.as_view(),
        name="diretoria_test_map_final",
    ),
    path(
        "diretoria/mapa-avancado/",
        TestMapAdvancedView.as_view(),
        name="diretoria_mapa_avancado",
    ),
    # APIs para dados do mapa
    path(
        "api/mapa/dados/",
        MapaDadosAPIView.as_view(),
        name="api_mapa_dados",
    ),
    path(
        "api/mapa/estatisticas/",
        MapaEstatisticasAPIView.as_view(),
        name="api_mapa_estatisticas",
    ),
    # APIs para atualizações em tempo real
    path(
        "api/mapa/realtime/",
        MapaRealtimeAPIView.as_view(),
        name="api_mapa_realtime",
    ),
    path(
        "api/mapa/status/",
        MapaStatusAPIView.as_view(),
        name="api_mapa_status",
    ),
    path(
        "api/mapa/webhook/",
        MapaWebhookView.as_view(),
        name="api_mapa_webhook",
    ),
    path(
        "diretoria/relatorios/",
        DiretoriaRelatoriosView.as_view(),
        name="diretoria_relatorios",
    ),
    path(
        "diretoria/api/metrics/",
        DiretoriaAPIMetricsView.as_view(),
        name="diretoria_api_metrics",
    ),
    path(
        "diretoria/api/charts/",
        DashboardChartsAPIView.as_view(),
        name="diretoria_api_charts",
    ),
    path(
        "diretoria/api/cursos/",
        DashboardCursosAPIView.as_view(),
        name="diretoria_api_cursos",
    ),
    path(
        "diretoria/api/coordenadores/",
        DashboardCoordenadoresAPIView.as_view(),
        name="diretoria_api_coordenadores",
    ),
    # Removido: views não existem
    # Página de debug temporária
    path(
        "diretoria/debug/",
        DiretoriaDebugView.as_view(),
        name="diretoria_debug",
    ),
    # Teste standalone do dashboard
    path(
        "diretoria/test/",
        TemplateView.as_view(template_name="core/diretoria/dashboard_test.html"),
        name="diretoria_test",
    ),
    # Serve Chart.js directly (removido - usar sistema padrão de static files)
    
    # Gestão Administrativa - CRUD para entidades principais
    path("gestao/", GestaoDashboardView.as_view(), name="gestao_dashboard"),
    
    # Gestão de Formadores
    path("gestao/formadores/", FormadorListView.as_view(), name="gestao_formadores"),
    path("gestao/formadores/novo/", FormadorCreateView.as_view(), name="gestao_formadores_create"),
    path("gestao/formadores/<uuid:pk>/editar/", FormadorUpdateView.as_view(), name="gestao_formadores_update"),
    path("gestao/formadores/<uuid:pk>/excluir/", FormadorDeleteView.as_view(), name="gestao_formadores_delete"),
    
    # Gestão de Municípios
    path("gestao/municipios/", MunicipioListView.as_view(), name="gestao_municipios"),
    path("gestao/municipios/novo/", MunicipioCreateView.as_view(), name="gestao_municipios_create"),
    path("gestao/municipios/<uuid:pk>/editar/", MunicipioUpdateView.as_view(), name="gestao_municipios_update"),
    path("gestao/municipios/<uuid:pk>/excluir/", MunicipioDeleteView.as_view(), name="gestao_municipios_delete"),
    
    # Gestão de Projetos
    path("gestao/projetos/", ProjetoListView.as_view(), name="gestao_projetos"),
    path("gestao/projetos/novo/", ProjetoCreateView.as_view(), name="gestao_projetos_create"),
    path("gestao/projetos/<uuid:pk>/editar/", ProjetoUpdateView.as_view(), name="gestao_projetos_update"),
    path("gestao/projetos/<uuid:pk>/excluir/", ProjetoDeleteView.as_view(), name="gestao_projetos_delete"),
    
    # Gestão de Tipos de Evento
    path("gestao/tipos-evento/", TipoEventoListView.as_view(), name="gestao_tipos_evento"),
    path("gestao/tipos-evento/novo/", TipoEventoCreateView.as_view(), name="gestao_tipos_evento_create"),
    path("gestao/tipos-evento/<uuid:pk>/editar/", TipoEventoUpdateView.as_view(), name="gestao_tipos_evento_update"),
    path("gestao/tipos-evento/<uuid:pk>/excluir/", TipoEventoDeleteView.as_view(), name="gestao_tipos_evento_delete"),
    
    # API para Dashboard Principal
    path(
        "api/dashboard-stats/",
        DashboardStatsAPIView.as_view(),
        name="dashboard_stats_api",
    ),
    # APIs para verificação de disponibilidade em tempo real
    path(
        "api/check-availability/",
        CheckAvailabilityAPI.as_view(),
        name="check_availability_api",
    ),
    path(
        "api/formador-details/",
        FormadorDetailsAPI.as_view(),
        name="formador_details_api",
    ),
    path(
        "api/formadores-superintendencia/",
        FormadoresSuperintendenciaView.as_view(),
        name="formadores_superintendencia_api",
    ),
    # APIs para sistema de aprovação avançado
    path("api/bulk-approval/", BulkApprovalAPI.as_view(), name="bulk_approval_api"),
    path(
        "api/solicitacoes-pendentes/",
        SolicitacoesPendentesAPI.as_view(),
        name="solicitacoes_pendentes_api",
    ),
    path(
        "api/solicitacao-conflicts/<uuid:solicitacao_id>/",
        SolicitacaoConflictsAPI.as_view(),
        name="solicitacao_conflicts_api",
    ),
    # APIs para sistema de notificações em tempo real
    path(
        "api/notifications/user/",
        UserNotificationsAPI.as_view(),
        name="user_notifications_api",
    ),
    path(
        "api/notifications/mark-read/",
        MarkNotificationReadAPI.as_view(),
        name="mark_notification_read_api",
    ),
    path(
        "api/notifications/mark-all-read/",
        MarkAllNotificationsReadAPI.as_view(),
        name="mark_all_notifications_read_api",
    ),
    path(
        "api/notifications/count/",
        NotificationCountAPI.as_view(),
        name="notification_count_api",
    ),
    path(
        "api/notifications/realtime/",
        RealtimeNotificationsAPI.as_view(),
        name="realtime_notifications_api",
    ),
    # APIs para logs de comunicação (apenas admin)
    path(
        "api/communications/logs/",
        CommunicationLogsAPI.as_view(),
        name="communication_logs_api",
    ),
    path(
        "api/communications/stats/",
        CommunicationStatsAPI.as_view(),
        name="communication_stats_api",
    ),
    # Páginas de administração
    path(
        "admin/communication-logs/",
        CommunicationLogsView.as_view(),
        name="admin_communication_logs",
    ),
    
    # Sistema CRUD para Deslocamentos
    path("deslocamentos/", DeslocamentoListView.as_view(), name="deslocamentos_list"),
    path("deslocamentos/novo/", DeslocamentoCreateView.as_view(), name="deslocamentos_create"),
    path("deslocamentos/<uuid:pk>/editar/", DeslocamentoUpdateView.as_view(), name="deslocamentos_update"),
    path("deslocamentos/<uuid:pk>/excluir/", DeslocamentoDeleteView.as_view(), name="deslocamentos_delete"),
    path("api/deslocamentos/", DeslocamentoAPI.as_view(), name="deslocamentos_api"),
]
