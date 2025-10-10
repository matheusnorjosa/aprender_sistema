"""
Bootstrap RBAC System - DAT-P08-v2
==================================

Creates canonical groups and assigns permissions for the RBAC system.
This command is idempotent and can be run multiple times safely.

Groups Created:
- coordenador: Can create event requests
- formador: Can view own events and block availability
- controle: Can manage pre-agenda queue
- gerente_super: Can approve/reject requests (Superintendência)
- dat: Can ingest data and view QA
- admin_ops: Full administrative access

Usage:
    python manage.py bootstrap_rbac
    python manage.py bootstrap_rbac --verbose
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction

from core import rbac


class Command(BaseCommand):
    """
    Bootstrap RBAC system with canonical groups and permissions.
    Idempotent operation - safe to run multiple times.
    """

    help = "Bootstrap RBAC: Create groups and assign permissions (idempotent)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each operation",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)

        self.stdout.write(self.style.MIGRATE_HEADING("=== BOOTSTRAP RBAC SYSTEM ==="))

        try:
            with transaction.atomic():
                # Step 1: Create canonical groups
                self.stdout.write("\n[1/3] Creating canonical groups...")
                created_groups = self._create_groups(verbose)

                # Step 2: Assign native Django permissions
                self.stdout.write("\n[2/3] Assigning native model permissions...")
                assigned_perms = self._assign_native_permissions(verbose)

                # Step 3: Assign custom permissions
                self.stdout.write("\n[3/3] Assigning custom permissions...")
                custom_perms = self._assign_custom_permissions(verbose)

                # Summary
                self.stdout.write(self.style.MIGRATE_HEADING("\n=== SUMMARY ==="))
                self.stdout.write(f"Groups created: {created_groups}")
                self.stdout.write(
                    f"Native permissions assigned: {assigned_perms['total']}"
                )
                self.stdout.write(
                    f"Custom permissions assigned: {custom_perms['total']}"
                )

                # List final state
                self.stdout.write(
                    self.style.MIGRATE_HEADING("\n=== GROUPS & PERMISSIONS ===")
                )
                self._list_groups_permissions()

                self.stdout.write(
                    self.style.SUCCESS("\n✓ RBAC bootstrap completed successfully!")
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Error: {e}"))
            raise

    def _create_groups(self, verbose):
        """Create all canonical groups (idempotent)."""
        created = 0

        for group_name in rbac.ALL_GROUPS:
            group, was_created = Group.objects.get_or_create(name=group_name)

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Created: {group_name}"))
            elif verbose:
                self.stdout.write(f"  - Exists: {group_name}")

        return created

    def _assign_native_permissions(self, verbose):
        """Assign native Django model permissions to groups."""
        stats = {"total": 0, "by_group": {}}

        # Import models dynamically to avoid circular imports
        from core.models import (
            Aprovacao,
            DisponibilidadeFormadores,
            EventoGoogleCalendar,
            Formador,
            LogAuditoria,
            Municipio,
            Projeto,
            Solicitacao,
            TipoEvento,
            Usuario,
        )

        # Define permission mappings
        permission_map = {
            rbac.COORDENADOR: [
                ("core", "solicitacao", "add_solicitacao"),
                ("core", "solicitacao", "view_solicitacao"),
                ("core", "solicitacao", "view_own_solicitacoes"),
            ],
            rbac.FORMADOR: [
                ("core", "formador", "view_formador"),
                ("core", "formador", "view_own_events"),
                ("core", "disponibilidadeformadores", "add_disponibilidadeformadores"),
                (
                    "core",
                    "disponibilidadeformadores",
                    "change_disponibilidadeformadores",
                ),
                ("core", "disponibilidadeformadores", "view_disponibilidadeformadores"),
            ],
            rbac.CONTROLE: [
                ("core", "solicitacao", "view_solicitacao"),
                ("core", "solicitacao", "change_solicitacao"),
                ("core", "solicitacao", "can_controlar_preagenda"),
                ("core", "eventogooglecalendar", "add_eventogooglecalendar"),
                ("core", "eventogooglecalendar", "view_eventogooglecalendar"),
                ("core", "eventogooglecalendar", "sync_calendar"),
                ("core", "logauditoria", "view_logauditoria"),
                ("core", "logauditoria", "view_relatorios"),
            ],
            rbac.GERENTE_SUPER: [
                ("core", "solicitacao", "view_solicitacao"),
                ("core", "solicitacao", "change_solicitacao"),
                ("core", "solicitacao", "can_controlar_preagenda"),
                ("core", "aprovacao", "add_aprovacao"),
                ("core", "aprovacao", "view_aprovacao"),
                ("core", "logauditoria", "view_logauditoria"),
                ("core", "logauditoria", "view_relatorios"),
            ],
            rbac.DAT: [
                ("core", "solicitacao", "view_solicitacao"),
                ("core", "usuario", "view_usuario"),
                ("core", "formador", "view_formador"),
                ("core", "municipio", "view_municipio"),
                ("core", "projeto", "view_projeto"),
                ("core", "tipoevento", "view_tipoevento"),
                ("core", "logauditoria", "view_logauditoria"),
                ("core", "logauditoria", "view_relatorios"),
            ],
            rbac.ADMIN_OPS: [
                # Admin ops gets all permissions from other groups
                # Plus full CRUD on all models
            ],
        }

        # Assign permissions to groups
        for group_name, perms in permission_map.items():
            group = Group.objects.get(name=group_name)
            group_stats = 0

            for app_label, model_name, codename in perms:
                try:
                    # Get permission by codename
                    perm = Permission.objects.get(
                        codename=codename, content_type__app_label=app_label
                    )

                    if not group.permissions.filter(pk=perm.pk).exists():
                        group.permissions.add(perm)
                        group_stats += 1
                        stats["total"] += 1

                        if verbose:
                            self.stdout.write(
                                f"  ✓ {group_name}: {app_label}.{codename}"
                            )

                except Permission.DoesNotExist:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ! Permission not found: {app_label}.{codename}"
                            )
                        )

            stats["by_group"][group_name] = group_stats

        # Admin Ops gets ALL permissions from all groups
        admin_group = Group.objects.get(name=rbac.ADMIN_OPS)
        all_perms = Permission.objects.filter(content_type__app_label="core")

        for perm in all_perms:
            if not admin_group.permissions.filter(pk=perm.pk).exists():
                admin_group.permissions.add(perm)
                stats["total"] += 1

                if verbose:
                    self.stdout.write(
                        f"  ✓ {rbac.ADMIN_OPS}: {perm.content_type.app_label}.{perm.codename}"
                    )

        return stats

    def _assign_custom_permissions(self, verbose):
        """Assign custom permissions defined in model Meta."""
        stats = {"total": 0}

        # Custom permissions are already created by Django migrations
        # This method documents the mapping for clarity

        custom_permission_map = {
            # Formador custom permissions
            "view_own_events": [rbac.FORMADOR, rbac.ADMIN_OPS],
            # Solicitacao custom permissions
            "sync_calendar": [rbac.CONTROLE, rbac.ADMIN_OPS],
            "view_own_solicitacoes": [rbac.COORDENADOR, rbac.ADMIN_OPS],
            "can_controlar_preagenda": [
                rbac.CONTROLE,
                rbac.GERENTE_SUPER,
                rbac.ADMIN_OPS,
            ],
            # LogAuditoria custom permissions
            "view_relatorios": [
                rbac.CONTROLE,
                rbac.GERENTE_SUPER,
                rbac.DAT,
                rbac.ADMIN_OPS,
            ],
            # LogComunicacao custom permissions
            "view_logs_comunicacao": [rbac.ADMIN_OPS],
        }

        for codename, group_names in custom_permission_map.items():
            try:
                perm = Permission.objects.get(
                    codename=codename, content_type__app_label="core"
                )

                for group_name in group_names:
                    group = Group.objects.get(name=group_name)

                    if not group.permissions.filter(pk=perm.pk).exists():
                        group.permissions.add(perm)
                        stats["total"] += 1

                        if verbose:
                            self.stdout.write(f"  ✓ {group_name}: custom.{codename}")

            except Permission.DoesNotExist:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ! Custom permission not found: {codename}"
                        )
                    )
            except Group.DoesNotExist:
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(f"  ! Group not found: {group_name}")
                    )

        return stats

    def _list_groups_permissions(self):
        """List all groups and their permission counts."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        for group_name in rbac.ALL_GROUPS:
            try:
                group = Group.objects.get(name=group_name)
                perm_count = group.permissions.count()

                # Get user count using the correct related name from custom User model
                # The related_name is 'usuarios' (defined in Usuario.groups field)
                user_count = User.objects.filter(groups=group).count()

                self.stdout.write(
                    f"  {group_name:15} | {perm_count:3} perms | {user_count:3} users"
                )
            except Group.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  {group_name:15} | NOT FOUND"))
