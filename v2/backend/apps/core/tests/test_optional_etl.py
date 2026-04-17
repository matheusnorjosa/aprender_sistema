"""
Tests verifying ETL module removal (#967, #971).

Verifies that:
- INCLUDE_ETL is always False (module removed)
- dat_ingest is not in INSTALLED_APPS
- Core services work independently
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.conf import settings


class TestETLRemoved:
    """Tests verifying ETL module is fully removed."""

    def test_include_etl_is_false(self):
        """INCLUDE_ETL must be False (module removed #971)."""
        assert settings.INCLUDE_ETL is False

    def test_dat_ingest_not_in_installed_apps(self):
        """dat_ingest must NOT be in INSTALLED_APPS."""
        assert "apps.dat_ingest" not in settings.INSTALLED_APPS

    def test_core_always_in_installed_apps(self):
        """core app must always be present."""
        assert "apps.core" in settings.INSTALLED_APPS

    def test_core_services_work_without_dat_ingest(self):
        """Core services (normalize, resolvers) work independently."""
        from apps.core.services import norm_text, resolve_municipio

        assert norm_text("  Test  ") == "test"
        assert callable(resolve_municipio)

    def test_etl_endpoint_returns_404(self, client):
        """ETL endpoints must return 404."""
        response = client.get("/api/etl/reports/latest/")
        assert response.status_code == 404
