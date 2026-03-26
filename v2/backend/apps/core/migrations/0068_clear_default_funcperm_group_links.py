"""
Remove vínculos automáticos entre permissões funcionais de sistema e grupos.

Objetivo:
- garantir baseline sem permissões pré-concedidas;
- manter concessão de acesso somente via Admin DAT.
"""

from __future__ import annotations

from django.db import migrations

SYSTEM_PERMISSION_CODENAMES = [
    "pode_aprovar_superintendencia",
    "pode_aprovar_gerente_superintendencia",
    "pode_gerenciar_superintendencia_only",
    "pode_criar_solicitacao_coord_dat",
    "pode_importar_controle_super",
    "pode_operar_dat",
    "pode_acessar_dashboard_compras",
    "pode_operar_dat_exclusivo",
    "pode_operar_controle_dat",
    "pode_operar_controle",
    "pode_operar_gerencia",
    "pode_acessar_dashboard_overview",
    "pode_acessar_map_metrics",
    "pode_editar_como_owner_ou_privilegiado",
]


def clear_default_links(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    through = PermissaoFuncional.groups.through
    perm_ids = list(
        PermissaoFuncional.objects.filter(codename__in=SYSTEM_PERMISSION_CODENAMES).values_list("id", flat=True)
    )
    if not perm_ids:
        return
    through.objects.filter(permissaofuncional_id__in=perm_ids).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0066_data_integrity_indexes_on_delete"),
    ]

    operations = [
        migrations.RunPython(clear_default_links, migrations.RunPython.noop),
    ]
