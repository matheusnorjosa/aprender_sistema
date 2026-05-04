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
    AuditLog,
    AvailabilityBlock,
    Config,
    Municipio,
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

# PR 16 hardening RBAC (2026-05-04): consolidação por operação Admin.
# m2m_changed dispara `pre_*` e `post_*` para `add`/`remove`/`clear`.
# Acumulamos os deltas durante uma operação (request thread-local) e
# emitimos UM AuditLog ao final. Para signals fora de Admin (ex: shell ou
# fixture), o consolidador ainda funciona: cada chamada gera 1 entry.
_PENDING_GROUP_CAP_DELTAS: dict[int, dict[str, list[str]]] = {}


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
# PR 16 hardening RBAC (2026-05-04): Group × Capability changes
# ================================================================
#
# Decisão D17: pós-PR 16, atribuição Group × Capability é admin-driven.
# Toda mudança em `PermissaoFuncional.groups` (Admin, ETL interno, shell)
# precisa: (1) invalidar o cache funcional dos usuários afetados;
# (2) registrar AuditLog `GROUP_CAPABILITY_CHANGED` consolidado.
#
# Consolidação: m2m_changed dispara seis vezes por operação (`pre_*` /
# `post_*` × `add`/`remove`/`clear`). Para emitir um único AuditLog por
# operação Admin, acumulamos os group_ids adicionados/removidos em
# `_PENDING_GROUP_CAP_DELTAS[capability_id]` durante os `post_*`, e o
# consumidor (Admin `save_related` ou helper de teste) finaliza com
# `flush_group_capability_audit(actor_user)`.
#
# Cache bust roda a cada `post_*` — invalidação é cheap e não pode
# atrasar (impacta `/api/me/policies/` em outros requests).


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
    Invalida cache funcional dos grupos afetados e acumula deltas para
    o AuditLog consolidado.

    Django Admin (filter_horizontal) usa `clear() + add()` para set —
    capturamos `pre_clear` para saber os pks ANTES de remoção, depois
    `post_add` para os novos. Diferenciamos `pre_clear` (snapshot) de
    `post_remove` (delta) para não duplicar contagens.

    Reverse mode (`group.permissoes_funcionais.add(perm)`): `instance`
    é o `Group`, `pk_set` contém ids de `PermissaoFuncional`. Cobrimos
    ambos os sentidos para robustez.
    """
    if action not in {"pre_clear", "post_add", "post_remove"}:
        return

    if reverse:
        # `group.permissoes_funcionais.{add,remove,clear}(...)` — instance=Group.
        affected_perm_ids: set[int]
        affected_group_ids: set[int]
        if action == "pre_clear":
            # Snapshot dos perms vinculados antes do clear.
            affected_perm_ids = set(instance.permissoes_funcionais.values_list("pk", flat=True))
            affected_group_ids = {int(instance.pk)}
        else:
            affected_perm_ids = set(pk_set or set())
            affected_group_ids = {int(instance.pk)}
    else:
        # `perm.groups.{add,remove,clear}(...)` — instance=PermissaoFuncional.
        if action == "pre_clear":
            # Snapshot dos grupos antes do clear.
            affected_group_ids = set(instance.groups.values_list("pk", flat=True))
        else:
            affected_group_ids = set(pk_set or set())
        affected_perm_ids = {int(instance.pk)}

    # Cache bust: invalida os usuários dos grupos afetados imediatamente.
    # Para `pre_clear`, os usuários ainda têm a relação no DB — invalidação
    # cobre o flush iminente. Em `post_add`, cobre os recém-adicionados.
    if affected_group_ids:
        invalidate_group_functional_permissions_cache(affected_group_ids)

    # Acumula delta por capability — finalizado por flush_group_capability_audit.
    for perm_id in affected_perm_ids:
        slot = _PENDING_GROUP_CAP_DELTAS.setdefault(perm_id, {"added_groups": [], "removed_groups": []})
        if action == "post_add":
            for gid in affected_group_ids:
                if gid not in slot["added_groups"]:
                    slot["added_groups"].append(gid)
        elif action in {"post_remove", "pre_clear"}:
            # Tanto `clear()` quanto `remove()` removem ids — registramos
            # uma vez só. `pre_clear` snapshot já cobriu todos os atuais.
            for gid in affected_group_ids:
                if gid not in slot["removed_groups"]:
                    slot["removed_groups"].append(gid)


def flush_group_capability_audit(actor_user: Any) -> list[int]:
    """
    Emite AuditLog consolidado por capability afetada na operação corrente.

    Chamado pelo `PermissaoFuncionalAdmin.save_related` (1 entry/capability
    por operação Admin) e por testes que querem validar o registro.
    Limpa o buffer em `_PENDING_GROUP_CAP_DELTAS` ao final.

    Retorna a lista de IDs de AuditLog criados (testes asseram contra
    isso). Em operações sem deltas (ex: salvar sem mudar groups),
    retorna lista vazia.
    """
    from django.contrib.auth.models import Group

    created_ids: list[int] = []
    if not _PENDING_GROUP_CAP_DELTAS:
        return created_ids

    # Snapshot dos deltas e clear imediato para evitar dupla emissão.
    pending = dict(_PENDING_GROUP_CAP_DELTAS)
    _PENDING_GROUP_CAP_DELTAS.clear()

    actor_id = getattr(actor_user, "id", None) if actor_user else None

    for perm_id, delta in pending.items():
        added_ids = list(delta.get("added_groups", []) or [])
        removed_ids = list(delta.get("removed_groups", []) or [])

        # Django Admin (filter_horizontal) executa `clear() + add()` mesmo
        # quando o set final é igual ao inicial. O delta net (entradas que
        # mudaram de fato) é (added \ removed) e (removed \ added).
        net_added = [gid for gid in added_ids if gid not in removed_ids]
        net_removed = [gid for gid in removed_ids if gid not in added_ids]

        if not net_added and not net_removed:
            continue

        try:
            perm = PermissaoFuncional.objects.get(pk=perm_id)
        except PermissaoFuncional.DoesNotExist:
            continue

        added_names = list(Group.objects.filter(pk__in=net_added).order_by("name").values_list("name", flat=True))
        removed_names = list(Group.objects.filter(pk__in=net_removed).order_by("name").values_list("name", flat=True))

        # Snapshot final dos grupos atribuídos (após mudança).
        after_names = list(perm.groups.order_by("name").values_list("name", flat=True))

        log = AuditLog.objects.create(
            usuario_id=actor_id,
            action="GROUP_CAPABILITY_CHANGED",
            model_name="PermissaoFuncional",
            details={
                "actor_user_id": actor_id,
                "capability_id": perm_id,
                "capability_codename": perm.codename,
                "added_groups": added_names,
                "removed_groups": removed_names,
                "groups_after": after_names,
            },
        )
        created_ids.append(int(log.pk))

    return created_ids
