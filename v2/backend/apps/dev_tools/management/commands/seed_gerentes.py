"""
Seed gerentes ao grupo função canônico "Gerente" + EquipeGerencia.papel=GERENTE.

Baseado em:
- Planilha Usuários.xlsx (Cargo="Gerente", Gerência=setor)
- 7 gerentes identificados, 4 faltam no banco (serão criados)

Fonte de verdade do papel hierárquico = Cargo (não participação na agenda).

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

Cada gerente recebe:
- grupo Django função "Gerente" (FUNCAO_GROUPS canônico, não "Gerência")
- EquipeGerencia.papel=GERENTE na gerência resolvida (idempotente)
- Gerencia.gerente FK (1 gerente principal por gerência)

Gerência ambígua/sem mapping seguro é pulada (skip + warning), sem erro.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

import pandas as pd

from apps.core.models import EquipeGerencia, Gerencia, Usuario

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
    help = "Seed gerentes ao grupo função Gerente + EquipeGerencia.papel=GERENTE"

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
        equipe_created = 0
        equipe_existing = 0
        skipped_ambiguous = 0
        errors = []

        # Get or create canonical função group "Gerente" (FUNCAO_GROUPS).
        gerente_group, group_created = Group.objects.get_or_create(name="Gerente")
        if group_created:
            self.stdout.write(self.style.SUCCESS("  ✓ Created Django Group: Gerente"))
        else:
            self.stdout.write("  - Group 'Gerente' already exists")

        with transaction.atomic():
            for gerente_data in GERENTES:
                cpf = gerente_data["cpf"]
                first_name = gerente_data["first_name"]
                last_name = gerente_data["last_name"]
                email = gerente_data["email"]
                gerencia_setor = (gerente_data["gerencia_setor"] or "").strip()

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

                # 2. Add to canonical função group "Gerente"
                if not usuario.groups.filter(name="Gerente").exists():
                    usuario.groups.add(gerente_group)
                    group_assignments += 1
                    self.stdout.write(self.style.SUCCESS(f"    → Added {usuario.username} to group 'Gerente'"))
                else:
                    self.stdout.write(f"    - {usuario.username} already in group 'Gerente'")

                # Skip gerência ambígua/sem mapping seguro (sem erro).
                if not gerencia_setor or gerencia_setor in {"-", "Individual"}:
                    skipped_ambiguous += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"    ⚠️  Gerência ambígua para {usuario.username} (setor={gerencia_setor!r}) — "
                            f"EquipeGerencia/FK pulados (decisão humana)"
                        )
                    )
                    continue

                # 3. Resolve gerência + criar EquipeGerencia.papel=GERENTE + FK
                try:
                    gerencia = Gerencia.objects.get(nome_setor=gerencia_setor)

                    # 3a. EquipeGerencia.papel=GERENTE (idempotente via UK gerencia+usuario+papel)
                    _, eq_created = EquipeGerencia.objects.get_or_create(
                        gerencia=gerencia,
                        usuario=usuario,
                        papel="GERENTE",
                        defaults={"ativo": True},
                    )
                    if eq_created:
                        equipe_created += 1
                        self.stdout.write(self.style.SUCCESS(f"    → EquipeGerencia GERENTE em {gerencia.nome_setor}"))
                    else:
                        equipe_existing += 1

                    # 3b. Gerencia.gerente FK (1 gerente principal; SUPERINTENDENCIA tem múltiplos)
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
  - EquipeGerencia created: {equipe_created}
  - EquipeGerencia existing: {equipe_existing}
  - Gerencia FK links: {gerencia_links}
  - Skipped (gerência ambígua): {skipped_ambiguous}
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
            self.stdout.write(self.style.SUCCESS(f"\n✅ {len(GERENTES)} gerentes seeded to group 'Gerente'"))

            # Verification
            self.stdout.write("\n🔍 Verification:")
            gerente_count = Group.objects.get(name="Gerente").user_set.count()  # type: ignore[attr-defined]
            self.stdout.write(f"  - Users in 'Gerente' group: {gerente_count}")

            equipe_gerente_count = EquipeGerencia.objects.filter(papel="GERENTE").count()
            self.stdout.write(f"  - EquipeGerencia papel=GERENTE: {equipe_gerente_count}")

            gerencias_with_gerente = Gerencia.objects.filter(gerente__isnull=False).count()
            self.stdout.write(f"  - Gerencias with gerente assigned: {gerencias_with_gerente}/7")
