"""
AS v2 — Load Testing with Locust (Gap 7 - PLAN_maturity_gaps.md)

Run load tests against the API to validate horizontal scaling.

Usage:
    # Start locust web UI
    cd v2/tests/load
    locust -f locustfile.py --host=http://localhost:8000

    # Headless mode (CI)
    locust -f locustfile.py --host=http://localhost:8000 \
        --headless -u 50 -r 5 -t 5m \
        --html=report.html

Test Scenarios:
    - Smoke: 10 users, 1/s spawn rate, 1 min
    - Load: 50 users, 5/s spawn rate, 5 min
    - Stress: 100 users, 10/s spawn rate, 10 min
    - Spike: 200 users, 50/s spawn rate, 2 min
"""

from locust import HttpUser, task, between, events
import time
import json


class QuickTest(HttpUser):
    """Light user that tests public endpoints only."""

    wait_time = between(1, 3)
    weight = 3  # 3x more frequent than AuthenticatedUser

    @task(5)
    def health_check(self):
        """GET /healthz/ - should be < 30ms p95."""
        self.client.get("/healthz/")

    @task(2)
    def detailed_health_check(self):
        """GET /healthz/detailed/ - checks DB and Redis."""
        self.client.get("/healthz/detailed/")


class AuthenticatedUser(HttpUser):
    """Authenticated user that tests API endpoints."""

    wait_time = between(2, 5)
    weight = 1
    token = None

    def on_start(self):
        """Login and get token at start of test."""
        # For load testing, use a test user or mock auth
        # In real scenario, configure test credentials via env vars
        import os

        username = os.getenv("LOAD_TEST_USERNAME", "load_test_user")
        password = os.getenv("LOAD_TEST_PASSWORD", "load_test_pass")

        response = self.client.post(
            "/api/auth/login/",
            json={"username": username, "password": password},
            catch_response=True,
        )

        if response.status_code == 200:
            # Session cookie should be set automatically
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")
            # Continue without auth for public endpoints

    @task(3)
    def get_me(self):
        """GET /api/me/ - should be < 80ms p95."""
        self.client.get("/api/me/")

    @task(2)
    def list_options_municipios(self):
        """GET /api/options/municipios/ - should be < 100ms p95."""
        self.client.get("/api/options/municipios/")

    @task(2)
    def list_options_projetos(self):
        """GET /api/options/projetos/ - should be < 100ms p95."""
        self.client.get("/api/options/projetos/")

    @task(1)
    def list_solicitacoes(self):
        """GET /api/solicitacoes/ - should be < 300ms p95."""
        self.client.get("/api/solicitacoes/")


class AvailabilityUser(HttpUser):
    """User focused on availability/scheduling endpoints."""

    wait_time = between(3, 8)
    weight = 1

    def on_start(self):
        """Login at start."""
        import os

        username = os.getenv("LOAD_TEST_USERNAME", "load_test_user")
        password = os.getenv("LOAD_TEST_PASSWORD", "load_test_pass")

        self.client.post(
            "/api/auth/login/",
            json={"username": username, "password": password},
        )

    @task(3)
    def monthly_availability(self):
        """GET /api/availability/monthly/ - should be < 400ms p95."""
        self.client.get(
            "/api/availability/monthly/",
            params={"year": 2026, "month": 1, "role": "FORMADOR"},
        )

    @task(1)
    def availability_blocks(self):
        """GET /api/availability-blocks/ - should be < 250ms p95."""
        self.client.get("/api/availability-blocks/")


# Event handlers for custom metrics

@events.request.add_listener
def log_request(request_type, name, response_time, response_length, **kwargs):
    """Log slow requests for analysis."""
    if response_time > 1000:  # > 1 second
        print(f"SLOW REQUEST: {request_type} {name} took {response_time}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print summary at end of test."""
    stats = environment.stats

    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)

    # Calculate percentiles
    for entry in stats.entries.values():
        if entry.num_requests > 0:
            p50 = entry.get_response_time_percentile(0.50)
            p95 = entry.get_response_time_percentile(0.95)
            p99 = entry.get_response_time_percentile(0.99)
            err_rate = (entry.num_failures / entry.num_requests) * 100

            print(f"\n{entry.name}:")
            print(f"  Requests: {entry.num_requests}")
            print(f"  Failures: {entry.num_failures} ({err_rate:.2f}%)")
            print(f"  p50: {p50:.0f}ms")
            print(f"  p95: {p95:.0f}ms")
            print(f"  p99: {p99:.0f}ms")

    print("\n" + "=" * 60)
