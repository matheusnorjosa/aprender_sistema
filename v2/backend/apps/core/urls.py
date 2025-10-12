"""
Core API URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = "core"

router = DefaultRouter()
router.register(r"solicitacoes", views.SolicitacaoViewSet, basename="solicitacao")
router.register(r"availability-blocks", views.AvailabilityBlockViewSet, basename="availability-block")

urlpatterns = [
    path("", views.api_root, name="api-root"),
    path("availability/check/", views.AvailabilityCheckView.as_view(), name="availability-check"),
    path("", include(router.urls)),
]
