"""Issue #1222 (Epic 1 RBAC Access Policy Realignment, 2026-04-24).

Migration data-only que realinha a atribuição de PermissaoFuncional aos
grupos conforme intent confirmada pelo stakeholder. Substitui o conjunto
completo via `groups.set(...)` — idempotente.

Mudanças vs seed anterior:
- approve_solicitation: removido DAT
- approve_solicitation_batch: adicionado Gerente
- create_solicitation: removido DAT, adicionado Gerente
- import_spreadsheet: removido Controle/Super, agora só DAT
- view_compras_dashboard: removido DAT, agora só Diretoria
- manage_purchases_and_materials: adicionado Controle
- operate_preagenda: removido DAT/Super, agora só Controle
- supervise_operations: removido Gerência/Super, agora só Diretoria
- view_overview_dashboard: removido Super/Gerência, agora só Diretoria
- view_map_metrics: removido Controle/DAT/Super/Gerência, agora só Diretoria
- edit_solicitation_as_owner_or_privileged: removido Super/DAT, agora Gerente/Coord/Apoio
- view_all_availability: removido Super/Gerência/Diretoria, adicionado Gerente/Coord/Apoio

Outros codenames (`execute_restricted_operations`, `manage_admin_registries`,
`run_daily_operations`) já estavam alinhados — set idempotente.
"""

from __future__ import annotations

from django.db import migrations

GROUP_ASSIGNMENTS: dict[str, list[str]] = {
    "approve_solicitation": ["Superintendência"],
    "approve_solicitation_batch": ["Gerente", "Superintendência"],
    "execute_restricted_operations": ["Superintendência"],
    "create_solicitation": ["Coordenador", "Apoio de Coordenação", "Gerente"],
    "import_spreadsheet": ["DAT"],
    "manage_admin_registries": ["DAT"],
    "view_compras_dashboard": ["Diretoria"],
    "manage_purchases_and_materials": ["DAT", "Controle"],
    "operate_preagenda": ["Controle"],
    "run_daily_operations": ["Controle"],
    "supervise_operations": ["Diretoria"],
    "view_overview_dashboard": ["Diretoria"],
    "view_map_metrics": ["Diretoria"],
    "edit_solicitation_as_owner_or_privileged": [
        "Gerente",
        "Coordenador",
        "Apoio de Coordenação",
    ],
    "view_all_availability": [
        "Controle",
        "Gerente",
        "Coordenador",
        "Apoio de Coordenação",
    ],
}


def forwards(apps, schema_editor):
    """Aplica as atribuições corretas via M2M set (idempotente)."""
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    Group = apps.get_model("auth", "Group")

    for codename, group_names in GROUP_ASSIGNMENTS.items():
        try:
            perm = PermissaoFuncional.objects.get(codename=codename)
        except PermissaoFuncional.DoesNotExist:
            # Codename ausente no banco — provável seed pré-Epic 1; pula
            continue
        groups = list(Group.objects.filter(name__in=group_names))
        perm.groups.set(groups)


def backwards(apps, schema_editor):
    """No-op: reverter exigiria persistir o estado anterior, e admin pode
    reajustar via /admin/grupos manualmente. Reverter em produção sem
    backup é mais perigoso do que aceitar a nova config."""
    pass


class Migration(migrations.Migration):
    dependencies = [("core", "0076_remove_old_pode_codenames")]
    operations = [migrations.RunPython(forwards, backwards)]
