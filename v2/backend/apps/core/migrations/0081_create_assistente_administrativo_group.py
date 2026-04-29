"""PR 3 hardening RBAC (2026-04-29): cria Função "Assistente Administrativo".

Contexto
--------

A regra de negócio confirmada pelo stakeholder em 2026-04-29 estende
`POST /api/solicitacoes/{id}/approve|reject/` e `batch-approve|batch-reject`
para um composite novo:

- Gerente da Superintendência (Setor `Superintendência` + Função `Gerente`)
- Assistente Administrativo do Controle (Setor `Controle` + Função
  `Assistente Administrativo`)

Esta migration cria o Django Group "Assistente Administrativo" como Função
formal em `apps.core.constants.FUNCAO_GROUPS`. A composite class
`IsAssistenteAdministrativoControle` (apps/core/rbac/permissions.py) checa
o vínculo simultâneo com "Controle".

Idempotente via `Group.objects.get_or_create`.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingParameterType=false, reportUnknownParameterType=false
from __future__ import annotations

from django.db import migrations

GROUP_NAME = "Assistente Administrativo"


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GROUP_NAME)


def backwards(apps, schema_editor):
    """Remove o group, exceto se já tiver usuários atribuídos."""
    Group = apps.get_model("auth", "Group")
    try:
        group = Group.objects.get(name=GROUP_NAME)
    except Group.DoesNotExist:
        return
    if group.user_set.exists():
        return
    group.delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0080_redistribute_view_all_availability")]
    operations = [migrations.RunPython(forwards, backwards)]
