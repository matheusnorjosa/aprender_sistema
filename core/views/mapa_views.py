"""
Views para o mapa interativo com dados reais do banco
ATUALIZADO: Usa Services centralizados e imports unificados
"""

# IMPORT ÚNICO - Single Source of Truth
from .base import *


class MapaDadosAPIView(BaseAPIView):
    """
    API para fornecer dados do mapa baseados no banco de dados real
    """
    
    def get(self, request):
        try:
            # Cache por 5 minutos
            cache_key = 'mapa_dados_brasil'
            dados = cache.get(cache_key)
            
            if not dados:
                dados = self._buscar_dados_mapa()
                cache.set(cache_key, dados, 300)  # 5 minutos
            
            return JsonResponse(dados, safe=False)
            
        except Exception as e:
            return JsonResponse({
                'error': f'Erro ao buscar dados: {str(e)}'
            }, status=500)
    
    def _buscar_dados_mapa(self):
        """
        Busca dados reais do banco para o mapa
        """
        # Buscar municípios com solicitações aprovadas usando query otimizada
        municipios_com_projetos = (
            get_optimized_solicitacao_queryset()
            .filter(
                status__in=[
                    SolicitacaoStatus.APROVADO,
                    SolicitacaoStatus.PRE_AGENDA,
                ]
            )
            .values(
                'municipio__nome',
                'municipio__uf',
                'projeto__nome'
            )
            .annotate(
                total_solicitacoes=Count('id'),
                projetos_distintos=Count('projeto', distinct=True)
            )
            .order_by('municipio__uf', 'municipio__nome')
        )
        
        # Agrupar por estado
        estados_data = {}
        
        for item in municipios_com_projetos:
            uf = item['municipio__uf']
            municipio_nome = item['municipio__nome']
            projeto_nome = item['projeto__nome']
            total_solicitacoes = item['total_solicitacoes']
            
            if uf not in estados_data:
                estados_data[uf] = {
                    'uf': uf,
                    'total_projetos': 0,
                    'total_solicitacoes': 0,
                    'municipios': {}
                }
            
            if municipio_nome not in estados_data[uf]['municipios']:
                estados_data[uf]['municipios'][municipio_nome] = {
                    'nome': municipio_nome,
                    'projetos': [],
                    'total_solicitacoes': 0
                }
            
            # Adicionar projeto se não existir
            if projeto_nome not in [p['nome'] for p in estados_data[uf]['municipios'][municipio_nome]['projetos']]:
                estados_data[uf]['municipios'][municipio_nome]['projetos'].append({
                    'nome': projeto_nome,
                    'solicitacoes': total_solicitacoes
                })
            
            estados_data[uf]['municipios'][municipio_nome]['total_solicitacoes'] += total_solicitacoes
            estados_data[uf]['total_solicitacoes'] += total_solicitacoes
            estados_data[uf]['total_projetos'] += 1
        
        # Converter para formato esperado pelo frontend
        resultado = {}
        
        for uf, dados_estado in estados_data.items():
            # Buscar nome do estado (assumindo que temos um mapeamento)
            nome_estado = self._get_nome_estado(uf)
            
            resultado[nome_estado] = {
                'uf': uf,
                'projects': dados_estado['total_projetos'],
                'solicitacoes': dados_estado['total_solicitacoes'],
                'municipalities': []
            }
            
            # Adicionar municípios
            for municipio_nome, dados_municipio in dados_estado['municipios'].items():
                resultado[nome_estado]['municipalities'].append({
                    'name': municipio_nome,
                    'projects': len(dados_municipio['projetos']),
                    'solicitacoes': dados_municipio['total_solicitacoes'],
                    'projetos': dados_municipio['projetos']
                })
        
        return resultado
    
    def _get_nome_estado(self, uf):
        """
        Mapeia UF para nome do estado
        """
        mapeamento = {
            'AC': 'Acre',
            'AL': 'Alagoas',
            'AP': 'Amapá',
            'AM': 'Amazonas',
            'BA': 'Bahia',
            'CE': 'Ceará',
            'DF': 'Distrito Federal',
            'ES': 'Espírito Santo',
            'GO': 'Goiás',
            'MA': 'Maranhão',
            'MT': 'Mato Grosso',
            'MS': 'Mato Grosso do Sul',
            'MG': 'Minas Gerais',
            'PA': 'Pará',
            'PB': 'Paraíba',
            'PR': 'Paraná',
            'PE': 'Pernambuco',
            'PI': 'Piauí',
            'RJ': 'Rio de Janeiro',
            'RN': 'Rio Grande do Norte',
            'RS': 'Rio Grande do Sul',
            'RO': 'Rondônia',
            'RR': 'Roraima',
            'SC': 'Santa Catarina',
            'SP': 'São Paulo',
            'SE': 'Sergipe',
            'TO': 'Tocantins'
        }
        return mapeamento.get(uf, f'Estado {uf}')


class MapaEstatisticasAPIView(BaseAPIView):
    """
    API para estatísticas gerais do mapa
    """
    
    def get(self, request):
        try:
            # Cache por 10 minutos
            cache_key = 'mapa_estatisticas'
            stats = cache.get(cache_key)
            
            if not stats:
                stats = self._calcular_estatisticas()
                cache.set(cache_key, stats, 600)  # 10 minutos
            
            return JsonResponse(stats, safe=False)
            
        except Exception as e:
            return JsonResponse({
                'error': f'Erro ao calcular estatísticas: {str(e)}'
            }, status=500)
    
    def _calcular_estatisticas(self):
        """
        Calcula estatísticas gerais para o mapa
        """
        # Usar DashboardService para estatísticas gerais como base
        stats_gerais = DashboardService.get_estatisticas_gerais()

        # Total de municípios com projetos
        municipios_com_projetos = (
            get_optimized_solicitacao_queryset()
            .filter(
                status__in=[
                    SolicitacaoStatus.APROVADO,
                    SolicitacaoStatus.PRE_AGENDA,
                ]
            )
            .values('municipio')
            .distinct()
            .count()
        )
        
        # Total de estados com projetos
        estados_com_projetos = (
            get_optimized_solicitacao_queryset()
            .filter(
                status__in=[
                    SolicitacaoStatus.APROVADO,
                    SolicitacaoStatus.PRE_AGENDA,
                ]
            )
            .values('municipio__uf')
            .distinct()
            .count()
        )
        
        # Usar dados já calculados do DashboardService
        total_solicitacoes = stats_gerais['solicitacoes_ano']  # Solicitações do ano atual
        total_projetos = stats_gerais['projetos_ativos']
        
        # Usar Service para coordenadores
        coordenadores_ativos = stats_gerais['coordenadores_total']
        
        # Usar FormadorService
        formadores_envolvidos = stats_gerais['formadores_ativos']
        
        # Solicitações por mês (últimos 12 meses) - query otimizada
        data_limite = timezone.now() - timedelta(days=365)
        solicitacoes_por_mes = (
            get_optimized_solicitacao_queryset()
            .filter(
                data_inicio__gte=data_limite,  # Usar data_inicio ao invés de data_solicitacao
                status__in=[
                    SolicitacaoStatus.APROVADO,
                    SolicitacaoStatus.PRE_AGENDA,
                ]
            )
            .annotate(mes=TruncMonth('data_inicio'))
            .values('mes')
            .annotate(total=Count('id'))
            .order_by('mes')
        )
        
        return {
            'municipios_com_projetos': municipios_com_projetos,
            'estados_com_projetos': estados_com_projetos,
            'total_solicitacoes': Solicitacao.objects.count(),  # Total geral
            'total_projetos': total_projetos,
            'coordenadores_ativos': coordenadores_ativos,
            'formadores_envolvidos': formadores_envolvidos,
            'solicitacoes_por_mes': list(solicitacoes_por_mes),
            'ultima_atualizacao': timezone.now().isoformat()
        }
