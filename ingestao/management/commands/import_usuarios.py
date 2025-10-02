"""
Comando canônico de importação de usuários (origem=planilha, is_provisorio=True)
Especificação: Hotfix Dia 3 - Sistema Aprender

STUB: Implementação futura
Este stub garante que o comando existe e está registrado no sistema.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """
    Importa usuários de planilhas Google Sheets com flags is_provisorio=True.

    Regras:
    - origem='planilha' (vs 'manual', 'api')
    - is_provisorio=True (usuário temporário até confirmação)
    - Valida CPF/email antes de criar
    - Registra em LogAuditoria

    Uso:
      python manage.py import_usuarios --sheet-id=<ID> [--dry-run]
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
                "⚠️  STUB: import_usuarios ainda não implementado (Hotfix Dia 3)"
            )
        )
        self.stdout.write(f"    Sheet ID: {sheet_id}")
        self.stdout.write(f"    Dry-run: {dry_run}")
        self.stdout.write(f"    Verbose: {verbose}")
        self.stdout.write("")
        self.stdout.write("📝 Implementação pendente:")
        self.stdout.write("   - Conectar com Google Sheets API")
        self.stdout.write("   - Validar CPF/email")
        self.stdout.write(
            "   - Criar usuários com origem='planilha', is_provisorio=True"
        )
        self.stdout.write("   - Registrar auditoria")

        return 0
