"""
Testes para comando benchmark_etl.

Valida que o comando executa sem erros e gera relatório JSON.

Issue #55: Revisão de performance com microbenchmarks.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false

from __future__ import annotations
import json
import pytest
from pathlib import Path
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_benchmark_executes_successfully(tmp_path):
    """Benchmark executa sem erros e gera relatório."""
    out_dir = tmp_path / "benchmark_output"
    out_dir.mkdir()

    # Executar benchmark com dataset minúsculo (10 users)
    call_command(
        "benchmark_etl",
        sizes="10",
        out=str(out_dir),
    )

    # Verificar que relatório foi gerado
    report_path = out_dir / "benchmark_report.json"
    assert report_path.exists(), "Relatório não foi gerado"

    # Verificar estrutura do relatório
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "sizes" in report
    assert "benchmarks" in report
    assert report["sizes"] == [10]
    assert len(report["benchmarks"]) == 1

    # Verificar métricas do benchmark
    benchmark = report["benchmarks"][0]
    assert benchmark["size"] == 10
    assert "normalize_text_ms" in benchmark
    assert "name_matching_ms" in benchmark
    assert "top_aggregation_ms" in benchmark
    assert "memory_peak_mb" in benchmark

    # Verificar que métricas são números válidos
    assert benchmark["normalize_text_ms"] >= 0
    assert benchmark["name_matching_ms"] >= 0
    assert benchmark["top_aggregation_ms"] >= 0
    assert benchmark["memory_peak_mb"] >= 0


def test_benchmark_multiple_sizes(tmp_path):
    """Benchmark suporta múltiplos tamanhos."""
    out_dir = tmp_path / "benchmark_output"
    out_dir.mkdir()

    # Executar com 2 tamanhos
    call_command(
        "benchmark_etl",
        sizes="10,20",
        out=str(out_dir),
    )

    # Verificar que relatório contém 2 benchmarks
    report_path = out_dir / "benchmark_report.json"
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert len(report["benchmarks"]) == 2
    assert report["benchmarks"][0]["size"] == 10
    assert report["benchmarks"][1]["size"] == 20
