"""
Comando para validar acesso ao Google Sheets.

Testa conexão com Google Sheets usando Service Account e exibe
as primeiras linhas de uma aba específica para validação.
"""

from django.core.management.base import BaseCommand

from ingestao.gsheets_adapter import fetch_sheet_csv


class Command(BaseCommand):
    help = "Valida acesso ao Google Sheets (Service Account) e imprime as 3 primeiras linhas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sheet-id", required=True, help="ID da planilha Google Sheets"
        )
        parser.add_argument("--gid", required=True, help="ID da aba (worksheet GID)")

    def handle(self, *args, **options):
        try:
            headers, rows = fetch_sheet_csv(options["sheet_id"], options["gid"])

            self.stdout.write(self.style.SUCCESS(f"✓ Headers: {headers}"))
            self.stdout.write(f"\nTotal de linhas: {len(rows)}\n")

            self.stdout.write(self.style.SUCCESS("Primeiras 3 linhas:"))
            for i, r in enumerate(rows[:3], 1):
                self.stdout.write(f"\n[Linha {i}]")
                for k, v in r.items():
                    self.stdout.write(f"  {k}: {v}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n\n✓ OK: acesso gspread/SA funcionando! ({len(rows)} linhas)"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ FALHA: {e}"))
            raise
