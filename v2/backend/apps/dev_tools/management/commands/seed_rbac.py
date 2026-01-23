"""
Seed RBAC — Criar grupos e permissões mínimas (idempotente).

Grupos criados:
- Superintendência
- Coordenador
- Apoio de Coordenação
- Formador
- Controle
- DAT
- Gerência

Permissões atribuídas por grupo conforme PR 12/N.
Atualizado em 2025-12-01: Adicionado grupo "Apoio de Coordenação".
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false
from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandParser

from apps.core.models import (
    AvailabilityBlock,
    Compra,
    Municipio,
    Projeto,
    Solicitacao,
    Usuario,
)

GROUPS = [
    "Superintendência",
    "Coordenador",
    "Apoio de Coordenação",
    "Formador",
    "Controle",
    "DAT",
    "Gerência",
]

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
            group, created = Group.objects.get_or_create(name=name)
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

        self.stdout.write(self.style.SUCCESS("RBAC seeds aplicados (idempotente)."))
