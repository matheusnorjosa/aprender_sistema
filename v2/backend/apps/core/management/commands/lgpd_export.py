"""
AS v2 — LGPD Data Export Command (Gap 10 - PLAN_maturity_gaps.md)

Export user data for LGPD compliance (data portability).

Usage:
    python manage.py lgpd_export --cpf=12345678901 --output=user_data.json
    python manage.py lgpd_export --email=user@example.com --output=user_data.json
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

if TYPE_CHECKING:
    from argparse import ArgumentParser


class Command(BaseCommand):
    """Export user data for LGPD compliance."""

    help = "Export user data for LGPD compliance (data portability)"

    def add_arguments(self, parser: ArgumentParser) -> None:
        """Add command arguments."""
        parser.add_argument(
            "--cpf",
            type=str,
            help="CPF of the user to export (digits only)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Email of the user to export",
        )
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Output file path (JSON format)",
        )
        parser.add_argument(
            "--include-audit",
            action="store_true",
            default=True,
            help="Include audit logs (default: True)",
        )
        parser.add_argument(
            "--include-gcal",
            action="store_true",
            default=False,
            help="Include GCal credentials info (default: False)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute LGPD data export."""
        from apps.core.models import (
            AuditLog,
            Aprovacao,
            AvailabilityBlock,
            Formador,
            GCalUserCredential,
            Solicitacao,
            Usuario,
        )

        cpf = options.get("cpf")
        email = options.get("email")
        output_path = options["output"]
        include_audit = options["include_audit"]
        include_gcal = options["include_gcal"]

        if not cpf and not email:
            raise CommandError("Either --cpf or --email is required")

        # Find user
        user = None
        if cpf:
            # Clean CPF (remove dots and dashes)
            cpf_clean = "".join(filter(str.isdigit, cpf))
            user = Usuario.objects.filter(cpf=cpf_clean).first()
        elif email:
            user = Usuario.objects.filter(email__iexact=email).first()

        if not user:
            raise CommandError(f"User not found with {'CPF ' + cpf if cpf else 'email ' + email}")

        self.stdout.write(f"Exporting data for user: {user.username} (ID: {user.id})")

        # Build export data
        data: dict[str, Any] = {
            "export_info": {
                "generated_at": timezone.now().isoformat(),
                "system": "Aprender Sistema v2",
                "purpose": "LGPD Data Portability (Art. 18, V)",
            },
            "personal_data": {
                "id": user.id,
                "username": user.username,
                "cpf": user.cpf,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "cargo": getattr(user, "cargo", None),
                "matricula": getattr(user, "matricula", None),
                "telefone": getattr(user, "telefone", None),
                "setores": list(user.setores) if hasattr(user, "setores") else [],
                "funcoes": list(user.funcoes) if hasattr(user, "funcoes") else [],
                "groups": list(user.groups.values_list("name", flat=True)),
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            },
        }

        # Solicitations created by user
        solicitations = Solicitacao.objects.filter(solicitante=user)
        data["solicitations_created"] = list(
            solicitations.values(
                "id",
                "titulo",
                "status",
                "fluxo",
                "data_inicio",
                "data_fim",
                "municipio__nome",
                "projeto__nome",
                "created_at",
                "updated_at",
            )
        )

        # Solicitations where user is a formador
        formador_obj = Formador.objects.filter(usuario=user).first()
        if formador_obj:
            data["formador_info"] = {
                "id": formador_obj.id,
                "nome": formador_obj.nome,
                "ativo": formador_obj.ativo,
            }

            # Events where user is assigned as formador
            formador_events = Solicitacao.objects.filter(formadores=formador_obj)
            data["events_as_formador"] = list(
                formador_events.values(
                    "id",
                    "titulo",
                    "status",
                    "data_inicio",
                    "data_fim",
                    "municipio__nome",
                )
            )

            # Availability blocks
            blocks = AvailabilityBlock.objects.filter(formador=formador_obj)
            data["availability_blocks"] = list(
                blocks.values(
                    "id",
                    "tipo",
                    "data_inicio",
                    "data_fim",
                    "motivo",
                    "created_at",
                )
            )
        else:
            data["formador_info"] = None
            data["events_as_formador"] = []
            data["availability_blocks"] = []

        # Approvals made by user
        approvals = Aprovacao.objects.filter(aprovador=user)
        data["approvals_made"] = list(
            approvals.values(
                "id",
                "solicitacao_id",
                "status",
                "comentario",
                "created_at",
            )
        )

        # Audit logs (if requested)
        if include_audit:
            audit_logs = AuditLog.objects.filter(usuario=user).order_by("-created_at")[:100]
            data["audit_logs"] = list(
                audit_logs.values(
                    "id",
                    "action",
                    "model_name",
                    "details",
                    "created_at",
                )
            )
        else:
            data["audit_logs"] = "(excluded from export)"

        # GCal credentials (if requested)
        if include_gcal:
            gcal_cred = GCalUserCredential.objects.filter(user=user).first()
            if gcal_cred:
                data["gcal_credentials"] = {
                    "has_credential": True,
                    "google_email": gcal_cred.google_email,
                    "created_at": gcal_cred.created_at.isoformat(),
                    "last_used_at": gcal_cred.last_used_at.isoformat() if gcal_cred.last_used_at else None,
                    # Note: We don't export actual tokens for security
                    "tokens": "(excluded for security)",
                }
            else:
                data["gcal_credentials"] = None
        else:
            data["gcal_credentials"] = "(excluded from export)"

        # Convert all datetime objects to ISO format strings
        data = self._serialize_data(data)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        self.stdout.write(
            self.style.SUCCESS(f"Data exported to: {output_path}")
        )

        # Summary
        self.stdout.write(f"  - Personal data: exported")
        self.stdout.write(f"  - Solicitations created: {len(data['solicitations_created'])}")
        self.stdout.write(f"  - Events as formador: {len(data['events_as_formador'])}")
        self.stdout.write(f"  - Availability blocks: {len(data['availability_blocks'])}")
        self.stdout.write(f"  - Approvals made: {len(data['approvals_made'])}")
        if include_audit:
            self.stdout.write(f"  - Audit logs: {len(data['audit_logs'])}")

    def _serialize_data(self, obj: Any) -> Any:
        """Recursively convert datetime objects to ISO format strings."""
        import datetime
        from decimal import Decimal

        if isinstance(obj, dict):
            return {k: self._serialize_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_data(item) for item in obj]
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        else:
            return obj
