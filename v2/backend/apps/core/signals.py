# pyright: reportAttributeAccessIssue=false, reportArgumentType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

"""
Core Signals — Auto-invalidação de cache

Signals:
- post_save(Config): Invalida cache quando Config é salvo

Uso:
    # Automático! Nenhuma ação necessária, basta salvar o Config:
    Config.objects.create(key="availability", value={"TRAVEL_BUFFER_MINUTES": 90})
    # → Cache cfg:v1:availability invalidado automaticamente

Registro:
    - Registrado em apps/core/apps.py no método ready()
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from apps.core.models import (
    AvailabilityBlock,
    Config,
    Municipio,
    Participation,
    PermissaoFuncional,
    Projeto,
    Solicitacao,
    TipoEvento,
)
from apps.core.services.config_service import bust_cfg
from apps.core.services.rbac_permissions import (
    invalidate_group_functional_permissions_cache,
)
from apps.core.utils.cache_utils import invalidate_availability_cache, invalidate_static_cache


@receiver(post_save, sender=Config)
def _cfg_invalidate(
    sender: type[Config], instance: Config, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache quando Config é salvo.

    Args:
        sender: Model class (Config)
        instance: Instância do Config salvo
        **kwargs: Argumentos extras do signal

    Side effects:
        - Chama bust_cfg(instance.key) para invalidar cache
    """
    bust_cfg(instance.key)


# ================================================================
# CP3: Cache Invalidation for Availability Checks
# ================================================================


@receiver([post_save, post_delete], sender=Solicitacao)
def _invalidate_cache_on_solicitacao_change(
    sender: type[Solicitacao], instance: Solicitacao, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de availability ao modificar Solicitacao.

    ASQ-007: Scoped invalidation — only bumps version for the affected user.
    """
    invalidate_availability_cache(usuario_id=getattr(instance, "usuario_id", None))


@receiver([post_save, post_delete], sender=AvailabilityBlock)
def _invalidate_cache_on_block_change(
    sender: type[AvailabilityBlock], instance: AvailabilityBlock, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de availability ao modificar AvailabilityBlock.

    ASQ-007: Scoped invalidation — only bumps version for the affected user.
    """
    invalidate_availability_cache(usuario_id=getattr(instance, "usuario_id", None))


@receiver([post_save, post_delete], sender=Participation)
def _invalidate_cache_on_participation_change(
    sender: type[Participation], instance: Participation, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de availability quando um usuário entra/sai de um evento como
    participante (Participation).

    #1556: sem este receiver, alocar um formador como participante (e não como
    criador da Solicitacao) deixava o cache dele (``avail_ver:<id>``) obsoleto —
    o caminho cacheado (check_conflicts / grade mensal) podia dizer "livre" para
    quem acabou de ser alocado.

    Convidados externos (``usuario_id=None`` + ``guest_email``) não têm
    disponibilidade; pular evita um bump GLOBAL indevido, já que
    ``invalidate_availability_cache(None)`` invalidaria o cache de TODOS.

    NOTA: ``bulk_create`` não dispara ``post_save`` — os call-sites que usam
    bulk (perform_update em views_solicitacao.py) invalidam explicitamente.
    """
    usuario_id = getattr(instance, "usuario_id", None)
    if usuario_id is not None:
        invalidate_availability_cache(usuario_id=usuario_id)


# ================================================================
# CP3: Cache Invalidation for Static Endpoints
# ================================================================


@receiver([post_save, post_delete], sender=Municipio)
def _invalidate_cache_on_municipio_change(
    sender: type[Municipio], instance: Municipio, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar Municipio.

    Args:
        sender: Model class (Municipio)
        instance: Instância do Municipio modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("Municipio")


@receiver([post_save, post_delete], sender=Projeto)
def _invalidate_cache_on_projeto_change(
    sender: type[Projeto], instance: Projeto, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar Projeto.

    Args:
        sender: Model class (Projeto)
        instance: Instância do Projeto modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("Projeto")


@receiver([post_save, post_delete], sender=TipoEvento)
def _invalidate_cache_on_tipo_evento_change(
    sender: type[TipoEvento], instance: TipoEvento, **kwargs: Any
) -> None:  # pyright: ignore[reportUnusedFunction]
    """
    Invalida cache de endpoints estáticos ao modificar TipoEvento.

    Args:
        sender: Model class (TipoEvento)
        instance: Instância do TipoEvento modificado
        **kwargs: Argumentos extras do signal

    Side effects:
        - Invalida cache de endpoints estáticos
    """
    invalidate_static_cache("TipoEvento")


# ================================================================
# Group × Capability changes — cache bust (auditoria movida p/ #1672)
# ================================================================
#
# Decisão D17: atribuição Group × Capability é admin-driven e AUDITADA.
# Toda mudança em `PermissaoFuncional.groups` (Admin, REST, shell, import)
# precisa: (1) invalidar o cache funcional dos usuários afetados;
# (2) registrar AuditLog `GROUP_CAPABILITY_CHANGED`.
#
# (2) NÃO é mais feito aqui. Um signal não tem acesso ao ator nem ao escopo
# transacional do request — foi por isso que existia o buffer global
# `_PENDING_GROUP_CAP_DELTAS`, que só persistia quando o Admin chamava
# `flush_group_capability_audit`; qualquer outro caminho (REST/shell/import)
# perdia o registro em silêncio (#1672). A auditoria passou para o serviço
# transacional `apps.core.services.audit`, chamado no call-site com
# before/after e ator explícitos.
#
# Aqui fica só o cache bust — barato, imediato e independente de ator
# (impacta `/api/me/policies/` em outros requests).


@receiver(m2m_changed, sender=PermissaoFuncional.groups.through)
def _on_permissao_funcional_groups_changed(  # pyright: ignore[reportUnusedFunction]
    sender: type[Any],
    instance: Any,
    action: str,
    reverse: bool,
    pk_set: set[int] | None,
    **kwargs: Any,
) -> None:
    """
    Invalida o cache funcional dos grupos afetados quando
    `PermissaoFuncional.groups` muda.

    Reverse mode (`group.permissoes_funcionais.{add,remove,clear}`): instance
    é o `Group` — o grupo afetado é ele mesmo. Forward (`perm.groups.{...}`):
    instance é a `PermissaoFuncional` e os grupos afetados vêm de `pk_set`
    (ou snapshot dos atuais em `pre_clear`, antes da remoção).
    """
    if action not in {"pre_clear", "post_add", "post_remove"}:
        return

    if reverse:
        affected_group_ids = {int(instance.pk)}
    elif action == "pre_clear":
        affected_group_ids = set(instance.groups.values_list("pk", flat=True))
    else:
        affected_group_ids = set(pk_set or set())

    if affected_group_ids:
        invalidate_group_functional_permissions_cache(affected_group_ids)
