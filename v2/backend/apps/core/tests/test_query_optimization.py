"""
AS v2 — Query Optimization Tests

Tests for N+1 query prevention (#406).
Validates that ViewSets use select_related/prefetch_related correctly.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportAttributeAccessIssue=false, reportUnusedVariable=false

from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.core.models import (
    AvailabilityBlock,
    Municipio,
    Participation,
    Projeto,
    Solicitacao,
    TipoEvento,
)

Usuario = get_user_model()


def unique_cpf() -> str:
    """Generate unique CPF for testing."""
    return str(uuid.uuid4())[:11].replace("-", "")


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda r: False})
class TestAvailabilityBlockQueryOptimization(TestCase):
    """Tests for AvailabilityBlockViewSet query optimization."""

    def setUp(self):
        self.client = APIClient()
        self.user = Usuario.objects.create_user(
            username="testuser_avail",
            password="testpass123",
            is_superuser=True,
            cpf=unique_cpf(),
        )
        self.client.force_authenticate(user=self.user)

    def test_list_blocks_uses_select_related(self):
        """Listing blocks should use select_related (fixed queries regardless of count)."""
        # Create 10 blocks
        for i in range(10):
            AvailabilityBlock.objects.create(
                usuario=self.user,
                inicio="2026-01-15T08:00:00Z",
                fim="2026-01-15T12:00:00Z",
                tipo="T",
                motivo=f"Test block {i}",
            )

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/availability-blocks/")

        self.assertEqual(response.status_code, 200)

        # Count queries that would indicate N+1 (selecting from usuario table multiple times)
        usuario_select_queries = [
            q
            for q in ctx.captured_queries
            if "SELECT" in q["sql"].upper() and "core_usuario" in q["sql"].lower() and "WHERE" in q["sql"].upper()
        ]

        # With select_related, should have at most 2 usuario queries
        # (one for auth, one for the JOIN in the main query)
        self.assertLessEqual(
            len(usuario_select_queries),
            3,
            f"Expected ≤3 usuario SELECT queries (with select_related), got {len(usuario_select_queries)}:\n"
            + "\n".join(q["sql"][:150] for q in usuario_select_queries),
        )


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda r: False})
class TestAvailabilityCheckManyQueryOptimization(TestCase):
    """Tests for AvailabilityCheckManyView query optimization."""

    def setUp(self):
        self.client = APIClient()
        # Create a user with the right permissions
        self.user = Usuario.objects.create_user(
            username="testuser_check",
            password="testpass123",
            is_superuser=True,  # Superuser has all permissions
            cpf=unique_cpf(),
        )
        self.client.force_authenticate(user=self.user)

        # Create test users
        self.test_users = []
        for i in range(10):
            u = Usuario.objects.create_user(
                username=f"formador_check_{i}",
                password="testpass123",
                cpf=unique_cpf(),
            )
            self.test_users.append(u)

    def test_check_many_uses_batch_fetch(self):
        """Checking 10 users should use batch fetch, not N queries."""
        user_ids = [u.id for u in self.test_users]

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                "/api/availability/check-many/",
                {
                    "usuarios_ids": user_ids,
                    "inicio": "2026-01-15T08:00:00Z",
                    "fim": "2026-01-15T12:00:00Z",
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 10)

        # Count usuario SELECT queries with WHERE id = (individual fetches)
        individual_usuario_queries = [
            q
            for q in ctx.captured_queries
            if "SELECT" in q["sql"].upper()
            and "core_usuario" in q["sql"].lower()
            and ("WHERE" in q["sql"] and '"id" =' in q["sql"])
            and "IN" not in q["sql"].upper()  # Exclude batch queries
        ]

        # With batch fetch, should have 0 individual usuario queries
        # All should use WHERE id IN (...)
        self.assertLessEqual(
            len(individual_usuario_queries),
            1,  # Allow 1 for auth
            f"Expected ≤1 individual usuario query (batch fetch used), got {len(individual_usuario_queries)}:\n"
            + "\n".join(q["sql"][:200] for q in individual_usuario_queries),
        )


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda r: False})
class TestUpdateFormadoresQueryOptimization(TestCase):
    """Tests for _update_formadores batch optimization."""

    def setUp(self):
        self.client = APIClient()

        # Create coordenador user
        self.coord = Usuario.objects.create_user(
            username="coord_update_test",
            password="testpass123",
            cpf=unique_cpf(),
        )
        # Add to Coordenador group
        from django.contrib.auth.models import Group

        coord_group, _ = Group.objects.get_or_create(name="Coordenador")
        self.coord.groups.add(coord_group)
        self.client.force_authenticate(user=self.coord)

        # Create required related objects
        self.municipio = Municipio.objects.create(
            nome=f"Fortaleza Update {uuid.uuid4().hex[:8]}",
            uf="CE",
        )
        self.projeto = Projeto.objects.create(
            nome=f"Test Project Update {uuid.uuid4().hex[:8]}",
            fluxo="NAO_SUPER",
        )
        self.tipo_evento = TipoEvento.objects.create(
            nome=f"Formação Update {uuid.uuid4().hex[:8]}",
        )

        # Create formadores
        self.formadores = []
        for i in range(10):
            u = Usuario.objects.create_user(
                username=f"formador_upd_{uuid.uuid4().hex[:8]}",
                password="testpass123",
                cpf=unique_cpf(),
            )
            self.formadores.append(u)

        # Create solicitacao
        self.solicitacao = Solicitacao.objects.create(
            usuario=self.coord,
            municipio=self.municipio,
            projeto=self.projeto,
            tipo_evento=self.tipo_evento,
            inicio="2026-01-20T08:00:00Z",
            fim="2026-01-20T12:00:00Z",
            status="aprovado",
        )

    def test_update_formadores_uses_batch_fetch(self):
        """Adding 10 formadores should use batch fetch for usuarios, not N queries."""
        formador_ids = [f.id for f in self.formadores]

        with CaptureQueriesContext(connection) as ctx:
            response = self.client.patch(
                f"/api/solicitacoes/{self.solicitacao.id}/",
                {
                    "extra_participants": {
                        "formador_ids": formador_ids,
                    },
                },
                format="json",
            )

        self.assertEqual(response.status_code, 200)

        # Verify all participations were created
        participations = Participation.objects.filter(
            solicitacao=self.solicitacao,
            role="FORMADOR",
        )
        self.assertEqual(participations.count(), 10)

        # Count individual usuario SELECT queries (not batch)
        individual_usuario_queries = [
            q
            for q in ctx.captured_queries
            if "SELECT" in q["sql"].upper()
            and "core_usuario" in q["sql"].lower()
            and "WHERE" in q["sql"]
            and '"id" =' in q["sql"]
            and "IN" not in q["sql"].upper()
        ]

        # With batch fetch, should have ≤2 individual queries (auth + coord)
        self.assertLessEqual(
            len(individual_usuario_queries),
            2,
            f"Expected ≤2 individual usuario queries (batch fetch used), got {len(individual_usuario_queries)}:\n"
            + "\n".join(q["sql"][:200] for q in individual_usuario_queries),
        )


@override_settings(DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": lambda r: False})
class TestSolicitacaoListQueryOptimization(TestCase):
    """Tests for SolicitacaoViewSet list query optimization."""

    def setUp(self):
        self.client = APIClient()
        self.user = Usuario.objects.create_user(
            username=f"testuser_list_{uuid.uuid4().hex[:8]}",
            password="testpass123",
            is_superuser=True,
            cpf=unique_cpf(),
        )
        self.client.force_authenticate(user=self.user)

        # Create required related objects
        self.municipio = Municipio.objects.create(
            nome=f"Fortaleza List {uuid.uuid4().hex[:8]}",
            uf="CE",
        )
        self.projeto = Projeto.objects.create(
            nome=f"Test List {uuid.uuid4().hex[:8]}",
            fluxo="NAO_SUPER",
        )
        self.tipo_evento = TipoEvento.objects.create(
            nome=f"Formação List {uuid.uuid4().hex[:8]}",
        )

        # Create 20 solicitações
        for i in range(20):
            Solicitacao.objects.create(
                usuario=self.user,
                municipio=self.municipio,
                projeto=self.projeto,
                tipo_evento=self.tipo_evento,
                inicio=f"2026-01-{15 + i % 10:02d}T08:00:00Z",
                fim=f"2026-01-{15 + i % 10:02d}T12:00:00Z",
            )

    def test_list_solicitacoes_uses_select_related(self):
        """Listing solicitações should use select_related (fixed queries)."""
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/solicitacoes/")

        self.assertEqual(response.status_code, 200)
        # Paginated response
        self.assertIn("results", response.data)

        # Count SELECT queries for related tables (would be N+1 without select_related)
        related_select_queries = [
            q
            for q in ctx.captured_queries
            if "SELECT" in q["sql"].upper()
            and (
                "core_municipio" in q["sql"].lower()
                or "core_projeto" in q["sql"].lower()
                or "core_tipoevento" in q["sql"].lower()
            )
            and "WHERE" in q["sql"]
            and '"id" =' in q["sql"]
        ]

        # With select_related, should have 0 individual related queries
        # (all should be JOINed in the main query)
        self.assertEqual(
            len(related_select_queries),
            0,
            f"Expected 0 individual related queries (select_related used), got {len(related_select_queries)}:\n"
            + "\n".join(q["sql"][:200] for q in related_select_queries),
        )
