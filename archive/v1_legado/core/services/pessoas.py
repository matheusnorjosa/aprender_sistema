"""
Serviço unificado para pessoas da Superintendência
HOTFIX 06/10: Inclui formadores E coordenadores
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q

GRUPOS_SUPER = ("formador", "coordenador")


def get_pessoas_super_qs(strict_super: bool = True):
    """
    Retorna usuários ativos que pertencem aos grupos-alvo (formador + coordenador).

    Args:
        strict_super (bool):
            - True: exige setor vinculado à Superintendência
            - False: ignora setor (fallback temporário)

    Returns:
        QuerySet de Usuario filtrado por grupos e setor (se strict_super=True)

    Notas:
        - FEATURE_SUPER_FALLBACK=True: ignora filtro de setor (para backfill)
        - Após backfill completo, desativar fallback e usar strict_super=True sempre
    """
    User = get_user_model()
    base = User.objects.filter(is_active=True, groups__name__in=GRUPOS_SUPER).distinct()

    # Se fallback ativo: retorna todos (ignora setor)
    if getattr(settings, "FEATURE_SUPER_FALLBACK", False):
        return base

    # Se strict_super: filtra por setor vinculado à superintendência
    if strict_super:
        return base.filter(setor__vinculado_superintendencia=True)

    return base
