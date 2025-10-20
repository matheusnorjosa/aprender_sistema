"""
Comparador de fontes de dados (Google Sheets vs CSV local).

Compara contagens e registros entre duas fontes de dados para validação
antes da importação efetiva.

Flags obrigatórias:
- --fonte-a: 'sheets' ou caminho para diretório
- --fonte-b: 'sheets' ou caminho para diretório
- --abas: Lista separada por vírgula (ex: ACerta,Brincando,Vidas,Super,Outros)

Opcional:
- --limit: Máximo de amostras por diferença (padrão: 10)
"""

from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from backend.config import sheets_config
from ingestao.adapters import CsvFolderAdapter, SheetsAdapter, parse_row_por_aba


class Command(BaseCommand):
    help = """
    Compara duas fontes de dados (Sheets vs CSV) para validação.

    Uso:
      python manage.py compare_fontes --fonte-a sheets --fonte-b /app/data/ingest/dia3/abas --abas ACerta,Brincando --limit 10
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--fonte-a",
            type=str,
            required=True,
            help="Primeira fonte: 'sheets' ou caminho para diretório",
        )
        parser.add_argument(
            "--fonte-b",
            type=str,
            required=True,
            help="Segunda fonte: 'sheets' ou caminho para diretório",
        )
        parser.add_argument(
            "--abas",
            type=str,
            required=True,
            help="Lista de abas separadas por vírgula (ex: ACerta,Brincando,Vidas,Super,Outros)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Máximo de amostras de diferenças (padrão: 10)",
        )

    def handle(self, *args, **options):
        fonte_a = options["fonte_a"]
        fonte_b = options["fonte_b"]
        abas_str = options["abas"]
        limit = options["limit"]

        # Parse abas
        abas = [aba.strip() for aba in abas_str.split(",")]

        self.stdout.write(self.style.SUCCESS("🔍 Comparador de Fontes"))
        self.stdout.write(f"   Fonte A: {fonte_a}")
        self.stdout.write(f"   Fonte B: {fonte_b}")
        self.stdout.write(f"   Abas: {', '.join(abas)}")
        self.stdout.write(f"   Limite amostras: {limit}")
        self.stdout.write("")

        # Preparar relatório
        report_lines = []
        report_lines.append("# Validação Fonte Dupla")
        report_lines.append(
            f"\nGerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        report_lines.append(f"\n## Fontes Comparadas")
        report_lines.append(f"- **Fonte A**: {fonte_a}")
        report_lines.append(f"- **Fonte B**: {fonte_b}")
        report_lines.append(f"\n## Abas Analisadas")
        report_lines.append(f"{', '.join(abas)}")
        report_lines.append(f"\n## Limite de Amostras")
        report_lines.append(f"{limit} registros por diferença")
        report_lines.append("\n---\n")

        total_a = 0
        total_b = 0

        for aba in abas:
            self.stdout.write(f"\n📋 Comparando aba: {aba}")
            report_lines.append(f"\n### Aba: {aba}\n")

            # Carregar fonte A
            rows_a = list(self._load_source(fonte_a, aba))
            count_a = len(rows_a)
            total_a += count_a

            # Carregar fonte B
            rows_b = list(self._load_source(fonte_b, aba))
            count_b = len(rows_b)
            total_b += count_b

            # Comparar contagens
            self.stdout.write(f"   Fonte A: {count_a} registros")
            self.stdout.write(f"   Fonte B: {count_b} registros")

            report_lines.append(f"**Contagens:**")
            report_lines.append(f"- Fonte A: {count_a} registros")
            report_lines.append(f"- Fonte B: {count_b} registros")

            # Análise de diferenças
            if count_a == count_b:
                self.stdout.write(self.style.SUCCESS(f"   ✅ Contagens iguais"))
                report_lines.append(f"- ✅ **Status**: Contagens iguais")
            else:
                diff = abs(count_a - count_b)
                pct = (
                    (diff / max(count_a, count_b) * 100)
                    if max(count_a, count_b) > 0
                    else 0
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"   ⚠️  Diferença: {diff} registros ({pct:.1f}%)"
                    )
                )
                report_lines.append(
                    f"- ⚠️  **Diferença**: {diff} registros ({pct:.1f}%)"
                )

            # Amostras (primeiros N registros de cada fonte)
            report_lines.append(
                f"\n**Amostras (primeiros {min(limit, count_a, count_b)} registros):**\n"
            )

            if rows_a[:limit]:
                report_lines.append(f"\n*Fonte A (amostra):*")
                for i, row in enumerate(rows_a[:limit], 1):
                    municipio = row.get("municipio", "N/A")
                    data = row.get("data", "N/A")
                    projeto = row.get("projeto", "N/A")
                    report_lines.append(f"{i}. {municipio} | {data} | {projeto}")

            if rows_b[:limit]:
                report_lines.append(f"\n*Fonte B (amostra):*")
                for i, row in enumerate(rows_b[:limit], 1):
                    municipio = row.get("municipio", "N/A")
                    data = row.get("data", "N/A")
                    projeto = row.get("projeto", "N/A")
                    report_lines.append(f"{i}. {municipio} | {data} | {projeto}")

            report_lines.append("\n---\n")

        # Resumo final
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"📊 RESUMO GERAL:")
        self.stdout.write(f"   Total Fonte A: {total_a} registros")
        self.stdout.write(f"   Total Fonte B: {total_b} registros")

        if total_a == total_b:
            self.stdout.write(self.style.SUCCESS(f"   ✅ Fontes idênticas"))
            report_lines.append(f"\n## Resumo Geral\n")
            report_lines.append(f"- Total Fonte A: {total_a} registros")
            report_lines.append(f"- Total Fonte B: {total_b} registros")
            report_lines.append(f"- ✅ **Resultado**: Fontes idênticas")
        else:
            diff_total = abs(total_a - total_b)
            pct_total = (
                (diff_total / max(total_a, total_b) * 100)
                if max(total_a, total_b) > 0
                else 0
            )
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️  Diferença total: {diff_total} registros ({pct_total:.1f}%)"
                )
            )
            report_lines.append(f"\n## Resumo Geral\n")
            report_lines.append(f"- Total Fonte A: {total_a} registros")
            report_lines.append(f"- Total Fonte B: {total_b} registros")
            report_lines.append(
                f"- ⚠️  **Diferença total**: {diff_total} registros ({pct_total:.1f}%)"
            )

        self.stdout.write(self.style.SUCCESS("=" * 60))

        # Salvar relatório
        report_path = Path("docs/VALIDACAO_FONTE_DUPLA.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"✅ Relatório salvo em: {report_path}"))

        return 0

    def _load_source(self, source, aba):
        """Carrega registros de uma fonte (Sheets ou CSV) e os parseia."""
        if source == "sheets":
            adapter = SheetsAdapter()
            gid = sheets_config.get_aba_gid(aba)

            if not gid:
                self.stdout.write(
                    self.style.WARNING(
                        f"   ⚠️  GID vazio para aba '{aba}' (Fonte: sheets)"
                    )
                )
                return []

            raw_rows = adapter.rows(sheets_config.AGENDA_2025_ID, gid)
        else:
            adapter = CsvFolderAdapter(source)
            csv_path = f"{aba}.csv"
            raw_rows = adapter.rows(csv_path)

        # Parsear todas as linhas
        parsed_rows = []
        for row in raw_rows:
            parsed = parse_row_por_aba(aba, row)
            if parsed:
                # Converter ParsedEvento para dict para exibição
                parsed_rows.append(
                    {
                        "municipio": parsed.municipio,
                        "data": str(parsed.data) if parsed.data else "N/A",
                        "projeto": parsed.projeto or "N/A",
                    }
                )

        return parsed_rows
