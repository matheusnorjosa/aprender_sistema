"""
Testes para endpoints GCal (Sprint 2 - Issue #65)

Endpoints testados:
- GET /api/gcal/calendars/
- GET /api/gcal/health/

Testes com override_settings para fake vs google client.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import Usuario


class TestGCalCalendarsEndpoint(APITestCase):
    """
    Testes para GET /api/gcal/calendars/
    """

    def setUp(self):
        """Setup: criar usuário autenticado"""
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            cpf="12345678901",
        )
        self.client.force_authenticate(user=self.usuario)

    @override_settings(GCAL_CLIENT="fake")
    def test_list_calendars_with_fake_client(self):
        """
        Testa listagem de calendários com fake client.
        """
        response = self.client.get("/api/gcal/calendars/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 3)  # Fake client retorna 3 calendários

        # Verificar estrutura
        first_calendar = response.data[0]
        self.assertIn("id", first_calendar)
        self.assertIn("summary", first_calendar)
        self.assertIn("primary", first_calendar)

        # Verificar calendário primário
        primary = next(cal for cal in response.data if cal["primary"])
        self.assertEqual(primary["id"], "primary")

    @override_settings(GCAL_CLIENT="FAKE")  # Testar normalização uppercase
    def test_list_calendars_case_insensitive(self):
        """
        Testa que GCAL_CLIENT aceita maiúsculas/minúsculas.
        """
        response = self.client.get("/api/gcal/calendars/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_calendars_requires_authentication(self):
        """
        Testa que endpoint requer autenticação.
        """
        self.client.logout()
        response = self.client.get("/api/gcal/calendars/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TestGCalHealthEndpoint(APITestCase):
    """
    Testes para GET /api/gcal/health/
    """

    def setUp(self):
        """Setup: criar usuário autenticado"""
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            cpf="12345678901",
        )
        self.client.force_authenticate(user=self.usuario)

    @override_settings(GCAL_CLIENT="fake")
    def test_health_check_with_fake_client(self):
        """
        Testa health check com fake client (sempre healthy).
        """
        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")
        self.assertEqual(response.data["client_type"], "fake")
        self.assertIn("details", response.data)

    @override_settings(GCAL_CLIENT="fake")
    def test_health_check_returns_200_when_healthy(self):
        """
        Testa que health check retorna 200 quando serviço está healthy.

        Issue #407: Retorna 503 quando unhealthy, 200 quando healthy.
        Fake client sempre retorna healthy.
        """
        response = self.client.get("/api/gcal/health/")

        # Fake client always returns healthy = 200
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "healthy")

    def test_health_check_requires_authentication(self):
        """
        Testa que endpoint requer autenticação.
        """
        self.client.logout()
        response = self.client.get("/api/gcal/health/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(GCAL_CLIENT="fake")
    def test_health_check_includes_client_type(self):
        """
        Testa que health check retorna client_type.
        """
        response = self.client.get("/api/gcal/health/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("client_type", response.data)
        self.assertEqual(response.data["client_type"], "fake")


class TestGCalEndpointsIntegration(APITestCase):
    """
    Testes de integração entre endpoints GCal.
    """

    def setUp(self):
        """Setup: criar usuário autenticado"""
        self.usuario = Usuario.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            cpf="12345678901",
        )
        self.client.force_authenticate(user=self.usuario)

    @override_settings(GCAL_CLIENT="fake")
    def test_calendars_and_health_consistency(self):
        """
        Testa que calendars e health retornam informações consistentes.
        """
        # Health check
        health_response = self.client.get("/api/gcal/health/")
        self.assertEqual(health_response.data["status"], "healthy")

        # Listar calendários
        calendars_response = self.client.get("/api/gcal/calendars/")
        self.assertEqual(calendars_response.status_code, status.HTTP_200_OK)

        # Se health é healthy, deve conseguir listar calendários
        if health_response.data["status"] == "healthy":
            self.assertIsInstance(calendars_response.data, list)
            self.assertGreater(len(calendars_response.data), 0)
