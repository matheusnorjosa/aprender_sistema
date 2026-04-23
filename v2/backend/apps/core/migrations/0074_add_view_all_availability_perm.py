"""
Epic 3.1 RBAC Refactor — adiciona a permissão funcional
`pode_ver_todas_disponibilidades` e atribui aos grupos Superintendência,
Controle, Gerência e Diretoria.

Substitui o padrão proibido
`user.groups.filter(name__in=["Superintendência", "Controle", ...]).exists()`
espalhado por views de availability por um check capability-oriented
canônico via `user_has_any_perm(user, "pode_ver_todas_disponibilidades")`.

Migration idempotente via `update_or_create` + `groups.set`. Reversível.

Ver v2/docs/plans/rbac-refactor/epic-3-hardcoded.md §2.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from django.db import migrations

NEW_PERM = {
    "codename": "pode_ver_todas_disponibilidades",
    "label": "Visualizar todas as disponibilidades",
    "description": "Acesso à grade mensal completa e bloqueios de qualquer usuário.",
    "category": "operacao",
}

# Grupos que recebem a nova permissão. Reflete o conjunto efetivo dos
# checks `groups.filter(name__in=[...])` que este refactor substitui.
GROUP_NAMES = ("Superintendência", "Controle", "Gerência", "Diretoria")


def forward(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    perm, _ = PermissaoFuncional.objects.update_or_create(
        codename=NEW_PERM["codename"],
        defaults={
            "label": NEW_PERM["label"],
            "description": NEW_PERM["description"],
            "category": NEW_PERM["category"],
            "is_system": True,
        },
    )

    groups = list(Group.objects.filter(name__in=GROUP_NAMES))
    if groups:
        perm.groups.add(*groups)


def reverse(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    PermissaoFuncional.objects.filter(codename=NEW_PERM["codename"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0073_rename_permission_labels"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
