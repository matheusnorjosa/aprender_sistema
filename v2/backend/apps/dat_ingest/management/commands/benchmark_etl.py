"""
Management command: benchmark_etl

Executa microbenchmarks dos comandos ETL com datasets sintéticos.

Uso:
    python manage.py benchmark_etl --sizes 100,1000

Saída:
    - out_etl/benchmark_report.json

Issue #55: Revisão de performance com microbenchmarks.
"""

import json
import time
import tracemalloc
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings

from apps.dat_ingest.management.commands.audit_agenda_users import (
    normalize_text,
    extract_tokens,
    jaccard_similarity,
    match_by_name,
)
from apps.dat_ingest import constants


class Command(BaseCommand):
    help = "Benchmark ETL operations with synthetic datasets"

    def add_arguments(self, parser):
        parser.add_argument(
            "--sizes",
            type=str,
            default="100,1000",
            help="Dataset sizes (comma-separated, default: 100,1000)",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=settings.ETL_OUTPUT_DIR,
            help="Output directory for report (default: settings.ETL_OUTPUT_DIR)",
        )

    def handle(self, *args, **options):
        sizes_str = options["sizes"]
        sizes = [int(s.strip()) for s in sizes_str.split(",")]
        out_dir = Path(options["out"])
        out_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("=" * 80)
        self.stdout.write("ETL PERFORMANCE BENCHMARK")
        self.stdout.write("=" * 80)

        results = {
            "sizes": sizes,
            "benchmarks": [],
        }

        for size in sizes:
            self.stdout.write(f"\n📊 Benchmarking com {size} usuários...")
            benchmark_result = self._benchmark_size(size)
            results["benchmarks"].append(benchmark_result)

            self.stdout.write(f"   ✅ normalize_text: {benchmark_result['normalize_text_ms']:.2f}ms")
            self.stdout.write(f"   ✅ name_matching: {benchmark_result['name_matching_ms']:.2f}ms")
            self.stdout.write(f"   ✅ top_aggregation: {benchmark_result['top_aggregation_ms']:.2f}ms")
            self.stdout.write(f"   ✅ memory_peak: {benchmark_result['memory_peak_mb']:.2f}MB")

        # Salvar relatório
        report_path = out_dir / "benchmark_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"✅ Benchmark concluído: {report_path}")
        self.stdout.write("=" * 80)

    def _benchmark_size(self, size):
        """Executa benchmarks para um tamanho específico de dataset."""
        # Gerar dados sintéticos
        synthetic_names = self._generate_synthetic_names(size)
        synthetic_map = {
            normalize_text(name): {"nome": name, "email": f"{i}@example.com", "cpf": ""}
            for i, name in enumerate(synthetic_names)
        }

        tracemalloc.start()
        peak_memory = 0

        # Benchmark 1: normalize_text (operação básica)
        start = time.perf_counter()
        for name in synthetic_names:
            normalize_text(name)
        normalize_elapsed = (time.perf_counter() - start) * 1000  # ms

        # Benchmark 2: name_matching (operação complexa)
        start = time.perf_counter()
        for name in synthetic_names[:min(100, size)]:  # Limitar a 100 para evitar O(n²) explosão
            match_by_name(name, synthetic_map)
        matching_elapsed = (time.perf_counter() - start) * 1000  # ms

        # Benchmark 3: top_aggregation (ordenação + limite)
        freq_map = {name: i % 50 for i, name in enumerate(synthetic_names)}  # Frequências sintéticas
        start = time.perf_counter()
        top_users = sorted(
            freq_map.items(),
            key=lambda x: (-x[1], x[0])
        )[:constants.TOP_UNKNOWN_USERS_LIMIT]
        aggregation_elapsed = (time.perf_counter() - start) * 1000  # ms

        # Medir memória pico
        current, peak = tracemalloc.get_traced_memory()
        peak_memory = peak / (1024 * 1024)  # MB
        tracemalloc.stop()

        return {
            "size": size,
            "normalize_text_ms": normalize_elapsed,
            "name_matching_ms": matching_elapsed,
            "top_aggregation_ms": aggregation_elapsed,
            "memory_peak_mb": peak_memory,
        }

    def _generate_synthetic_names(self, count):
        """Gera nomes sintéticos para benchmark."""
        first_names = ["João", "Maria", "Pedro", "Ana", "Carlos", "Juliana", "Lucas", "Beatriz"]
        last_names = ["Silva", "Santos", "Oliveira", "Costa", "Souza", "Lima", "Pereira", "Ferreira"]

        names = []
        for i in range(count):
            first = first_names[i % len(first_names)]
            last = last_names[(i // len(first_names)) % len(last_names)]
            # Adicionar variação para evitar duplicatas exatas
            suffix = f" {chr(65 + (i // 64))}" if i >= 64 else ""
            names.append(f"{first} {last}{suffix}")

        return names
