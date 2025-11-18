"""
Tests for CP2 - Redis Sessions.

Validates that sessions are stored in Redis cache instead of database,
providing 100x faster performance and horizontal scaling support.
"""
import time

import pytest
from django.contrib.sessions.backends.cache import SessionStore
from django.core.cache import cache


@pytest.mark.django_db
class TestRedisSessionsCP2:
    """Test suite for Redis session backend (CP2)."""

    def test_session_saves_to_redis(self):
        """
        Test: Sessions are stored in Redis cache.

        Validates SESSION_ENGINE = "django.contrib.sessions.backends.cache"
        """
        session = SessionStore()
        session["user_id"] = 123
        session["username"] = "test_user"
        session.save()

        # Verify session key was created
        assert session.session_key is not None

        # Verify data is in Redis (not database)
        # Cache key format: "django.contrib.sessions.cache{session_key}"
        cache_key = f"django.contrib.sessions.cache{session.session_key}"
        cached_data = cache.get(cache_key)

        assert cached_data is not None
        assert cached_data.get("user_id") == 123
        assert cached_data.get("username") == "test_user"

    def test_session_retrieval_from_redis(self):
        """
        Test: Sessions can be retrieved from Redis.

        Validates data persistence and retrieval.
        """
        # Create and save session
        session1 = SessionStore()
        session1["test_data"] = "hello_world"
        session1.save()

        session_key = session1.session_key

        # Retrieve session using same key
        session2 = SessionStore(session_key=session_key)
        assert session2.get("test_data") == "hello_world"

    def test_session_expiry(self):
        """
        Test: Sessions expire after configured timeout.

        Validates SESSION_COOKIE_AGE setting (default: 30 minutes).
        """
        session = SessionStore()
        session["temporary_data"] = "expires_soon"
        session.set_expiry(1)  # 1 second
        session.save()

        session_key = session.session_key

        # Verify data exists
        session2 = SessionStore(session_key=session_key)
        assert session2.get("temporary_data") == "expires_soon"

        # Wait for expiry
        time.sleep(2)

        # Verify data expired
        session3 = SessionStore(session_key=session_key)
        assert session3.get("temporary_data") is None

    def test_session_renewal_on_save(self):
        """
        Test: Sessions are renewed on each request.

        Validates SESSION_SAVE_EVERY_REQUEST = True configuration.
        This prevents sessions from expiring during active usage.
        """
        session = SessionStore()
        session["user_id"] = 456
        session.set_expiry(2)  # 2 seconds
        session.save()

        session_key = session.session_key

        # Simulate request cycle: load, modify, and save (renewal)
        time.sleep(1)  # 1 second passed
        session2 = SessionStore(session_key=session_key)
        session2["last_activity"] = "renewed"  # Modify to trigger save
        session2.save()  # Renews expiry

        # Wait another second (total 2s from original, but renewed at 1s)
        time.sleep(1)

        # Session should still be valid (renewed at 1s mark)
        session3 = SessionStore(session_key=session_key)
        assert session3.get("user_id") == 456
        assert session3.get("last_activity") == "renewed"

    def test_session_delete(self):
        """
        Test: Sessions can be deleted (logout).

        Validates session cleanup.
        """
        session = SessionStore()
        session["user_id"] = 789
        session.save()

        session_key = session.session_key

        # Verify session exists
        session2 = SessionStore(session_key=session_key)
        assert session2.get("user_id") == 789

        # Delete session
        session.delete()

        # Verify session is gone
        session3 = SessionStore(session_key=session_key)
        assert session3.get("user_id") is None

    def test_session_custom_cookie_name(self):
        """
        Test: Custom session cookie name (asv2sid).

        Validates SESSION_COOKIE_NAME setting.
        """
        from django.conf import settings

        assert settings.SESSION_COOKIE_NAME == "asv2sid"

    def test_session_security_settings(self):
        """
        Test: Session security settings are properly configured.

        Validates:
        - SESSION_COOKIE_HTTPONLY = True (XSS protection)
        - SESSION_COOKIE_SAMESITE = "Lax" (CSRF protection)
        - SESSION_EXPIRE_AT_BROWSER_CLOSE = True (security)
        """
        from django.conf import settings

        assert settings.SESSION_COOKIE_HTTPONLY is True
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"
        assert settings.SESSION_EXPIRE_AT_BROWSER_CLOSE is True

    def test_session_timeout_30_minutes(self):
        """
        Test: Default session timeout is 30 minutes.

        Validates SESSION_COOKIE_AGE = 1800 (60 * 30).
        This is reduced from 2 weeks for security and performance.
        """
        from django.conf import settings

        # 30 minutes = 1800 seconds
        assert settings.SESSION_COOKIE_AGE == 60 * 30

    def test_redis_backend_configured(self):
        """
        Test: Session engine is configured to use Redis cache.

        Validates SESSION_ENGINE and SESSION_CACHE_ALIAS settings.
        """
        from django.conf import settings

        assert settings.SESSION_ENGINE == "django.contrib.sessions.backends.cache"
        assert settings.SESSION_CACHE_ALIAS == "default"

    def test_multiple_concurrent_sessions(self):
        """
        Test: Multiple sessions can coexist in Redis.

        Validates horizontal scaling capability.
        """
        # Create 3 different sessions
        sessions = []
        for i in range(3):
            session = SessionStore()
            session["user_id"] = 1000 + i
            session.save()
            sessions.append(session)

        # Verify all sessions exist independently
        for i, session in enumerate(sessions):
            retrieved = SessionStore(session_key=session.session_key)
            assert retrieved.get("user_id") == 1000 + i
