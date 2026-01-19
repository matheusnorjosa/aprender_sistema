"""
Tests for API versioning (#410).

Validates:
- /api/v1/ endpoints work correctly
- /api/ backward compatible endpoints work
- Deprecation decorator adds proper headers
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.test import TestCase
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from apps.core.deprecation import deprecated_endpoint
from apps.core.models import Usuario


class TestAPIVersioning(TestCase):
    """Tests for API versioning configuration."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        # Create a user for authenticated endpoints
        self.user = Usuario.objects.create_user(
            username="test_versioning",
            email="test_versioning@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_v1_endpoint_works(self) -> None:
        """Versioned endpoint /api/v1/ should work."""
        # Test CSRF endpoint which is AllowAny
        self.client.logout()  # Test without auth
        response = self.client.get("/api/v1/csrf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.json())

    def test_unversioned_endpoint_works(self) -> None:
        """Backward compatible /api/ endpoint should work."""
        self.client.logout()
        response = self.client.get("/api/csrf/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrfToken", response.json())

    def test_v1_and_unversioned_return_same_data(self) -> None:
        """Both /api/v1/ and /api/ should return identical data."""
        self.client.logout()

        # Get from versioned endpoint
        response_v1 = self.client.get("/api/v1/csrf/")

        # Get from unversioned endpoint
        response_unversioned = self.client.get("/api/csrf/")

        # Both should succeed
        self.assertEqual(response_v1.status_code, status.HTTP_200_OK)
        self.assertEqual(response_unversioned.status_code, status.HTTP_200_OK)

        # Both should have csrfToken (values may differ due to fresh tokens)
        self.assertIn("csrfToken", response_v1.json())
        self.assertIn("csrfToken", response_unversioned.json())

    def test_v1_authenticated_endpoint(self) -> None:
        """Authenticated v1 endpoint should work with authentication."""
        response = self.client.get("/api/v1/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "test_versioning")

    def test_unversioned_authenticated_endpoint(self) -> None:
        """Authenticated unversioned endpoint should work."""
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["username"], "test_versioning")


class TestDeprecationDecorator(TestCase):
    """Tests for deprecation decorator."""

    def test_deprecated_endpoint_adds_headers(self) -> None:
        """deprecated_endpoint should add X-Deprecated headers."""
        # Note: deprecated_endpoint must be OUTERMOST decorator (before api_view)
        @deprecated_endpoint("Use /new-endpoint/", removal_version="v2")
        @api_view(["GET"])
        def old_endpoint(request: Request) -> Response:
            return Response({"status": "ok"})

        # Simulate request
        from rest_framework.test import APIRequestFactory
        factory = APIRequestFactory()
        request = factory.get("/old/")
        response = old_endpoint(request)

        self.assertEqual(response["X-Deprecated"], "true")
        self.assertEqual(response["X-Deprecated-Message"], "Use /new-endpoint/")
        self.assertEqual(response["X-Removal-Version"], "v2")

class TestVersioningConfiguration(TestCase):
    """Tests for versioning DRF configuration."""

    def test_versioning_config_in_settings(self) -> None:
        """Versioning configuration should be in REST_FRAMEWORK settings."""
        from django.conf import settings

        rf_settings = settings.REST_FRAMEWORK

        self.assertEqual(
            rf_settings.get("DEFAULT_VERSIONING_CLASS"),
            "rest_framework.versioning.URLPathVersioning"
        )
        self.assertEqual(rf_settings.get("DEFAULT_VERSION"), "v1")
        self.assertIn("v1", rf_settings.get("ALLOWED_VERSIONS", []))
