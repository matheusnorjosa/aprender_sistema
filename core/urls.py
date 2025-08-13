from django.urls import path
from .views import (
    SolicitacaoCreateView, SolicitacaoOKView,
    AprovacoesPendentesView, AprovacaoDetailView
)

urlpatterns = [
    path("solicitar/", SolicitacaoCreateView.as_view(), name="solicitar_evento"),
    path("solicitar/ok/", SolicitacaoOKView.as_view(), name="solicitacao_ok"),
    path("aprovacoes/pendentes/", AprovacoesPendentesView.as_view(), name="aprovacoes_pendentes"),
    path("aprovacoes/<uuid:pk>/", AprovacaoDetailView.as_view(), name="aprovacao_detail"),
]
