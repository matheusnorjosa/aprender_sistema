"""
Django MCP Tools - Ferramentas para Interação AI
===============================================

Define as ferramentas MCP que expõem os models Django para interação
com agentes AI via Model Context Protocol.

Autor: Claude Code
Data: Janeiro 2025
"""

from typing import Dict, Any, List, Optional
from django.db.models import Q
from django.contrib.auth import get_user_model

from mcp_server.query_tool import ModelQueryToolset, QueryTool
from mcp_server.djangomcp import MCPToolset
from core.models import (
    Formador, Municipio, Projeto, TipoEvento,
    Solicitacao, SolicitacaoStatus, Aprovacao,
    DisponibilidadeFormadores, LogAuditoria,
    Setor, Deslocamento
)

User = get_user_model()


class FormadorQueryTool(ModelQueryToolset):
    """
    Ferramenta MCP para consultar formadores
    Permite que AI agents consultem dados de formadores com filtros
    """
    model = Formador
    
    def get_queryset(self):
        """Retorna queryset otimizado com relacionamentos"""
        return (
            super()
            .get_queryset()
            .select_related('usuario', 'usuario__municipio')
            .filter(ativo=True)
        )
    
    def get_description(self):
        return "Consulta formadores ativos do sistema com informações de usuário e localização"


class MunicipioQueryTool(ModelQueryToolset):
    """Ferramenta MCP para consultar municípios"""
    model = Municipio
    
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True).order_by('nome')
    
    def get_description(self):
        return "Consulta municípios ativos onde o sistema opera"


class ProjetoQueryTool(ModelQueryToolset):
    """Ferramenta MCP para consultar projetos"""
    model = Projeto
    
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('setor')
            .filter(ativo=True)
            .order_by('nome')
        )
    
    def get_description(self):
        return "Consulta projetos ativos do sistema organizados por setor"


class SolicitacaoQueryTool(ModelQueryToolset):
    """Ferramenta MCP para consultar solicitações de eventos"""
    model = Solicitacao
    
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                'solicitante', 
                'projeto', 
                'municipio', 
                'tipo_evento'
            )
            .prefetch_related('formadores_solicitados')
            .order_by('-data_criacao')
        )
    
    def get_description(self):
        return "Consulta solicitações de eventos com relacionamentos completos"


class SolicitacoesPendentesTool(QueryTool):
    """Ferramenta específica para obter solicitações pendentes de aprovação"""
    
    def get_name(self):
        return "solicitacoes_pendentes"
    
    def get_description(self):
        return "Retorna solicitações pendentes de aprovação pela superintendência"
    
    def execute(self, **kwargs):
        solicitacoes = (
            Solicitacao.objects
            .filter(status=SolicitacaoStatus.PENDENTE)
            .select_related('solicitante', 'projeto', 'municipio', 'tipo_evento')
            .prefetch_related('formadores_solicitados')
            .order_by('-data_criacao')
        )
        
        result = []
        for sol in solicitacoes:
            result.append({
                'id': str(sol.id),
                'titulo': sol.titulo,
                'solicitante': sol.solicitante.get_full_name(),
                'projeto': sol.projeto.nome,
                'municipio': sol.municipio.nome,
                'tipo_evento': sol.tipo_evento.nome,
                'data_inicio': sol.data_inicio.isoformat(),
                'data_fim': sol.data_fim.isoformat(),
                'formadores_solicitados': [
                    f.usuario.get_full_name() for f in sol.formadores_solicitados.all()
                ],
                'data_criacao': sol.data_criacao.isoformat(),
                'observacoes': sol.observacoes or ''
            })
        
        return {
            'total': len(result),
            'solicitacoes': result
        }


class DisponibilidadeFormadorTool(QueryTool):
    """Ferramenta para consultar disponibilidade de formadores"""
    
    def get_name(self):
        return "disponibilidade_formadores"
    
    def get_description(self):
        return "Consulta disponibilidade de formadores por período"
    
    def execute(self, formador_id=None, data_inicio=None, data_fim=None, **kwargs):
        from datetime import datetime, date
        
        # Construir filtros
        filters = Q()
        
        if formador_id:
            filters &= Q(formador_id=formador_id)
        
        if data_inicio:
            if isinstance(data_inicio, str):
                data_inicio = datetime.fromisoformat(data_inicio).date()
            filters &= Q(data__gte=data_inicio)
            
        if data_fim:
            if isinstance(data_fim, str):
                data_fim = datetime.fromisoformat(data_fim).date()
            filters &= Q(data__lte=data_fim)
        
        disponibilidades = (
            DisponibilidadeFormadores.objects
            .filter(filters)
            .select_related('formador__usuario')
            .order_by('formador__usuario__first_name', 'data')
        )
        
        result = []
        for disp in disponibilidades:
            result.append({
                'formador': disp.formador.usuario.get_full_name(),
                'formador_id': str(disp.formador.id),
                'data': disp.data.isoformat(),
                'periodo': disp.periodo,
                'disponivel': disp.disponivel,
                'codigo': disp.codigo,
                'observacoes': disp.observacoes or ''
            })
        
        return {
            'total': len(result),
            'disponibilidades': result
        }


class RelatorioEventosTool(QueryTool):
    """Ferramenta para gerar relatórios de eventos"""
    
    def get_name(self):
        return "relatorio_eventos"
    
    def get_description(self):
        return "Gera relatórios estatísticos sobre eventos e solicitações"
    
    def execute(self, periodo_dias=30, **kwargs):
        from datetime import datetime, timedelta
        from django.db.models import Count, Q
        
        data_limite = datetime.now() - timedelta(days=periodo_dias)
        
        # Estatísticas por status
        stats_status = (
            Solicitacao.objects
            .filter(data_criacao__gte=data_limite)
            .values('status')
            .annotate(total=Count('id'))
            .order_by('status')
        )
        
        # Estatísticas por projeto
        stats_projeto = (
            Solicitacao.objects
            .filter(data_criacao__gte=data_limite)
            .select_related('projeto')
            .values('projeto__nome')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        
        # Estatísticas por município
        stats_municipio = (
            Solicitacao.objects
            .filter(data_criacao__gte=data_limite)
            .select_related('municipio')
            .values('municipio__nome')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        
        # Formadores mais solicitados
        formadores_solicitados = (
            Solicitacao.objects
            .filter(data_criacao__gte=data_limite)
            .prefetch_related('formadores_solicitados__usuario')
            .values('formadores_solicitados__usuario__first_name')
            .annotate(total=Count('id'))
            .order_by('-total')[:10]
        )
        
        return {
            'periodo_dias': periodo_dias,
            'data_limite': data_limite.isoformat(),
            'estatisticas': {
                'por_status': list(stats_status),
                'por_projeto': list(stats_projeto),
                'por_municipio': list(stats_municipio),
                'formadores_mais_solicitados': list(formadores_solicitados)
            }
        }


class LogAuditoriaTool(ModelQueryToolset):
    """Ferramenta para consultar logs de auditoria"""
    model = LogAuditoria
    
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related('usuario')
            .order_by('-timestamp')[:100]  # Limitar aos últimos 100 registros
        )
    
    def get_description(self):
        return "Consulta logs de auditoria do sistema (últimos 100 registros)"


# Lista de todas as ferramentas MCP para registro manual
ALL_MCP_TOOLSETS = [
    FormadorQueryTool,
    MunicipioQueryTool,
    ProjetoQueryTool,
    SolicitacaoQueryTool,
    LogAuditoriaTool,
]

ALL_MCP_TOOLS = [
    SolicitacoesPendentesTool,
    DisponibilidadeFormadorTool,
    RelatorioEventosTool,
]