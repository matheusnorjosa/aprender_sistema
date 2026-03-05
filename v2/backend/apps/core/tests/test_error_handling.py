"""
Tests for custom exception handling (#407 Error Handling).

Tests the custom exception classes and exception handler.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from unittest import mock

from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.exceptions import APIError, ConflictError, NotFoundError, ServiceUnavailableError, ValidationAPIError
from apps.core.models import Usuario


class TestCustomExceptionClasses(TestCase):
    """Test custom exception class behavior."""

    def test_api_error_defaults(self):
        """APIError has correct defaults."""
        exc = APIError()
        self.assertEqual(exc.code, "API_ERROR")
        self.assertEqual(exc.message, "Ocorreu um erro na API.")
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.details, {})

    def test_api_error_custom_values(self):
        """APIError accepts custom values."""
        exc = APIError(
            code="CUSTOM_CODE",
            message="Custom message",
            details={"key": "value"},
            status_code=422,
        )
        self.assertEqual(exc.code, "CUSTOM_CODE")
        self.assertEqual(exc.message, "Custom message")
        self.assertEqual(exc.status_code, 422)
        self.assertEqual(exc.details, {"key": "value"})

    def test_validation_api_error(self):
        """ValidationAPIError has correct defaults and structure."""
        exc = ValidationAPIError(message="Campo inválido", field="email")
        self.assertEqual(exc.code, "VALIDATION_ERROR")
        self.assertEqual(exc.message, "Campo inválido")
        self.assertEqual(exc.status_code, 400)
        self.assertEqual(exc.details["field"], "email")

    def test_not_found_error(self):
        """NotFoundError creates correct message."""
        exc = NotFoundError(resource="Solicitação", identifier=123)
        self.assertEqual(exc.code, "NOT_FOUND")
        self.assertEqual(exc.message, "Solicitação não encontrado.")
        self.assertEqual(exc.status_code, 404)
        self.assertEqual(exc.details["resource"], "Solicitação")
        self.assertEqual(exc.details["identifier"], "123")

    def test_service_unavailable_error(self):
        """ServiceUnavailableError creates correct message."""
        exc = ServiceUnavailableError(
            service="Google Calendar",
            details="Connection timeout",
        )
        self.assertEqual(exc.code, "SERVICE_UNAVAILABLE")
        self.assertEqual(exc.message, "Serviço Google Calendar indisponível.")
        self.assertEqual(exc.status_code, 503)
        self.assertEqual(exc.details["service"], "Google Calendar")
        self.assertEqual(exc.details["error"], "Connection timeout")

    def test_conflict_error(self):
        """ConflictError creates correct message."""
        exc = ConflictError(
            message="Solicitação já aprovada",
            details={"status": "aprovado"},
        )
        self.assertEqual(exc.code, "CONFLICT")
        self.assertEqual(exc.message, "Solicitação já aprovada")
        self.assertEqual(exc.status_code, 409)
        self.assertEqual(exc.details["status"], "aprovado")


class TestExceptionHandlerFormat(APITestCase):
    """Test that the exception handler returns standardized format."""

    def setUp(self):
        """Create authenticated user."""
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            cpf="12345678901",
        )
        self.client.force_authenticate(user=self.usuario)

    def test_404_error_has_detail_and_code(self):
        """404 errors include detail and code fields."""
        response = self.client.get("/api/solicitacoes/999999/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        # Code should be present (NOT_FOUND or ERROR depending on exception type)
        self.assertIsNotNone(response.data["code"])

    def test_403_error_has_detail_and_code(self):
        """403 errors include detail and code fields."""
        self.client.logout()
        response = self.client.get("/api/solicitacoes/")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("detail", response.data)
        self.assertIn("code", response.data)
        self.assertIsNotNone(response.data["code"])


class TestGCalHealthErrorHandling(APITestCase):
    """Test gcal_health returns proper HTTP status codes (#407)."""

    def setUp(self):
        """Create authenticated user with GCal access role."""
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            cpf="12345678901",
        )
        group, _ = Group.objects.get_or_create(name="Controle")
        self.usuario.groups.add(group)
        self.client.force_authenticate(user=self.usuario)

    @override_settings(GCAL_CLIENT="fake")
    def test_gcal_health_returns_200_when_healthy(self):
        """gcal_health returns 200 when service is healthy."""
        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")

    @override_settings(GCAL_CLIENT="fake")
    @mock.patch("apps.core.views_gcal.gcal.get_gcal_client_and_calendar_id")
    def test_gcal_health_returns_503_when_unhealthy(self, mock_get_client):
        """gcal_health returns 503 when service is unhealthy."""
        mock_client = mock.MagicMock()
        mock_client.health_check.return_value = {
            "status": "unhealthy",
            "client_type": "google",
            "details": "Service unavailable",
        }
        mock_get_client.return_value = (mock_client, "calendar_id")

        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["code"], "SERVICE_UNAVAILABLE")

    @override_settings(GCAL_CLIENT="fake")
    @mock.patch("apps.core.views_gcal.gcal.get_gcal_client_and_calendar_id")
    def test_gcal_health_returns_503_on_exception(self, mock_get_client):
        """gcal_health returns 503 when exception occurs."""
        mock_get_client.side_effect = Exception("Connection timeout")

        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("detail", response.data)
        self.assertEqual(response.data["code"], "SERVICE_UNAVAILABLE")
        self.assertIn("Google Calendar", response.data["detail"])

    @override_settings(GCAL_CLIENT="fake")
    @mock.patch("apps.core.views_gcal.gcal.get_gcal_client_and_calendar_id")
    def test_gcal_health_error_includes_service_details(self, mock_get_client):
        """gcal_health error response includes service details."""
        mock_client = mock.MagicMock()
        mock_client.health_check.return_value = {
            "status": "unhealthy",
            "client_type": "google",
            "details": "API quota exceeded",
        }
        mock_get_client.return_value = (mock_client, "calendar_id")

        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("errors", response.data)
        self.assertEqual(response.data["errors"]["service"], "Google Calendar")
