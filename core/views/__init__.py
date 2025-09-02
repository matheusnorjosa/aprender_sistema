"""
Views modulares do core.
Organizadas por funcionalidade para melhor manutenibilidade.
"""

# Imports das views principais
from .home_views import home, HomeView
from .solicitacao_views import SolicitacaoCreateView, SolicitacaoOKView
from .aprovacao_views import AprovacoesPendentesView, AprovacaoDetailView
from .formador_views import BloqueioCreateView, FormadorEventosView
from .auth_views import CustomLoginView
from .controle_views import GoogleCalendarMonitorView, AuditoriaLogView, ControleAPIStatusView
from .controle_pre_agenda_views import ControlePreAgendaView, CriarEventoGoogleCalendarView, RemoverEventoPreAgendaView
from .coordenador_views import CoordenadorMeusEventosView
from .diretoria_views import (
    DiretoriaExecutiveDashboardView, DiretoriaRelatoriosView, 
    DashboardStatsAPIView, DiretoriaAPIMetricsView
)

# Lista para facilitar importação
__all__ = [
    'home', 'HomeView',
    'SolicitacaoCreateView', 'SolicitacaoOKView', 
    'AprovacoesPendentesView', 'AprovacaoDetailView',
    'BloqueioCreateView', 'FormadorEventosView',
    'CustomLoginView',
    'GoogleCalendarMonitorView', 'AuditoriaLogView', 'ControleAPIStatusView',
    'ControlePreAgendaView', 'CriarEventoGoogleCalendarView', 'RemoverEventoPreAgendaView',
    'CoordenadorMeusEventosView',
    'DiretoriaExecutiveDashboardView', 'DiretoriaRelatoriosView',
    'DashboardStatsAPIView', 'DiretoriaAPIMetricsView'
]