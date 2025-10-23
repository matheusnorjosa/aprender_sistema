"""
Core API URLs (v2-only, views ativas isoladas)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Imports de módulos isolados (GAP-001 fix)
from .views_basic import CurrentUserView, api_root
from .views_health import features, readyz
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
    GCalBulkReapplyView,
)
from .views_lookup import (
    MunicipioLookup,
    ProjetoLookup,
    TipoEventoLookup,
    UsuarioLookup,
)
from .views_validate import SolicitationValidateView
from .views import (
    MunicipioViewSet,
    ProjetoViewSet,
    CompraViewSet,
    # UsuarioAdminViewSet,  # Comentado no views.py (PR #20)
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
# router.register(r"usuarios-admin", UsuarioAdminViewSet, basename="usuario-admin")  # Comentado (PR #20)
router.register(r"audit-logs", AuditLogViewSet, basename="audit-log")

urlpatterns = [
    path("", api_root, name="api-root"),
    path("readyz/", readyz, name="readyz"),
    path("features/", features, name="features"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
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
    # GCal Dashboard (PR14 - Ajustes pós-merge)
    path("gcal/status-summary/", GCalStatusSummaryView.as_view(), name="gcal-status-summary"),
    path("gcal/list/", GCalListView.as_view(), name="gcal-list"),
    path("gcal/drift/", GCalDriftView.as_view(), name="gcal-drift"),
    path("gcal/reapply/", GCalBulkReapplyView.as_view(), name="gcal-bulk-reapply"),
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
