# Generated manually on 2026-03-20
"""
Data migration idempotente para o baseline de 14 permissoes funcionais RBAC.

Importante:
- Nao importa modulos runtime para manter migration congelada.
- Cria grupos via get_or_create para ser autossuficiente.
"""

from __future__ import annotations

from django.db import migrations, transaction

_SEED = [
    {
        "codename": "pode_aprovar_superintendencia",
        "label": "Aprovar/Reprovar (Superintendencia)",
        "description": "Permite operacoes de aprovacao/reprovacao por usuarios privilegiados.",
        "category": "solicitacao",
        "groups": ["Superintendência", "DAT"],
    },
    {
        "codename": "pode_aprovar_gerente_superintendencia",
        "label": "Aprovar em lote (Gerente da Superintendencia)",
        "description": "Permissao base para regra composta de gerente da Superintendencia.",
        "category": "solicitacao",
        "groups": ["Superintendência"],
    },
    {
        "codename": "pode_gerenciar_superintendencia_only",
        "label": "Operacao exclusiva da Superintendencia",
        "description": "Usada em operacoes restritas (ex.: deletes criticos).",
        "category": "solicitacao",
        "groups": ["Superintendência"],
    },
    {
        "codename": "pode_criar_solicitacao_coord_dat",
        "label": "Criar solicitacao (Coordenacao/DAT)",
        "description": "Permite criacao de solicitacoes por Coordenador, Apoio e DAT.",
        "category": "solicitacao",
        "groups": ["Coordenador", "Apoio de Coordenação", "DAT"],
    },
    {
        "codename": "pode_importar_controle_super",
        "label": "Importacao (Controle/Superintendencia)",
        "description": "Permite operacoes de importacao e controle de dados.",
        "category": "importacao",
        "groups": ["Controle", "Superintendência"],
    },
    {
        "codename": "pode_operar_dat",
        "label": "Operacao DAT",
        "description": "Permite operacoes administrativas do DAT.",
        "category": "admin_dat",
        "groups": ["DAT"],
    },
    {
        "codename": "pode_acessar_dashboard_compras",
        "label": "Dashboard de Compras",
        "description": "Permite acesso ao dashboard de compras.",
        "category": "dashboard",
        "groups": ["DAT", "Diretoria"],
    },
    {
        "codename": "pode_operar_dat_exclusivo",
        "label": "Operacao DAT (exclusiva)",
        "description": "Permissao para a classe IsDAT.",
        "category": "admin_dat",
        "groups": ["DAT"],
    },
    {
        "codename": "pode_operar_controle_dat",
        "label": "Operacao compartilhada (Controle/DAT)",
        "description": "Permite operacoes compartilhadas entre Controle, DAT e Superintendencia.",
        "category": "operacao",
        "groups": ["Controle", "DAT", "Superintendência"],
    },
    {
        "codename": "pode_operar_controle",
        "label": "Operacao Controle",
        "description": "Permissao de operacoes exclusivas do grupo Controle.",
        "category": "operacao",
        "groups": ["Controle"],
    },
    {
        "codename": "pode_operar_gerencia",
        "label": "Operacao Gerencial",
        "description": "Permite operacoes para Gerencia, Superintendencia e Diretoria.",
        "category": "gerencia",
        "groups": ["Gerência", "Superintendência", "Diretoria"],
    },
    {
        "codename": "pode_acessar_dashboard_overview",
        "label": "Dashboard Overview",
        "description": "Permite acesso ao dashboard geral.",
        "category": "dashboard",
        "groups": ["Superintendência", "Gerência", "Diretoria"],
    },
    {
        "codename": "pode_acessar_map_metrics",
        "label": "Map Metrics",
        "description": "Permite acesso a metricas geograficas.",
        "category": "dashboard",
        "groups": ["Controle", "DAT", "Superintendência", "Gerência", "Diretoria"],
    },
    {
        "codename": "pode_editar_como_owner_ou_privilegiado",
        "label": "Owner ou privilegiado",
        "description": "Permissao base para regra owner-or-privileged.",
        "category": "solicitacao",
        "groups": ["Superintendência", "DAT"],
    },
]


def _validate_seed() -> None:
    if len(_SEED) != 14:
        raise RuntimeError("Seed de permissoes funcionais deve conter 14 itens.")

    seen = set()
    for item in _SEED:
        codename = item["codename"]
        if codename in seen:
            raise RuntimeError(f"Codename duplicado no seed: {codename}")
        seen.add(codename)


def seed_permissoes_funcionais(apps, schema_editor):
    _validate_seed()
    Group = apps.get_model("auth", "Group")
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")

    with transaction.atomic():
        groups_by_name = {}
        for item in _SEED:
            for group_name in item["groups"]:
                if group_name in groups_by_name:
                    continue
                group, _ = Group.objects.get_or_create(name=group_name)
                groups_by_name[group_name] = group

        for item in _SEED:
            perm, _ = PermissaoFuncional.objects.update_or_create(
                codename=item["codename"],
                defaults={
                    "label": item["label"],
                    "description": item["description"],
                    "category": item["category"],
                    "is_system": True,
                },
            )
            perm.groups.set([groups_by_name[name].pk for name in item["groups"]])


def reverse_seed_permissoes_funcionais(apps, schema_editor):
    PermissaoFuncional = apps.get_model("core", "PermissaoFuncional")
    codenames = [item["codename"] for item in _SEED]
    PermissaoFuncional.objects.filter(codename__in=codenames).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0064_permissaofuncional"),
    ]

    operations = [
        migrations.RunPython(seed_permissoes_funcionais, reverse_seed_permissoes_funcionais),
    ]
