"""
Signals para atualizações automáticas do mapa
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone

from core.models import Solicitacao, SolicitacaoStatus


@receiver(post_save, sender=Solicitacao)
def on_solicitacao_saved(sender, instance, created, **kwargs):
    """
    Signal disparado quando uma solicitação é salva
    """
    # Só processar se o status for relevante para o mapa
    if instance.status in [
        SolicitacaoStatus.APROVADO,
        SolicitacaoStatus.PRE_AGENDA,
    ]:
        # Invalidar cache do mapa
        cache.delete('mapa_dados_brasil')
        cache.delete('mapa_estatisticas')
        
        # Marcar que houve mudança para o tempo real
        cache.set('mapa_last_update', timezone.now().isoformat(), timeout=3600)
        
        # Log da atualização
        print(f"🗺️ Mapa atualizado: Nova solicitação em {instance.municipio.nome}/{instance.municipio.uf}")


@receiver(post_delete, sender=Solicitacao)
def on_solicitacao_deleted(sender, instance, **kwargs):
    """
    Signal disparado quando uma solicitação é deletada
    """
    # Invalidar cache do mapa
    cache.delete('mapa_dados_brasil')
    cache.delete('mapa_estatisticas')
    
    # Marcar que houve mudança para o tempo real
    cache.set('mapa_last_update', timezone.now().isoformat(), timeout=3600)
    
    # Log da atualização
    print(f"🗺️ Mapa atualizado: Solicitação removida de {instance.municipio.nome}/{instance.municipio.uf}")


# Função para ser chamada manualmente quando necessário
def invalidate_mapa_cache():
    """
    Função para invalidar cache do mapa manualmente
    """
    cache.delete('mapa_dados_brasil')
    cache.delete('mapa_estatisticas')
    print("🗺️ Cache do mapa invalidado manualmente")
