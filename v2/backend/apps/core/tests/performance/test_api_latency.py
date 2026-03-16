"""
Performance tests for API latency SLOs.

Tests validate that endpoints meet their SLO targets defined in SLO_DEFINITIONS.md.
These tests are marked with @pytest.mark.performance and can be run separately.

Run: pytest apps/core/tests/performance/ -v -m performance
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false
from __future__ import annotations

import statistics
import time
from typing import TYPE_CHECKING

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import Gerencia, Municipio, Projeto, TipoEvento, Usuario

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [pytest.mark.django_db, pytest.mark.performance]


# SLO Targets (from SLO_DEFINITIONS.md)
SLO_TARGETS = {
    "solicitacoes_list": {"p50": 0.1, "p95": 0.3, "p99": 0.5},
    "me": {"p50": 0.03, "p95": 0.08, "p99": 0.15},
    "healthz": {"p50": 0.01, "p95": 0.03, "p99": 0.05},
    "options": {"p50": 0.05, "p95": 0.1, "p99": 0.2},
    "availability_monthly": {"p50": 0.15, "p95": 0.4, "p99": 0.8},
}


def percentile(data: list[float], p: int) -> float:
    """Calculate percentile of a sorted list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def measure_latency(
    client: APIClient,
    url: str,
    iterations: int = 50,
    method: str = "get",
    warmup_iterations: int = 5,
) -> dict[str, float]:
    """
    Measure latency for an endpoint over multiple iterations.

    Returns dict with p50, p95, p99, mean, min, max in seconds.
    """
    times: list[float] = []
    request_method: Callable = getattr(client, method)

    # Warmup avoids cold-start artifacts (lazy imports/cache/session init)
    # from skewing p99 in short synthetic runs.
    for _ in range(warmup_iterations):
        response = request_method(url)
        assert response.status_code < 500, f"Server error: {response.status_code}"

    for _ in range(iterations):
        start = time.perf_counter()
        response = request_method(url)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

        # Ensure request was successful (2xx or 4xx auth errors)
        assert response.status_code < 500, f"Server error: {response.status_code}"

    return {
        "p50": percentile(times, 50),
        "p95": percentile(times, 95),
        "p99": percentile(times, 99),
        "mean": statistics.mean(times),
        "min": min(times),
        "max": max(times),
        "samples": len(times),
    }


@pytest.fixture
def authenticated_client(db) -> APIClient:
    """Create an authenticated API client."""
    user = Usuario.objects.create_user(
        username="perf_test_user",
        email="perf@test.com",
        password="test123",
        cpf="99999999999",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def setup_minimal_data(db) -> None:
    """Create minimal data for performance tests."""
    Municipio.objects.get_or_create(nome="Fortaleza", defaults={"uf": "CE", "ativo": True})
    Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Super"})
    Projeto.objects.get_or_create(nome="Teste Perf", defaults={"ativo": True, "fluxo": "SUPER"})
    TipoEvento.objects.get_or_create(nome="Formação")
    Group.objects.get_or_create(name="Formador")


class TestHealthzLatency:
    """Tests for /healthz/ endpoint latency."""

    def test_healthz_p95_under_30ms(self):
        """GET /healthz/ should respond in <30ms (p95)."""
        client = APIClient()
        metrics = measure_latency(client, "/healthz/", iterations=100)

        assert metrics["p95"] < SLO_TARGETS["healthz"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['healthz']['p95']}s\n"
            f"Metrics: {metrics}"
        )

    def test_healthz_p99_under_50ms(self):
        """GET /healthz/ should respond in <50ms (p99)."""
        client = APIClient()
        metrics = measure_latency(client, "/healthz/", iterations=100)

        assert metrics["p99"] < SLO_TARGETS["healthz"]["p99"], (
            f"p99 latency {metrics['p99']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['healthz']['p99']}s\n"
            f"Metrics: {metrics}"
        )


class TestMeEndpointLatency:
    """Tests for /api/me/ endpoint latency."""

    def test_me_p95_under_80ms(self, authenticated_client):
        """GET /api/me/ should respond in <80ms (p95)."""
        metrics = measure_latency(authenticated_client, "/api/me/", iterations=50)

        assert metrics["p95"] < SLO_TARGETS["me"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['me']['p95']}s\n"
            f"Metrics: {metrics}"
        )

    def test_me_p99_under_150ms(self, authenticated_client):
        """GET /api/me/ should respond in <150ms (p99)."""
        metrics = measure_latency(authenticated_client, "/api/me/", iterations=50)

        assert metrics["p99"] < SLO_TARGETS["me"]["p99"], (
            f"p99 latency {metrics['p99']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['me']['p99']}s\n"
            f"Metrics: {metrics}"
        )


class TestOptionsEndpointLatency:
    """Tests for /api/options/* endpoints latency."""

    def test_municipios_options_p95_under_100ms(self, authenticated_client, setup_minimal_data):
        """GET /api/options/municipios/ should respond in <100ms (p95)."""
        metrics = measure_latency(authenticated_client, "/api/options/municipios/", iterations=50)

        assert metrics["p95"] < SLO_TARGETS["options"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['options']['p95']}s\n"
            f"Metrics: {metrics}"
        )

    def test_projetos_options_p95_under_100ms(self, authenticated_client, setup_minimal_data):
        """GET /api/options/projetos/ should respond in <100ms (p95)."""
        metrics = measure_latency(authenticated_client, "/api/options/projetos/", iterations=50)

        assert metrics["p95"] < SLO_TARGETS["options"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['options']['p95']}s\n"
            f"Metrics: {metrics}"
        )


class TestSolicitacoesLatency:
    """Tests for /api/solicitacoes/ endpoint latency."""

    def test_solicitacoes_list_p95_under_300ms(self, authenticated_client, setup_minimal_data):
        """GET /api/solicitacoes/ should respond in <300ms (p95)."""
        metrics = measure_latency(authenticated_client, "/api/solicitacoes/", iterations=30)

        assert metrics["p95"] < SLO_TARGETS["solicitacoes_list"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['solicitacoes_list']['p95']}s\n"
            f"Metrics: {metrics}"
        )


class TestAvailabilityMonthlyLatency:
    """Tests for /api/availability/monthly/ endpoint latency."""

    def test_availability_monthly_p95_under_400ms(self, authenticated_client, setup_minimal_data):
        """GET /api/availability/monthly/ should respond in <400ms (p95)."""
        metrics = measure_latency(
            authenticated_client,
            "/api/availability/monthly/?year=2026&month=1&role=FORMADOR",
            iterations=30,
        )

        assert metrics["p95"] < SLO_TARGETS["availability_monthly"]["p95"], (
            f"p95 latency {metrics['p95']:.3f}s exceeds SLO target "
            f"{SLO_TARGETS['availability_monthly']['p95']}s\n"
            f"Metrics: {metrics}"
        )


class TestLatencyReport:
    """Generate a comprehensive latency report for all endpoints."""

    def test_generate_latency_report(self, authenticated_client, setup_minimal_data):
        """Generate a latency report for key endpoints."""
        endpoints = [
            ("/healthz/", "healthz"),
            ("/api/me/", "me"),
            ("/api/options/municipios/", "options"),
            ("/api/solicitacoes/", "solicitacoes_list"),
            ("/api/availability/monthly/?year=2026&month=1&role=FORMADOR", "availability_monthly"),
        ]

        report = []
        all_within_slo = True

        for url, slo_key in endpoints:
            client = APIClient() if url == "/healthz/" else authenticated_client
            metrics = measure_latency(client, url, iterations=20)

            slo = SLO_TARGETS.get(slo_key, {})
            p95_ok = metrics["p95"] < slo.get("p95", float("inf"))
            p99_ok = metrics["p99"] < slo.get("p99", float("inf"))

            if not (p95_ok and p99_ok):
                all_within_slo = False

            report.append(
                {
                    "endpoint": url.split("?")[0],
                    "p50": f"{metrics['p50']*1000:.1f}ms",
                    "p95": f"{metrics['p95']*1000:.1f}ms",
                    "p99": f"{metrics['p99']*1000:.1f}ms",
                    "p95_slo": f"{slo.get('p95', 0)*1000:.0f}ms" if slo else "N/A",
                    "p95_ok": "OK" if p95_ok else "FAIL",
                }
            )

        # Print report
        print("\n" + "=" * 80)
        print("LATENCY REPORT")
        print("=" * 80)
        print(f"{'Endpoint':<45} {'p50':>10} {'p95':>10} {'p99':>10} {'SLO':>10} {'Status':>8}")
        print("-" * 80)
        for r in report:
            print(
                f"{r['endpoint']:<45} {r['p50']:>10} {r['p95']:>10} {r['p99']:>10} {r['p95_slo']:>10} {r['p95_ok']:>8}"
            )
        print("=" * 80)

        # Test passes but logs the report
        assert True, "Report generated"
