"""
AS v2 — LGPD Data Export Command (Gap 10 - PLAN_maturity_gaps.md)

Export user data for LGPD compliance (data portability).

Usage:
    python manage.py lgpd_export --cpf=12345678901 --output=user_data.json
    python manage.py lgpd_export --email=user@example.com --output=user_data.json
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportAttributeAccessIssue=false, reportUnknownArgumentType=false, reportArgumentType=false

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from django.core.management.base import BaseCommand, CommandError

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
        from apps.core.models import AuditLog, Usuario
        from apps.core.services.lgpd_export_service import build_lgpd_export_data, export_counts

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
            identifier = f"CPF {cpf}" if cpf else f"email {email}"
            raise CommandError(f"User not found with {identifier}")

        self.stdout.write(f"Exporting data for user: {user.username} (ID: {user.id})")

        # Dossiê montado pelo serviço compartilhado (SSOT — mesma lógica do endpoint
        # self-service `GET /api/me/export/`). Já vem JSON-serializável.
        data = build_lgpd_export_data(user, include_audit=include_audit, include_gcal=include_gcal)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        self.stdout.write(self.style.SUCCESS(f"Data exported to: {output_path}"))

        # LGPD art. 18 (acesso/portabilidade): a exportacao do dossie de um titular e'
        # operacao sensivel e precisa de trilha (art. 37). Registra o FATO — alvo, destino,
        # contagens — NUNCA os valores de PII exportados.
        from apps.core.services.audit import registrar_auditoria

        registrar_auditoria(
            actor=None,  # comando CLI de admin; sem request user
            action=AuditLog.Action.EXPORT,
            model_name="Usuario",
            details={
                "target_user_id": user.pk,
                "output_path": str(output_path),
                "include_audit": bool(include_audit),
                "counts": export_counts(data),
            },
            imediato=True,
        )

        # Summary
        counts = export_counts(data)
        self.stdout.write("  - Personal data: exported")
        self.stdout.write(f"  - Solicitations created: {counts['solicitations_created']}")
        self.stdout.write(f"  - Events as formador: {counts['events_as_formador']}")
        self.stdout.write(f"  - Availability blocks: {counts['availability_blocks']}")
        self.stdout.write(f"  - Approvals made: {counts['approvals_made']}")
        if include_audit and isinstance(data["audit_logs"], list):
            self.stdout.write(f"  - Audit logs: {len(data['audit_logs'])}")
