# aprender_sistema/core/urls.py
from django.contrib.auth.views import LogoutView
from django.urls import path
from django.views.generic import TemplateView

from .views import HomeView  # Nova importação
from .views import home  # Mantendo a função home também (opcional)
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
)
from .views.admin_views import CommunicationLogsView
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
from .views_calendar import MapaMensalPageView, MapaMensalView
from .views.deslocamento_views import (
    DeslocamentoListView,
    DeslocamentoCreateView,
    DeslocamentoUpdateView,
    DeslocamentoDeleteView,
    DeslocamentoAPI,
)

app_name = "core"

urlpatterns = [
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
        "diretoria/relatorios/",
        DiretoriaRelatoriosView.as_view(),
        name="diretoria_relatorios",
    ),
    path(
        "diretoria/api/metrics/",
        DiretoriaAPIMetricsView.as_view(),
        name="diretoria_api_metrics",
    ),
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
        FormadoresSuperintendenciaAPI.as_view(),
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
