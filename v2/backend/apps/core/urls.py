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

app_name = "core"

router = DefaultRouter()
router.register(r"solicitacoes", SolicitacaoViewSet, basename="solicitacao")
router.register(
    r"availability-blocks",
    AvailabilityBlockViewSet,
    basename="availability-block",
)

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
    path("", include(router.urls)),
]
