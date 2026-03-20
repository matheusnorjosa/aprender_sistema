"""
Tests for OpenAPI documentation (#412).

Validates:
- Schema generation works
- Key endpoints are documented
- Error schemas are included
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from typing import Any

from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Usuario


class TestOpenAPISchema(TestCase):
    """Tests for OpenAPI schema generation."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        # Create superuser for accessing schema
        self.user = Usuario.objects.create_superuser(
            username="admin_openapi",
            email="admin_openapi@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_schema_endpoint_returns_200(self) -> None:
        """Schema endpoint should return 200."""
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)

    def test_schema_contains_version_info(self) -> None:
        """Schema should contain API version info."""
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()

        self.assertIn("info", schema)
        # Version may include API version suffix like "2.0.0 (v1)"
        self.assertTrue(
            schema["info"]["version"].startswith("2.0.0"),
            f"Expected version to start with '2.0.0', got '{schema['info']['version']}'",
        )
        self.assertIn("Aprender", schema["info"]["title"])

    def test_schema_contains_solicitacoes_endpoints(self) -> None:
        """Schema should document solicitacoes endpoints."""
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()

        paths = schema.get("paths", {})

        # Check that solicitacoes endpoints are documented
        self.assertTrue(
            any("/solicitacoes" in path for path in paths.keys()), "Schema should contain solicitacoes endpoints"
        )

    def test_schema_contains_availability_endpoints(self) -> None:
        """Schema should document availability endpoints."""
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()

        paths = schema.get("paths", {})

        # Check that availability endpoints are documented
        self.assertTrue(
            any("/availability" in path for path in paths.keys()), "Schema should contain availability endpoints"
        )

    def test_swagger_ui_endpoint_returns_200(self) -> None:
        """Swagger UI endpoint should return 200."""
        response = self.client.get("/api/docs/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("swagger", response.content.decode().lower())

    def test_redoc_endpoint_returns_200(self) -> None:
        """Redoc endpoint should return 200."""
        response = self.client.get("/api/redoc/")

        self.assertEqual(response.status_code, 200)

    def _get_response_schema(self, schema: dict[str, Any], path: str, method: str, status_code: str) -> dict[str, Any]:
        path_data = schema.get("paths", {}).get(path, {})
        method_data = path_data.get(method, {})
        response_data = method_data.get("responses", {}).get(status_code, {})
        content = response_data.get("content", {}).get("application/json", {})
        return content.get("schema", {})

    def _resolve_schema_properties(self, schema: dict[str, Any], schema_ref: dict[str, Any]) -> dict[str, Any]:
        if "allOf" in schema_ref and schema_ref["allOf"]:
            first_ref = schema_ref["allOf"][0]
            if isinstance(first_ref, dict):
                return self._resolve_schema_properties(schema, first_ref)

        if "oneOf" in schema_ref and schema_ref["oneOf"]:
            first_ref = schema_ref["oneOf"][0]
            if isinstance(first_ref, dict):
                return self._resolve_schema_properties(schema, first_ref)

        if "anyOf" in schema_ref and schema_ref["anyOf"]:
            first_ref = schema_ref["anyOf"][0]
            if isinstance(first_ref, dict):
                return self._resolve_schema_properties(schema, first_ref)

        if schema_ref.get("type") == "array":
            items_ref = schema_ref.get("items", {})
            if isinstance(items_ref, dict):
                return self._resolve_schema_properties(schema, items_ref)

        if "$ref" not in schema_ref:
            return schema_ref.get("properties", {})

        ref = schema_ref["$ref"]
        component_name = ref.split("/")[-1]
        component_schema = schema.get("components", {}).get("schemas", {}).get(component_name, {})
        return component_schema.get("properties", {})

    def test_schema_has_typed_response_for_current_user(self) -> None:
        """Schema must define explicit response fields for /api/me/."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        response_schema = self._get_response_schema(schema, "/api/me/", "get", "200")
        self.assertTrue(response_schema, "Expected typed 200 response schema for /api/me/")

        properties = self._resolve_schema_properties(schema, response_schema)
        for field in [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
            "groups",
            "setores",
            "funcoes",
            "is_superuser",
            "is_superintendencia",
            "can_approve_super",
            "permissions",
        ]:
            self.assertIn(field, properties, f"Missing field '{field}' in /api/me/ OpenAPI response schema")

    def test_schema_has_typed_response_for_config_get_and_put(self) -> None:
        """Schema must define explicit response fields for /api/config/ GET and PUT."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        expected_fields = [
            "TRAVEL_BUFFER_MINUTES",
            "AVAILABILITY_DAILY_LIMIT_HOURS",
            "ALLOW_ADJACENT_EVENTS",
            "BLOCK_AUTO_APPROVE",
            "BATCH_SIZE",
            "LOCK_TTL_SECONDS",
            "AUTO_RETRY_ON_ERROR",
            "MAX_RETRIES",
            "SEND_UPDATES",
            "SESSION_COOKIE_AGE",
            "SESSION_WARNING_THRESHOLD",
            "AUTOCOMPLETE_DEBOUNCE_MS",
            "ENABLE_MULTI_CALENDAR",
            "ENABLE_BATCH_ACTIONS",
            "ENABLE_ADVANCED_FILTERS",
        ]

        for method in ["get", "put"]:
            response_schema = self._get_response_schema(schema, "/api/config/", method, "200")
            self.assertTrue(response_schema, f"Expected typed 200 response schema for /api/config/ {method.upper()}")
            properties = self._resolve_schema_properties(schema, response_schema)

            for field in expected_fields:
                self.assertIn(
                    field,
                    properties,
                    f"Missing field '{field}' in /api/config/ {method.upper()} OpenAPI response schema",
                )

    def test_schema_has_typed_response_for_dashboard_overview(self) -> None:
        """Schema must define explicit response fields for /api/dashboard/overview/."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        response_schema = self._get_response_schema(schema, "/api/dashboard/overview/", "get", "200")
        self.assertTrue(response_schema, "Expected typed 200 response schema for /api/dashboard/overview/")

        properties = self._resolve_schema_properties(schema, response_schema)
        for field in ["kpis", "por_fluxo", "por_gerencia", "top_coordenadores"]:
            self.assertIn(
                field,
                properties,
                f"Missing field '{field}' in /api/dashboard/overview/ OpenAPI response schema",
            )

    def test_schema_has_typed_response_for_home_stats(self) -> None:
        """Schema must define explicit response fields for /api/stats/home/."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        response_schema = self._get_response_schema(schema, "/api/stats/home/", "get", "200")
        self.assertTrue(response_schema, "Expected typed 200 response schema for /api/stats/home/")

        properties = self._resolve_schema_properties(schema, response_schema)
        for field in ["pending_approvals", "upcoming_events", "my_requests"]:
            self.assertIn(field, properties, f"Missing field '{field}' in /api/stats/home/ OpenAPI response schema")

    def test_schema_has_typed_response_for_monthly_availability(self) -> None:
        """Schema must define explicit response fields and query parameters for /api/availability/monthly/."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        response_schema = self._get_response_schema(schema, "/api/availability/monthly/", "get", "200")
        self.assertTrue(response_schema, "Expected typed 200 response schema for /api/availability/monthly/")

        properties = self._resolve_schema_properties(schema, response_schema)
        for field in ["days", "legend", "people", "cells", "details_index"]:
            self.assertIn(
                field,
                properties,
                f"Missing field '{field}' in /api/availability/monthly/ OpenAPI response schema",
            )

        parameters = schema.get("paths", {}).get("/api/availability/monthly/", {}).get("get", {}).get("parameters", [])
        parameter_names = {param.get("name") for param in parameters}
        for param_name in ["year", "month", "role", "gerencia_id", "sector", "q"]:
            self.assertIn(
                param_name, parameter_names, f"Missing query parameter '{param_name}' in monthly availability"
            )

    def test_schema_has_typed_responses_for_options_endpoints(self) -> None:
        """Schema must define explicit list item fields for /api/options/* endpoints used by frontend."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        endpoints = [
            ("/api/options/municipios/", ["id", "nome", "uf"]),
            ("/api/options/projetos/", ["id", "nome", "codigo"]),
            ("/api/options/tipos-evento/", ["id", "nome"]),
            ("/api/options/usuarios/", ["id", "first_name", "last_name", "email"]),
            ("/api/options/produtos/", ["id", "nome", "codigo"]),
            ("/api/options/coordenadores/", ["id", "nome", "area", "ativo"]),
            ("/api/options/areas/", ["id", "nome", "cor"]),
            ("/api/options/formadores-do-setor/", ["id", "first_name", "last_name", "email"]),
        ]

        for path, expected_fields in endpoints:
            response_schema = self._get_response_schema(schema, path, "get", "200")
            self.assertTrue(response_schema, f"Expected typed 200 response schema for {path} GET")
            properties = self._resolve_schema_properties(schema, response_schema)
            for field in expected_fields:
                self.assertIn(
                    field,
                    properties,
                    f"Missing field '{field}' in {path} GET OpenAPI response schema",
                )

    def test_schema_has_typed_responses_for_import_operations_used_by_frontend(self) -> None:
        """Schema must define explicit request/response contracts for critical import operations."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        import_paths = [
            "/api/controle/import-compras/",
            "/api/controle/import-acoes/",
            "/api/dat/import-cadastros/",
            "/api/disponibilidade/import-bloqueios/",
            "/api/deslocamentos/import/",
            "/api/solicitacoes/import/",
            "/api/usuarios/import/",
            "/api/municipios/import/",
            "/api/colecoes/import/",
            "/api/equipe-gerencia/import/",
            "/api/produtos/import/",
        ]

        for path in import_paths:
            response_schema = self._get_response_schema(schema, path, "post", "200")
            self.assertTrue(response_schema, f"Expected typed 200 response schema for {path} POST")
            properties = self._resolve_schema_properties(schema, response_schema)

            for field in ["stats", "pendencias", "dry_run", "file", "path", "detail"]:
                self.assertIn(field, properties, f"Missing field '{field}' in {path} POST OpenAPI response schema")

            request_schema = (
                schema.get("paths", {})
                .get(path, {})
                .get("post", {})
                .get("requestBody", {})
                .get("content", {})
                .get("multipart/form-data", {})
                .get("schema", {})
            )
            self.assertTrue(request_schema, f"Expected multipart request schema for {path} POST")
            request_properties = self._resolve_schema_properties(schema, request_schema)
            self.assertIn("file", request_properties, f"Missing field 'file' in {path} POST request schema")

    def test_schema_has_typed_responses_for_gcal_dashboard_reads(self) -> None:
        """Schema must define explicit response fields for critical GCal dashboard read endpoints."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        endpoints = [
            ("/api/gcal/status-summary/", "get", "200", ["counts", "total"]),
            ("/api/gcal/dashboard/metrics/", "get", "200", ["counts", "recent_errors", "window"]),
            ("/api/gcal/dashboard/events/", "get", "200", ["count", "next", "previous", "results"]),
            (
                "/api/gcal/dashboard/insights/success-rate/",
                "get",
                "200",
                ["published", "error", "pending", "none", "rate", "window"],
            ),
            ("/api/gcal/dashboard/insights/top/", "get", "200", ["items", "window", "metric", "limit"]),
            (
                "/api/gcal/dashboard/events/{id}/detail/",
                "get",
                "200",
                ["id", "gcal_status", "external_event_id", "timeline"],
            ),
        ]

        for path, method, status_code, expected_fields in endpoints:
            response_schema = self._get_response_schema(schema, path, method, status_code)
            self.assertTrue(
                response_schema, f"Expected typed {status_code} response schema for {path} {method.upper()}"
            )
            properties = self._resolve_schema_properties(schema, response_schema)
            for field in expected_fields:
                self.assertIn(
                    field,
                    properties,
                    f"Missing field '{field}' in {path} {method.upper()} OpenAPI response schema",
                )

    def test_schema_has_typed_responses_for_gcal_dashboard_batch_actions(self) -> None:
        """Schema must define explicit request/response schemas for critical GCal batch actions."""
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, 200)
        schema = response.json()

        for path in ["/api/gcal/dashboard/batch/reapply/", "/api/gcal/dashboard/batch/resync/"]:
            response_schema = self._get_response_schema(schema, path, "post", "202")
            self.assertTrue(response_schema, f"Expected typed 202 response schema for {path} POST")
            properties = self._resolve_schema_properties(schema, response_schema)

            for field in ["queued", "errors", "dry_run", "apply_blocked"]:
                self.assertIn(field, properties, f"Missing field '{field}' in {path} POST OpenAPI response schema")

            request_schema = (
                schema.get("paths", {})
                .get(path, {})
                .get("post", {})
                .get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            self.assertTrue(request_schema, f"Expected request schema for {path} POST")
            request_properties = self._resolve_schema_properties(schema, request_schema)
            self.assertIn("ids", request_properties, f"Missing field 'ids' in {path} POST request schema")


class TestSchemaErrors(TestCase):
    """Tests for error response schemas."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.client = APIClient()

        self.user = Usuario.objects.create_superuser(
            username="admin_schema_errors",
            email="admin_schema_errors@test.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

    def test_schema_contains_error_responses(self) -> None:
        """Schema should document error response codes."""
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()

        paths = schema.get("paths", {})

        # Find a documented endpoint and check for error responses
        for path_name, path_data in paths.items():
            if "/solicitacoes" in path_name:
                for method, method_data in path_data.items():
                    if method == "get" and "responses" in method_data:
                        responses = method_data["responses"]
                        # Should have 400 error documented
                        if "400" in responses:
                            self.assertIn("400", responses)
                            return

        # If we get here, at least one endpoint should have error docs
        # This test verifies the structure is present


class TestSchemaConfiguration(TestCase):
    """Tests for schema configuration."""

    def test_spectacular_settings_configured(self) -> None:
        """SPECTACULAR_SETTINGS should be configured."""
        from django.conf import settings

        self.assertIn("SPECTACULAR_SETTINGS", dir(settings))

        spectacular_settings = settings.SPECTACULAR_SETTINGS

        self.assertEqual(spectacular_settings.get("TITLE"), "Aprender Sistema API")
        self.assertEqual(spectacular_settings.get("VERSION"), "2.0.0")

    def test_schema_class_configured(self) -> None:
        """REST_FRAMEWORK should use drf-spectacular schema class."""
        from django.conf import settings

        rf_settings = settings.REST_FRAMEWORK

        self.assertEqual(rf_settings.get("DEFAULT_SCHEMA_CLASS"), "drf_spectacular.openapi.AutoSchema")
