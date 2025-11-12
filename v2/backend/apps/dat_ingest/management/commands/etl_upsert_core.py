"""
ETL Command: Upsert staging → SSOT tables (idempotent by natural keys)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from apps.core.models import Municipio, Projeto, TipoEvento, Usuario
from apps.dat_ingest.models import StgMunicipio, StgProjeto, StgTipoEvento, StgUsuario


class Command(BaseCommand):
    help = "Upsert staging → SSOT tables (idempotent by natural keys)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Simulate without writing to DB")
        parser.add_argument(
            "--only",
            choices=["usuarios", "municipios", "projetos", "tipos"],
            help="Process only specific entity type",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options["dry_run"]
        only = options["only"]

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN MODE] No changes will be saved"))

        total_created = 0
        total_updated = 0
        total_unchanged = 0

        if only is None or only == "usuarios":
            created, updated, unchanged = self._upsert_usuarios(dry_run=dry_run)
            total_created += created
            total_updated += updated
            total_unchanged += unchanged

        if only is None or only == "municipios":
            created, updated, unchanged = self._upsert_municipios(dry_run=dry_run)
            total_created += created
            total_updated += updated
            total_unchanged += unchanged

        if only is None or only == "projetos":
            created, updated, unchanged = self._upsert_projetos(dry_run=dry_run)
            total_created += created
            total_updated += updated
            total_unchanged += unchanged

        if only is None or only == "tipos":
            created, updated, unchanged = self._upsert_tipos_evento(dry_run=dry_run)
            total_created += created
            total_updated += updated
            total_unchanged += unchanged

        self.stdout.write(
            self.style.SUCCESS(
                f"\n[SUMMARY] Created: {total_created}, Updated: {total_updated}, Unchanged: {total_unchanged}"
            )
        )

    @transaction.atomic
    def _upsert_usuarios(self, dry_run: bool = False) -> tuple[int, int, int]:
        """
        Upsert Usuario by natural key: email (case-insensitive, trimmed)
        Returns: (created, updated, unchanged)
        """
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        stg_usuarios = StgUsuario.objects.all()
        self.stdout.write(f"\n[Usuarios] Processing {stg_usuarios.count()} staging records...")

        for stg in stg_usuarios:
            # Natural key: email (normalized)
            email = stg.email.strip().lower()

            if dry_run:
                # In dry-run, just check if exists
                exists = Usuario.objects.filter(email__iexact=email).exists()
                if exists:
                    unchanged_count += 1
                else:
                    created_count += 1
                continue

            # Build defaults dict
            defaults = {
                "first_name": stg.nome.split()[0] if stg.nome else "",
                "last_name": " ".join(stg.nome.split()[1:]) if len(stg.nome.split()) > 1 else "",
                "cpf": stg.cpf or "",
                "telefone": stg.telefone or "",
                "cargo": stg.perfil or "Formador",
                "is_active": stg.ativo,
            }

            # Generate username from email if needed
            username = email.split("@")[0]

            try:
                obj, created = Usuario.objects.update_or_create(
                    email__iexact=email,
                    defaults={
                        "username": username,
                        "email": email,
                        **defaults,
                    },
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created: {stg.nome} ({email})")
                else:
                    # Check if any field changed
                    changed = False
                    for field, value in defaults.items():
                        if getattr(obj, field) != value:
                            changed = True
                            break

                    if changed:
                        updated_count += 1
                        self.stdout.write(f"  ↻ Updated: {stg.nome} ({email})")
                    else:
                        unchanged_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing {email}: {e}"))

        self.stdout.write(
            f"  Usuarios: {created_count} created, {updated_count} updated, {unchanged_count} unchanged"
        )
        return created_count, updated_count, unchanged_count

    @transaction.atomic
    def _upsert_municipios(self, dry_run: bool = False) -> tuple[int, int, int]:
        """
        Upsert Municipio by natural key: (nome, uf)
        Returns: (created, updated, unchanged)
        """
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        stg_municipios = StgMunicipio.objects.all()
        self.stdout.write(f"\n[Municipios] Processing {stg_municipios.count()} staging records...")

        for stg in stg_municipios:
            # Natural key: (nome, uf) - both normalized
            nome = stg.nome.strip()
            uf = stg.uf.strip().upper()

            if dry_run:
                exists = Municipio.objects.filter(nome=nome, uf=uf).exists()
                if exists:
                    unchanged_count += 1
                else:
                    created_count += 1
                continue

            defaults = {
                "ativo": stg.ativo,
            }

            try:
                obj, created = Municipio.objects.update_or_create(
                    nome=nome, uf=uf, defaults=defaults
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created: {nome}-{uf}")
                else:
                    if obj.ativo != stg.ativo:
                        updated_count += 1
                        self.stdout.write(f"  ↻ Updated: {nome}-{uf}")
                    else:
                        unchanged_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing {nome}-{uf}: {e}"))

        self.stdout.write(
            f"  Municipios: {created_count} created, {updated_count} updated, {unchanged_count} unchanged"
        )
        return created_count, updated_count, unchanged_count

    @transaction.atomic
    def _upsert_projetos(self, dry_run: bool = False) -> tuple[int, int, int]:
        """
        Upsert Projeto by natural key: nome
        Returns: (created, updated, unchanged)
        """
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        stg_projetos = StgProjeto.objects.all()
        self.stdout.write(f"\n[Projetos] Processing {stg_projetos.count()} staging records...")

        for stg in stg_projetos:
            # Natural key: nome
            nome = stg.nome.strip()

            if dry_run:
                exists = Projeto.objects.filter(nome=nome).exists()
                if exists:
                    unchanged_count += 1
                else:
                    created_count += 1
                continue

            defaults = {
                "descricao": stg.descricao or "",
                "ativo": stg.ativo,
            }

            try:
                obj, created = Projeto.objects.update_or_create(nome=nome, defaults=defaults)

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created: {nome}")
                else:
                    changed = obj.descricao != stg.descricao or obj.ativo != stg.ativo
                    if changed:
                        updated_count += 1
                        self.stdout.write(f"  ↻ Updated: {nome}")
                    else:
                        unchanged_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing {nome}: {e}"))

        self.stdout.write(
            f"  Projetos: {created_count} created, {updated_count} updated, {unchanged_count} unchanged"
        )
        return created_count, updated_count, unchanged_count

    @transaction.atomic
    def _upsert_tipos_evento(self, dry_run: bool = False) -> tuple[int, int, int]:
        """
        Upsert TipoEvento by natural key: nome
        Returns: (created, updated, unchanged)
        """
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        stg_tipos = StgTipoEvento.objects.all()
        self.stdout.write(f"\n[Tipos Evento] Processing {stg_tipos.count()} staging records...")

        for stg in stg_tipos:
            # Natural key: nome
            nome = stg.nome.strip()

            if dry_run:
                exists = TipoEvento.objects.filter(nome=nome).exists()
                if exists:
                    unchanged_count += 1
                else:
                    created_count += 1
                continue

            defaults = {
                "descricao": stg.descricao or "",
                "cor": stg.cor or "",
            }

            try:
                obj, created = TipoEvento.objects.update_or_create(nome=nome, defaults=defaults)

                if created:
                    created_count += 1
                    self.stdout.write(f"  ✓ Created: {nome}")
                else:
                    changed = obj.descricao != stg.descricao or obj.cor != stg.cor
                    if changed:
                        updated_count += 1
                        self.stdout.write(f"  ↻ Updated: {nome}")
                    else:
                        unchanged_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing {nome}: {e}"))

        self.stdout.write(
            f"  Tipos Evento: {created_count} created, {updated_count} updated, {unchanged_count} unchanged"
        )
        return created_count, updated_count, unchanged_count
