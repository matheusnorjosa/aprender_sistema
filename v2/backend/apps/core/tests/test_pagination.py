"""
Tests for pagination (#408).

Validates:
- GCalListView returns paginated response
- metrics_map respects limit parameter
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.tests.factories import (
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
)


class TestGCalListPagination(TestCase):
    """Tests for GCalListView pagination."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        # Create superuser with permission
        self.user = UsuarioFactory(superuser=True)
        self.client.force_authenticate(user=self.user)

        # Create required objects
        self.municipio = MunicipioFactory(
            nome="Test City",
            uf="CE",
            latitude=Decimal("-3.7172"),
            longitude=Decimal("-38.5433"),
        )
        self.tipo_evento = TipoEventoFactory(nome="Test Type")
        self.projeto = ProjetoFactory(nome="Test Project")

    def test_gcal_list_returns_paginated_response(self) -> None:
        """GCalListView should return paginated response with count, next, results."""
        # Create 10 approved solicitações
        now = timezone.now()
        for i in range(10):
            SolicitacaoFactory(
                usuario=self.user,
                status="aprovado",
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                projeto=self.projeto,
                inicio=now + timedelta(hours=i),
                fim=now + timedelta(hours=i + 1),
            )

        response = self.client.get("/api/gcal/list/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check paginated response structure
        self.assertIn("count", data)
        self.assertIn("results", data)
        self.assertEqual(data["count"], 10)
        self.assertEqual(len(data["results"]), 10)

    def test_gcal_list_respects_page_size(self) -> None:
        """GCalListView should respect page_size parameter."""
        now = timezone.now()
        for i in range(15):
            SolicitacaoFactory(
                usuario=self.user,
                status="aprovado",
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                projeto=self.projeto,
                inicio=now + timedelta(hours=i),
                fim=now + timedelta(hours=i + 1),
            )

        response = self.client.get("/api/gcal/list/?page_size=5")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["count"], 15)
        self.assertEqual(len(data["results"]), 5)
        self.assertIsNotNone(data.get("next"))

    def test_gcal_list_page_size_capped_at_max(self) -> None:
        """page_size should be capped at max_page_size (1000)."""
        now = timezone.now()
        # Create just a few items
        for i in range(5):
            SolicitacaoFactory(
                usuario=self.user,
                status="aprovado",
                municipio=self.municipio,
                tipo_evento=self.tipo_evento,
                projeto=self.projeto,
                inicio=now + timedelta(hours=i),
                fim=now + timedelta(hours=i + 1),
            )

        # Request way more than max_page_size
        response = self.client.get("/api/gcal/list/?page_size=5000")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should still work, just capped
        self.assertEqual(len(data["results"]), 5)


class TestMetricsMapLimit(TestCase):
    """Tests for metrics_map limit parameter."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        # Create superuser with permission
        self.user = UsuarioFactory(superuser=True)
        self.client.force_authenticate(user=self.user)

        # Create municipios with coordinates
        self.municipios = []
        for i in range(20):
            m = MunicipioFactory(
                nome=f"City {i}",
                uf="CE",
                latitude=Decimal("-3.7172") + Decimal(str(i * 0.1)),
                longitude=Decimal("-38.5433") + Decimal(str(i * 0.1)),
            )
            self.municipios.append(m)

        self.tipo_evento = TipoEventoFactory(nome="Test Type")
        self.projeto = ProjetoFactory(nome="Test Project")

        # Create solicitações for different municipios
        now = timezone.now()
        for i, municipio in enumerate(self.municipios):
            SolicitacaoFactory(
                usuario=self.user,
                status="aprovado",
                municipio=municipio,
                tipo_evento=self.tipo_evento,
                projeto=self.projeto,
                inicio=now + timedelta(hours=i),
                fim=now + timedelta(hours=i + 1),
            )

    def test_metrics_map_default_limit(self) -> None:
        """metrics_map should not truncate by default."""
        response = self.client.get("/api/metrics/map/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("meta", data)
        self.assertIsNone(data["meta"]["limit"])
        self.assertEqual(data["meta"]["max_limit"], 1000)
        self.assertEqual(len(data["by_municipio"]), 20)

    def test_metrics_map_respects_limit_parameter(self) -> None:
        """metrics_map should respect limit parameter."""
        response = self.client.get("/api/metrics/map/?limit=10")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["meta"]["limit"], 10)
        self.assertLessEqual(len(data["by_municipio"]), 10)

    def test_metrics_map_limit_capped_at_1000(self) -> None:
        """limit should be capped at max_limit (1000)."""
        response = self.client.get("/api/metrics/map/?limit=5000")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["meta"]["limit"], 1000)
        self.assertEqual(data["meta"]["max_limit"], 1000)

    def test_metrics_map_invalid_limit_returns_400(self) -> None:
        """Invalid limit value should return 400."""
        response = self.client.get("/api/metrics/map/?limit=invalid")

        self.assertEqual(response.status_code, 400)


class TestPaginationClasses(TestCase):
    """Tests for pagination class configuration."""

    def test_standard_pagination_config(self) -> None:
        """StandardPagination should have correct config."""
        from apps.core.pagination import StandardPagination

        pagination = StandardPagination()
        self.assertEqual(pagination.page_size, 100)
        self.assertEqual(pagination.page_size_query_param, "page_size")
        self.assertEqual(pagination.max_page_size, 500)

    def test_large_pagination_config(self) -> None:
        """LargePagination should have correct config."""
        from apps.core.pagination import LargePagination

        pagination = LargePagination()
        self.assertEqual(pagination.page_size, 200)
        self.assertEqual(pagination.page_size_query_param, "page_size")
        self.assertEqual(pagination.max_page_size, 1000)
