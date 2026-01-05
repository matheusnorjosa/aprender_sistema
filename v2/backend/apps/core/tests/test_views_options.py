"""
Tests for views_options.py coverage improvement.

Issue #319: Aumentar cobertura de views_options.py (64% -> 85%+)

Covers:
- usuarios_options (lines 164-177)
- produtos_options (lines 197-207)
- coordenadores_options (lines 227-237)
- areas_options (lines 257-267)
- Cache behavior for all endpoints
- Empty list scenarios
"""

import pytest
from uuid import uuid4

from django.core.cache import cache
from rest_framework.test import APIClient

from apps.core.models import (
    DATArea,
    DATCoordenador,
    Municipio,
    Produto,
    Projeto,
    TipoEvento,
    Usuario,
)


@pytest.fixture
def projeto_base():
    """Base project for tests that require Projeto FK."""
    return Projeto.objects.create(
        nome="Projeto Base",
        codigo="BASE",
        ativo=True,
        is_test=False,
    )


@pytest.fixture
def api_client():
    """REST API client."""
    return APIClient()


@pytest.fixture
def usuario_autenticado():
    """Authenticated user for API requests."""
    uid = uuid4().hex[:8]
    return Usuario.objects.create_user(
        username=f"user_{uid}",
        password="senha123",
        cpf=str(uuid4().int % 10**11).zfill(11),
        email=f"user_{uid}@test.com",
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


# ============================================================
# Tests for usuarios_options (lines 164-177)
# ============================================================


@pytest.mark.django_db
class TestUsuariosOptions:
    """Tests for usuarios_options endpoint."""

    def test_returns_active_users(self, api_client, usuario_autenticado):
        """Returns list of active users."""
        # Create additional active users
        user1 = Usuario.objects.create_user(
            username="formador1",
            password="senha123",
            cpf="11111111111",
            email="formador1@test.com",
            first_name="Ana",
            last_name="Silva",
            is_active=True,
        )
        user2 = Usuario.objects.create_user(
            username="formador2",
            password="senha123",
            cpf="22222222222",
            email="formador2@test.com",
            first_name="Bruno",
            last_name="Costa",
            is_active=True,
        )
        # Create inactive user (should not appear)
        Usuario.objects.create_user(
            username="inativo",
            password="senha123",
            cpf="33333333333",
            email="inativo@test.com",
            is_active=False,
        )

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/usuarios/")

        assert response.status_code == 200
        data = response.json()

        # Should include active users only
        emails = [u["email"] for u in data]
        assert "formador1@test.com" in emails
        assert "formador2@test.com" in emails
        assert "inativo@test.com" not in emails

    def test_requires_authentication(self, api_client):
        """Endpoint requires authentication."""
        response = api_client.get("/api/options/usuarios/")
        assert response.status_code in (401, 403)

    def test_cache_works(self, api_client, usuario_autenticado):
        """Results are cached for 5 minutes."""
        api_client.force_authenticate(user=usuario_autenticado)

        # First request - cache miss
        response1 = api_client.get("/api/options/usuarios/")
        assert response1.status_code == 200

        # Verify cache was set
        cached = cache.get("static_endpoint:usuarios_options")
        assert cached is not None

        # Second request - cache hit
        response2 = api_client.get("/api/options/usuarios/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_empty_list(self, api_client, usuario_autenticado):
        """Returns empty list when no active users exist (except auth user)."""
        # Deactivate all users except the authenticated one
        Usuario.objects.exclude(id=usuario_autenticado.id).update(is_active=False)

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/usuarios/")

        assert response.status_code == 200
        # At least the authenticated user should be there
        assert len(response.json()) >= 1


# ============================================================
# Tests for produtos_options (lines 197-207)
# ============================================================


@pytest.mark.django_db
class TestProdutosOptions:
    """Tests for produtos_options endpoint."""

    def test_returns_active_products(self, api_client, usuario_autenticado, projeto_base):
        """Returns list of active products."""
        prod1 = Produto.objects.create(
            nome="Kit Alfabetização",
            codigo="KIT-ALF",
            ativo=True,
            projeto=projeto_base,
        )
        prod2 = Produto.objects.create(
            nome="Material Didático",
            codigo="MAT-DID",
            ativo=True,
            projeto=projeto_base,
        )
        # Create inactive product (should not appear)
        Produto.objects.create(
            nome="Produto Inativo",
            codigo="INATIVO",
            ativo=False,
            projeto=projeto_base,
        )

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/produtos/")

        assert response.status_code == 200
        data = response.json()

        # Should include active products only
        nomes = [p["nome"] for p in data]
        assert "Kit Alfabetização" in nomes
        assert "Material Didático" in nomes
        assert "Produto Inativo" not in nomes

    def test_requires_authentication(self, api_client):
        """Endpoint requires authentication."""
        response = api_client.get("/api/options/produtos/")
        assert response.status_code in (401, 403)

    def test_cache_works(self, api_client, usuario_autenticado, projeto_base):
        """Results are cached for 5 minutes."""
        Produto.objects.create(nome="Produto Cache", codigo="CACHE", ativo=True, projeto=projeto_base)

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - cache miss
        response1 = api_client.get("/api/options/produtos/")
        assert response1.status_code == 200

        # Verify cache was set
        cached = cache.get("static_endpoint:produtos_options")
        assert cached is not None

        # Second request - cache hit
        response2 = api_client.get("/api/options/produtos/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_empty_list(self, api_client, usuario_autenticado):
        """Returns empty list when no active products exist."""
        Produto.objects.all().delete()

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/produtos/")

        assert response.status_code == 200
        assert response.json() == []

    def test_ordered_by_name(self, api_client, usuario_autenticado, projeto_base):
        """Products are ordered by name."""
        Produto.objects.create(nome="Zebra", codigo="Z", ativo=True, projeto=projeto_base)
        Produto.objects.create(nome="Alfa", codigo="A", ativo=True, projeto=projeto_base)
        Produto.objects.create(nome="Beta", codigo="B", ativo=True, projeto=projeto_base)

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/produtos/")

        assert response.status_code == 200
        nomes = [p["nome"] for p in response.json()]
        assert nomes == sorted(nomes)


# ============================================================
# Tests for coordenadores_options (lines 227-237)
# ============================================================


@pytest.mark.django_db
class TestCoordenadoresOptions:
    """Tests for coordenadores_options endpoint."""

    def test_returns_all_coordinators(self, api_client, usuario_autenticado):
        """Returns list of DAT coordinators."""
        DATCoordenador.objects.create(
            nome="Maria Silva", area="Formação", created_by=usuario_autenticado
        )
        DATCoordenador.objects.create(
            nome="João Santos", area="Formação", created_by=usuario_autenticado
        )

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/coordenadores/")

        assert response.status_code == 200
        data = response.json()

        nomes = [c["nome"] for c in data]
        assert "Maria Silva" in nomes
        assert "João Santos" in nomes

    def test_requires_authentication(self, api_client):
        """Endpoint requires authentication."""
        response = api_client.get("/api/options/coordenadores/")
        assert response.status_code in (401, 403)

    def test_cache_works(self, api_client, usuario_autenticado):
        """Results are cached for 5 minutes."""
        DATCoordenador.objects.create(
            nome="Coord Cache", area="Cache Test", created_by=usuario_autenticado
        )

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - cache miss
        response1 = api_client.get("/api/options/coordenadores/")
        assert response1.status_code == 200

        # Verify cache was set
        cached = cache.get("static_endpoint:coordenadores_options")
        assert cached is not None

        # Second request - cache hit
        response2 = api_client.get("/api/options/coordenadores/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_empty_list(self, api_client, usuario_autenticado):
        """Returns empty list when no coordinators exist."""
        DATCoordenador.objects.all().delete()

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/coordenadores/")

        assert response.status_code == 200
        assert response.json() == []

    def test_ordered_by_name(self, api_client, usuario_autenticado):
        """Coordinators are ordered by name."""
        DATCoordenador.objects.create(nome="Zeca", area="Test", created_by=usuario_autenticado)
        DATCoordenador.objects.create(nome="Ana", area="Test", created_by=usuario_autenticado)
        DATCoordenador.objects.create(nome="Bruno", area="Test", created_by=usuario_autenticado)

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/coordenadores/")

        assert response.status_code == 200
        nomes = [c["nome"] for c in response.json()]
        assert nomes == sorted(nomes)


# ============================================================
# Tests for areas_options (lines 257-267)
# ============================================================


@pytest.mark.django_db
class TestAreasOptions:
    """Tests for areas_options endpoint."""

    def test_returns_all_areas(self, api_client, usuario_autenticado):
        """Returns list of DAT areas."""
        area1 = DATArea.objects.create(nome="Formação", ordem=1, cor="#FF5733")
        area2 = DATArea.objects.create(nome="Acompanhamento", ordem=2, cor="#33FF57")

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/areas/")

        assert response.status_code == 200
        data = response.json()

        nomes = [a["nome"] for a in data]
        assert "Formação" in nomes
        assert "Acompanhamento" in nomes

    def test_requires_authentication(self, api_client):
        """Endpoint requires authentication."""
        response = api_client.get("/api/options/areas/")
        assert response.status_code in (401, 403)

    def test_cache_works(self, api_client, usuario_autenticado):
        """Results are cached for 5 minutes."""
        DATArea.objects.create(nome="Cache Area", ordem=1)

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - cache miss
        response1 = api_client.get("/api/options/areas/")
        assert response1.status_code == 200

        # Verify cache was set
        cached = cache.get("static_endpoint:areas_options")
        assert cached is not None

        # Second request - cache hit
        response2 = api_client.get("/api/options/areas/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_empty_list(self, api_client, usuario_autenticado):
        """Returns empty list when no areas exist."""
        DATArea.objects.all().delete()

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/areas/")

        assert response.status_code == 200
        assert response.json() == []

    def test_ordered_by_ordem_then_name(self, api_client, usuario_autenticado):
        """Areas are ordered by ordem, then name."""
        DATArea.objects.create(nome="Zeta", ordem=1)
        DATArea.objects.create(nome="Alfa", ordem=2)
        DATArea.objects.create(nome="Beta", ordem=1)

        api_client.force_authenticate(user=usuario_autenticado)
        response = api_client.get("/api/options/areas/")

        assert response.status_code == 200
        data = response.json()
        # First all ordem=1 (Beta, Zeta by name), then ordem=2 (Alfa)
        nomes = [a["nome"] for a in data]
        assert nomes[0] == "Beta"  # ordem=1, name=Beta
        assert nomes[1] == "Zeta"  # ordem=1, name=Zeta
        assert nomes[2] == "Alfa"  # ordem=2


# ============================================================
# Additional tests for already-covered endpoints (cache hit paths)
# ============================================================


@pytest.mark.django_db
class TestMunicipiosOptionsCache:
    """Additional cache tests for municipios_options."""

    def test_cache_hit_returns_cached_data(self, api_client, usuario_autenticado):
        """Municipios endpoint returns cached data on cache hit."""
        Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - populates cache
        response1 = api_client.get("/api/options/municipios/")
        assert response1.status_code == 200

        # Verify cache is set
        cached = cache.get("static_endpoint:municipios_options")
        assert cached is not None

        # Second request - should use cache
        response2 = api_client.get("/api/options/municipios/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()


@pytest.mark.django_db
class TestProjetosOptionsCache:
    """Additional cache tests for projetos_options."""

    def test_cache_hit_returns_cached_data(self, api_client, usuario_autenticado):
        """Projetos endpoint returns cached data on cache hit."""
        Projeto.objects.create(nome="Teste", codigo="TST", ativo=True, is_test=False)

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - populates cache
        response1 = api_client.get("/api/options/projetos/")
        assert response1.status_code == 200

        # Verify cache is set (Python boolean is capitalized: False not false)
        cached = cache.get("static_endpoint:projetos_options:include_test=False")
        assert cached is not None

        # Second request - should use cache
        response2 = api_client.get("/api/options/projetos/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_include_test_param_uses_different_cache(self, api_client, usuario_autenticado):
        """include_test=true uses separate cache key."""
        Projeto.objects.create(nome="Normal", codigo="NRM", ativo=True, is_test=False)
        Projeto.objects.create(nome="Test Project", codigo="TST2", ativo=True, is_test=True)

        api_client.force_authenticate(user=usuario_autenticado)

        # Request without include_test
        response1 = api_client.get("/api/options/projetos/")
        assert response1.status_code == 200
        nomes1 = [p["nome"] for p in response1.json()]
        assert "Normal" in nomes1
        assert "Test Project" not in nomes1

        # Request with include_test=true
        response2 = api_client.get("/api/options/projetos/?include_test=true")
        assert response2.status_code == 200
        nomes2 = [p["nome"] for p in response2.json()]
        assert "Normal" in nomes2
        assert "Test Project" in nomes2

        # Verify separate cache keys (Python boolean capitalized: True/False)
        cached_without = cache.get("static_endpoint:projetos_options:include_test=False")
        cached_with = cache.get("static_endpoint:projetos_options:include_test=True")
        assert cached_without is not None
        assert cached_with is not None
        assert len(cached_with) > len(cached_without)


@pytest.mark.django_db
class TestTiposEventoOptionsCache:
    """Additional cache tests for tipos_evento_options."""

    def test_cache_hit_returns_cached_data(self, api_client, usuario_autenticado):
        """Tipos evento endpoint returns cached data on cache hit."""
        TipoEvento.objects.create(nome="Formação")

        api_client.force_authenticate(user=usuario_autenticado)

        # First request - populates cache
        response1 = api_client.get("/api/options/tipos-evento/")
        assert response1.status_code == 200

        # Verify cache is set
        cached = cache.get("static_endpoint:tipos_evento_options")
        assert cached is not None

        # Second request - should use cache
        response2 = api_client.get("/api/options/tipos-evento/")
        assert response2.status_code == 200
        assert response1.json() == response2.json()
