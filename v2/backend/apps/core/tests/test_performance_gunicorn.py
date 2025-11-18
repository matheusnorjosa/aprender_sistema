"""
Performance tests for CP1 - Gunicorn optimization.

Tests validate that the application can handle increased concurrent load
after Gunicorn workers/threads configuration.

Target: 100-200 req/s (baseline: 10-50 req/s)
"""
import concurrent.futures
import time

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.mark.performance
@pytest.mark.skip(reason="Performance tests should be run manually in staging/production, not in CI")
@pytest.mark.django_db
class TestGunicornPerformance:
    """
    Performance tests for Gunicorn optimization (CP1).

    NOTE: These tests are skipped in CI because:
    - ThreadPoolExecutor + force_login() doesn't work reliably in test environment
    - Performance tests require production-like environment (multiple Gunicorn workers)
    - CI runs with single worker for deterministic testing

    To run these tests manually in staging/production:
    1. Deploy with Gunicorn workers configured (CP1)
    2. Run: pytest -v -m performance apps/core/tests/test_performance_gunicorn.py
    3. Or use manual benchmarks with ab/wrk (see TestManualBenchmark docstring)
    """

    @pytest.fixture
    def api_client(self):
        """Create API client."""
        return Client()

    @pytest.fixture
    def authenticated_user(self, db):
        """Create authenticated user."""
        user = User.objects.create_user(
            username="perf_test_user",
            email="perf@test.com",
            password="testpass123",
        )
        return user

    def test_concurrent_api_requests(self, api_client, authenticated_user):
        """
        Test application handles concurrent requests without errors.

        Validates:
        - No 500 errors under concurrent load
        - Response times are reasonable
        - All workers handle requests correctly
        """
        # Login
        api_client.force_login(authenticated_user)

        # Endpoint to test (lightweight endpoint)
        url = "/api/me/"

        # Test parameters
        num_requests = 50  # Total requests
        num_workers = 10  # Concurrent workers

        def make_request(request_id):
            """Make single request and return (status_code, duration)."""
            start = time.time()
            response = api_client.get(url)
            duration = time.time() - start
            return (request_id, response.status_code, duration)

        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Validate results
        status_codes = [r[1] for r in results]
        durations = [r[2] for r in results]

        # All requests should succeed (200 OK)
        assert all(
            code == 200 for code in status_codes
        ), f"Some requests failed: {status_codes}"

        # Calculate statistics
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        # Log statistics (pytest will capture this with -v)
        print(f"\n📊 Performance Statistics:")
        print(f"  Total requests: {num_requests}")
        print(f"  Concurrent workers: {num_workers}")
        print(f"  Average response time: {avg_duration:.3f}s")
        print(f"  Min response time: {min_duration:.3f}s")
        print(f"  Max response time: {max_duration:.3f}s")
        print(f"  Success rate: {len([c for c in status_codes if c == 200])/len(status_codes)*100:.1f}%")

        # Validate performance thresholds
        # With Gunicorn optimization, 95% of requests should complete in < 1s
        p95_duration = sorted(durations)[int(0.95 * len(durations))]
        assert p95_duration < 1.0, f"P95 latency too high: {p95_duration:.3f}s > 1.0s"

    def test_no_worker_timeout_on_load(self, api_client, authenticated_user):
        """
        Test workers don't timeout under sustained load.

        Validates GUNICORN_TIMEOUT=120 configuration.
        """
        api_client.force_login(authenticated_user)
        url = "/api/me/"

        # Sustained load test: 100 requests over 10 seconds
        num_requests = 100
        duration = 10  # seconds
        interval = duration / num_requests

        start_time = time.time()
        errors = []

        for i in range(num_requests):
            try:
                response = api_client.get(url)
                if response.status_code != 200:
                    errors.append(f"Request {i}: status {response.status_code}")
            except Exception as e:
                errors.append(f"Request {i}: {type(e).__name__}: {e}")

            # Maintain target request rate
            elapsed = time.time() - start_time
            expected_time = (i + 1) * interval
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)

        assert not errors, f"Errors during sustained load: {errors[:5]}"  # Show first 5 errors


@pytest.mark.performance
@pytest.mark.skip(reason="Manual benchmark - requires Apache Bench (ab) or wrk")
class TestManualBenchmark:
    """
    Manual benchmark instructions for CP1 validation.

    Run these commands manually to validate throughput improvement:

    # Baseline (before CP1):
    # Expected: 10-50 req/s

    # After CP1 optimization:
    # Expected: 100-200 req/s

    Using Apache Bench (ab):
    ```bash
    # Install: sudo apt-get install apache2-utils (Linux) or brew install ab (macOS)

    # Test GET /api/me/ (authenticated endpoint)
    ab -n 1000 -c 10 -H "Cookie: sessionid=<valid_session>" http://localhost:8002/api/me/

    # Test GET /api/projetos/ (list endpoint)
    ab -n 1000 -c 10 -H "Cookie: sessionid=<valid_session>" http://localhost:8002/api/projetos/
    ```

    Using wrk (more advanced):
    ```bash
    # Install: sudo apt-get install wrk (Linux) or brew install wrk (macOS)

    # Test with 10 connections for 30 seconds
    wrk -t4 -c10 -d30s --header "Cookie: sessionid=<valid_session>" http://localhost:8002/api/me/

    # Expected output after CP1:
    # Requests/sec: 100-200 (baseline: 10-50)
    # Latency p50: <50ms
    # Latency p95: <200ms
    ```

    Metrics to track:
    - Throughput (req/s): Should increase 2-4x
    - Latency P50/P95: Should remain stable or improve
    - Error rate: Should remain 0%
    """

    def test_manual_benchmark_placeholder(self):
        """Placeholder for manual benchmark documentation."""
        pytest.skip("Run manual benchmarks using ab or wrk (see docstring)")
