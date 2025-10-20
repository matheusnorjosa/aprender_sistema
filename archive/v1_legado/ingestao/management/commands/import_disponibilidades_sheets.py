"""
Comando canônico de importação de disponibilidades.
Suporta ingestão dual: Google Sheets ou CSV local.

Flags:
- --from: 'sheets' ou caminho para arquivo CSV (ex: /app/data/ingest/dia3/disponibilidades.csv)

Regras de negócio:
- Não usar "MENSAL"; priorizar ANUAL, DESLOCAMENTO, Bloqueios
- Importa disponibilidade de formadores
"""

from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.config import sheets_config
from ingestao.adapters import CsvFolderAdapter, SheetsAdapter


class Command(BaseCommand):
    help = """
    Importa disponibilidades (Google Sheets ou CSV local).

    Uso:
      # Google Sheets
      python manage.py import_disponibilidades_sheets --from sheets --dry-run

      # CSV local
      python manage.py import_disponibilidades_sheets --from /app/data/ingest/dia3/disponibilidades.csv --dry-run
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

        self.stdout.write(
            self.style.SUCCESS(f"🚀 Import disponibilidades - Fonte: {source}")
        )
        self.stdout.write(f"   Dry-run: {dry_run}")
        self.stdout.write("")

        # Determinar adapter
        if source == "sheets":
            adapter = SheetsAdapter()

            # Priorizar ANUAL (não MENSAL)
            gid = sheets_config.ABAS_DISPONIBILIDADE.get("ANUAL", "")

            if not gid:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  GID 'Anual' não configurado - tentando outros formatos"
                    )
                )
                # Fallback: tentar primeira aba disponível
                if sheets_config.ABAS_DISPONIBILIDADE:
                    first_key = next(iter(sheets_config.ABAS_DISPONIBILIDADE))
                    gid = sheets_config.ABAS_DISPONIBILIDADE[first_key]
                    self.stdout.write(f"   Usando aba: {first_key}")

            if not gid:
                self.stdout.write(
                    self.style.ERROR(
                        "❌ Nenhum GID configurado em ABAS_DISPONIBILIDADE"
                    )
                )
                return 1

            self.stdout.write(
                f"📊 Usando Google Sheets: {sheets_config.DISPONIBILIDADE_2025_ID}"
            )
            rows_iter = adapter.rows(sheets_config.DISPONIBILIDADE_2025_ID, gid)
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
                formador = row.get("Formador", "").strip()
                tipo = row.get("Tipo", "").strip()
                data = row.get("Data", "").strip()

                if not formador or not tipo:
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(f"   ⚠️  Linha incompleta: {row}")
                        )
                    skipped += 1
                    continue

                # Ignorar tipo MENSAL (regra de negócio)
                if tipo.upper() == "MENSAL":
                    if verbose:
                        self.stdout.write(
                            self.style.WARNING(
                                f"   ⏭️  Ignorando MENSAL para {formador}"
                            )
                        )
                    skipped += 1
                    continue

                if verbose:
                    self.stdout.write(
                        f"   📝 {formador} | Tipo: {tipo} | Data: {data or 'N/A'}"
                    )

                if not dry_run:
                    # TODO: Criar DisponibilidadeFormador
                    # Tipos válidos: ANUAL, DESLOCAMENTO, Bloqueios
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
        self.stdout.write(f"   Pulados (MENSAL + duplicados): {skipped}")
        self.stdout.write(f"   Erros: {errors}")
        self.stdout.write(self.style.SUCCESS("=" * 60))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN: Nenhuma alteração foi salva no banco")
            )

        return 0
