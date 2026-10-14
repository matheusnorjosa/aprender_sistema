"""
Signals de invalidação de cache para RBAC funcional.

Grupos, `PermissaoFuncional` e `Group` invalidam na hora. Vínculo (`EquipeGerencia`) e perfil
(`Gerencia`), que entram na fórmula desde o PR B (grupos ∪ pacote, ADR-020), invalidam só
depois do commit (`transaction.on_commit`): o ensaio com rollback não mexe no cache, e nenhum
request repovoa o cache com o estado velho entre a invalidação e o commit. Escrita por
`.update()`/`bulk_update` não dispara sinal: quem a fizer chama
`bump_functional_permissions_cache_version()` à mão.
"""

# pyright: reportUnusedFunction=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete
from django.dispatch import receiver

from apps.core.models import EquipeGerencia, Gerencia, PermissaoFuncional
from apps.core.services.rbac_permissions import (
    bump_functional_permissions_cache_version,
    invalidate_group_functional_permissions_cache,
    invalidate_user_functional_permissions_cache,
    invalidate_users_functional_permissions_cache,
)
from apps.core.services.rbac_service import invalidate_assignable_groups_cache

User = get_user_model()


@receiver(m2m_changed, sender=User.groups.through)
def _invalidate_funcperm_on_user_groups_change(
    sender: type[Any],
    instance: Any,
    action: str,
    reverse: bool = False,
    pk_set: set[int] | None = None,
    **kwargs: Any,
) -> None:
    # P1-3: Forward (reverse=False) → instance é o User que mudou de grupos.
    # Reverse (reverse=True) → instance é o Group (ex.: sync_members via
    # `group.user_set.set(...)`); os usuários afetados vêm em `pk_set`. O handler
    # antigo assumia sempre instance=User (`instance.id`), então no reverse
    # invalidava a chave errada e deixava a autorização revogada em cache até o
    # TTL (300s).
    if not reverse:
        if action in {"post_add", "post_remove", "post_clear"}:
            user_id = getattr(instance, "id", None)
            if isinstance(user_id, int):
                invalidate_user_functional_permissions_cache(user_id)
        return

    if action in {"post_add", "post_remove"} and pk_set:
        invalidate_users_functional_permissions_cache(pk_set)
    elif action == "pre_clear":
        # `group.user_set.clear()` não fornece pk_set → snapshot dos membros
        # atuais ANTES do clear.
        member_ids = list(instance.user_set.values_list("id", flat=True))
        if member_ids:
            invalidate_users_functional_permissions_cache(member_ids)


@receiver(m2m_changed, sender=PermissaoFuncional.groups.through)
def _invalidate_funcperm_on_permission_groups_change(
    sender: type[Any],
    instance: PermissaoFuncional,
    action: str,
    pk_set: set[int] | None = None,
    **kwargs: Any,
) -> None:
    invalidate_assignable_groups_cache()
    if action == "pre_clear":
        existing_group_ids = list(instance.groups.values_list("id", flat=True))
        invalidate_group_functional_permissions_cache(existing_group_ids)
        return

    if action in {"post_add", "post_remove"} and pk_set:
        invalidate_group_functional_permissions_cache(pk_set)


@receiver(post_save, sender=PermissaoFuncional)
def _invalidate_funcperm_on_permission_save(
    sender: type[PermissaoFuncional],
    instance: PermissaoFuncional,
    **kwargs: Any,
) -> None:
    invalidate_assignable_groups_cache()
    group_ids = list(instance.groups.values_list("id", flat=True))
    if group_ids:
        invalidate_group_functional_permissions_cache(group_ids)
    else:
        bump_functional_permissions_cache_version()


@receiver(post_delete, sender=PermissaoFuncional)
def _invalidate_funcperm_on_permission_delete(
    sender: type[PermissaoFuncional],
    instance: PermissaoFuncional,
    **kwargs: Any,
) -> None:
    # Relações M2M podem já ter sido removidas; invalidação global protege contra stale cache.
    invalidate_assignable_groups_cache()
    bump_functional_permissions_cache_version()


@receiver(post_save, sender=Group)
@receiver(post_delete, sender=Group)
def _invalidate_funcperm_on_group_change(
    sender: type[Group],
    instance: Group,
    **kwargs: Any,
) -> None:
    invalidate_assignable_groups_cache()
    group_id = getattr(instance, "id", None)
    if isinstance(group_id, int):
        invalidate_group_functional_permissions_cache([group_id])


@receiver(pre_delete, sender=Group)
def _invalidate_funcperm_on_group_delete_members(
    sender: type[Group],
    instance: Group,
    **kwargs: Any,
) -> None:
    # M05-03 (#1667): ao deletar um Group, o cascade que remove as linhas de
    # User.groups.through NÃO emite m2m_changed, então
    # _invalidate_funcperm_on_user_groups_change nunca dispara e o cache
    # POR-USUÁRIO dos ex-membros fica stale até o TTL (300s) — mantendo em cache
    # capabilities que a exclusão do grupo revogou. Snapshot dos membros ANTES do
    # cascade (mesmo padrão do pre_clear acima) e invalida o cache por-usuário.
    member_ids = list(instance.user_set.values_list("id", flat=True))
    if member_ids:
        invalidate_users_functional_permissions_cache(member_ids)


@receiver(post_save, sender=EquipeGerencia)
@receiver(post_delete, sender=EquipeGerencia)
def _invalidate_funcperm_on_vinculo_change(
    sender: type[EquipeGerencia],
    instance: EquipeGerencia,
    **kwargs: Any,
) -> None:
    # PR B (ADR-020): vínculo EQUIPE/GERENTE pode dar o pacote do perfil. Invalida sempre (o
    # papel pode ter mudado de/para um papel com pacote); só depois do commit.
    usuario_id = int(instance.usuario_id)
    transaction.on_commit(lambda: invalidate_user_functional_permissions_cache(usuario_id))


@receiver(post_save, sender=Gerencia)
def _invalidate_funcperm_on_gerencia_change(
    sender: type[Gerencia],
    instance: Gerencia,
    **kwargs: Any,
) -> None:
    # PR B (ADR-020): o perfil muda o pacote de todos os vínculos da gerência. Gerência muda
    # raramente; invalidação global (bump de versão), só depois do commit.
    transaction.on_commit(bump_functional_permissions_cache_version)
