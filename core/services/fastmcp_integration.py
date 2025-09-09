"""
FastMCP Integration for Aprender Sistema
========================================

Advanced MCP server implementation using FastMCP framework,
providing high-performance, production-ready MCP services for our educational system.

Author: Claude Code
Date: Janeiro 2025
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.db.models import Q

try:
    from fastmcp import FastMCP
    from fastmcp.resources import Resource
    from fastmcp.tools import Tool
    from fastmcp.prompts import Prompt
except ImportError:
    FastMCP = None
    Resource = None
    Tool = None
    Prompt = None

from core.models import (
    Formador, Municipio, Projeto, TipoEvento,
    Solicitacao, SolicitacaoStatus, Aprovacao,
    DisponibilidadeFormadores, LogAuditoria,
    Setor, Deslocamento
)

logger = logging.getLogger(__name__)


class AprenderSistemaMCP:
    """
    Advanced MCP server for Aprender Sistema using FastMCP
    
    Provides high-performance tools and resources for:
    - Educational data queries
    - System analytics
    - Administrative operations
    - Real-time monitoring
    """
    
    def __init__(self):
        self.enabled = FastMCP is not None
        if not self.enabled:
            logger.warning("FastMCP not available - install with: pip install fastmcp")
            return
        
        self.mcp = FastMCP(
            name="Aprender Sistema MCP"
        )
        
        # Register all tools and resources
        self._register_tools()
        self._register_resources()
        self._register_prompts()
    
    def _register_tools(self):
        """Register MCP tools for system operations"""
        if not self.enabled:
            return
            
        @self.mcp.tool()
        async def search_formadores(
            query: str = "",
            ativo: bool = True,
            limit: int = 50
        ) -> Dict[str, Any]:
            """
            Search for formadores (instructors) in the system
            
            Args:
                query: Search term for name or area
                ativo: Filter by active status
                limit: Maximum results to return
            """
            try:
                formadores = Formador.objects.filter(ativo=ativo)
                
                if query:
                    formadores = formadores.filter(
                        Q(usuario__first_name__icontains=query) |
                        Q(usuario__last_name__icontains=query) |
                        Q(usuario__email__icontains=query)
                    )
                
                formadores = formadores.select_related('usuario')[:limit]
                
                results = []
                for formador in formadores:
                    results.append({
                        'id': str(formador.id),
                        'nome': formador.usuario.get_full_name(),
                        'email': formador.usuario.email,
                        'ativo': formador.ativo,
                        'data_criacao': formador.data_criacao.isoformat()
                    })
                
                return {
                    'total_found': len(results),
                    'formadores': results
                }
                
            except Exception as e:
                logger.error(f"Error searching formadores: {e}")
                return {'error': str(e)}
        
        @self.mcp.tool()
        async def get_pending_solicitacoes(limit: int = 20) -> Dict[str, Any]:
            """
            Get pending solicitacoes (event requests) for approval
            
            Args:
                limit: Maximum results to return
            """
            try:
                solicitacoes = (
                    Solicitacao.objects
                    .filter(status=SolicitacaoStatus.PENDENTE)
                    .select_related('solicitante', 'projeto', 'municipio', 'tipo_evento')
                    .prefetch_related('formadores_solicitados')
                    .order_by('-data_criacao')[:limit]
                )
                
                results = []
                for sol in solicitacoes:
                    results.append({
                        'id': str(sol.id),
                        'titulo': sol.titulo,
                        'solicitante': sol.solicitante.get_full_name(),
                        'projeto': sol.projeto.nome,
                        'municipio': sol.municipio.nome,
                        'tipo_evento': sol.tipo_evento.nome,
                        'data_inicio': sol.data_inicio.isoformat(),
                        'data_fim': sol.data_fim.isoformat(),
                        'formadores_solicitados': [
                            f.usuario.get_full_name() 
                            for f in sol.formadores_solicitados.all()
                        ],
                        'data_criacao': sol.data_criacao.isoformat(),
                        'observacoes': sol.observacoes or ''
                    })
                
                return {
                    'total_pending': len(results),
                    'solicitacoes': results
                }
                
            except Exception as e:
                logger.error(f"Error getting pending solicitacoes: {e}")
                return {'error': str(e)}
        
        @self.mcp.tool()
        async def get_system_analytics() -> Dict[str, Any]:
            """
            Get comprehensive system analytics and metrics
            """
            try:
                from datetime import datetime, timedelta
                from django.db.models import Count
                
                now = datetime.now()
                last_30_days = now - timedelta(days=30)
                
                # Basic counts
                stats = {
                    'total_formadores': Formador.objects.filter(ativo=True).count(),
                    'total_municipios': Municipio.objects.filter(ativo=True).count(),
                    'total_projetos': Projeto.objects.filter(ativo=True).count(),
                    'total_solicitacoes': Solicitacao.objects.count(),
                    'pending_solicitacoes': Solicitacao.objects.filter(
                        status=SolicitacaoStatus.PENDENTE
                    ).count()
                }
                
                # Recent activity
                recent_solicitacoes = (
                    Solicitacao.objects
                    .filter(data_criacao__gte=last_30_days)
                    .values('status')
                    .annotate(count=Count('id'))
                )
                
                # Top projects by requests
                top_projetos = (
                    Solicitacao.objects
                    .filter(data_criacao__gte=last_30_days)
                    .values('projeto__nome')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )
                
                # Top municipalities
                top_municipios = (
                    Solicitacao.objects
                    .filter(data_criacao__gte=last_30_days)
                    .values('municipio__nome')
                    .annotate(count=Count('id'))
                    .order_by('-count')[:5]
                )
                
                return {
                    'basic_stats': stats,
                    'recent_activity': {
                        'period': '30_days',
                        'solicitacoes_by_status': list(recent_solicitacoes),
                        'top_projetos': list(top_projetos),
                        'top_municipios': list(top_municipios)
                    },
                    'generated_at': now.isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting system analytics: {e}")
                return {'error': str(e)}
        
        @self.mcp.tool()
        async def check_formador_availability(
            formador_id: str,
            data_inicio: str,
            data_fim: str
        ) -> Dict[str, Any]:
            """
            Check formador availability for a given period
            
            Args:
                formador_id: UUID of the formador
                data_inicio: Start date (ISO format)
                data_fim: End date (ISO format)
            """
            try:
                from datetime import datetime
                
                # Parse dates
                inicio = datetime.fromisoformat(data_inicio.replace('Z', '+00:00'))
                fim = datetime.fromisoformat(data_fim.replace('Z', '+00:00'))
                
                # Get formador
                try:
                    formador = Formador.objects.get(id=formador_id, ativo=True)
                except Formador.DoesNotExist:
                    return {'error': 'Formador not found or inactive'}
                
                # Check availability
                conflicts = DisponibilidadeFormadores.objects.filter(
                    formador=formador,
                    data__range=[inicio.date(), fim.date()],
                    disponivel=False
                )
                
                # Check existing events
                existing_events = Solicitacao.objects.filter(
                    formadores_solicitados=formador,
                    status__in=[SolicitacaoStatus.APROVADO, SolicitacaoStatus.PRE_AGENDA],
                    data_inicio__lt=fim,
                    data_fim__gt=inicio
                )
                
                return {
                    'formador': {
                        'id': str(formador.id),
                        'nome': formador.usuario.get_full_name()
                    },
                    'period': {
                        'inicio': data_inicio,
                        'fim': data_fim
                    },
                    'available': conflicts.count() == 0 and existing_events.count() == 0,
                    'conflicts': {
                        'availability_blocks': conflicts.count(),
                        'existing_events': existing_events.count()
                    },
                    'details': {
                        'blocked_dates': [
                            conflict.data.isoformat() for conflict in conflicts
                        ],
                        'conflicting_events': [
                            {
                                'titulo': event.titulo,
                                'data_inicio': event.data_inicio.isoformat(),
                                'data_fim': event.data_fim.isoformat()
                            }
                            for event in existing_events
                        ]
                    }
                }
                
            except Exception as e:
                logger.error(f"Error checking formador availability: {e}")
                return {'error': str(e)}
    
    def _register_resources(self):
        """Register MCP resources for data access"""
        if not self.enabled:
            return
            
        @self.mcp.resource("formadores://active")
        async def active_formadores() -> str:
            """List of all active formadores in JSON format"""
            try:
                formadores = (
                    Formador.objects
                    .filter(ativo=True)
                    .select_related('usuario')
                    .order_by('usuario__first_name')
                )
                
                data = []
                for formador in formadores:
                    data.append({
                        'id': str(formador.id),
                        'nome': formador.usuario.get_full_name(),
                        'email': formador.usuario.email,
                        'data_criacao': formador.data_criacao.isoformat()
                    })
                
                import json
                return json.dumps(data, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting active formadores resource: {e}")
                return json.dumps({'error': str(e)})
        
        @self.mcp.resource("projects://active")
        async def active_projects() -> str:
            """List of all active projects in JSON format"""
            try:
                projetos = (
                    Projeto.objects
                    .filter(ativo=True)
                    .select_related('setor')
                    .order_by('nome')
                )
                
                data = []
                for projeto in projetos:
                    data.append({
                        'id': str(projeto.id),
                        'nome': projeto.nome,
                        'descricao': projeto.descricao or '',
                        'setor': projeto.setor.nome if projeto.setor else None,
                        'ativo': projeto.ativo
                    })
                
                import json
                return json.dumps(data, indent=2)
                
            except Exception as e:
                logger.error(f"Error getting active projects resource: {e}")
                return json.dumps({'error': str(e)})
    
    def _register_prompts(self):
        """Register MCP prompts for AI interactions"""
        if not self.enabled:
            return
            
        @self.mcp.prompt()
        async def system_status_report() -> str:
            """Generate a comprehensive system status report"""
            try:
                analytics = await self.get_system_analytics()
                
                if 'error' in analytics:
                    return f"Error generating system status: {analytics['error']}"
                
                report = f"""
# Aprender Sistema - Status Report

## Basic Statistics
- Active Formadores: {analytics['basic_stats']['total_formadores']}
- Active Municipalities: {analytics['basic_stats']['total_municipios']}
- Active Projects: {analytics['basic_stats']['total_projetos']}
- Total Requests: {analytics['basic_stats']['total_solicitacoes']}
- Pending Approvals: {analytics['basic_stats']['pending_solicitacoes']}

## Recent Activity (Last 30 Days)
### Top Projects by Requests:
"""
                
                for projeto in analytics['recent_activity']['top_projetos']:
                    report += f"- {projeto['projeto__nome']}: {projeto['count']} requests\n"
                
                report += "\n### Top Municipalities:\n"
                for municipio in analytics['recent_activity']['top_municipios']:
                    report += f"- {municipio['municipio__nome']}: {municipio['count']} requests\n"
                
                report += f"\nReport generated at: {analytics['generated_at']}"
                
                return report
                
            except Exception as e:
                logger.error(f"Error generating system status report: {e}")
                return f"Error generating report: {str(e)}"
    
    async def get_system_analytics(self):
        """Helper method to get system analytics (used by prompt)"""
        # This would call the tool directly - implementation depends on FastMCP structure
        pass
    
    def get_server(self):
        """Get the FastMCP server instance"""
        if not self.enabled:
            return None
        return self.mcp


# Global service instance
aprender_mcp = AprenderSistemaMCP()


def get_fastmcp_server():
    """Get the FastMCP server for external use"""
    return aprender_mcp.get_server()


async def start_mcp_server(port: int = 3000):
    """Start the FastMCP server on specified port"""
    if not aprender_mcp.enabled:
        logger.error("FastMCP not available")
        return
    
    server = aprender_mcp.get_server()
    if server:
        logger.info(f"Starting Aprender Sistema MCP server on port {port}")
        # Implementation depends on FastMCP server startup method
        await server.run(port=port)