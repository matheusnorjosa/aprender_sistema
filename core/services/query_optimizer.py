"""
Django Query Optimization Service - Sistema Aprender
Performance-optimized QuerySets with intelligent caching
"""

from typing import Dict, List, Optional, Any, QuerySet
from django.db.models import Prefetch, Q, Count, F, Case, When, IntegerField
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta

from core.models import (
    Formador, Solicitacao, Municipio, Projeto, TipoEvento, 
    Aprovacao, DisponibilidadeFormadores, LogAuditoria, Deslocamento
)
from .cache_service import cache_service, cached_property_method


class OptimizedQueryManager:
    """
    Manager for optimized database queries with caching
    """
    
    @staticmethod
    def get_formadores_optimized(ativo=True, with_stats=False):
        """
        Get formadores with optimized queries and optional statistics
        """
        cache_key = cache_service.generate_key('formadores', 'list', ativo, with_stats)
        
        def fetch_data():
            queryset = (
                Formador.objects
                .filter(ativo=ativo)
                .select_related('usuario')  # Optimize FK lookup
                .order_by('usuario__first_name', 'usuario__last_name')
            )
            
            if with_stats:
                # Add statistics annotations
                queryset = queryset.annotate(
                    total_solicitacoes=Count('solicitacao', distinct=True),
                    solicitacoes_aprovadas=Count(
                        'solicitacao',
                        filter=Q(solicitacao__status='Aprovado'),
                        distinct=True
                    ),
                    eventos_este_mes=Count(
                        'solicitacao',
                        filter=Q(
                            solicitacao__status='Aprovado',
                            solicitacao__data_inicio__month=timezone.now().month,
                            solicitacao__data_inicio__year=timezone.now().year
                        ),
                        distinct=True
                    )
                )
            
            # Convert to list of dicts for caching
            return list(queryset.values(
                'id', 'usuario__first_name', 'usuario__last_name', 
                'usuario__email', 'ativo', 'data_criacao',
                *(['total_solicitacoes', 'solicitacoes_aprovadas', 'eventos_este_mes'] if with_stats else [])
            ))
        
        return cache_service.get_or_set_json(cache_key, fetch_data, 'medium')
    
    @staticmethod
    def get_solicitacoes_dashboard(user_profile=None, status_filter=None, limit=50):
        """
        Get solicitacoes optimized for dashboard views
        """
        cache_key = cache_service.generate_key(
            'solicitacoes', 'dashboard', 
            getattr(user_profile, 'id', 'all'), 
            status_filter, limit
        )
        
        def fetch_data():
            queryset = (
                Solicitacao.objects
                .select_related(
                    'solicitante',           # User who made request
                    'projeto',               # Project
                    'municipio',             # Municipality  
                    'tipo_evento'            # Event type
                )
                .prefetch_related(
                    'formadores_solicitados',  # Many-to-many formadores
                    Prefetch(
                        'aprovacao_set',
                        queryset=Aprovacao.objects.select_related('usuario')
                    )
                )
                .order_by('-data_solicitacao')
            )
            
            # Apply filters
            if user_profile == 'coordenador':
                # Show only user's own solicitacoes if coordenador
                queryset = queryset.filter(solicitante=user_profile.user)
            
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # Add annotations for quick stats
            queryset = queryset.annotate(
                formadores_count=Count('formadores_solicitados'),
                has_conflicts=Case(
                    When(status='ConflitosDetectados', then=1),
                    default=0,
                    output_field=IntegerField()
                )
            )[:limit]
            
            # Serialize to dict for caching
            results = []
            for solicitacao in queryset:
                results.append({
                    'id': str(solicitacao.id),
                    'titulo': solicitacao.titulo,
                    'solicitante': solicitacao.solicitante.get_full_name(),
                    'projeto': solicitacao.projeto.nome,
                    'municipio': solicitacao.municipio.nome,
                    'tipo_evento': solicitacao.tipo_evento.nome,
                    'status': solicitacao.status,
                    'data_inicio': solicitacao.data_inicio.isoformat(),
                    'data_fim': solicitacao.data_fim.isoformat(),
                    'data_solicitacao': solicitacao.data_solicitacao.isoformat(),
                    'formadores_count': solicitacao.formadores_count,
                    'has_conflicts': bool(solicitacao.has_conflicts),
                    'formadores': [
                        f.usuario.get_full_name() 
                        for f in solicitacao.formadores_solicitados.all()
                    ]
                })
            
            return results
        
        return cache_service.get_or_set_json(cache_key, fetch_data, 'short')
    
    @staticmethod
    def get_availability_conflicts_optimized(formador_ids: List[str], start_date: str, end_date: str):
        """
        Optimized query for availability conflicts checking
        """
        cache_key = cache_service.generate_key(
            'conflicts', 'check', 
            '_'.join(sorted(formador_ids)), start_date, end_date
        )
        
        def fetch_data():
            from datetime import datetime
            
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            conflicts = {
                'bloqueios': [],
                'eventos_existentes': [],
                'deslocamentos': []
            }
            
            # Check availability blocks (optimized)
            bloqueios = (
                DisponibilidadeFormadores.objects
                .filter(
                    formador_id__in=formador_ids,
                    data__range=[start_dt.date(), end_dt.date()],
                    disponivel=False
                )
                .select_related('formador__usuario')
                .values(
                    'formador__usuario__first_name',
                    'formador__usuario__last_name', 
                    'data', 'tipo_bloqueio', 'observacoes'
                )
            )
            conflicts['bloqueios'] = list(bloqueios)
            
            # Check existing approved events (optimized)
            eventos_existentes = (
                Solicitacao.objects
                .filter(
                    formadores_solicitados__in=formador_ids,
                    status__in=['Aprovado', 'PreAgenda'],
                    data_inicio__lt=end_dt,
                    data_fim__gt=start_dt
                )
                .select_related('projeto', 'municipio', 'tipo_evento')
                .prefetch_related('formadores_solicitados__usuario')
                .values(
                    'titulo', 'data_inicio', 'data_fim',
                    'projeto__nome', 'municipio__nome'
                )
            )
            conflicts['eventos_existentes'] = list(eventos_existentes)
            
            # Check displacement conflicts (optimized)
            deslocamentos = (
                Deslocamento.objects
                .filter(
                    formador_id__in=formador_ids,
                    data__range=[start_dt.date(), end_dt.date()]
                )
                .select_related('formador__usuario', 'municipio_origem', 'municipio_destino')
                .values(
                    'formador__usuario__first_name',
                    'formador__usuario__last_name',
                    'data', 'municipio_origem__nome', 
                    'municipio_destino__nome', 'tempo_estimado_minutos'
                )
            )
            conflicts['deslocamentos'] = list(deslocamentos)
            
            return conflicts
        
        return cache_service.get_or_set_json(cache_key, fetch_data, 'short')
    
    @staticmethod
    def get_monthly_availability_map(ano: int, mes: int):
        """
        Optimized monthly availability map query
        """
        cache_key = cache_service.generate_key('availability_map', ano, mes)
        
        def fetch_data():
            from calendar import monthrange
            import datetime
            
            first_day = datetime.date(ano, mes, 1)
            last_day = datetime.date(ano, mes, monthrange(ano, mes)[1])
            
            # Get all formadores with their availability
            formadores = (
                Formador.objects
                .filter(ativo=True)
                .select_related('usuario')
                .prefetch_related(
                    Prefetch(
                        'disponibilidadeformadores_set',
                        queryset=DisponibilidadeFormadores.objects.filter(
                            data__range=[first_day, last_day]
                        ),
                        to_attr='month_availability'
                    ),
                    Prefetch(
                        'solicitacao_set',
                        queryset=Solicitacao.objects.filter(
                            status__in=['Aprovado', 'PreAgenda'],
                            data_inicio__month=mes,
                            data_inicio__year=ano
                        ).select_related('municipio', 'projeto'),
                        to_attr='month_events'
                    )
                )
            )
            
            availability_map = {}
            
            for formador in formadores:
                formador_data = {
                    'nome': formador.usuario.get_full_name(),
                    'email': formador.usuario.email,
                    'disponibilidade': {},
                    'eventos': []
                }
                
                # Process availability blocks
                for disp in formador.month_availability:
                    day = disp.data.day
                    formador_data['disponibilidade'][day] = {
                        'disponivel': disp.disponivel,
                        'tipo_bloqueio': disp.tipo_bloqueio,
                        'observacoes': disp.observacoes
                    }
                
                # Process events
                for evento in formador.month_events:
                    formador_data['eventos'].append({
                        'titulo': evento.titulo,
                        'data_inicio': evento.data_inicio.isoformat(),
                        'data_fim': evento.data_fim.isoformat(),
                        'municipio': evento.municipio.nome,
                        'projeto': evento.projeto.nome,
                        'status': evento.status
                    })
                
                availability_map[str(formador.id)] = formador_data
            
            return availability_map
        
        return cache_service.get_or_set_json(cache_key, fetch_data, 'medium')
    
    @staticmethod
    def get_dashboard_analytics():
        """
        Optimized analytics query for dashboards
        """
        cache_key = cache_service.generate_key('analytics', 'dashboard', 'main')
        
        def fetch_data():
            from datetime import datetime, timedelta
            
            now = datetime.now()
            thirty_days_ago = now - timedelta(days=30)
            
            # Basic counts with single query
            basic_stats = {
                'formadores_ativos': Formador.objects.filter(ativo=True).count(),
                'municipios_ativos': Municipio.objects.filter(ativo=True).count(),
                'projetos_ativos': Projeto.objects.filter(ativo=True).count(),
                'tipos_evento_ativos': TipoEvento.objects.filter(ativo=True).count()
            }
            
            # Status distribution with single query
            status_stats = dict(
                Solicitacao.objects
                .values('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            )
            
            # Recent activity with optimized query
            recent_activity = (
                Solicitacao.objects
                .filter(data_solicitacao__gte=thirty_days_ago)
                .values('projeto__nome', 'municipio__nome')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
            
            # Top formadores by events
            top_formadores = (
                Formador.objects
                .filter(ativo=True)
                .annotate(
                    eventos_count=Count(
                        'solicitacao',
                        filter=Q(solicitacao__status='Aprovado')
                    )
                )
                .filter(eventos_count__gt=0)
                .select_related('usuario')
                .order_by('-eventos_count')[:5]
                .values(
                    'usuario__first_name', 'usuario__last_name', 
                    'eventos_count'
                )
            )
            
            return {
                'basic_stats': basic_stats,
                'status_distribution': status_stats,
                'recent_activity': list(recent_activity),
                'top_formadores': list(top_formadores),
                'generated_at': now.isoformat()
            }
        
        return cache_service.get_or_set_json(cache_key, fetch_data, 'long')
    
    @staticmethod
    def invalidate_related_caches(model_name: str, obj_id: Optional[str] = None):
        """
        Invalidate related caches when data changes
        """
        patterns_to_clear = []
        
        if model_name.lower() == 'solicitacao':
            patterns_to_clear.extend([
                'solicitacoes:*',
                'dashboard:*',
                'analytics:*',
                'conflicts:*'
            ])
        elif model_name.lower() == 'formador':
            patterns_to_clear.extend([
                'formadores:*',
                'conflicts:*',
                'availability_map:*'
            ])
        elif model_name.lower() in ['municipio', 'projeto', 'tipoevento']:
            patterns_to_clear.extend([
                'dashboard:*',
                'analytics:*'
            ])
        
        for pattern in patterns_to_clear:
            cache_service.clear_pattern(pattern)


# Global instance
query_optimizer = OptimizedQueryManager()