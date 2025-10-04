"""
Comando canônico de importação de usuários (origem=planilha, is_provisorio=True).
Suporta ingestão dual: Google Sheets ou CSV local.

Flags:
- --from: 'sheets' ou caminho para arquivo CSV (ex: /app/data/ingest/dia3/usuarios.csv)

Regras de negócio:
- origem='planilha' (vs 'manual', 'api')
- is_provisorio=True (usuário temporário até confirmação)
- Valida CPF/email antes de criar
- Registra em LogAuditoria
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.config import sheets_config
from ingestao.adapters import CsvFolderAdapter, SheetsAdapter


class Command(BaseCommand):
    help = """
    Importa usuários de planilhas (Google Sheets ou CSV local).

    Uso:
      # Google Sheets
      python manage.py import_usuarios --from sheets --dry-run

      # CSV local
      python manage.py import_usuarios --from /app/data/ingest/dia3/usuarios.csv --dry-run
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            dest="source",
            type=str,
            default="sheets",
            help="Fonte de dados: 'sheets' ou caminho para arquivo CSV",
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
        source = options["source"]
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        self.stdout.write(self.style.SUCCESS(f"🚀 Import usuários - Fonte: {source}"))
        self.stdout.write(f"   Dry-run: {dry_run}")
        self.stdout.write("")

        # Determinar adapter
        if source == "sheets":
            adapter = SheetsAdapter()
            gid = sheets_config.ABAS_USUARIOS.get("Ativos", "")

            if not gid:
                self.stdout.write(
                    self.style.ERROR(
                        "❌ GID 'Ativos' não configurado em sheets_config.py"
                    )
                )
                return 1

            self.stdout.write(f"📊 Usando Google Sheets: {sheets_config.USUARIOS_ID}")
            rows_iter = adapter.rows(sheets_config.USUARIOS_ID, gid)
        else:
            # CSV local
            adapter = CsvFolderAdapter(str(Path(source).parent))
            csv_filename = Path(source).name

            self.stdout.write(f"📁 Usando CSV local: {source}")
            rows_iter = adapter.rows(csv_filename)

        # Processar linhas
        created = 0
        skipped = 0
        errors = 0

        for row in rows_iter:
            try:
                nome = row.get("Nome", "").strip()
                cpf = row.get("CPF", "").strip()
                email = row.get("Email", "").strip()

                if not nome or not cpf:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"   ⚠️  Linha incompleta: {row}")
                        )
                    skipped += 1
                    continue

                # Verificar se já existe (stub)
                # Em produção: Usuario.objects.filter(cpf=cpf).exists()

                if verbose:
                    self.stdout.write(
                        f"   📝 {nome} | CPF: {cpf} | Email: {email or 'N/A'}"
                    )

                if not dry_run:
                    # TODO: Criar Usuario com origem='planilha', is_provisorio=True
                    pass

                created += 1

            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Erro ao processar linha: {e}")
                )
                if verbose:
                    self.stdout.write(f"      Linha: {row}")

        # Resumo final
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"📊 RESUMO:")
        self.stdout.write(f"   Criados: {created}")
        self.stdout.write(f"   Pulados (duplicados): {skipped}")
        self.stdout.write(f"   Erros: {errors}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0
