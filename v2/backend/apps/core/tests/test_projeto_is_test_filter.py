"""
Tests for is_test filter in Projeto endpoints (Issue #153).

Tests:
- test_projeto_viewset_filters_test_by_default
- test_projeto_viewset_includes_test_with_param
- test_projeto_viewset_explicit_false
- test_projeto_option_viewset_filters_test_by_default
- test_projeto_option_viewset_includes_test_with_param
- test_projeto_option_viewset_explicit_false
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.models import Projeto, Usuario


@pytest.fixture
def dat_user(db):
    """Create DAT user for CRUD permissions."""
    user = Usuario.objects.create_user(
        username="dat_user",
        email="dat@example.com",
        password="testpass123",
    )
    dat_group, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(dat_group)
    return user


@pytest.fixture
def regular_user(db):
    """Create regular authenticated user for options endpoints."""
    return Usuario.objects.create_user(
        username="regular_user",
        email="user@example.com",
        password="testpass123",
    )


@pytest.fixture
def projetos_mixed(db):
    """Create mix of production and test projects."""
    # Production projects
    prod1 = Projeto.objects.create(nome="CIRANDAR", fluxo="SUPER", ativo=True, is_test=False)
    prod2 = Projeto.objects.create(nome="ACERTA MATEMÁTICA", fluxo="NAO_SUPER", ativo=True, is_test=False)

    # Test projects
    test1 = Projeto.objects.create(nome="SMOKE SUPER", fluxo="SUPER", ativo=True, is_test=True)
    test2 = Projeto.objects.create(nome="TESTE E2E", fluxo="SUPER", ativo=True, is_test=True)

    # Inactive project (should be filtered by options endpoint anyway)
    inactive = Projeto.objects.create(nome="INACTIVE", fluxo="SUPER", ativo=False, is_test=False)

    return {
        "production": [prod1, prod2],
        "test": [test1, test2],
        "inactive": inactive,
    }


@pytest.mark.django_db
class TestProjetoViewSetIsTestFilter:
    """Tests for ProjetoViewSet is_test filter (Issue #153)."""

    def test_projeto_viewset_filters_test_by_default(self, dat_user, projetos_mixed):
        """Test that ProjetoViewSet filters out is_test=True by default."""
        client = APIClient()
        client.force_authenticate(user=dat_user)

        response = client.get("/api/projetos/")

        assert response.status_code == 200
        data = response.json()

        # Response is paginated
        results = data["results"] if "results" in data else data
        count = data.get("count", len(results))

        # Should only return production projects (2) + inactive (1) = 3
        # (DAT can see inactive projects, but not test projects by default)
        assert count == 3
        assert len(results) == 3

        # Verify none are test projects
        for projeto in results:
            assert projeto["is_test"] is False

        # Verify production projects are present
        nomes = [p["nome"] for p in results]
        assert "CIRANDAR" in nomes
        assert "ACERTA MATEMÁTICA" in nomes
        assert "INACTIVE" in nomes

        # Verify test projects are NOT present
        assert "SMOKE SUPER" not in nomes
        assert "TESTE E2E" not in nomes

    def test_projeto_viewset_includes_test_with_param(self, dat_user, projetos_mixed):
        """Test that ProjetoViewSet includes is_test=True with ?include_test=true."""
        client = APIClient()
        client.force_authenticate(user=dat_user)

        response = client.get("/api/projetos/?include_test=true")

        assert response.status_code == 200
        data = response.json()

        # Response is paginated
        results = data["results"] if "results" in data else data
        count = data.get("count", len(results))

        # Should return ALL projects (2 prod + 2 test + 1 inactive) = 5
        assert count == 5
        assert len(results) == 5

        # Verify test projects are present
        nomes = [p["nome"] for p in results]
        assert "CIRANDAR" in nomes
        assert "ACERTA MATEMÁTICA" in nomes
        assert "SMOKE SUPER" in nomes
        assert "TESTE E2E" in nomes
        assert "INACTIVE" in nomes

    def test_projeto_viewset_explicit_false(self, dat_user, projetos_mixed):
        """Test that ProjetoViewSet filters test projects with ?include_test=false."""
        client = APIClient()
        client.force_authenticate(user=dat_user)

        response = client.get("/api/projetos/?include_test=false")

        assert response.status_code == 200
        data = response.json()

        # Response is paginated
        results = data["results"] if "results" in data else data
        count = data.get("count", len(results))

        # Should only return production projects (same as default)
        assert count == 3
        assert len(results) == 3

        # Verify none are test projects
        for projeto in results:
            assert projeto["is_test"] is False

    def test_projeto_viewset_case_insensitive_param(self, dat_user, projetos_mixed):
        """Test that include_test param is case-insensitive."""
        client = APIClient()
        client.force_authenticate(user=dat_user)

        # Test various cases
        for param_value in ["True", "TRUE", "tRuE"]:
            response = client.get(f"/api/projetos/?include_test={param_value}")
            assert response.status_code == 200
            data = response.json()
            count = data.get("count", len(data.get("results", data)))
            assert count == 5  # All projects

    def test_projeto_viewset_invalid_param_value(self, dat_user, projetos_mixed):
        """Test that invalid include_test values default to false."""
        client = APIClient()
        client.force_authenticate(user=dat_user)

        # Invalid values should be treated as false
        for param_value in ["yes", "1", "invalid"]:
            response = client.get(f"/api/projetos/?include_test={param_value}")
            assert response.status_code == 200
            data = response.json()
            count = data.get("count", len(data.get("results", data)))
            assert count == 3  # Only production projects


@pytest.mark.django_db
class TestProjetoOptionViewSetIsTestFilter:
    """Tests for ProjetoOptionViewSet is_test filter (Issue #153)."""

    def test_projeto_option_viewset_filters_test_by_default(self, regular_user, projetos_mixed):
        """Test that ProjetoOptionViewSet filters out is_test=True by default."""
        # Debug: Check what's in the database
        from apps.core.models import Projeto

        all_projetos = list(Projeto.objects.all().values("nome", "ativo", "is_test"))
        print(f"\n=== DEBUG: All projects in DB: {all_projetos}")

        active_only = list(Projeto.objects.filter(ativo=True).values("nome", "is_test"))
        print(f"=== DEBUG: Active projects: {active_only}")

        prod_only = list(Projeto.objects.filter(ativo=True, is_test=False).values("nome"))
        print(f"=== DEBUG: Active + NOT test: {prod_only}")

        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/")

        assert response.status_code == 200
        data = response.json()

        print(f"=== DEBUG: API response: {data}")

        # Should only return ACTIVE production projects (2)
        # (Options endpoint already filters ativo=True)
        assert len(data) == 2, f"Expected 2, got {len(data)}: {data}"

        # Verify production projects are present
        nomes = [p["nome"] for p in data]
        assert "CIRANDAR" in nomes
        assert "ACERTA MATEMÁTICA" in nomes

        # Verify test projects are NOT present
        assert "SMOKE SUPER" not in nomes
        assert "TESTE E2E" not in nomes

        # Verify inactive is NOT present (filtered by ativo=True)
        assert "INACTIVE" not in nomes

    def test_projeto_option_viewset_includes_test_with_param(self, regular_user, projetos_mixed):
        """Test that ProjetoOptionViewSet includes is_test=True with ?include_test=true."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/?include_test=true")

        assert response.status_code == 200
        data = response.json()

        # Should return ACTIVE projects (2 prod + 2 test) = 4
        # (Still filtered by ativo=True)
        assert len(data) == 4

        # Verify all active projects are present
        nomes = [p["nome"] for p in data]
        assert "CIRANDAR" in nomes
        assert "ACERTA MATEMÁTICA" in nomes
        assert "SMOKE SUPER" in nomes
        assert "TESTE E2E" in nomes

        # Verify inactive is still NOT present
        assert "INACTIVE" not in nomes

    def test_projeto_option_viewset_explicit_false(self, regular_user, projetos_mixed):
        """Test that ProjetoOptionViewSet filters test projects with ?include_test=false."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/?include_test=false")

        assert response.status_code == 200
        data = response.json()

        # Should only return ACTIVE production projects (same as default)
        assert len(data) == 2

        nomes = [p["nome"] for p in data]
        assert "CIRANDAR" in nomes
        assert "ACERTA MATEMÁTICA" in nomes

    def test_projeto_option_viewset_unauthenticated(self, projetos_mixed):
        """Test that unauthenticated requests are rejected."""
        client = APIClient()

        response = client.get("/api/options/projetos/")

        # DRF returns 403 (Forbidden) for unauthenticated requests with IsAuthenticated permission
        assert response.status_code == 403

    def test_projeto_option_viewset_combined_filters(self, regular_user, projetos_mixed):
        """Test that is_test filter works with search filter."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        # Search for "SUPER" - should only find production "CIRANDAR" (fluxo=SUPER)
        # NOT "SMOKE SUPER" or "TESTE E2E" (both are test projects)
        response = client.get("/api/options/projetos/?search=SUPER")

        assert response.status_code == 200
        data = response.json()

        # Only CIRANDAR has "SUPER" in nome and is production
        nomes = [p["nome"] for p in data]
        assert "CIRANDAR" in nomes
        assert "SMOKE SUPER" not in nomes  # Filtered by is_test=True


@pytest.mark.django_db
class TestProjetoViewSetPermissions:
    """Test that DAT permission is still enforced after filter changes."""

    def test_projeto_viewset_requires_dat_permission(self, regular_user, projetos_mixed):
        """Test that non-DAT users cannot access ProjetoViewSet."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/projetos/")

        assert response.status_code == 403  # Forbidden

    def test_projeto_option_viewset_allows_authenticated(self, regular_user, projetos_mixed):
        """Test that any authenticated user can access ProjetoOptionViewSet."""
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.get("/api/options/projetos/")

        assert response.status_code == 200  # OK
