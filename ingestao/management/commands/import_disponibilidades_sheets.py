"""
Comando canônico de importação de disponibilidades de formadores
Especificação: Hotfix Dia 3 - Sistema Aprender

STUB: Implementação futura
Este stub garante que o comando existe e está registrado no sistema.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """
    Importa disponibilidades (bloqueios) de formadores de planilhas Google Sheets.

    Regras:
    - Parse de códigos: T (total), P (parcial)
    - Validação de horários (hora_inicio < hora_fim)
    - Registra em DisponibilidadeFormadores
    - Registra em LogAuditoria

    Uso:
      python manage.py import_disponibilidades_sheets --sheet-id=<ID> [--dry-run]
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--sheet-id", type=str, required=True, help="ID da planilha Google Sheets"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula importação sem salvar no banco",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Exibe logs detalhados"
        )

    def handle(self, *args, **options):
        sheet_id = options["sheet_id"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        self.stdout.write(
            self.style.WARNING(
                "⚠️  STUB: import_disponibilidades_sheets ainda não implementado (Hotfix Dia 3)"
            )
        )
        self.stdout.write(f"    Sheet ID: {sheet_id}")
        self.stdout.write(f"    Dry-run: {dry_run}")
        self.stdout.write(f"    Verbose: {verbose}")
        self.stdout.write("")
        self.stdout.write("📝 Implementação pendente:")
        self.stdout.write("   - Conectar com Google Sheets API")
        self.stdout.write("   - Parse códigos T/P (total/parcial)")
        self.stdout.write("   - Validar horários")
        self.stdout.write("   - Criar registros DisponibilidadeFormadores")
        self.stdout.write("   - Registrar auditoria")

        return 0
