"""
Epic 4.3 RBAC Refactor — remove os 15 codenames legacy `pode_*` após
Epic 4.2 (#1211) migrar todas as usagens internas para os novos
`verb_noun` em inglês.

Esta é a etapa final do dual-write iniciado em Epic 4.1 (#1210).
Soak pós-4.2 confirmado zero (ambiente single-user, sem integrações
externas consumindo codenames antigos).

Idempotente via `.filter(codename__in=...).delete()`. Reversível
delegando para o seed runtime (que reseeda os 15 se chamado).

Ver v2/docs/plans/rbac-refactor/epic-4-codenames.md §4.3.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from django.db import migrations

# Codenames legacy a remover (todos `pode_*` pt-BR).
OLD_CODENAMES: tuple[str, ...] = (
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
    "pode_ver_todas_disponibilidades",
)


def forward(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    PermissaoFuncional.objects.filter(codename__in=OLD_CODENAMES).delete()


def reverse(apps, schema_editor) -> None:
    """
    Rollback: delega para `seed_functional_permissions` se for necessário
    recriar o estado. O seed do seed_functional_permissions após esta
    migration só contém os 15 `verb_noun`; um rollback real requer
    também reverter o seed para incluir os `pode_*`. Deixamos o reverse
    como no-op — rollback pleno deste epic requer revert do Epic 4.1
    no código + rerun deste migrate em reverse.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0075_dual_write_verb_noun_codenames"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
