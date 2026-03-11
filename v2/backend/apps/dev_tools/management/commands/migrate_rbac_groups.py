"""
Management command para migrar usuários para nova estrutura RBAC (Setor + Função).

Uso:
    python manage.py migrate_rbac_groups --dry-run  # Preview das mudanças
    python manage.py migrate_rbac_groups            # Aplicar mudanças

Este comando:
1. Lista usuários e seus grupos atuais
2. Identifica usuários que precisam do grupo "Gerente"
3. Adiciona o grupo "Gerente" aos usuários identificados
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser

from apps.core.constants import FUNCAO_GROUPS, SETOR_GROUPS
from apps.core.models import Usuario


class Command(BaseCommand):
    help = "Migra usuários para nova estrutura RBAC (Setor + Função)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview das mudanças sem aplicar",
        )
        parser.add_argument(
            "--user",
            type=str,
            help="Migrar apenas um usuário específico (username)",
        )
        parser.add_argument(
            "--add-gerente",
            type=str,
            help="Adicionar grupo Gerente a um usuário específico (username)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run: bool = options["dry_run"]
        specific_user: str | None = options["user"]
        add_gerente_user: str | None = options["add_gerente"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY-RUN (preview) ===\n"))

        # Se --add-gerente foi especificado, adiciona grupo Gerente ao usuário
        if add_gerente_user:
            self._add_gerente_to_user(add_gerente_user, dry_run)
            return

        # Listar todos os usuários ou um específico
        if specific_user:
            users = Usuario.objects.filter(username=specific_user)
        else:
            users = Usuario.objects.filter(is_active=True).order_by("username")

        self.stdout.write(f"\nAnalisando {users.count()} usuários...\n")
        self.stdout.write("-" * 80)

        gerente_group = Group.objects.get(name="Gerente")
        users_to_update: list[tuple[Usuario, str]] = []

        for user in users:
            groups: list[str] = list(user.groups.values_list("name", flat=True))
            setores: list[str] = [g for g in groups if g in SETOR_GROUPS]
            funcoes: list[str] = [g for g in groups if g in FUNCAO_GROUPS]

            # Identificar se o usuário precisa do grupo Gerente
            # Regra: Se é superuser ou está em Gerência, provavelmente é gerente
            needs_gerente = False
            reason = ""

            if user.is_superuser:
                needs_gerente = True
                reason = "is_superuser=True"
            elif "Gerência" in setores and "Gerente" not in funcoes:
                needs_gerente = True
                reason = "Está em Gerência mas não tem função Gerente"

            self.stdout.write(
                f"\n{user.username}:\n"
                f'  Setores: {setores or "Nenhum"}\n'
                f'  Funções: {funcoes or "Nenhum"}\n'
                f"  is_superuser: {user.is_superuser}"
            )

            if needs_gerente:
                users_to_update.append((user, reason))
                self.stdout.write(self.style.WARNING(f"  → Precisa do grupo Gerente: {reason}"))

        self.stdout.write("\n" + "-" * 80)
        self.stdout.write(f"\nResumo: {len(users_to_update)} usuários precisam do grupo Gerente\n")

        if users_to_update and not dry_run:
            self.stdout.write(self.style.SUCCESS("\nAplicando mudanças...\n"))
            for user, reason in users_to_update:
                user.groups.add(gerente_group)
                self.stdout.write(f"  ✓ {user.username}: adicionado ao grupo Gerente")

            self.stdout.write(self.style.SUCCESS("\nMigração concluída!"))
        elif users_to_update:
            self.stdout.write(self.style.WARNING("\nUse sem --dry-run para aplicar as mudanças."))

    def _add_gerente_to_user(self, username: str, dry_run: bool) -> None:
        """Adiciona grupo Gerente a um usuário específico."""
        try:
            user = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Usuário "{username}" não encontrado.'))
            return

        gerente_group = Group.objects.get(name="Gerente")
        groups: list[str] = list(user.groups.values_list("name", flat=True))

        self.stdout.write(f"\nUsuário: {user.username}")
        self.stdout.write(f"Grupos atuais: {groups}")

        if "Gerente" in groups:
            self.stdout.write(self.style.SUCCESS("  → Já possui o grupo Gerente"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("  → Seria adicionado ao grupo Gerente"))
        else:
            user.groups.add(gerente_group)
            self.stdout.write(self.style.SUCCESS("  ✓ Adicionado ao grupo Gerente"))
