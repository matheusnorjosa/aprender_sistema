"""
Views para atualizações em tempo real do mapa
"""
import json
import time
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.core.cache import cache
from datetime import datetime, timedelta

from core.models import Municipio, Solicitacao, Projeto, SolicitacaoStatus


class MapaRealtimeAPIView(View):
    """
    API Server-Sent Events para atualizações em tempo real do mapa
    """
    
    def get(self, request):
        """
        Retorna um stream de Server-Sent Events com atualizações do mapa
        Apenas quando há mudanças reais, não faz polling constante
        """
        def event_stream():
            # Enviar heartbeat inicial
            yield f"data: {json.dumps({'type': 'connected', 'timestamp': timezone.now().isoformat()})}\n\n"
            
            # Usar cache para detectar mudanças
            last_cache_key = 'mapa_last_update'
            last_update = cache.get(last_cache_key)
            
            if not last_update:
                # Primeira vez, definir timestamp atual
                cache.set(last_cache_key, timezone.now().isoformat(), timeout=3600)
                yield f"data: {json.dumps({'type': 'initialized', 'timestamp': timezone.now().isoformat()})}\n\n"
            
            # Manter conexão viva com heartbeat a cada 30 segundos
            heartbeat_count = 0
            while True:
                try:
                    # Verificar se houve mudanças no cache
                    current_update = cache.get(last_cache_key)
                    
                    if current_update and current_update != last_update:
                        # Houve mudança! Buscar dados atualizados
                        novas_solicitacoes = (
                            Solicitacao.objects
                            .filter(
                                status__in=[
                                    SolicitacaoStatus.APROVADO,
                                    SolicitacaoStatus.PRE_AGENDA,
                                ]
                            )
                            .select_related('municipio', 'projeto')
                            .values(
                                'municipio__nome',
                                'municipio__uf',
                                'projeto__nome',
                                'data_solicitacao'
                            )
                            .order_by('-data_solicitacao')[:10]  # Últimas 10
                        )
                        
                        if novas_solicitacoes.exists():
                            # Processar novas solicitações
                            estados_afetados = set()
                            municipios_afetados = []
                            
                            for sol in novas_solicitacoes:
                                uf = sol['municipio__uf']
                                municipio_nome = sol['municipio__nome']
                                projeto_nome = sol['projeto__nome']
                                
                                estados_afetados.add(uf)
                                municipios_afetados.append({
                                    'uf': uf,
                                    'municipio': municipio_nome,
                                    'projeto': projeto_nome,
                                    'data': sol['data_solicitacao'].isoformat()
                                })
                            
                            # Enviar evento de atualização
                            event_data = {
                                'type': 'mapa_update',
                                'timestamp': timezone.now().isoformat(),
                                'estados_afetados': list(estados_afetados),
                                'municipios_afetados': municipios_afetados,
                                'message': f'Novos projetos adicionados em {len(estados_afetados)} estado(s)'
                            }
                            
                            yield f"data: {json.dumps(event_data)}\n\n"
                            
                            # Atualizar timestamp
                            last_update = current_update
                    
                    # Heartbeat a cada 30 segundos para manter conexão viva
                    heartbeat_count += 1
                    if heartbeat_count >= 6:  # 6 * 5s = 30s
                        yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': timezone.now().isoformat()})}\n\n"
                        heartbeat_count = 0
                    
                    # Aguardar 5 segundos
                    time.sleep(5)
                    
                except Exception as e:
                    # Enviar evento de erro
                    error_data = {
                        'type': 'error',
                        'timestamp': timezone.now().isoformat(),
                        'message': f'Erro no stream: {str(e)}'
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
                    time.sleep(10)  # Aguardar mais tempo em caso de erro
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Headers'] = 'Cache-Control'
        
        return response


class MapaStatusAPIView(View):
    """
    API para verificar status de atualizações do mapa
    """
    
    def get(self, request):
        try:
            # Verificar se há solicitações recentes (últimas 24 horas)
            data_limite = datetime.now() - timedelta(hours=24)
            
            solicitacoes_recentes = (
                Solicitacao.objects
                .filter(
                    data_solicitacao__gte=data_limite,
                    status__in=[
                        SolicitacaoStatus.APROVADO,
                        SolicitacaoStatus.PRE_AGENDA,
                    ]
                )
                .select_related('municipio')
                .values('municipio__uf')
                .distinct()
                .count()
            )
            
            # Verificar estados com novos projetos
            estados_com_novos_projetos = (
                Solicitacao.objects
                .filter(
                    data_solicitacao__gte=data_limite,
                    status__in=[
                        SolicitacaoStatus.APROVADO,
                        SolicitacaoStatus.PRE_AGENDA,
                    ]
                )
                .select_related('municipio')
                .values('municipio__uf')
                .distinct()
            )
            
            estados_afetados = [item['municipio__uf'] for item in estados_com_novos_projetos]
            
            return JsonResponse({
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'solicitacoes_recentes': solicitacoes_recentes,
                'estados_afetados': estados_afetados,
                'tem_atualizacoes': len(estados_afetados) > 0
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)


class MapaWebhookView(View):
    """
    Webhook para ser chamado quando uma nova solicitação é criada/aprovada
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            municipio_id = data.get('municipio_id')
            projeto_id = data.get('projeto_id')
            acao = data.get('acao')  # 'criada', 'aprovada', 'reprovada'
            
            if not municipio_id or not acao:
                return JsonResponse({
                    'success': False,
                    'error': 'municipio_id e acao são obrigatórios'
                }, status=400)
            
            # Buscar dados do município
            try:
                municipio = Municipio.objects.get(id=municipio_id)
                projeto = Projeto.objects.get(id=projeto_id) if projeto_id else None
            except (Municipio.DoesNotExist, Projeto.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Município ou projeto não encontrado'
                }, status=404)
            
            # Invalidar cache do mapa
            cache.delete('mapa_dados_brasil')
            cache.delete('mapa_estatisticas')
            
            # Retornar dados para atualização do mapa
            return JsonResponse({
                'success': True,
                'timestamp': timezone.now().isoformat(),
                'municipio': {
                    'nome': municipio.nome,
                    'uf': municipio.uf
                },
                'projeto': {
                    'nome': projeto.nome if projeto else None
                },
                'acao': acao,
                'message': f'Município {municipio.nome}/{municipio.uf} atualizado'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'JSON inválido'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
