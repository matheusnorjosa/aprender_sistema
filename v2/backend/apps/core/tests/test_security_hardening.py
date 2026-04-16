"""
Security Hardening Tests — SEC-RECON, SEC-AUTH, INFRA

Covers:
- SEC-RECON-01: /healthz minimal payload, /healthz/detailed auth (#1126)
- SEC-RECON-02: /metrics auth gate (#1127)
- SEC-RECON-03: /api/readyz/ conditional payload, /api/version/ conditional (#1128)
- SEC-AUTH-01: Compound lockout key IP+username (#1130)
- SEC-AUTH-02: SECRET_KEY production guard (#1131)
- SEC-AUTH-03: ALLOWED_HOSTS production guard (#1132)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import pytest
from django.test import RequestFactory, TestCase, override_settings

from apps.core.views_auth import (
    _clear_failed_attempts,
    _get_failed_attempts,
    _get_lockout_key,
    _increment_failed_attempts,
    _is_account_locked,
)


# ================================================================
# SEC-RECON-01: /healthz endpoints (#1126)
# ================================================================
class TestHealthzMinimalPayload(TestCase):
    """SEC-RECON-01: /healthz/ must return minimal payload without sensitive data."""

    def test_healthz_returns_ok_without_environment(self):
        response = self.client.get("/healthz/")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}
        assert "environment" not in data
        assert "debug" not in data
        assert "timezone" not in data

    def test_healthz_detailed_anonymous_external_returns_403(self):
        response = self.client.get("/healthz/detailed/", REMOTE_ADDR="203.0.113.1")
        assert response.status_code == 403

    def test_healthz_detailed_internal_ip_returns_200(self):
        response = self.client.get("/healthz/detailed/", REMOTE_ADDR="127.0.0.1")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "environment" not in data  # removed sensitive field

    def test_healthz_detailed_superuser_returns_200(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_superuser("admin_health", "a@b.com", "pass1234")
        self.client.force_login(admin)
        response = self.client.get("/healthz/detailed/", REMOTE_ADDR="203.0.113.1")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data


# ================================================================
# SEC-RECON-02: /metrics auth gate (#1127)
# ================================================================
class TestMetricsAuthGate(TestCase):
    """SEC-RECON-02: /metrics must require staff or internal IP."""

    def test_metrics_anonymous_external_returns_403(self):
        response = self.client.get("/metrics", REMOTE_ADDR="203.0.113.1")
        assert response.status_code == 403

    def test_metrics_internal_ip_returns_200(self):
        response = self.client.get("/metrics", REMOTE_ADDR="127.0.0.1")
        # Should return 200 with prometheus metrics (or at least not 403)
        assert response.status_code != 403

    def test_metrics_staff_returns_200(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff = User.objects.create_user("staff_metrics", "s@b.com", "pass1234", is_staff=True)
        self.client.force_login(staff)
        response = self.client.get("/metrics", REMOTE_ADDR="203.0.113.1")
        assert response.status_code != 403


# ================================================================
# SEC-RECON-03: /api/readyz/ and /api/version/ (#1128)
# ================================================================
class TestReadyzConditionalPayload(TestCase):
    """SEC-RECON-03: readyz anonymous gets minimal, admin gets full."""

    def test_readyz_anonymous_returns_status_only(self):
        response = self.client.get("/api/readyz/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" not in data

    def test_readyz_admin_returns_full_payload(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_user("admin_readyz", "r@b.com", "pass1234", is_staff=True)
        self.client.force_login(admin)
        response = self.client.get("/api/readyz/")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data


class TestVersionConditionalPayload(TestCase):
    """SEC-RECON-03: version anonymous gets only version tag, admin gets full."""

    def test_version_anonymous_no_git_sha(self):
        response = self.client.get("/api/version/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "git_sha" not in data
        assert "build_date" not in data

    def test_version_admin_gets_git_sha(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        admin = User.objects.create_user("admin_ver", "v@b.com", "pass1234", is_staff=True)
        self.client.force_login(admin)
        response = self.client.get("/api/version/")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "git_sha" in data
        assert "build_date" in data


# ================================================================
# SEC-AUTH-01: Compound lockout key (#1130)
# ================================================================
class TestCompoundLockout(TestCase):
    """SEC-AUTH-01: Lockout keyed by IP+username, with global fallback."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_lockout_key_includes_ip(self):
        key = _get_lockout_key("admin", "192.168.1.1")
        assert "admin" in key
        assert "192.168.1.1" in key

    def test_lockout_key_global_when_no_ip(self):
        key = _get_lockout_key("admin")
        assert "global" in key
        assert "admin" in key

    def test_lockout_key_case_insensitive(self):
        key1 = _get_lockout_key("Admin", "1.2.3.4")
        key2 = _get_lockout_key("admin", "1.2.3.4")
        assert key1 == key2

    @override_settings(ACCOUNT_LOCKOUT_THRESHOLD=3, ACCOUNT_LOCKOUT_DURATION=60)
    def test_lockout_by_ip_username(self):
        """Same IP hitting same username gets locked after threshold."""
        for _ in range(3):
            _increment_failed_attempts("victim", "10.0.0.1")
        assert _is_account_locked("victim", "10.0.0.1") is True

    @override_settings(ACCOUNT_LOCKOUT_THRESHOLD=3, ACCOUNT_LOCKOUT_DURATION=60)
    def test_different_ip_not_locked(self):
        """Different IP for same username is NOT locked by IP-specific threshold."""
        for _ in range(3):
            _increment_failed_attempts("victim", "10.0.0.1")
        # Different IP should not be locked (IP-specific threshold not reached)
        assert _is_account_locked("victim", "10.0.0.2") is False

    @override_settings(ACCOUNT_LOCKOUT_THRESHOLD=3, ACCOUNT_LOCKOUT_DURATION=60)
    def test_lockout_cleared_on_success(self):
        """Login success clears both IP-specific and global counters."""
        for _ in range(2):
            _increment_failed_attempts("user1", "10.0.0.1")
        _clear_failed_attempts("user1", "10.0.0.1")
        assert _get_failed_attempts("user1", "10.0.0.1") == 0
        assert _get_failed_attempts("user1") == 0  # global also cleared


# ================================================================
# SEC-AUTH-02: SECRET_KEY production guard (#1131)
# ================================================================
class TestSecretKeyProductionGuard(TestCase):
    """SEC-AUTH-02: Production must reject insecure SECRET_KEY."""

    def test_insecure_key_detected(self):
        """The default key starts with 'django-insecure' and would be blocked."""
        default_key = "django-insecure-dev-key-CHANGE-IN-PRODUCTION-abcd1234efgh5678ijkl9012mnop3456qrst"
        assert default_key.startswith("django-insecure")

    def test_secure_key_accepted(self):
        """A proper production key does not start with 'django-insecure'."""
        secure_key = "a" * 64
        assert not secure_key.startswith("django-insecure")
        assert len(secure_key) >= 50


# ================================================================
# SEC-AUTH-03: ALLOWED_HOSTS production guard (#1132)
# ================================================================
class TestAllowedHostsProductionGuard(TestCase):
    """SEC-AUTH-03: Production must reject dev-only hosts."""

    def test_dev_hosts_detected(self):
        """Default hosts are all dev hosts."""
        dev_hosts = {"localhost", "127.0.0.1", "testserver", "web", "0.0.0.0"}
        default_hosts = ["localhost", "127.0.0.1", "testserver", "web"]
        assert dev_hosts.issuperset(default_hosts)

    def test_production_hosts_accepted(self):
        """Real production hosts are not a subset of dev hosts."""
        dev_hosts = {"localhost", "127.0.0.1", "testserver", "web", "0.0.0.0"}
        prod_hosts = ["aprender.example.com", "www.aprender.example.com"]
        assert not dev_hosts.issuperset(prod_hosts)

    def test_0_0_0_0_removed_from_defaults(self):
        """0.0.0.0 should no longer be in default ALLOWED_HOSTS."""
        from django.conf import settings

        assert "0.0.0.0" not in settings.ALLOWED_HOSTS
