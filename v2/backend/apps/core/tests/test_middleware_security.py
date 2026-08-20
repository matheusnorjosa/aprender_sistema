"""
Tests for SecurityHeadersMiddleware — CSP configuration.

Covers:
- SEC-CSP-01 (#1103): unsafe-eval conditional on environment
- CSP mode (enforce vs report-only)
- Permissions-Policy always present
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.test import TestCase, override_settings


class TestCSPUnsafeEval(TestCase):
    """SEC-CSP-01: unsafe-eval only in development."""

    @override_settings(ENVIRONMENT="production")
    def test_production_csp_no_unsafe_eval(self):
        """Production CSP must NOT contain unsafe-eval in script-src."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        assert "unsafe-eval" not in csp, f"Production CSP should not have unsafe-eval: {csp}"

    @override_settings(ENVIRONMENT="development")
    def test_development_csp_has_unsafe_eval(self):
        """Development CSP must contain unsafe-eval (React hot reload)."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        assert "unsafe-eval" in csp, f"Development CSP should have unsafe-eval: {csp}"

    @override_settings(ENVIRONMENT="production")
    def test_csp_always_has_unsafe_inline_for_styles(self):
        """style-src must always include unsafe-inline (Ant Design needs it)."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        assert "style-src 'self' 'unsafe-inline'" in csp, f"style-src missing unsafe-inline: {csp}"

    @override_settings(ENVIRONMENT="production")
    def test_production_csp_script_src_has_no_unsafe_inline(self):
        """SEC-004 (#1462): script-src must NOT contain unsafe-inline."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        # Isola a diretiva script-src (style-src legitimamente mantém 'unsafe-inline').
        script_directive = next((d for d in csp.split(";") if d.strip().startswith("script-src")), "")
        assert script_directive, f"script-src directive missing: {csp}"
        assert "unsafe-inline" not in script_directive, f"script-src should not have unsafe-inline: {csp}"

    def test_csp_connect_src_has_no_github(self):
        """G8 (#1462): connect-src must not allowlist api.github.com (sem consumidor)."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        assert "api.github.com" not in csp, f"connect-src should not have api.github.com: {csp}"


class TestCSPMode(TestCase):
    """CSP mode: enforce vs report-only."""

    def test_csp_header_present(self):
        """CSP header must be present on responses."""
        response = self.client.get("/healthz/")
        has_csp = "Content-Security-Policy" in response or "Content-Security-Policy-Report-Only" in response
        assert has_csp, "No CSP header found"

    def test_csp_has_frame_ancestors_none(self):
        """CSP must block framing (clickjacking prevention)."""
        response = self.client.get("/healthz/")
        csp = response.get("Content-Security-Policy", "") or response.get("Content-Security-Policy-Report-Only", "")
        assert "frame-ancestors 'none'" in csp


class TestPermissionsPolicy(TestCase):
    """Permissions-Policy header tests."""

    def test_permissions_policy_present(self):
        """Permissions-Policy must be present."""
        response = self.client.get("/healthz/")
        assert "Permissions-Policy" in response

    def test_permissions_policy_blocks_camera(self):
        """Camera must be blocked."""
        response = self.client.get("/healthz/")
        pp = response.get("Permissions-Policy", "")
        assert "camera=()" in pp
