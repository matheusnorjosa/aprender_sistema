"""
Epic 4.1 RBAC Refactor — dual-write dos novos codenames `verb_noun`
em inglês.

Cria 15 novas PermissaoFuncional (uma para cada antiga `pode_*`),
copiando defaults E associações M2M de groups. Após esta migration,
`user.has_perm("pode_X")` E `user.has_perm("new_X")` retornam True
para usuários nos mesmos grupos — dual-write completo.

Após 1 semana de soak (Epic 4.3), os antigos `pode_*` serão removidos.

Idempotente via `update_or_create` + `groups.add`. Reversível: remove
apenas os codenames novos (mantém os antigos).

Ver v2/docs/plans/rbac-refactor/epic-4-codenames.md §4.1.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from django.db import migrations

# Mapeamento canônico (espelha CODENAME_MAPPING do plano + tests).
MAPPING: tuple[tuple[str, str], ...] = (
    ("pode_aprovar_superintendencia", "approve_solicitation"),
    ("pode_aprovar_gerente_superintendencia", "approve_solicitation_batch"),
    ("pode_gerenciar_superintendencia_only", "execute_restricted_operations"),
    ("pode_criar_solicitacao_coord_dat", "create_solicitation"),
    ("pode_importar_controle_super", "import_spreadsheet"),
    ("pode_operar_dat", "manage_admin_registries"),
    ("pode_acessar_dashboard_compras", "view_compras_dashboard"),
    ("pode_operar_dat_exclusivo", "manage_purchases_and_materials"),
    ("pode_operar_controle_dat", "operate_preagenda"),
    ("pode_operar_controle", "run_daily_operations"),
    ("pode_operar_gerencia", "supervise_operations"),
    ("pode_acessar_dashboard_overview", "view_overview_dashboard"),
    ("pode_acessar_map_metrics", "view_map_metrics"),
    ("pode_editar_como_owner_ou_privilegiado", "edit_solicitation_as_owner_or_privileged"),
    ("pode_ver_todas_disponibilidades", "view_all_availability"),
)


def forward(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")

    for old_codename, new_codename in MAPPING:
        try:
            old_perm = PermissaoFuncional.objects.get(codename=old_codename)
        except PermissaoFuncional.DoesNotExist:
            # Migration tolerante: se um codename antigo não existir
            # (banco anômalo), pula sem falhar. Seed runtime depois cria.
            continue

        # Idempotência: get_or_create + update dos defaults
        new_perm, _ = PermissaoFuncional.objects.update_or_create(
            codename=new_codename,
            defaults={
                "label": old_perm.label,
                "description": old_perm.description,
                "category": old_perm.category,
                "is_system": True,
            },
        )

        # Copia M2M groups (idempotente via .add — não duplica)
        new_perm.groups.add(*old_perm.groups.all())


def reverse(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    new_codenames = [new for _, new in MAPPING]
    PermissaoFuncional.objects.filter(codename__in=new_codenames).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0074_add_view_all_availability_perm"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
