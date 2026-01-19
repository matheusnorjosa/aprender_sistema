"""
Tests for response consistency (#411).

Validates:
- Custom endpoints use standardized response format
- All responses have 'data' and 'meta' keys
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false, reportIndexIssue=false

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.responses import APIResponse


class TestAPIResponseFactory(TestCase):
    """Tests for APIResponse factory methods."""

    def test_success_response_format(self) -> None:
        """APIResponse.success should return data and meta keys."""
        response = APIResponse.success(data={"key": "value"})
        content = response.data

        self.assertIn("data", content)
        self.assertIn("meta", content)
        self.assertEqual(content["data"]["key"], "value")
        self.assertIn("timestamp", content["meta"])

    def test_success_with_meta(self) -> None:
        """APIResponse.success should merge custom meta."""
        response = APIResponse.success(
            data={"key": "value"},
            meta={"custom": "field"}
        )
        content = response.data

        self.assertIn("timestamp", content["meta"])
        self.assertEqual(content["meta"]["custom"], "field")

    def test_list_response_format(self) -> None:
        """APIResponse.list should return items and total."""
        items = [{"id": 1}, {"id": 2}]
        response = APIResponse.list(items=items)
        content = response.data

        self.assertIn("data", content)
        self.assertIn("meta", content)
        self.assertEqual(content["data"]["items"], items)
        self.assertEqual(content["data"]["total"], 2)

    def test_list_with_explicit_total(self) -> None:
        """APIResponse.list should use explicit total if provided."""
        items = [{"id": 1}]
        response = APIResponse.list(items=items, total=100)
        content = response.data

        self.assertEqual(content["data"]["total"], 100)

    def test_availability_response_format(self) -> None:
        """APIResponse.availability should return available and conflicts."""
        response = APIResponse.availability(ok=True, conflicts=[])
        content = response.data

        self.assertIn("data", content)
        self.assertTrue(content["data"]["available"])
        self.assertEqual(content["data"]["conflicts"], [])

    def test_availability_with_conflicts(self) -> None:
        """APIResponse.availability should include conflicts."""
        conflicts = [{"type": "overlap", "id": 1}]
        response = APIResponse.availability(ok=False, conflicts=conflicts)
        content = response.data

        self.assertFalse(content["data"]["available"])
        self.assertEqual(content["data"]["conflicts"], conflicts)


class TestReportsResponseConsistency(TestCase):
    """Tests for reports endpoints response format."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        # Create superuser with permission
        self.user = Usuario.objects.create_superuser(
            username="admin_consistency",
            email="admin_consistency@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        # Create required objects
        self.municipio = Municipio.objects.create(
            nome="Test City",
            uf="CE",
            latitude=Decimal("-3.7172"),
            longitude=Decimal("-38.5433"),
        )
        self.tipo_evento = TipoEvento.objects.create(nome="Test Type")
        self.projeto = Projeto.objects.create(nome="Test Project")

        # Create some solicitações
        now = timezone.now()
        for i in range(5):
            Solicitacao.objects.create(
                usuario=self.user,
                status="aprovado",
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                projeto=self.projeto,
                inicio=now + timedelta(hours=i),
                fim=now + timedelta(hours=i + 1),
            )

    def _assert_standard_response_format(self, data: dict[str, Any]) -> None:
        """Assert response has standard format."""
        self.assertIn("data", data, "Response missing 'data' key")
        self.assertIn("meta", data, "Response missing 'meta' key")
        self.assertIn("timestamp", data["meta"], "Meta missing 'timestamp'")

    def test_reports_status_counts_format(self) -> None:
        """reports_status_counts should use standard response format."""
        response = self.client.get("/api/reports/status-counts/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_standard_response_format(data)
        self.assertIn("counts", data["data"])
        self.assertIn("total", data["data"])

    def test_reports_top_projects_format(self) -> None:
        """reports_top_projects should use standard response format."""
        response = self.client.get("/api/reports/top-projects/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_standard_response_format(data)
        self.assertIn("items", data["data"])
        self.assertIn("total", data["data"])

    def test_reports_weekly_approved_format(self) -> None:
        """reports_weekly_approved should use standard response format."""
        response = self.client.get("/api/reports/weekly-approved/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_standard_response_format(data)
        self.assertIn("items", data["data"])
        self.assertIn("total", data["data"])

    def test_reports_by_uf_format(self) -> None:
        """reports_by_uf should use standard response format."""
        response = self.client.get("/api/reports/by-uf/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self._assert_standard_response_format(data)
        self.assertIn("items", data["data"])
        self.assertIn("total", data["data"])
