"""
AS v2 — Monthly Grid Benchmark (ASQ-004, issue #777)

Micro-benchmark the `build_monthly_grid` service against the current
database. Reports wall-time percentiles and query count per call so the
service's p95 can be tracked across PRs.

Usage:
    python manage.py bench_monthly_grid --year 2026 --month 4 --role FORMADOR --iterations 20

The command runs `iterations` sequential calls and prints:
- p50/p95/p99 wall time (ms)
- mean query count per call
- first-call vs cold-DB baseline
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportUntypedBaseClass=false

from __future__ import annotations

import json
import statistics
import time
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import connection, reset_queries

from apps.core.services.monthly_grid_service import build_monthly_grid


class Command(BaseCommand):
    help = "Benchmark build_monthly_grid wall time + query count (ASQ-004)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--month", type=int, required=True)
        parser.add_argument(
            "--role",
            type=str,
            default="FORMADOR",
            choices=["FORMADOR", "COORDENADOR"],
        )
        parser.add_argument("--gerencia-id", type=int, default=None)
        parser.add_argument("--sector", type=str, default=None)
        parser.add_argument("--iterations", type=int, default=20)
        parser.add_argument(
            "--warmup",
            type=int,
            default=2,
            help="Warm-up iterations excluded from the percentile calc.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit results as JSON (for CI artifacts).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        year: int = options["year"]
        month: int = options["month"]
        role: str = options["role"]
        gerencia_id = options["gerencia_id"]
        sector: str | None = options["sector"]
        iterations: int = options["iterations"]
        warmup: int = options["warmup"]
        emit_json: bool = options["json"]

        kwargs = dict(
            year=year,
            month=month,
            role=role,
            gerencia_id=gerencia_id,
            sector=sector,
        )

        # Temporarily enable query logging for this process.
        _prev_debug = connection.force_debug_cursor
        connection.force_debug_cursor = True

        samples_ms: list[float] = []
        query_counts: list[int] = []

        try:
            total_runs = warmup + iterations
            for idx in range(total_runs):
                reset_queries()
                t0 = time.perf_counter()
                build_monthly_grid(**kwargs)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                q_count = len(connection.queries)

                if idx >= warmup:
                    samples_ms.append(elapsed_ms)
                    query_counts.append(q_count)
        finally:
            connection.force_debug_cursor = _prev_debug
            reset_queries()

        samples_ms.sort()
        summary: dict[str, Any] = {
            "year": year,
            "month": month,
            "role": role,
            "gerencia_id": gerencia_id,
            "sector": sector,
            "iterations": iterations,
            "warmup": warmup,
            "wall_time_ms": {
                "min": round(samples_ms[0], 2),
                "p50": round(statistics.median(samples_ms), 2),
                "p95": round(_percentile(samples_ms, 95), 2),
                "p99": round(_percentile(samples_ms, 99), 2),
                "max": round(samples_ms[-1], 2),
                "mean": round(statistics.mean(samples_ms), 2),
            },
            "query_count": {
                "min": min(query_counts),
                "mean": round(statistics.mean(query_counts), 2),
                "max": max(query_counts),
            },
        }

        if emit_json:
            self.stdout.write(json.dumps(summary, indent=2))
            return

        self.stdout.write(self.style.SUCCESS("=== build_monthly_grid benchmark ==="))
        self.stdout.write(
            f"year={year} month={month} role={role} " f"gerencia_id={gerencia_id or '-'} sector={sector or '-'}"
        )
        self.stdout.write(f"iterations={iterations} warmup={warmup}")
        self.stdout.write("")
        self.stdout.write(f"wall-time ms  min={summary['wall_time_ms']['min']}")
        self.stdout.write(f"              p50={summary['wall_time_ms']['p50']}")
        self.stdout.write(f"              p95={summary['wall_time_ms']['p95']}")
        self.stdout.write(f"              p99={summary['wall_time_ms']['p99']}")
        self.stdout.write(f"              max={summary['wall_time_ms']['max']}")
        self.stdout.write(f"              mean={summary['wall_time_ms']['mean']}")
        self.stdout.write("")
        self.stdout.write(
            f"queries/call  min={summary['query_count']['min']} "
            f"mean={summary['query_count']['mean']} "
            f"max={summary['query_count']['max']}"
        )


def _percentile(sorted_samples: list[float], p: int) -> float:
    if not sorted_samples:
        return 0.0
    k = (len(sorted_samples) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_samples) - 1)
    if f == c:
        return sorted_samples[f]
    return sorted_samples[f] + (sorted_samples[c] - sorted_samples[f]) * (k - f)
