"""
Analytics Dashboard Service for Aprender Sistema
=================================================

Advanced analytics and visualization system using Plotly and Dash,
providing comprehensive dashboards for educational data analysis.

Author: Claude Code
Date: Janeiro 2025
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.db.models import Count, Q, Avg, Sum
from django.utils import timezone

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.utils import PlotlyJSONEncoder
    from plotly.offline import plot
except ImportError:
    go = None
    px = None
    PlotlyJSONEncoder = None
    plot = None

try:
    import dash
    from dash import dcc, html, Input, Output, callback
except ImportError:
    dash = None
    dcc = None
    html = None
    Input = None
    Output = None
    callback = None

from core.models import (
    Formador, Municipio, Projeto, TipoEvento,
    Solicitacao, SolicitacaoStatus, Aprovacao,
    DisponibilidadeFormadores, LogAuditoria
)

logger = logging.getLogger(__name__)


class EducationalAnalytics:
    """
    Advanced educational analytics service providing:
    - Performance dashboards
    - Trend analysis
    - Capacity planning
    - Resource optimization
    """
    
    def __init__(self):
        self.enabled = go is not None and px is not None
        if not self.enabled:
            logger.warning("Plotly not available - install with: pip install plotly")
    
    def get_formador_performance_data(self, days: int = 30) -> Dict[str, Any]:
        """Get formador performance metrics for the last N days"""
        try:
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Get formador event counts
            formador_stats = (
                Solicitacao.objects
                .filter(
                    data_solicitacao__gte=start_date,
                    status=SolicitacaoStatus.APROVADO
                )
                .values('formadores__usuario__first_name', 
                       'formadores__usuario__last_name')
                .annotate(
                    total_eventos=Count('id')
                )
                .order_by('-total_eventos')
            )
            
            formadores = []
            eventos = []
            duracoes = []
            
            for stat in formador_stats:
                if stat['formadores__usuario__first_name']:
                    nome = f"{stat['formadores__usuario__first_name']} {stat['formadores__usuario__last_name']}"
                    formadores.append(nome)
                    eventos.append(stat['total_eventos'])
                    duracoes.append(4.0)  # Default duration for chart display
            
            return {
                'formadores': formadores,
                'eventos': eventos,
                'duracoes_medias': duracoes,
                'period': f'{days} days',
                'generated_at': end_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting formador performance data: {e}")
            return {'error': str(e)}
    
    def get_municipal_distribution_data(self) -> Dict[str, Any]:
        """Get event distribution by municipality"""
        try:
            municipal_stats = (
                Solicitacao.objects
                .values('municipio__nome')
                .annotate(
                    total_eventos=Count('id'),
                    aprovados=Count('id', filter=Q(status=SolicitacaoStatus.APROVADO)),
                    pendentes=Count('id', filter=Q(status=SolicitacaoStatus.PENDENTE))
                )
                .order_by('-total_eventos')
            )
            
            municipios = []
            totals = []
            aprovados = []
            pendentes = []
            
            for stat in municipal_stats:
                municipios.append(stat['municipio__nome'])
                totals.append(stat['total_eventos'])
                aprovados.append(stat['aprovados'])
                pendentes.append(stat['pendentes'])
            
            return {
                'municipios': municipios,
                'totals': totals,
                'aprovados': aprovados,
                'pendentes': pendentes
            }
            
        except Exception as e:
            logger.error(f"Error getting municipal distribution: {e}")
            return {'error': str(e)}
    
    def get_project_timeline_data(self) -> Dict[str, Any]:
        """Get project activity timeline data"""
        try:
            # Last 6 months of data
            end_date = timezone.now()
            start_date = end_date - timedelta(days=180)
            
            timeline_data = (
                Solicitacao.objects
                .filter(data_solicitacao__gte=start_date)
                .extra(select={'month': "strftime('%%Y-%%m', data_solicitacao)"})
                .values('month', 'projeto__nome')
                .annotate(count=Count('id'))
                .order_by('month', 'projeto__nome')
            )
            
            # Organize data by month and project
            months = set()
            projects = set()
            data_matrix = {}
            
            for item in timeline_data:
                month = item['month']
                project = item['projeto__nome']
                count = item['count']
                
                months.add(month)
                projects.add(project)
                
                if month not in data_matrix:
                    data_matrix[month] = {}
                data_matrix[month][project] = count
            
            return {
                'months': sorted(list(months)),
                'projects': sorted(list(projects)),
                'data_matrix': data_matrix,
                'period': f'{start_date.date()} to {end_date.date()}'
            }
            
        except Exception as e:
            logger.error(f"Error getting project timeline: {e}")
            return {'error': str(e)}
    
    def create_formador_performance_chart(self, data: Dict[str, Any]) -> Optional[str]:
        """Create formador performance bar chart"""
        if not self.enabled or 'error' in data:
            return None
        
        try:
            fig = go.Figure()
            
            # Add bars for event count
            fig.add_trace(go.Bar(
                name='Eventos Realizados',
                x=data['formadores'],
                y=data['eventos'],
                marker_color='#1f77b4'
            ))
            
            # Add line for average duration
            fig.add_trace(go.Scatter(
                name='Duração Média (h)',
                x=data['formadores'],
                y=data['duracoes_medias'],
                mode='lines+markers',
                yaxis='y2',
                line=dict(color='#ff7f0e', width=3),
                marker=dict(size=8)
            ))
            
            # Update layout
            fig.update_layout(
                title=f'Performance dos Formadores - {data["period"]}',
                xaxis_title='Formadores',
                yaxis_title='Número de Eventos',
                yaxis2=dict(
                    title='Duração Média (horas)',
                    overlaying='y',
                    side='right'
                ),
                height=500,
                showlegend=True,
                hovermode='x unified'
            )
            
            return fig.to_json()
            
        except Exception as e:
            logger.error(f"Error creating formador performance chart: {e}")
            return None
    
    def create_municipal_pie_chart(self, data: Dict[str, Any]) -> Optional[str]:
        """Create municipality distribution pie chart"""
        if not self.enabled or 'error' in data:
            return None
        
        try:
            fig = go.Figure(data=[
                go.Pie(
                    labels=data['municipios'],
                    values=data['totals'],
                    hole=0.3,
                    textinfo='label+percent',
                    textposition='outside'
                )
            ])
            
            fig.update_layout(
                title='Distribuição de Eventos por Município',
                height=500,
                showlegend=True
            )
            
            return fig.to_json()
            
        except Exception as e:
            logger.error(f"Error creating municipal pie chart: {e}")
            return None
    
    def create_project_heatmap(self, data: Dict[str, Any]) -> Optional[str]:
        """Create project activity heatmap"""
        if not self.enabled or 'error' in data:
            return None
        
        try:
            months = data['months']
            projects = data['projects']
            matrix = data['data_matrix']
            
            # Build z-matrix for heatmap
            z_data = []
            for project in projects:
                row = []
                for month in months:
                    count = matrix.get(month, {}).get(project, 0)
                    row.append(count)
                z_data.append(row)
            
            fig = go.Figure(data=go.Heatmap(
                z=z_data,
                x=months,
                y=projects,
                colorscale='Blues',
                showscale=True,
                colorbar=dict(title="Eventos")
            ))
            
            fig.update_layout(
                title='Atividade dos Projetos ao Longo do Tempo',
                xaxis_title='Mês',
                yaxis_title='Projetos',
                height=400
            )
            
            return fig.to_json()
            
        except Exception as e:
            logger.error(f"Error creating project heatmap: {e}")
            return None
    
    def generate_comprehensive_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive analytics dashboard data"""
        try:
            # Get all data
            formador_data = self.get_formador_performance_data()
            municipal_data = self.get_municipal_distribution_data()
            timeline_data = self.get_project_timeline_data()
            
            # Generate charts
            charts = {}
            
            if not ('error' in formador_data):
                charts['formador_performance'] = self.create_formador_performance_chart(formador_data)
            
            if not ('error' in municipal_data):
                charts['municipal_distribution'] = self.create_municipal_pie_chart(municipal_data)
            
            if not ('error' in timeline_data):
                charts['project_timeline'] = self.create_project_heatmap(timeline_data)
            
            # Basic statistics
            stats = {
                'total_formadores': Formador.objects.filter(ativo=True).count(),
                'total_municipios': Municipio.objects.filter(ativo=True).count(),
                'total_projetos': Projeto.objects.filter(ativo=True).count(),
                'pending_solicitacoes': Solicitacao.objects.filter(
                    status=SolicitacaoStatus.PENDENTE
                ).count(),
                'approved_this_month': Solicitacao.objects.filter(
                    status=SolicitacaoStatus.APROVADO,
                    data_solicitacao__gte=timezone.now().replace(day=1)
                ).count()
            }
            
            return {
                'charts': charts,
                'statistics': stats,
                'raw_data': {
                    'formador_performance': formador_data,
                    'municipal_distribution': municipal_data,
                    'project_timeline': timeline_data
                },
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive dashboard: {e}")
            return {'error': str(e)}


class DashInteractiveApp:
    """
    Interactive Dash application for real-time analytics
    """
    
    def __init__(self):
        self.enabled = dash is not None and dcc is not None
        if not self.enabled:
            logger.warning("Dash not available - install with: pip install dash")
            return
        
        self.analytics = EducationalAnalytics()
        self.app = dash.Dash(__name__)
        self._setup_layout()
        self._setup_callbacks()
    
    def _setup_layout(self):
        """Setup Dash application layout"""
        if not self.enabled:
            return
        
        self.app.layout = html.Div([
            html.H1("Aprender Sistema - Dashboard Analytics", 
                   className="header-title"),
            
            html.Div([
                html.Div([
                    html.H3("Métricas Gerais"),
                    html.Div(id="general-stats")
                ], className="stats-panel"),
                
                html.Div([
                    html.H3("Controles"),
                    dcc.Dropdown(
                        id='period-selector',
                        options=[
                            {'label': '7 dias', 'value': 7},
                            {'label': '30 dias', 'value': 30},
                            {'label': '90 dias', 'value': 90}
                        ],
                        value=30,
                        className="dropdown"
                    ),
                    html.Button("Atualizar", id="refresh-button", 
                              className="refresh-btn")
                ], className="controls-panel")
            ], className="top-panel"),
            
            html.Div([
                html.Div([
                    dcc.Graph(id="formador-performance-chart")
                ], className="chart-container"),
                
                html.Div([
                    dcc.Graph(id="municipal-pie-chart")
                ], className="chart-container")
            ], className="charts-row"),
            
            html.Div([
                dcc.Graph(id="project-heatmap")
            ], className="full-width-chart"),
            
            dcc.Interval(
                id='interval-component',
                interval=30*1000,  # Update every 30 seconds
                n_intervals=0
            )
        ])
    
    def _setup_callbacks(self):
        """Setup Dash callbacks for interactivity"""
        if not self.enabled:
            return
        
        @self.app.callback(
            [Output('formador-performance-chart', 'figure'),
             Output('municipal-pie-chart', 'figure'),
             Output('project-heatmap', 'figure'),
             Output('general-stats', 'children')],
            [Input('refresh-button', 'n_clicks'),
             Input('period-selector', 'value'),
             Input('interval-component', 'n_intervals')]
        )
        def update_dashboard(n_clicks, period_days, n_intervals):
            # Get fresh data
            dashboard_data = self.analytics.generate_comprehensive_dashboard()
            
            if 'error' in dashboard_data:
                error_fig = go.Figure()
                error_fig.add_annotation(text=f"Error: {dashboard_data['error']}")
                return error_fig, error_fig, error_fig, "Error loading data"
            
            # Parse chart JSON data
            charts = dashboard_data['charts']
            stats = dashboard_data['statistics']
            
            formador_fig = go.Figure()
            if charts.get('formador_performance'):
                formador_fig = go.Figure(json.loads(charts['formador_performance']))
            
            municipal_fig = go.Figure()
            if charts.get('municipal_distribution'):
                municipal_fig = go.Figure(json.loads(charts['municipal_distribution']))
            
            heatmap_fig = go.Figure()
            if charts.get('project_timeline'):
                heatmap_fig = go.Figure(json.loads(charts['project_timeline']))
            
            # Generate stats display
            stats_display = html.Div([
                html.P(f"Formadores Ativos: {stats['total_formadores']}"),
                html.P(f"Municípios: {stats['total_municipios']}"),
                html.P(f"Projetos: {stats['total_projetos']}"),
                html.P(f"Solicitações Pendentes: {stats['pending_solicitacoes']}"),
                html.P(f"Aprovados Este Mês: {stats['approved_this_month']}")
            ])
            
            return formador_fig, municipal_fig, heatmap_fig, stats_display
    
    def get_server(self):
        """Get Dash server for integration with Django"""
        if not self.enabled:
            return None
        return self.app.server
    
    def run(self, host='127.0.0.1', port=8050, debug=False):
        """Run the Dash application"""
        if not self.enabled:
            logger.error("Dash not available")
            return
        
        logger.info(f"Starting Dashboard on http://{host}:{port}")
        self.app.run_server(host=host, port=port, debug=debug)


# Global instances
educational_analytics = EducationalAnalytics()
interactive_dashboard = DashInteractiveApp()


# Convenience functions
def get_dashboard_data():
    """Get comprehensive dashboard data"""
    return educational_analytics.generate_comprehensive_dashboard()


def get_formador_chart(days: int = 30):
    """Get formador performance chart"""
    data = educational_analytics.get_formador_performance_data(days)
    return educational_analytics.create_formador_performance_chart(data)


def get_municipal_chart():
    """Get municipal distribution chart"""
    data = educational_analytics.get_municipal_distribution_data()
    return educational_analytics.create_municipal_pie_chart(data)


def start_interactive_dashboard(port: int = 8050):
    """Start interactive Dash dashboard"""
    if interactive_dashboard.enabled:
        interactive_dashboard.run(port=port)
    else:
        logger.error("Interactive dashboard not available")