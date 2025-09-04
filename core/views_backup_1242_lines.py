# aprender_sistema/core/views.py

"""
ATENÇÃO: Este arquivo foi refatorado em uma estrutura modular.
Todas as views foram movidas para o diretório core/views/

Para encontrar uma view específica, veja:
- home_views.py: HomeView, home
- auth_views.py: CustomLoginView
- solicitacao_views.py: SolicitacaoCreateView, SolicitacaoOKView
- aprovacao_views.py: AprovacoesPendentesView, AprovacaoDetailView
- formador_views.py: BloqueioCreateView, FormadorEventosView
- controle_views.py: GoogleCalendarMonitorView, AuditoriaLogView, ControleAPIStatusView
- coordenador_views.py: CoordenadorMeusEventosView
- diretoria_views.py: DiretoriaExecutiveDashboardView, DiretoriaRelatoriosView, etc.

As views são automaticamente importadas através de core/views/__init__.py
"""

# Import all views from modular structure
from .views import *
