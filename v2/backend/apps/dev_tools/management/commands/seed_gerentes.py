"""
Seed gerentes ao grupo "Gerência" e vincular a Gerencia.

Baseado em:
- Planilha Usuários.xlsx (coluna F = "Gerente", coluna G = "Gerência")
- 7 gerentes identificados, 4 faltam no banco (serão criados)

Usage:
    python manage.py seed_gerentes --dry-run  # Preview
    python manage.py seed_gerentes            # Apply

Mapping (Planilha Gerência → Database Gerencia.nome_setor):
- "Superintendência" → nome_setor="Super" (SUPERINTENDENCIA)
- "Vidas" → nome_setor="Vidas" (GERENCIA 2)
- "Fluir" → nome_setor="Fluir" (GERENCIA 3)
- "ACerta" → nome_setor="ACerta" (GERENCIA 4)
- "Brincando" → nome_setor="Brincando" (GERENCIA 5)
- "Sou da Paz" → nome_setor="Sou da Paz" (GERENCIA 6)
- "Individual" → nome_setor="Individual" (GERENCIA INDIVIDUAL)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

import pandas as pd

from apps.core.models import Gerencia, Usuario

# Managers from Usuários.xlsx (Ativos sheet, cargo="Gerente")
GERENTES = [
    {
        "first_name": "Fernanda",
        "last_name": "Ramos Lopes",
        "cpf": "00564395390",  # Pad to 11 digits
        "email": "gerencia1.projetos1@aprendereditora.com.br",
        "gerencia_setor": "Super",  # Maps to SUPERINTENDENCIA
    },
    {
        "first_name": "Gleice Anne",
        "last_name": "Lima de Sousa",
        "cpf": "76255735320",
        "email": "gerencia.projetos5@aprendereditora.com.br",
        "gerencia_setor": "Brincando",  # Maps to GERENCIA 5
    },
    {
        "first_name": "Katy",
        "last_name": "Araújo e Silva",
        "cpf": "44092717334",
        "email": "gerencia.projetos4@aprendereditora.com.br",
        "gerencia_setor": "ACerta",  # Maps to GERENCIA 4
    },
    {
        "first_name": "Maria Cristina",
        "last_name": "Meaney",
        "cpf": "12972082850",
        "email": "gerencia.projetos1@aprendereditora.com.br",
        "gerencia_setor": "Super",  # Maps to SUPERINTENDENCIA
    },
    {
        "first_name": "Maria Solange",
        "last_name": "de Almeida Cavalcante",
        "cpf": "86324020304",
        "email": "gerencia3.projetos1@aprendereditora.com.br",
        "gerencia_setor": "Super",  # Maps to SUPERINTENDENCIA
    },
    {
        "first_name": "Patrícia",
        "last_name": "Lemos de Paiva",
        "cpf": "69165246349",
        "email": "gerencia.projetos2@aprendereditora.com.br",
        "gerencia_setor": "Vidas",  # Maps to GERENCIA 2
    },
    {
        "first_name": "Paula",
        "last_name": "Ferreira Freire",
        "cpf": "68214227372",
        "email": "gerencia2.projetos1@aprendereditora.com.br",
        "gerencia_setor": "Super",  # Maps to SUPERINTENDENCIA
    },
]


def generate_username(first_name: str, last_name: str) -> str:
    """
    Generate username from name.

    Pattern: firstname.lastname (lowercase, no accents)
    Example: "Maria Cristina Meaney" → "maria.meaney"
    """
    # Take first name and last surname
    first = first_name.split()[0].lower()
    last = last_name.split()[-1].lower()

    # Remove accents (basic implementation)
    accents = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "õ": "o",
        "ô": "o",
        "ú": "u",
        "ç": "c",
    }
    for accented, plain in accents.items():
        first = first.replace(accented, plain)
        last = last.replace(accented, plain)

    return f"{first}.{last}"


class Command(BaseCommand):
    help = "Seed gerentes ao grupo Gerência e vincular a Gerencia"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview only, don't commit changes",
        )

    def handle(self, *args: str, **options: dict[str, Any]) -> None:
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No changes will be committed\n"))

        self.stdout.write("Seeding gerentes...\n")

        # Stats
        users_created = 0
        users_existing = 0
        group_assignments = 0
        gerencia_links = 0
        errors = []

        # Get or create "Gerência" group
        gerencia_group, group_created = Group.objects.get_or_create(name="Gerência")
        if group_created:
            self.stdout.write(self.style.SUCCESS("  ✓ Created Django Group: Gerência"))
        else:
            self.stdout.write("  - Group 'Gerência' already exists")

        with transaction.atomic():
            for gerente_data in GERENTES:
                cpf = gerente_data["cpf"]
                first_name = gerente_data["first_name"]
                last_name = gerente_data["last_name"]
                email = gerente_data["email"]
                gerencia_setor = gerente_data["gerencia_setor"]

                # 1. Get or create Usuario
                usuario, created = Usuario.objects.get_or_create(
                    cpf=cpf,
                    defaults={
                        "username": generate_username(first_name, last_name),
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "cargo": "Gerente",
                        "is_active": True,
                    },
                )

                if created:
                    users_created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Created usuario: {usuario.username} ({first_name} {last_name})")
                    )
                else:
                    users_existing += 1
                    self.stdout.write(f"  - Usuario already exists: {usuario.username} ({first_name} {last_name})")

                # 2. Add to "Gerência" group
                if not usuario.groups.filter(name="Gerência").exists():
                    usuario.groups.add(gerencia_group)
                    group_assignments += 1
                    self.stdout.write(self.style.SUCCESS(f"    → Added {usuario.username} to group 'Gerência'"))
                else:
                    self.stdout.write(f"    - {usuario.username} already in group 'Gerência'")

                # 3. Link to Gerencia via gerente FK
                try:
                    gerencia = Gerencia.objects.get(nome_setor=gerencia_setor)

                    # Special case: SUPERINTENDENCIA has 4 managers
                    # Only link if gerente is not already set
                    if gerencia.gerente is None:
                        gerencia.gerente = usuario  # type: ignore[misc]
                        gerencia.save()
                        gerencia_links += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"    → Linked {usuario.username} as gerente of {gerencia.nome} ({gerencia.nome_setor})"
                            )
                        )
                    elif gerencia.gerente == usuario:
                        self.stdout.write(f"    - {usuario.username} already linked to {gerencia.nome}")
                    else:
                        # SUPERINTENDENCIA has multiple managers - only first one gets linked
                        self.stdout.write(
                            self.style.WARNING(
                                f"    ⚠️  {gerencia.nome} already has gerente {gerencia.gerente.username}, skipping FK link for {usuario.username}"
                            )
                        )

                except Gerencia.DoesNotExist:
                    error_msg = f"Gerencia with nome_setor='{gerencia_setor}' not found for {usuario.username}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f"    ✗ {error_msg}"))

            # Rollback if dry-run
            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("\n🔄 Rolling back (dry-run mode)"))

        # Summary
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"""
✅ Seed complete:
  - Usuarios created: {users_created}
  - Usuarios existing: {users_existing}
  - Group assignments: {group_assignments}
  - Gerencia FK links: {gerencia_links}
  - Errors: {len(errors)}
"""))

        if errors:
            self.stdout.write(self.style.ERROR("\n❌ Errors:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY RUN: No changes committed. Run without --dry-run to apply.")
            )
        else:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS(f"\n✅ {len(GERENTES)} gerentes seeded to group 'Gerência'"))

            # Verification
            self.stdout.write("\n🔍 Verification:")
            gerencia_count = Group.objects.get(name="Gerência").user_set.count()  # type: ignore[attr-defined]
            self.stdout.write(f"  - Users in 'Gerência' group: {gerencia_count}")

            gerencias_with_gerente = Gerencia.objects.filter(gerente__isnull=False).count()
            self.stdout.write(f"  - Gerencias with gerente assigned: {gerencias_with_gerente}/7")
