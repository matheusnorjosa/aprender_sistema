"""
Tests for /api/auth/ping/ endpoint (CP5 - Issue #164)

Session keep-alive functionality:
- POST /api/auth/ping/ renews session
- Returns session_age from settings
- Requires authentication
- Works with SESSION_SAVE_EVERY_REQUEST=True
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

Usuario = get_user_model()


@pytest.fixture
def authenticated_client(db):
    """Client with authenticated user."""
    client = APIClient()
    user = Usuario.objects.create_user(
        username="testuser",
        password="testpass123",
        email="test@example.com",
        cpf="12345678901"
    )
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
class TestAuthPing:
    """Tests for /api/auth/ping/ endpoint."""

    def test_ping_requires_authentication(self):
        """POST /api/auth/ping/ requires authentication."""
        client = APIClient()
        response = client.post('/api/auth/ping/')

        # DRF with IsAuthenticated returns 403 Forbidden for unauthenticated requests
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_ping_renews_session(self, authenticated_client):
        """POST /api/auth/ping/ renews session successfully."""
        client, user = authenticated_client

        response = client.post('/api/auth/ping/')

        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert response.data['message'] == 'Session renewed'

    def test_ping_returns_session_age(self, authenticated_client):
        """POST /api/auth/ping/ returns session_age from settings."""
        client, user = authenticated_client

        response = client.post('/api/auth/ping/')

        assert response.status_code == status.HTTP_200_OK
        assert 'session_age' in response.data

        # Should match SESSION_COOKIE_AGE from settings
        expected_age = getattr(settings, 'SESSION_COOKIE_AGE', 1800)
        assert response.data['session_age'] == expected_age

    def test_ping_with_cp2_session_cookie_age(self, authenticated_client, settings):
        """Ping returns CP2 session age (30 min = 1800s)."""
        client, user = authenticated_client

        # CP2: SESSION_COOKIE_AGE=1800 (30 min)
        settings.SESSION_COOKIE_AGE = 1800

        response = client.post('/api/auth/ping/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['session_age'] == 1800  # 30 minutes

    def test_ping_does_not_accept_get(self, authenticated_client):
        """GET /api/auth/ping/ is not allowed (only POST)."""
        client, user = authenticated_client

        response = client.get('/api/auth/ping/')

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_ping_modifies_session(self, authenticated_client):
        """Ping marks session as modified."""
        client, user = authenticated_client

        # Get session before ping
        response_before = client.get('/api/me/')
        assert response_before.status_code == status.HTTP_200_OK

        # Ping endpoint
        response_ping = client.post('/api/auth/ping/')
        assert response_ping.status_code == status.HTTP_200_OK

        # Session should still be valid
        response_after = client.get('/api/me/')
        assert response_after.status_code == status.HTTP_200_OK
        assert response_after.data['id'] == user.id
