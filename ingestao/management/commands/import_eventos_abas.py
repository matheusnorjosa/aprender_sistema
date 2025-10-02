"""
Comando canônico de importação de eventos das abas de planilhas
Especificação: Hotfix Dia 3 - Sistema Aprender

STUB: Implementação futura
Este stub garante que o comando existe e está registrado no sistema.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = """
    Importa eventos de abas de planilhas Google Sheets com lógica de derive_status.

    Regras:
    - derive_status: data_inicio < 25/09/2025 → REALIZADO, senão AGENDADO
    - cancelado_flag: coluna 'Cancelado' define status=CANCELADO
    - AprovacaoHistorico: registra aprovação histórica se status=REALIZADO
    - COORDENADOR_ACOMPANHA: parse de campo booleano

    Uso:
      python manage.py import_eventos_abas --sheet-id=<ID> --aba=<NOME> [--dry-run]
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--sheet-id", type=str, required=True, help="ID da planilha Google Sheets"
        )
        parser.add_argument(
            "--aba",
            type=str,
            required=True,
            help="Nome da aba (ex: 'Super', 'ACerta', 'Bloqueios')",
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
        aba = options["aba"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        self.stdout.write(
            self.style.WARNING(
                "⚠️  STUB: import_eventos_abas ainda não implementado (Hotfix Dia 3)"
            )
        )
        self.stdout.write(f"    Sheet ID: {sheet_id}")
        self.stdout.write(f"    Aba: {aba}")
        self.stdout.write(f"    Dry-run: {dry_run}")
        self.stdout.write(f"    Verbose: {verbose}")
        self.stdout.write("")
        self.stdout.write("📝 Implementação pendente:")
        self.stdout.write("   - Conectar com Google Sheets API")
        self.stdout.write("   - Aplicar derive_status (< 25/09/2025 → REALIZADO)")
        self.stdout.write("   - Processar flag 'Cancelado' → status=CANCELADO")
        self.stdout.write("   - Criar AprovacaoHistorico para eventos REALIZADO")
        self.stdout.write("   - Parse COORDENADOR_ACOMPANHA")
        self.stdout.write("   - Registrar auditoria")

        return 0
