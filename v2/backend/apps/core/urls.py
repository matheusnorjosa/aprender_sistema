"""
Core API URLs (v2-only, views ativas isoladas)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Imports de módulos isolados (GAP-001 fix)
from .views_basic import CurrentUserView, api_root
from .views_health import features, readyz
from .views_auth import login, logout
from .views_solicitacao import SolicitacaoViewSet
from .views_availability import (
    AvailabilityBlockViewSet,
    AvailabilityCheckView,
    AvailabilityCheckManyView,
)
from .views_availability_monthly import MonthlyAvailabilityView
from .views_controle_imports import ImportComprasView
from .views_imports import ControleImportAcoesView, DATImportCadastrosView
from .views_compras import ControleComprasListView
from .views_controle_dat import ControleAcoesListView, DATAcoesListCreateView
from .views_metrics import metrics_map
from .views_reports import (
    reports_status_counts,
    reports_top_projects,
    reports_weekly_approved,
    reports_by_uf,
)
from .views_options import (
    municipios_options,
    projetos_options,
    tipos_evento_options,
    usuarios_options,
)
from .views_preagenda import PreAgendaListView
from .views_gcal_dashboard import (
    GCalStatusSummaryView,
    GCalListView,
    GCalDriftView,
    GCalPublishBatchView,
    DashboardMetricsView,
    DashboardEventsView,
    DashboardEventsExportView,
    GCalBatchReapplyView,
    GCalBatchResyncView,
)
from .views_gcal import gcal_calendars, gcal_health
from .views_lookup import (
    MunicipioLookup,
    ProjetoLookup,
    TipoEventoLookup,
    UsuarioLookup,
)
from .views_validate import SolicitationValidateView
from .views_oauth import (
    google_oauth_start,
    google_oauth_callback,
    google_oauth_status,
    google_oauth_disconnect,
    google_oauth_list_calendars,
    google_oauth_select_calendar,
)
from .views import (
    MunicipioViewSet,
    ProjetoViewSet,
    CompraViewSet,
    UsuarioAdminViewSet,  # Reativado (Fase 1 Iteração 2, GAP-001)
    GroupViewSet,  # Criado (Fase 1 Iteração 2, GAP-002)
    AuditLogViewSet,
)

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
router.register(r"compras", CompraViewSet, basename="compra")
router.register(r"usuarios-admin", UsuarioAdminViewSet, basename="usuario-admin")  # Reativado (Fase 1 Iteração 2, GAP-001)
router.register(r"grupos", GroupViewSet, basename="grupo")  # Criado (Fase 1 Iteração 2, GAP-002)
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", api_root, name="api-root"),
    path("readyz/", readyz, name="readyz"),
    path("features/", features, name="features"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    # Authentication
    path("auth/login/", login, name="auth-login"),
    path("auth/logout/", logout, name="auth-logout"),
    # Google OAuth 2.0 (Sprint 1 - Issue #1)
    path("oauth/google/start/", google_oauth_start, name="google-oauth-start"),
    path("oauth/google/callback/", google_oauth_callback, name="google-oauth-callback"),
    path("integrations/google/status/", google_oauth_status, name="google-oauth-status"),
    path("integrations/google/disconnect/", google_oauth_disconnect, name="google-oauth-disconnect"),
    path("integrations/google/calendars/", google_oauth_list_calendars, name="google-oauth-list-calendars"),
    path("integrations/google/select-calendar/", google_oauth_select_calendar, name="google-oauth-select-calendar"),
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
    path("reports/status-counts/", reports_status_counts, name="reports-status-counts"),
    path("reports/top-projects/", reports_top_projects, name="reports-top-projects"),
    path("reports/weekly-approved/", reports_weekly_approved, name="reports-weekly-approved"),
    path("reports/by-uf/", reports_by_uf, name="reports-by-uf"),
    # Options API
    path("options/municipios/", municipios_options, name="options-municipios"),
    path("options/projetos/", projetos_options, name="options-projetos"),
    path("options/tipos-evento/", tipos_evento_options, name="options-tipos-evento"),
    path("options/usuarios/", usuarios_options, name="options-usuarios"),
    # PR16: Lookup (Autocomplete) API
    path("lookup/municipios/", MunicipioLookup.as_view(), name="lookup-municipios"),
    path("lookup/projetos/", ProjetoLookup.as_view(), name="lookup-projetos"),
    path("lookup/tipos-evento/", TipoEventoLookup.as_view(), name="lookup-tipos-evento"),
    path("lookup/usuarios/", UsuarioLookup.as_view(), name="lookup-usuarios"),
    # PR16: Validation API
    path("solicitacoes/validate/", SolicitationValidateView.as_view(), name="solicitacao-validate"),
    path("", include(router.urls)),
]
