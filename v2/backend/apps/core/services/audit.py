# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

"""
Servico central de auditoria transacional (#1672).

Ponto UNICO de emissao de `AuditLog`. Por padrao adia a gravacao para
`transaction.on_commit`, de modo que a trilha reflita exatamente o que foi
commitado — nada de trilha-fantasma se a transacao der rollback, e (o bug que
motivou o issue) nada perdido quando a mudanca de privilegio NAO vem do Django
Admin (shell, script, REST, import).

Substitui o buffer global `_PENDING_GROUP_CAP_DELTAS` de `signals.py`, que so
persistia quando o Admin chamava `flush_group_capability_audit`. Agora o
before/after e o ator sao capturados no proprio call-site (mesmo modelo que
`sync_members` ja usa) e emitidos aqui.

Semantica de `on_commit`:
- Fora de qualquer transacao (autocommit): o callback roda IMEDIATAMENTE.
- Dentro de um `atomic()`: roda apos o commit do bloco mais externo. Se o bloco
  der rollback, o AuditLog nao e criado.
- Em teste `django_db` (transacao externa que sempre da rollback), use o fixture
  `django_capture_on_commit_callbacks(execute=True)` do pytest-django para
  executar os callbacks e observar os registros.
"""

from __future__ import annotations

from typing import Any, Iterable

from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.models import AuditLog, PermissaoFuncional

# Sentinela para distinguir "nao passei usuario_id" de "passei usuario_id=None".
_UNSET: Any = object()


def _actor_id(actor: Any) -> int | None:
    """ID do ator, ou None para anonimo/sistema.

    Aceita `Usuario`, `None` e `AnonymousUser`. Anonimo tem
    `is_authenticated=False` -> None. Sistema (shell/script sem ator) passa
    `actor=None` -> None.
    """
    if actor is None:
        return None
    if not getattr(actor, "is_authenticated", False):
        return None
    return getattr(actor, "id", None)


def _group_names(ids: Iterable[int]) -> list[str]:
    """Nomes de grupos (ordenados) a partir de um iteravel de pks."""
    id_list = list(ids)
    if not id_list:
        return []
    return list(Group.objects.filter(pk__in=id_list).order_by("name").values_list("name", flat=True))


def registrar_auditoria(
    *,
    actor: Any,
    action: str,
    model_name: str | None = None,
    details: dict[str, Any] | None = None,
    imediato: bool = False,
    usuario_id: Any = _UNSET,
) -> None:
    """Emite um `AuditLog` de forma transacional.

    Por padrao (`imediato=False`) adia a criacao para `transaction.on_commit`.
    Passe `imediato=True` para criar sincronicamente (ex.: fora de transacao,
    quando se quer garantir o insert na hora).

    `details` e materializado por valor (copia rasa) no momento da chamada: o
    call-site deve montar o snapshot before/after ANTES de chamar. O insert em
    si e a unica parte adiada.

    `usuario_id` (FK do ator) e derivado de `actor` por padrao. Passe explicito
    quando o ator pode nao existir no momento do commit — ex.: auto-exclusao de
    usuario, onde a FK precisa ser None mesmo com o ator preservado em `details`.
    """
    resolved_id = _actor_id(actor) if usuario_id is _UNSET else usuario_id
    payload = {
        "usuario_id": resolved_id,
        "action": action,
        "model_name": model_name,
        "details": dict(details or {}),
    }

    def _emit() -> None:
        AuditLog.objects.create(**payload)

    if imediato:
        _emit()
    else:
        transaction.on_commit(_emit)


def auditar_group_capability_change(
    *,
    actor: Any,
    capability: PermissaoFuncional,
    before_group_ids: Iterable[int],
    after_group_ids: Iterable[int],
    imediato: bool = False,
) -> bool:
    """Auditoria de mudanca nos GRUPOS de UMA capability.

    Path `perm.groups.set(...)` (Django Admin `filter_horizontal`, shell). O
    call-site captura o snapshot dos group_ids ANTES e DEPOIS; aqui comparamos
    e emitimos UM `GROUP_CAPABILITY_CHANGED` se houve delta liquido.

    Mantem o contrato de `details` legado (actor_user_id, capability_id,
    capability_codename, added_groups, removed_groups, groups_after) consumido
    por `test_pr16` e pelo serializer de auditoria.

    Retorna True se registrou, False se no-op (sem delta).
    """
    before = set(before_group_ids)
    after = set(after_group_ids)
    added = after - before
    removed = before - after
    if not added and not removed:
        return False

    registrar_auditoria(
        actor=actor,
        action=AuditLog.Action.GROUP_CAPABILITY_CHANGED,
        model_name="PermissaoFuncional",
        details={
            "actor_user_id": _actor_id(actor),
            "capability_id": capability.pk,
            "capability_codename": capability.codename,
            "added_groups": _group_names(added),
            "removed_groups": _group_names(removed),
            "groups_after": _group_names(after),
        },
        imediato=imediato,
    )
    return True


def auditar_group_capabilities_set(
    *,
    actor: Any,
    group: Group,
    before_cap_ids: Iterable[int],
    after_cap_ids: Iterable[int],
    imediato: bool = False,
) -> int:
    """Auditoria quando o SET de capabilities de UM grupo muda (REST).

    Path `group.permissoes_funcionais.set(...)` (GroupSerializer create/update).
    Este e' o caminho que hoje PERDE o registro: o buffer acumulava mas ninguem
    fazia flush fora do Admin. Emite um `GROUP_CAPABILITY_CHANGED` por capability
    afetada, mantendo o contrato per-capability do path do Admin.

    Deve ser chamado APOS o `.set()` (usa o estado atual de `cap.groups` para
    `groups_after`). Retorna o numero de capabilities auditadas.
    """
    before = set(before_cap_ids)
    after = set(after_cap_ids)
    added_caps = after - before
    removed_caps = before - after
    affected = added_caps | removed_caps
    if not affected:
        return 0

    count = 0
    for cap in PermissaoFuncional.objects.filter(pk__in=affected):
        gained = cap.pk in added_caps
        registrar_auditoria(
            actor=actor,
            action=AuditLog.Action.GROUP_CAPABILITY_CHANGED,
            model_name="PermissaoFuncional",
            details={
                "actor_user_id": _actor_id(actor),
                "capability_id": cap.pk,
                "capability_codename": cap.codename,
                "added_groups": [group.name] if gained else [],
                "removed_groups": [] if gained else [group.name],
                "groups_after": _group_names(cap.groups.values_list("pk", flat=True)),
                "via": "group_serializer",
            },
            imediato=imediato,
        )
        count += 1
    return count


def auditar_assign_groups(
    *,
    actor: Any,
    target_user: Any,
    before_group_ids: Iterable[int],
    after_group_ids: Iterable[int],
    imediato: bool = False,
) -> bool:
    """Auditoria de mudanca de MEMBERSHIP de um usuario (`user.groups.set`).

    Path `assign_groups` (view) e UsuarioAdminSerializer.create/update. Compara
    before/after e emite `ASSIGN_GROUPS` se houve delta liquido. Retorna True se
    registrou, False se no-op.
    """
    before = set(before_group_ids)
    after = set(after_group_ids)
    added = after - before
    removed = before - after
    if not added and not removed:
        return False

    registrar_auditoria(
        actor=actor,
        action=AuditLog.Action.ASSIGN_GROUPS,
        model_name="Usuario",
        details={
            "actor_user_id": _actor_id(actor),
            "target_user_id": target_user.pk,
            "target_username": getattr(target_user, "username", None),
            "added_groups": _group_names(added),
            "removed_groups": _group_names(removed),
            "groups_after": _group_names(after),
        },
        imediato=imediato,
    )
    return True


def auditar_reset_senha(
    *,
    actor: Any,
    target_user: Any,
    contexto: str = "update",
    imediato: bool = False,
) -> None:
    """Auditoria de senha definida/redefinida por um ADMIN para OUTRO usuario.

    A troca self-service (`/api/me/change-password/`) ja audita `CHANGE_PASSWORD`
    no proprio endpoint — aqui e o caso do #1672: admin/DAT define a senha de um
    terceiro (serializer create/update). NUNCA inclui a senha nos `details`.
    """
    registrar_auditoria(
        actor=actor,
        action=AuditLog.Action.RESET_PASSWORD,
        model_name="Usuario",
        details={
            "actor_user_id": _actor_id(actor),
            "target_user_id": target_user.pk,
            "target_username": getattr(target_user, "username", None),
            "contexto": contexto,
        },
        imediato=imediato,
    )


def auditar_user_delete(
    *,
    actor: Any,
    target_user: Any,
    imediato: bool = False,
) -> None:
    """Auditoria de exclusao de usuario.

    Deve ser chamado ANTES de `target_user.delete()` (le pk/username enquanto
    existem — os `details` sao materializados na hora da chamada). Auto-exclusao
    e tratada aqui: a FK (`usuario_id`) vira None para nao referenciar a linha
    que sera removida, mas o `actor_user_id` fica preservado em `details`.
    """
    actor_id = _actor_id(actor)
    self_delete = actor_id is not None and actor_id == target_user.pk
    registrar_auditoria(
        actor=actor,
        usuario_id=None if self_delete else _UNSET,
        action=AuditLog.Action.USER_DELETE,
        model_name="Usuario",
        details={
            "actor_user_id": actor_id,
            "target_user_id": target_user.pk,
            "target_username": getattr(target_user, "username", None),
            "target_is_superuser": bool(getattr(target_user, "is_superuser", False)),
        },
        imediato=imediato,
    )
