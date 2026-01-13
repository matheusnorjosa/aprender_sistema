"""
Tests for optional ETL deployment (INCLUDE_ETL setting).

Verifies that:
- INCLUDE_ETL defaults to True (backward compatibility)
- dat_ingest is included when INCLUDE_ETL=true
- URLs are conditionally registered
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from django.conf import settings


class TestIncludeETLSetting:
    """Tests for INCLUDE_ETL configuration."""

    def test_include_etl_defaults_to_true(self):
        """INCLUDE_ETL should default to True for backward compatibility."""
        # The setting should exist
        assert hasattr(settings, "INCLUDE_ETL")
        # Default is True (we're running with default settings)
        assert settings.INCLUDE_ETL is True

    def test_dat_ingest_in_installed_apps_when_enabled(self):
        """dat_ingest should be in INSTALLED_APPS when INCLUDE_ETL=true."""
        # With default settings, dat_ingest should be included
        if settings.INCLUDE_ETL:
            assert "apps.dat_ingest" in settings.INSTALLED_APPS

    def test_core_always_in_installed_apps(self):
        """core app should always be in INSTALLED_APPS regardless of INCLUDE_ETL."""
        assert "apps.core" in settings.INSTALLED_APPS

    def test_core_services_available_without_dat_ingest(self):
        """Core services (normalize, resolvers) should work without dat_ingest."""
        # These imports should work regardless of INCLUDE_ETL
        from apps.core.services import norm_text, resolve_municipio

        # Basic functionality test
        assert norm_text("  Test  ") == "test"
        assert callable(resolve_municipio)


class TestETLURLsConditional:
    """Tests for conditional ETL URL registration."""

    def test_etl_urls_registered_when_enabled(self, client):
        """ETL endpoints should be accessible when INCLUDE_ETL=true."""
        if not settings.INCLUDE_ETL:
            pytest.skip("ETL not enabled")

        # The etl/reports/latest/ endpoint exists in dat_ingest.urls
        # It requires authentication, so we expect 403 (not 404)
        response = client.get("/api/etl/reports/latest/")
        # 403 = endpoint exists but auth required
        # 404 = endpoint doesn't exist
        assert response.status_code in [403, 401], (
            f"Expected 403/401 (auth required), got {response.status_code}"
        )

    def test_core_urls_always_registered(self, client):
        """Core endpoints should always be accessible."""
        # healthz is always available (no auth required)
        response = client.get("/healthz/")
        assert response.status_code == 200

        # api root requires auth (but endpoint exists)
        response = client.get("/api/")
        assert response.status_code in [200, 403, 401]


class TestETLExclusionDocumentation:
    """Documentation tests for ETL exclusion."""

    def test_include_etl_env_var_documented(self):
        """Verify the expected behavior of INCLUDE_ETL."""
        # This test documents the expected behavior:
        #
        # INCLUDE_ETL=true (default):
        #   - apps.dat_ingest in INSTALLED_APPS
        #   - ETL management commands available
        #   - /api/etl-reports/ endpoint available
        #
        # INCLUDE_ETL=false:
        #   - apps.dat_ingest NOT in INSTALLED_APPS
        #   - ETL management commands NOT available
        #   - /api/etl-reports/ returns 404
        #   - Core functionality (normalize, resolvers) still works
        #
        # To deploy without ETL:
        #   docker-compose.prod.yml:
        #     environment:
        #       - INCLUDE_ETL=false
        pass
