"""
Core API URLs (v2-only, views ativas isoladas)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportMissingImports=false

from __future__ import annotations

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from .views import DATRegistroViewSet  # DAT Registros module
from .views import GerenciaViewSet  # Issue #145
from .views import GroupViewSet  # Criado (Fase 1 Iteração 2, GAP-002)
from .views import PermissaoFuncionalViewSet  # Issue #829
from .views import ProdutoViewSet  # Issue #146
from .views import ProjetoGeralViewSet  # DAT Registros module
from .views import RBACMetaView  # Issue #829
from .views import UsuarioAdminViewSet  # Reativado (Fase 1 Iteração 2, GAP-001)
from .views import (  # DAT Module ViewSets; Plano Formacoes (novo modelo estruturado)
    AcaoInstanciaViewSet,
    AuditLogViewSet,
    CicloAcoesViewSet,
    CompraViewSet,
    DATAcaoViewSet,
    DATAreaViewSet,
    DATCadastroViewSet,
    DATCompraViewSet,
    DATCoordenadorViewSet,
    DATFormacaoViewSet,
    MunicipioViewSet,
    NotificacaoInternaViewSet,
    PlanoFormacoesViewSet,
    ProjetoViewSet,
)
from .views.stats import HomeStatsView
from .views_auth import csrf_token, login, logout, ping
from .views_availability import AvailabilityBlockViewSet, AvailabilityCheckManyView, AvailabilityCheckView
from .views_availability_monthly import MonthlyAvailabilityView

# Imports de módulos isolados (GAP-001 fix)
from .views_basic import CurrentUserView, api_root
from .views_compras import ControleComprasListView
from .views_config import config_view  # Issue #187
from .views_controle_dat import ControleAcoesListView, DATAcoesListCreateView
from .views_controle_imports import ImportComprasView
from .views_dashboard import dashboard_overview  # Issue #311
from .views_deslocamento import DeslocamentoViewSet  # Issue #188
from .views_gcal import AlertsSummaryView  # Issue #97
from .views_gcal import EventDetailAPIView  # Issue #98
from .views_gcal import SuccessRateView  # Issue #99
from .views_gcal import TopInsightsView  # Issue #99
from .views_gcal import (  # Core GCal; Dashboard views
    DashboardEventsExportView,
    DashboardEventsView,
    DashboardMetricsView,
    GCalBatchReapplyView,
    GCalBatchResyncView,
    GCalDriftView,
    GCalListView,
    GCalPublishBatchView,
    GCalStatusSummaryView,
    gcal_calendars,
    gcal_health,
)
from .views_health import features, readyz, versionz
from .views_import_bloqueios import ImportBloqueiosView
from .views_import_colecoes import ImportColecoesView
from .views_import_deslocamentos import ImportDeslocamentosView
from .views_import_equipe_gerencia import ImportEquipeGerenciaView
from .views_import_eventos import ImportEventosView
from .views_import_municipios import ImportMunicipiosView
from .views_import_produtos import ImportProdutosView
from .views_import_usuarios import ImportUsuariosView
from .views_imports import ControleImportAcoesView, DATImportCadastrosView
from .views_lookup import MunicipioLookup, ProjetoLookup, TipoEventoLookup, UsuarioLookup
from .views_metrics import (
    formadores_metrics,
    metrics_map,
    metrics_map_coordinators,
    productivity_metrics,
    quality_metrics,
)
from .views_oauth import (
    google_oauth_callback,
    google_oauth_disconnect,
    google_oauth_list_calendars,
    google_oauth_list_events,
    google_oauth_select_calendar,
    google_oauth_start,
    google_oauth_status,
)
from .views_options import (
    areas_options,
    coordenadores_options,
    formadores_do_setor_options,
    municipios_options,
    produtos_options,
    projetos_options,
    tipos_evento_options,
    usuarios_options,
)
from .views_preagenda import PreAgendaListView
from .views_reports import reports_by_uf, reports_status_counts, reports_top_projects, reports_weekly_approved
from .views_solicitacao import SolicitacaoViewSet
from .views_validate import SolicitationValidateView

app_name = "core"

router = DefaultRouter()
router.register(r"solicitacoes", SolicitacaoViewSet, basename="solicitacao")
router.register(
    r"availability-blocks",
    AvailabilityBlockViewSet,
    basename="availability-block",
)
# Admin API ViewSets
router.register(r"municipios", MunicipioViewSet, basename="municipio")
router.register(r"projetos", ProjetoViewSet, basename="projeto")
router.register(r"produtos", ProdutoViewSet, basename="produto")  # Issue #146
router.register(r"gerencias", GerenciaViewSet, basename="gerencia")  # Issue #145
router.register(r"compras", CompraViewSet, basename="compra")
router.register(
    r"usuarios-admin", UsuarioAdminViewSet, basename="usuario-admin"
)  # Reativado (Fase 1 Iteração 2, GAP-001)
router.register(r"grupos", GroupViewSet, basename="grupo")  # Criado (Fase 1 Iteração 2, GAP-002)
router.register(
    r"permissoes-funcionais",
    PermissaoFuncionalViewSet,
    basename="permissao-funcional",
)  # Issue #829
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")
router.register(r"deslocamentos", DeslocamentoViewSet, basename="deslocamento")  # Issue #188
# DAT Registros module (SPEC_DAT_REGISTROS.md)
router.register(r"dat/registros", DATRegistroViewSet, basename="dat-registro")
router.register(r"projetos-gerais", ProjetoGeralViewSet, basename="projeto-geral")
# DAT Module (5 páginas React)
router.register(r"dat/areas", DATAreaViewSet, basename="dat-area")
router.register(r"dat/coordenadores", DATCoordenadorViewSet, basename="dat-coordenador")
router.register(r"dat/acoes-ciclo", DATAcaoViewSet, basename="dat-acao-ciclo")
router.register(r"dat/compras-materiais", DATCompraViewSet, basename="dat-compra-material")
router.register(r"dat/cadastros", DATCadastroViewSet, basename="dat-cadastro")
router.register(r"dat/formacoes", DATFormacaoViewSet, basename="dat-formacao")
# Plano Formacoes (novo modelo estruturado)
router.register(r"dat/plano-formacoes", PlanoFormacoesViewSet, basename="plano-formacoes")
# Acoes/Notificacoes internas (Issue #872)
router.register(r"ciclos-acoes", CicloAcoesViewSet, basename="ciclo-acoes")
router.register(r"acoes-instancia", AcaoInstanciaViewSet, basename="acao-instancia")
router.register(r"notificacoes-internas", NotificacaoInternaViewSet, basename="notificacao-interna")

urlpatterns = [
    path("", api_root, name="api-root"),
    path("readyz/", readyz, name="readyz"),
    path("version/", versionz, name="version"),
    path("features/", features, name="features"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("rbac/meta/", RBACMetaView.as_view(), name="rbac-meta"),
    path("stats/home/", HomeStatsView.as_view(), name="stats-home"),
    # CSRF Token (Issue #135)
    path("csrf/", csrf_token, name="csrf-token"),
    # Authentication
    path("auth/login/", login, name="auth-login"),
    path("auth/logout/", logout, name="auth-logout"),
    path("auth/ping/", ping, name="auth-ping"),  # CP5 - Session keep-alive
    # Google OAuth 2.0 (Sprint 1 - Issue #1)
    path("oauth/google/start/", google_oauth_start, name="google-oauth-start"),
    path("oauth/google/callback/", google_oauth_callback, name="google-oauth-callback"),
    path("integrations/google/status/", google_oauth_status, name="google-oauth-status"),
    path("integrations/google/disconnect/", google_oauth_disconnect, name="google-oauth-disconnect"),
    path("integrations/google/calendars/", google_oauth_list_calendars, name="google-oauth-list-calendars"),
    path("integrations/google/select-calendar/", google_oauth_select_calendar, name="google-oauth-select-calendar"),
    path("integrations/google/events/", google_oauth_list_events, name="google-oauth-list-events"),
    path(
        "availability/check/",
        AvailabilityCheckView.as_view(),
        name="availability-check",
    ),
    path(
        "availability/check-many/",
        AvailabilityCheckManyView.as_view(),
        name="availability-check-many",
    ),
    path(
        "availability/monthly/",
        MonthlyAvailabilityView.as_view(),
        name="availability-monthly",
    ),
    path(
        "controle/import-compras/",
        ImportComprasView.as_view(),
        name="controle-import-compras",
    ),
    # Alias for RBAC tests
    path(
        "import-compras/",
        ImportComprasView.as_view(),
        name="import-compras",
    ),
    path(
        "controle/import-acoes/",
        ControleImportAcoesView.as_view(),
        name="controle-import-acoes",
    ),
    path(
        "controle/compras/",
        ControleComprasListView.as_view(),
        name="controle-compras-list",
    ),
    path(
        "controle/acoes/",
        ControleAcoesListView.as_view(),
        name="controle-acoes-list",
    ),
    path(
        "dat/import-cadastros/",
        DATImportCadastrosView.as_view(),
        name="dat-import-cadastros",
    ),
    path(
        "disponibilidade/import-bloqueios/",
        ImportBloqueiosView.as_view(),
        name="import-bloqueios",
    ),
    path(
        "deslocamentos/import/",
        ImportDeslocamentosView.as_view(),
        name="import-deslocamentos",
    ),
    path(
        "solicitacoes/import/",
        ImportEventosView.as_view(),
        name="import-eventos",
    ),
    path(
        "usuarios/import/",
        ImportUsuariosView.as_view(),
        name="import-usuarios",
    ),
    path(
        "produtos/import/",
        ImportProdutosView.as_view(),
        name="import-produtos",
    ),
    path(
        "municipios/import/",
        ImportMunicipiosView.as_view(),
        name="import-municipios",
    ),
    path(
        "colecoes/import/",
        ImportColecoesView.as_view(),
        name="import-colecoes",
    ),
    path(
        "equipe-gerencia/import/",
        ImportEquipeGerenciaView.as_view(),
        name="import-equipe-gerencia",
    ),
    path(
        "dat/acoes/",
        DATAcoesListCreateView.as_view(),
        name="dat-acoes-list-create",
    ),
    # Pré-agenda
    path("pre-agenda/", PreAgendaListView.as_view(), name="pre-agenda"),
    # GCal Dashboard (PR14 - Ajustes pós-merge + Fase 2 batch publish)
    path("gcal/status-summary/", GCalStatusSummaryView.as_view(), name="gcal-status-summary"),
    path("gcal/list/", GCalListView.as_view(), name="gcal-list"),
    path("gcal/drift/", GCalDriftView.as_view(), name="gcal-drift"),
    path("gcal/publish-batch/", GCalPublishBatchView.as_view(), name="gcal-publish-batch"),
    # Sprint 5 - Dashboard/Monitoring
    path("gcal/dashboard/metrics/", DashboardMetricsView.as_view(), name="gcal-dashboard-metrics"),
    path("gcal/dashboard/events/", DashboardEventsView.as_view(), name="gcal-dashboard-events"),
    # Issue #97 - Alerts Summary (badge + toast)
    path("gcal/dashboard/alerts/summary/", AlertsSummaryView.as_view(), name="gcal-alerts-summary"),
    # Issue #98 - Event Detail with Timeline
    path("gcal/dashboard/events/<int:pk>/detail/", EventDetailAPIView.as_view(), name="gcal-event-detail"),
    # Issue #99 - Insights (Success Rate + Top 5)
    path("gcal/dashboard/insights/success-rate/", SuccessRateView.as_view(), name="gcal-insights-success-rate"),
    path("gcal/dashboard/insights/top/", TopInsightsView.as_view(), name="gcal-insights-top"),
    # Issue #96 - Export CSV/JSON
    path("gcal/dashboard/events/export/", DashboardEventsExportView.as_view(), name="gcal-dashboard-events-export"),
    # Issue #95 - Batch Reapply/Resync
    path("gcal/dashboard/batch/reapply/", GCalBatchReapplyView.as_view(), name="gcal-batch-reapply"),
    path("gcal/dashboard/batch/resync/", GCalBatchResyncView.as_view(), name="gcal-batch-resync"),
    # GCal Endpoints (Sprint 2 - Issue #65)
    path("gcal/calendars/", gcal_calendars, name="gcal-calendars"),
    path("gcal/health/", gcal_health, name="gcal-health"),
    # Metrics and Reports
    path("metrics/map/", metrics_map, name="metrics-map"),
    path("metrics/map/coordinators/", metrics_map_coordinators, name="metrics-map-coordinators"),
    # Issue #189: Team Metrics Endpoints
    path("metrics/team/productivity/", productivity_metrics, name="metrics-team-productivity"),
    path("metrics/team/formadores/", formadores_metrics, name="metrics-team-formadores"),
    path("metrics/team/quality/", quality_metrics, name="metrics-team-quality"),
    path("reports/status-counts/", reports_status_counts, name="reports-status-counts"),
    path("reports/top-projects/", reports_top_projects, name="reports-top-projects"),
    path("reports/weekly-approved/", reports_weekly_approved, name="reports-weekly-approved"),
    path("reports/by-uf/", reports_by_uf, name="reports-by-uf"),
    # Options API
    path("options/municipios/", municipios_options, name="options-municipios"),
    path("options/projetos/", projetos_options, name="options-projetos"),
    path("options/tipos-evento/", tipos_evento_options, name="options-tipos-evento"),
    path("options/usuarios/", usuarios_options, name="options-usuarios"),
    path("options/produtos/", produtos_options, name="options-produtos"),
    path("options/coordenadores/", coordenadores_options, name="options-coordenadores"),
    path("options/areas/", areas_options, name="options-areas"),
    path("options/formadores-do-setor/", formadores_do_setor_options, name="options-formadores-do-setor"),
    # PR16: Lookup (Autocomplete) API
    path("lookup/municipios/", MunicipioLookup.as_view(), name="lookup-municipios"),
    path("lookup/projetos/", ProjetoLookup.as_view(), name="lookup-projetos"),
    path("lookup/tipos-evento/", TipoEventoLookup.as_view(), name="lookup-tipos-evento"),
    path("lookup/usuarios/", UsuarioLookup.as_view(), name="lookup-usuarios"),
    # PR16: Validation API
    path("solicitacoes/validate/", SolicitationValidateView.as_view(), name="solicitacao-validate"),
    # Issue #187: Config API
    path("config/", config_view, name="config"),
    # Issue #311: Dashboard Overview
    path("dashboard/overview/", dashboard_overview, name="dashboard-overview"),
    # API Documentation (drf-spectacular)
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="core:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="core:schema"), name="redoc"),
    path("", include(router.urls)),
]
