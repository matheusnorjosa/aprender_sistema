"""
Seed idempotente de permissoes funcionais (RBAC configuravel).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group
from django.db import transaction

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.models import PermissaoFuncional

# União canônica de todos os grupos RBAC base (setor + função). SSOT em
# apps.core.constants. Mesma lista usada pelo command dev_tools `seed_rbac`.
BASE_GROUP_NAMES: tuple[str, ...] = tuple(SETOR_GROUPS + [f for f in FUNCAO_GROUPS if f not in SETOR_GROUPS])


def ensure_base_groups() -> int:
    """
    Garante a existência de TODOS os grupos RBAC base (setor + função).

    Idempotente. Necessário em ambientes sem as migrations de seed RunPython
    (ex.: `pytest --no-migrations`), onde nenhuma migration cria os grupos.
    `seed_functional_permissions(assign_default_groups=True)` só cria os grupos
    que têm capability atribuída (7 dos 18); este helper cobre os demais
    (setores sem capability, Formador, Assistente Administrativo). Retorna a
    quantidade de grupos criados nesta chamada.
    """
    created = 0
    for name in BASE_GROUP_NAMES:
        _, was_created = Group.objects.get_or_create(name=name)
        if was_created:
            created += 1
    return created


@dataclass(frozen=True)
class FunctionalPermissionSeed:
    codename: str
    label: str
    description: str
    category: str
    group_names: tuple[str, ...]


# Seed canônico pós-Issue 1.4 (Epic 1 RBAC Access Policy Realignment, 2026-04-24).
# Codenames em `verb_noun` inglês conforme convenção NIST/Django/GitLab.
# Labels e descriptions capability-oriented (sem nome de setor).
# Atribuições alinhadas à intent confirmada pelo stakeholder:
#   - DAT: módulo administrativo (cadastros, importação, compras DAT)
#   - Controle: operações diárias (controle, pre-agenda, gestão availability)
#   - Diretoria: dashboards executivos
#   - Superintendência: aprovações e operações restritas
#   - Funções (Gerente, Coordenador, Apoio Coord): solicitações + availability
#   - Formador: nenhuma perm (acessa só /meus-eventos via IsAuthenticated)
# Ver v2/docs/RBAC_NAMING.md §1, §2 e §3.4 para regras vigentes.
FUNCTIONAL_PERMISSIONS_SEED: tuple[FunctionalPermissionSeed, ...] = (
    FunctionalPermissionSeed(
        codename="approve_solicitation",
        label="Aprovar solicitações",
        description="Aprovar ou reprovar solicitações pendentes.",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="approve_solicitation_batch",
        label="Aprovar solicitações em lote",
        description="Aprovar múltiplas solicitações em uma operação.",
        category="solicitacao",
        group_names=("Gerente", "Superintendência"),
    ),
    FunctionalPermissionSeed(
        codename="execute_restricted_operations",
        label="Executar operações restritas",
        description="Operações destrutivas (exclusões críticas).",
        category="solicitacao",
        group_names=("Superintendência",),
    ),
    FunctionalPermissionSeed(
        codename="create_solicitation",
        label="Criar solicitações de evento",
        description="Submeter novas solicitações ao fluxo de aprovação.",
        category="solicitacao",
        group_names=("Coordenador", "Apoio de Coordenação", "Gerente"),
    ),
    FunctionalPermissionSeed(
        codename="import_spreadsheet",
        label="Importar planilhas e dados",
        description="Carregar dados em massa via CSV/XLSX.",
        category="importacao",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="manage_admin_registries",
        label="Administrar cadastros",
        description="Gerenciar cadastros e configurações administrativas.",
        category="cadastros_administrativos",
        group_names=("DAT",),
    ),
    FunctionalPermissionSeed(
        codename="view_compras_dashboard",
        label="Visualizar dashboard de compras",
        description="Acesso ao painel de indicadores de compras.",
        category="dashboard",
        group_names=("Diretoria",),
    ),
    FunctionalPermissionSeed(
        codename="manage_purchases_and_materials",
        label="Administrar compras e materiais",
        description="Operações administrativas restritas sobre compras e materiais.",
        category="cadastros_administrativos",
        group_names=("DAT", "Controle"),
    ),
    FunctionalPermissionSeed(
        codename="operate_preagenda",
        label="Operar pré-agenda e relatórios",
        description="Pré-agenda, relatórios gerenciais e publicações operacionais.",
        category="operacao",
        group_names=("Controle",),
    ),
    FunctionalPermissionSeed(
        codename="run_daily_operations",
        label="Executar rotinas operacionais",
        description="Imports, workflow diário e conferências.",
        category="operacao",
        group_names=("Controle",),
    ),
    FunctionalPermissionSeed(
        codename="supervise_operations",
        label="Exercer supervisão gerencial",
        description="Atuação gerencial e supervisão de equipe.",
        category="supervisao",
        group_names=("Diretoria",),
    ),
    FunctionalPermissionSeed(
        codename="view_overview_dashboard",
        label="Visualizar dashboard geral",
        description="Painel executivo de visão geral.",
        category="dashboard",
        group_names=("Diretoria",),
    ),
    FunctionalPermissionSeed(
        codename="view_map_metrics",
        label="Visualizar métricas geográficas",
        description="Dashboards com distribuição por região.",
        category="dashboard",
        group_names=("Diretoria",),
    ),
    FunctionalPermissionSeed(
        codename="edit_solicitation_as_owner_or_privileged",
        label="Editar solicitações próprias ou privilegiadas",
        description="Editar solicitações que você criou ou com privilégio.",
        category="solicitacao",
        group_names=("Gerente", "Coordenador", "Apoio de Coordenação"),
    ),
    FunctionalPermissionSeed(
        codename="manage_internal_actions",
        label="Administrar ações internas",
        description=(
            "CRUD de templates de ações, ciclos, instâncias e notificações "
            "internas. Feature em desenvolvimento — capability sem grupos "
            "atribuídos por padrão (apenas superuser bypassa por ora). Quando "
            "a feature for liberada, atribuir via admin UI ao papel correto."
        ),
        category="cadastros_administrativos",
        group_names=(),
    ),
    FunctionalPermissionSeed(
        codename="view_all_availability",
        label="Visualizar todas as disponibilidades",
        description=(
            "Acesso transversal à grade mensal completa e bloqueios de qualquer "
            "usuário, sem restrição por escopo. Atribuída apenas a papéis com "
            "alcance organizacional amplo (operação cross-setor e suporte/"
            "validação cross-setor). Papéis restritos caem em verificação de "
            "escopo por vínculo via EquipeGerencia (autorização por dado, não "
            "por feature)."
        ),
        category="operacao",
        group_names=("Controle", "DAT"),
    ),
)


def _validate_seed() -> None:
    # Epic 4.3 (2026-04-24): dual-write terminado, apenas os 15 `verb_noun`.
    # Onda 1 C3 (2026-04-27): +1 capability `manage_internal_actions` (zero
    # grupos atribuídos por seed; só superuser bypassa). Total: 16.
    if len(FUNCTIONAL_PERMISSIONS_SEED) != 16:
        raise ValueError("Seed de permissoes funcionais deve conter exatamente 16 itens.")

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
