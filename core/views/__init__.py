"""
Views modulares do core.
Organizadas por funcionalidade para melhor manutenibilidade.
"""

from .aprovacao_views import AprovacaoDetailView, AprovacoesPendentesView
from .auth_views import CustomLoginView
from .controle_pre_agenda_views import (
    ControlePreAgendaView,
    CriarEventoGoogleCalendarView,
    RemoverEventoPreAgendaView,
)
from .controle_views import (
    AuditoriaLogView,
    ControleAPIStatusView,
    GoogleCalendarMonitorView,
)
from .coordenador_views import CoordenadorMeusEventosView
from .diretoria_views import (
    DashboardStatsAPIView,
    DiretoriaAPIMetricsView,
    DiretoriaExecutiveDashboardView,
    DiretoriaRelatoriosView,
    TestMapView,
    TestMapSimpleView,
    TestMapFinalView,
    TestMapAdvancedView,
)
from .formador_views import BloqueioCreateView, FormadorEventosView

# Imports das views principais
from .home_views import HomeView, home
from .solicitacao_views import SolicitacaoCreateView, SolicitacaoOKView

# Imports das views de importação
from .importacao_views import (
    CursosCSVUploadView,
    CursosCSVProcessarView,
    CursosCSVPreviewView,
    VinculosProjetoCursoListView,
    CursosSemVinculoListView,
    VincularCursoProjetoView,
    DesvincularCursoView,
    ReprocessarVinculacaoAutomaticaView,
)

# Lista para facilitar importação
__all__ = [
    "home",
    "HomeView",
    "SolicitacaoCreateView",
    "SolicitacaoOKView",
    "AprovacoesPendentesView",
    "AprovacaoDetailView",
    "BloqueioCreateView",
    "FormadorEventosView",
    "CustomLoginView",
    "GoogleCalendarMonitorView",
    "AuditoriaLogView",
    "ControleAPIStatusView",
    "ControlePreAgendaView",
    "CriarEventoGoogleCalendarView",
    "RemoverEventoPreAgendaView",
    "CoordenadorMeusEventosView",
    "DiretoriaExecutiveDashboardView",
    "DiretoriaRelatoriosView",
    "DashboardStatsAPIView",
    "DiretoriaAPIMetricsView",
    "TestMapView",
    "TestMapSimpleView",
    "TestMapFinalView",
    "TestMapAdvancedView",
    # Views de importação
    "CursosCSVUploadView",
    "CursosCSVProcessarView",
    "CursosCSVPreviewView",
    "VinculosProjetoCursoListView",
    "CursosSemVinculoListView",
    "VincularCursoProjetoView",
    "DesvincularCursoView",
    "ReprocessarVinculacaoAutomaticaView",
]
