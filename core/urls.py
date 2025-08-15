# aprender_sistema/core/urls.py
from django.urls import path
from .views import (
    SolicitacaoCreateView, SolicitacaoOKView,
    AprovacoesPendentesView, AprovacaoDetailView,
    BloqueioCreateView,
    home
)
from .views_calendar import MapaMensalView, MapaMensalPageView
from django.views.generic import TemplateView

app_name = "core"

urlpatterns = [
    # Adicionei a URL para a página inicial
    path("", home, name="home"),
    
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
    
    # Página visual (HTML)
    path("disponibilidade/", MapaMensalPageView.as_view(), name="mapa_mensal_page"),
]
