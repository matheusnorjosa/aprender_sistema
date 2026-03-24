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


FUNCTIONAL_PERMISSIONS_SEED: tuple[FunctionalPermissionSeed, ...] = (
    FunctionalPermissionSeed(
        codename="pode_aprovar_superintendencia",
        label="Aprovar/Reprovar (Superintendencia)",
        description="Permite operacoes de aprovacao/reprovacao por usuarios privilegiados.",
        category="solicitacao",
        group_names=("Superintendência", "DAT"),
    ),
    FunctionalPermissionSeed(
        codename="pode_aprovar_gerente_superintendencia",
        label="Aprovar em lote (Gerente da Superintendencia)",
        description="Permissao base para regra composta de gerente da Superintendencia.",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="pode_gerenciar_superintendencia_only",
        label="Operacao exclusiva da Superintendencia",
        description="Usada em operacoes restritas (ex.: deletes criticos).",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="pode_criar_solicitacao_coord_dat",
        label="Criar solicitacao (Coordenacao/DAT)",
        description="Permite criacao de solicitacoes por Coordenador, Apoio e DAT.",
        category="solicitacao",
        group_names=("Coordenador", "Apoio de Coordenação", "DAT"),
    ),
    FunctionalPermissionSeed(
        codename="pode_importar_controle_super",
        label="Importacao (Controle/Superintendencia)",
        description="Permite operacoes de importacao e controle de dados.",
        category="importacao",
        group_names=("Controle", "Superintendência"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_dat",
        label="Operacao DAT",
        description="Permite operacoes administrativas do DAT.",
        category="admin_dat",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_dashboard_compras",
        label="Dashboard de Compras",
        description="Permite acesso ao dashboard de compras.",
        category="dashboard",
        group_names=("DAT", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_dat_exclusivo",
        label="Operacao DAT (exclusiva)",
        description="Permissao para a classe IsDAT.",
        category="admin_dat",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_controle_dat",
        label="Operacao compartilhada (Controle/DAT)",
        description="Permite operacoes compartilhadas entre Controle, DAT e Superintendencia.",
        category="operacao",
        group_names=("Controle", "DAT", "Superintendência"),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_controle",
        label="Operacao Controle",
        description="Permissao de operacoes exclusivas do grupo Controle.",
        category="operacao",
        group_names=("Controle",),
    ),
    FunctionalPermissionSeed(
        codename="pode_operar_gerencia",
        label="Operacao Gerencial",
        description="Permite operacoes para Gerencia, Superintendencia e Diretoria.",
        category="gerencia",
        group_names=("Gerência", "Superintendência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_dashboard_overview",
        label="Dashboard Overview",
        description="Permite acesso ao dashboard geral.",
        category="dashboard",
        group_names=("Superintendência", "Gerência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_acessar_map_metrics",
        label="Map Metrics",
        description="Permite acesso a metricas geograficas.",
        category="dashboard",
        group_names=("Controle", "DAT", "Superintendência", "Gerência", "Diretoria"),
    ),
    FunctionalPermissionSeed(
        codename="pode_editar_como_owner_ou_privilegiado",
        label="Owner ou privilegiado",
        description="Permissao base para regra owner-or-privileged.",
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
