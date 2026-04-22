"""
Seed RBAC — Criar grupos e permissões mínimas (idempotente).

Grupos criados: união de SETOR_GROUPS (13) + FUNCAO_GROUPS (4), conforme
apps.core.constants. Setores de projeto (Vidas, Fluir, etc.) não recebem
permissões Django CRUD — servem como marca de filtro RBAC via
EquipeGerencia. Setores administrativos (DAT, Controle, Superintendência,
Diretoria) e funções (Coordenador, Formador, Apoio, Gerente) recebem as
Django permissions em PERMS_BY_GROUP abaixo.

Atualizado em 2026-04-22: passou a usar SETOR_GROUPS + FUNCAO_GROUPS como
SSOT (antes a lista estava hardcoded com 8 entradas e divergia).
Atualizado em 2025-12-01: Adicionado grupo "Apoio de Coordenação".
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false
from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandParser

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.models import AvailabilityBlock, Compra, Municipio, Projeto, Solicitacao, Usuario
from apps.core.services.functional_permissions_seed import seed_functional_permissions

# Lista canônica completa: todos os grupos seedados (setor + função).
GROUPS: list[str] = SETOR_GROUPS + [f for f in FUNCAO_GROUPS if f not in SETOR_GROUPS]

PERMS_BY_GROUP = {
    # DAT: Admin completo em Usuario, Municipio; view+add em Solicitacao
    "DAT": [
        ("add", Usuario),
        ("change", Usuario),
        ("delete", Usuario),
        ("view", Usuario),
        ("add", Municipio),
        ("change", Municipio),
        ("delete", Municipio),
        ("view", Municipio),
        ("view", Solicitacao),
        ("add", Solicitacao),
    ],
    # Controle: Import e pré-agenda
    "Controle": [
        ("view", Municipio),
        ("view", Projeto),
        ("view", Compra),
        ("add", Compra),
        ("add", AvailabilityBlock),
        ("change", AvailabilityBlock),
        ("delete", AvailabilityBlock),
        ("view", AvailabilityBlock),
    ],
    # Superintendência: Aprovar/reprovar + read references
    "Superintendência": [
        ("view", Solicitacao),
        ("change", Solicitacao),
        ("view", Usuario),
        ("view", Municipio),
        ("view", Projeto),
    ],
    # Coordenador: Nova solicitação + read references
    "Coordenador": [
        ("add", Solicitacao),
        ("view", Solicitacao),
        ("view", Municipio),
        ("view", Projeto),
    ],
    # Apoio de Coordenação: Mesmas permissões que Coordenador + view usuários
    "Apoio de Coordenação": [
        ("add", Solicitacao),
        ("view", Solicitacao),
        ("view", Municipio),
        ("view", Projeto),
        ("view", Usuario),  # Para auxiliar coordenador
    ],
    # Formador: Bloqueio de agenda + read solicitações
    "Formador": [
        ("add", AvailabilityBlock),
        ("change", AvailabilityBlock),
        ("delete", AvailabilityBlock),
        ("view", AvailabilityBlock),
        ("view", Solicitacao),
    ],
    # Gerência: view solicitações (legacy)
    "Gerência": [("view", Solicitacao)],
    # Diretoria: view solicitações (dashboards)
    "Diretoria": [("view", Solicitacao)],
}


def perm_codename(action: str, model: Any) -> str:
    """Gera codename de permissão: <action>_<model_name>."""
    return f"{action}_{model._meta.model_name}"


class Command(BaseCommand):
    """Command para criar/atualizar grupos e permissões (idempotente)."""

    help = "Cria/atualiza grupos e permissões mínimas (idempotente)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Exibir detalhes da operação",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        verbose = opts.get("verbose", False)

        # Criar grupos
        for name in GROUPS:
            _, created = Group.objects.get_or_create(name=name)
            if verbose and created:
                self.stdout.write(f"  ✅ Grupo criado: {name}")
            elif verbose:
                self.stdout.write(f"  ✓  Grupo existente: {name}")

        # Atribuir permissões
        for group_name, items in PERMS_BY_GROUP.items():
            g = Group.objects.get(name=group_name)
            for action, model in items:
                ct = ContentType.objects.get_for_model(model)
                code = perm_codename(action, model)
                try:
                    p = Permission.objects.get(content_type=ct, codename=code)
                    g.permissions.add(p)
                    if verbose:
                        self.stdout.write(f"  ✅ Permissão atribuída: {group_name} → {code}")
                except Permission.DoesNotExist:
                    # Silencioso: permissão não existe (pode ser normal)
                    if verbose:
                        self.stdout.write(self.style.WARNING(f"  ⚠️  Permissão não encontrada: {code}"))

        fp_stats = seed_functional_permissions(verbose=verbose, assign_default_groups=False)
        if verbose:
            self.stdout.write(
                "  ✅ Permissões funcionais: created={created} updated={updated} groups_created={groups} unlinked={unlinked}".format(
                    created=fp_stats["permissions_created"],
                    updated=fp_stats["permissions_updated"],
                    groups=fp_stats["groups_created"],
                    unlinked=fp_stats["permissions_unlinked"],
                )
            )

        self.stdout.write(self.style.SUCCESS("RBAC seeds aplicados (idempotente)."))
