# aprender_sistema/core/urls.py
from django.urls import path
from .views import (
    SolicitacaoCreateView, SolicitacaoOKView,
    AprovacoesPendentesView, AprovacaoDetailView,
    BloqueioCreateView
)
from .views_calendar import MapaMensalView
from django.views.generic import TemplateView

urlpatterns = [
    # RF02
    path("solicitar/", SolicitacaoCreateView.as_view(), name="solicitar_evento"),
    path("solicitar/ok/", SolicitacaoOKView.as_view(), name="solicitacao_ok"),

    # RF04
    path("aprovacoes/pendentes/", AprovacoesPendentesView.as_view(), name="aprovacoes_pendentes"),
    path("aprovacoes/<uuid:pk>/", AprovacaoDetailView.as_view(), name="aprovacao_detail"),

    # Bloqueio de agenda
    path("bloqueios/novo/", BloqueioCreateView.as_view(), name="bloqueio_novo"),
    path("bloqueios/ok/", TemplateView.as_view(template_name="core/bloqueio_ok.html"), name="bloqueio_ok"),

    # Mapa mensal (JSON)
    path("mapa-mensal/", MapaMensalView.as_view(), name="mapa_mensal"),
]
