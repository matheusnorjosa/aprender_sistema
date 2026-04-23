"""
Epic 1 RBAC Refactor — rename labels + descriptions + categorias de
PermissaoFuncional para forma capability-oriented.

Zero mudança de comportamento:
- Codenames permanecem (rename de codename é Epic 4)
- Associações group↔permission permanecem
- Apenas texto user-visible muda

Idempotente via `update_or_create` — seguro para re-run.

Ver master-plan §3.2, §3.4 e v2/docs/plans/rbac-refactor/epic-1-labels.md.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportMissingParameterType=false

from __future__ import annotations

from django.db import migrations

# Dados espelham FUNCTIONAL_PERMISSIONS_SEED pós-Epic 1. Manter sincronizado
# com apps/core/services/functional_permissions_seed.py.
LABEL_UPDATES: tuple[tuple[str, str, str, str], ...] = (
    # (codename, label, description, category)
    (
        "pode_aprovar_superintendencia",
        "Aprovar solicitações",
        "Aprovar ou reprovar solicitações pendentes.",
        "solicitacao",
    ),
    (
        "pode_aprovar_gerente_superintendencia",
        "Aprovar solicitações em lote",
        "Aprovar múltiplas solicitações em uma operação.",
        "solicitacao",
    ),
    (
        "pode_gerenciar_superintendencia_only",
        "Executar operações restritas",
        "Operações destrutivas (exclusões críticas).",
        "solicitacao",
    ),
    (
        "pode_criar_solicitacao_coord_dat",
        "Criar solicitações de evento",
        "Submeter novas solicitações ao fluxo de aprovação.",
        "solicitacao",
    ),
    (
        "pode_importar_controle_super",
        "Importar planilhas e dados",
        "Carregar dados em massa via CSV/XLSX.",
        "importacao",
    ),
    (
        "pode_operar_dat",
        "Administrar cadastros",
        "Gerenciar cadastros e configurações administrativas.",
        "cadastros_administrativos",
    ),
    (
        "pode_acessar_dashboard_compras",
        "Visualizar dashboard de compras",
        "Acesso ao painel de indicadores de compras.",
        "dashboard",
    ),
    (
        "pode_operar_dat_exclusivo",
        "Administrar compras e materiais",
        "Operações administrativas restritas sobre compras e materiais.",
        "cadastros_administrativos",
    ),
    (
        "pode_operar_controle_dat",
        "Operar pré-agenda e relatórios",
        "Pré-agenda, relatórios gerenciais e publicações operacionais.",
        "operacao",
    ),
    (
        "pode_operar_controle",
        "Executar rotinas operacionais",
        "Imports, workflow diário e conferências.",
        "operacao",
    ),
    (
        "pode_operar_gerencia",
        "Exercer supervisão gerencial",
        "Atuação gerencial e supervisão de equipe.",
        "supervisao",
    ),
    (
        "pode_acessar_dashboard_overview",
        "Visualizar dashboard geral",
        "Painel executivo de visão geral.",
        "dashboard",
    ),
    (
        "pode_acessar_map_metrics",
        "Visualizar métricas geográficas",
        "Dashboards com distribuição por região.",
        "dashboard",
    ),
    (
        "pode_editar_como_owner_ou_privilegiado",
        "Editar solicitações próprias ou privilegiadas",
        "Editar solicitações que você criou ou com privilégio.",
        "solicitacao",
    ),
)


# Estado pré-Epic 1 — usado pelo `reverse_func` se alguém precisar reverter.
LABEL_UPDATES_REVERSE: tuple[tuple[str, str, str, str], ...] = (
    (
        "pode_aprovar_superintendencia",
        "Aprovar/Reprovar (Superintendencia)",
        "Permite aprovar ou reprovar solicitacoes pendentes.",
        "solicitacao",
    ),
    (
        "pode_aprovar_gerente_superintendencia",
        "Aprovar em lote (Gerente da Superintendencia)",
        "Permite aprovar varias solicitacoes de uma vez.",
        "solicitacao",
    ),
    (
        "pode_gerenciar_superintendencia_only",
        "Operacao exclusiva da Superintendencia",
        "Permite executar operacoes restritas, como exclusoes criticas.",
        "solicitacao",
    ),
    (
        "pode_criar_solicitacao_coord_dat",
        "Criar solicitacao (Coordenacao/DAT)",
        "Permite criar novas solicitacoes no sistema.",
        "solicitacao",
    ),
    (
        "pode_importar_controle_super",
        "Importacao (Controle/Superintendencia)",
        "Permite importar planilhas e controlar dados do sistema.",
        "importacao",
    ),
    (
        "pode_operar_dat",
        "Operacao DAT",
        "Permite gerenciar cadastros e configuracoes do DAT.",
        "admin_dat",
    ),
    (
        "pode_acessar_dashboard_compras",
        "Dashboard de Compras",
        "Permite acesso ao dashboard de compras.",
        "dashboard",
    ),
    (
        "pode_operar_dat_exclusivo",
        "Operacao DAT (exclusiva)",
        "Permite acesso a funcionalidades exclusivas do DAT.",
        "admin_dat",
    ),
    (
        "pode_operar_controle_dat",
        "Operacao compartilhada (Controle/DAT)",
        "Permite operacoes compartilhadas entre Controle e DAT.",
        "operacao",
    ),
    (
        "pode_operar_controle",
        "Operacao Controle",
        "Permite operacoes exclusivas do setor Controle.",
        "operacao",
    ),
    (
        "pode_operar_gerencia",
        "Operacao Gerencial",
        "Permite atuacao gerencial e supervisao operacional.",
        "gerencia",
    ),
    (
        "pode_acessar_dashboard_overview",
        "Dashboard Overview",
        "Permite acesso ao dashboard geral.",
        "dashboard",
    ),
    (
        "pode_acessar_map_metrics",
        "Map Metrics",
        "Permite acesso a metricas geograficas.",
        "dashboard",
    ),
    (
        "pode_editar_como_owner_ou_privilegiado",
        "Owner ou privilegiado",
        "Permite editar solicitacoes proprias ou de outros usuarios.",
        "solicitacao",
    ),
)


def _apply_updates(updates, PermissaoFuncional) -> None:
    for codename, label, description, category in updates:
        PermissaoFuncional.objects.filter(codename=codename).update(
            label=label,
            description=description,
            category=category,
        )


def forward(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    _apply_updates(LABEL_UPDATES, PermissaoFuncional)


def reverse(apps, schema_editor) -> None:
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    _apply_updates(LABEL_UPDATES_REVERSE, PermissaoFuncional)


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0072_importjob"),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
