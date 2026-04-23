"""
Seed idempotente de permissoes funcionais (RBAC configuravel).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.models import PermissaoFuncional


@dataclass(frozen=True)
class FunctionalPermissionSeed:
    codename: str
    label: str
    description: str
    category: str
    group_names: tuple[str, ...]


# Epic 1 RBAC Refactor (2026-04-23): labels + descriptions + categorias
# reescritas em forma capability-oriented (o que a pessoa PODE FAZER),
# não identity-oriented (quem faz hoje). Codenames permanecem intactos —
# rename de codename é Epic 4. Group_names permanecem intactos — mudança
# organizacional é deferida permanentemente (ver master-plan §9.1).
FUNCTIONAL_PERMISSIONS_SEED: tuple[FunctionalPermissionSeed, ...] = (
    FunctionalPermissionSeed(
        codename="pode_aprovar_superintendencia",
        label="Aprovar solicitações",
        description="Aprovar ou reprovar solicitações pendentes.",
        category="solicitacao",
        group_names=("Superintendência", "DAT"),
    ),
    FunctionalPermissionSeed(
        codename="pode_aprovar_gerente_superintendencia",
        label="Aprovar solicitações em lote",
        description="Aprovar múltiplas solicitações em uma operação.",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="pode_gerenciar_superintendencia_only",
        label="Executar operações restritas",
        description="Operações destrutivas (exclusões críticas).",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="pode_criar_solicitacao_coord_dat",
        label="Criar solicitações de evento",
        description="Submeter novas solicitações ao fluxo de aprovação.",
        category="solicitacao",
        group_names=("Coordenador", "Apoio de Coordenação", "DAT"),
    ),
    FunctionalPermissionSeed(
        codename="pode_importar_controle_super",
        label="Importar planilhas e dados",
        description="Carregar dados em massa via CSV/XLSX.",
        category="importacao",
        group_names=("Controle", "Superintendência"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_dat",
        label="Administrar cadastros",
        description="Gerenciar cadastros e configurações administrativas.",
        category="cadastros_administrativos",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_dashboard_compras",
        label="Visualizar dashboard de compras",
        description="Acesso ao painel de indicadores de compras.",
        category="dashboard",
        group_names=("DAT", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_dat_exclusivo",
        label="Administrar compras e materiais",
        description="Operações administrativas restritas sobre compras e materiais.",
        category="cadastros_administrativos",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_controle_dat",
        label="Operar pré-agenda e relatórios",
        description="Pré-agenda, relatórios gerenciais e publicações operacionais.",
        category="operacao",
        group_names=("Controle", "DAT", "Superintendência"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_controle",
        label="Executar rotinas operacionais",
        description="Imports, workflow diário e conferências.",
        category="operacao",
        group_names=("Controle",),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_gerencia",
        label="Exercer supervisão gerencial",
        description="Atuação gerencial e supervisão de equipe.",
        category="supervisao",
        group_names=("Gerência", "Superintendência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_dashboard_overview",
        label="Visualizar dashboard geral",
        description="Painel executivo de visão geral.",
        category="dashboard",
        group_names=("Superintendência", "Gerência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_map_metrics",
        label="Visualizar métricas geográficas",
        description="Dashboards com distribuição por região.",
        category="dashboard",
        group_names=("Controle", "DAT", "Superintendência", "Gerência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_editar_como_owner_ou_privilegiado",
        label="Editar solicitações próprias ou privilegiadas",
        description="Editar solicitações que você criou ou com privilégio.",
        category="solicitacao",
        group_names=("Superintendência", "DAT"),
    ),
)


def _validate_seed() -> None:
    if len(FUNCTIONAL_PERMISSIONS_SEED) != 14:
        raise ValueError("Seed de permissoes funcionais deve conter exatamente 14 itens.")

    seen: set[str] = set()
    for item in FUNCTIONAL_PERMISSIONS_SEED:
        if item.codename in seen:
            raise ValueError(f"Codename duplicado no seed: {item.codename}")
        seen.add(item.codename)


def seed_functional_permissions(
    *,
    verbose: bool = False,
    assign_default_groups: bool = False,
) -> dict[str, int]:
    """
    Aplica seed idempotente de permissoes funcionais.

    Por padrão, não atribui permissões a grupos automaticamente.
    Para cenários de teste/migração legada, use assign_default_groups=True.
    """

    _validate_seed()

    stats = {
        "groups_created": 0,
        "permissions_created": 0,
        "permissions_updated": 0,
        "permissions_unlinked": 0,
    }

    with transaction.atomic():
        groups_by_name: dict[str, Group] = {}
        if assign_default_groups:
            for item in FUNCTIONAL_PERMISSIONS_SEED:
                for group_name in item.group_names:
                    if group_name in groups_by_name:
                        continue
                    group, created = Group.objects.get_or_create(name=group_name)
                    groups_by_name[group_name] = group
                    if created:
                        stats["groups_created"] += 1

        for item in FUNCTIONAL_PERMISSIONS_SEED:
            perm, created = PermissaoFuncional.objects.update_or_create(
                codename=item.codename,
                defaults={
                    "label": item.label,
                    "description": item.description,
                    "category": item.category,
                    "is_system": True,
                },
            )
            if created:
                stats["permissions_created"] += 1
            else:
                stats["permissions_updated"] += 1

            if assign_default_groups:
                perm.groups.set([groups_by_name[name] for name in item.group_names])
            else:
                if perm.groups.exists():
                    stats["permissions_unlinked"] += 1
                perm.groups.clear()

            if verbose:
                if assign_default_groups:
                    print(f"[seed_functional_permissions] {item.codename}: {item.group_names}")
                else:
                    print(f"[seed_functional_permissions] {item.codename}: sem vinculo automatico")

    return stats


def functional_permissions_codenames() -> tuple[str, ...]:
    return tuple(item.codename for item in FUNCTIONAL_PERMISSIONS_SEED)


def functional_permissions_seed_snapshot() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """
    Snapshot estavel para uso em testes.
    """

    return tuple((item.codename, item.group_names) for item in FUNCTIONAL_PERMISSIONS_SEED)
