"""
Seed gerentes ao grupo função canônico "Gerente" + EquipeGerencia.papel=GERENTE.

A lista de gerentes NÃO mora no código (F5 do scan de segurança, 16/10/2026: CPF, nome e e-mail
de pessoa real não entram no git). O operador passa um arquivo JSON guardado FORA do repositório:

    [
      {"first_name": "...", "last_name": "...", "cpf": "<11 dígitos>", "email": "...",
       "gerencia_setor": "Super"},
      ...
    ]

Fonte de verdade do papel hierárquico = Cargo (não participação na agenda).

Usage:
    python manage.py seed_gerentes --arquivo /caminho/fora/do/git/gerentes.json --dry-run  # Preview
    python manage.py seed_gerentes --arquivo /caminho/fora/do/git/gerentes.json            # Apply

Mapping (gerencia_setor → Database Gerencia.nome_setor):
- "Super" (SUPERINTENDENCIA), "Vidas" (GERENCIA 2), "Fluir" (GERENCIA 3), "ACerta" (GERENCIA 4),
  "Brincando" (GERENCIA 5), "Sou da Paz" (GERENCIA 6), "Individual" (GERENCIA INDIVIDUAL)

Cada gerente recebe:
- grupo Django função "Gerente" (FUNCAO_GROUPS canônico, não "Gerência")
- EquipeGerencia.papel=GERENTE na gerência resolvida (idempotente)
- Gerencia.gerente FK (1 gerente principal por gerência)

Gerência ambígua/sem mapping seguro é pulada (skip + warning), sem erro.
A saída identifica cada conta por u<id>, sem nome, CPF ou e-mail.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction

from apps.core.models import EquipeGerencia, Gerencia, Usuario

CAMPOS_OBRIGATORIOS = ("first_name", "last_name", "cpf", "email", "gerencia_setor")


def carregar_gerentes(caminho: str) -> list[dict[str, str]]:
    """Lê e valida a lista do arquivo do operador. Erro de leitura ou de formato vira CommandError."""
    arquivo = Path(caminho)
    if not arquivo.is_file():
        raise CommandError("Arquivo da lista de gerentes não encontrado (use --arquivo).")
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CommandError("Arquivo da lista de gerentes não é um JSON legível.") from exc
    if not isinstance(dados, list):
        raise CommandError("O arquivo deve trazer uma lista de gerentes.")
    gerentes: list[dict[str, str]] = []
    for posicao, item in enumerate(dados, start=1):
        if not isinstance(item, dict) or any(not isinstance(item.get(c), str) for c in CAMPOS_OBRIGATORIOS):
            # Só a posição: a mensagem não repete o conteúdo (dado pessoal).
            raise CommandError(f"Item {posicao} da lista sem um dos campos {', '.join(CAMPOS_OBRIGATORIOS)}.")
        gerentes.append({c: item[c] for c in CAMPOS_OBRIGATORIOS})
    return gerentes


def generate_username(first_name: str, last_name: str) -> str:
    """
    Generate username from name.

    Pattern: firstname.lastname (lowercase, no accents)
    Example: "Ana Lima Sousa" → "ana.sousa"
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
    help = "Seed gerentes ao grupo função Gerente + EquipeGerencia.papel=GERENTE (lista em --arquivo)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--arquivo",
            help="JSON com a lista de gerentes, guardado FORA do repositório",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview only, don't commit changes",
        )

    def handle(self, *args: str, **options: Any) -> None:
        dry_run = options.get("dry_run", False)
        caminho = options.get("arquivo")
        if not caminho:
            raise CommandError("Informe a lista de gerentes com --arquivo (JSON fora do repositório).")
        gerentes = carregar_gerentes(caminho)

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
            for gerente_data in gerentes:
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
                conta = f"u{usuario.pk}"

                if created:
                    users_created += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created usuario: {conta}"))
                else:
                    users_existing += 1
                    self.stdout.write(f"  - Usuario already exists: {conta}")

                # 2. Add to canonical função group "Gerente"
                if not usuario.groups.filter(name="Gerente").exists():
                    usuario.groups.add(gerente_group)
                    group_assignments += 1
                    self.stdout.write(self.style.SUCCESS(f"    → Added {conta} to group 'Gerente'"))
                else:
                    self.stdout.write(f"    - {conta} already in group 'Gerente'")

                # Skip gerência ambígua/sem mapping seguro (sem erro).
                if not gerencia_setor or gerencia_setor in {"-", "Individual"}:
                    skipped_ambiguous += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"    ⚠️  Gerência ambígua para {conta} (setor={gerencia_setor!r}) — "
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
                                f"    → Linked {conta} as gerente of {gerencia.nome} ({gerencia.nome_setor})"
                            )
                        )
                    elif gerencia.gerente == usuario:
                        self.stdout.write(f"    - {conta} already linked to {gerencia.nome}")
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    ⚠️  {gerencia.nome} already has gerente u{gerencia.gerente.pk}, skipping {conta}"
                            )
                        )

                except Gerencia.DoesNotExist:
                    error_msg = f"Gerencia with nome_setor='{gerencia_setor}' not found for {conta}"
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
            self.stdout.write(self.style.SUCCESS(f"\n✅ {len(gerentes)} gerentes seeded to group 'Gerente'"))

            # Verification
            self.stdout.write("\n🔍 Verification:")
            gerente_count = Group.objects.get(name="Gerente").user_set.count()  # type: ignore[attr-defined]
            self.stdout.write(f"  - Users in 'Gerente' group: {gerente_count}")

            equipe_gerente_count = EquipeGerencia.objects.filter(papel="GERENTE").count()
            self.stdout.write(f"  - EquipeGerencia papel=GERENTE: {equipe_gerente_count}")

            gerencias_with_gerente = Gerencia.objects.filter(gerente__isnull=False).count()
            self.stdout.write(f"  - Gerencias with gerente assigned: {gerencias_with_gerente}/7")
