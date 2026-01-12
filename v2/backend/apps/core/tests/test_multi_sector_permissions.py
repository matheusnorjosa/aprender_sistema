"""
Testes para permissões e filtros multi-setor (Epic #379).

Testa:
- HasSectorAccess permission (Issue #381)
- MonthlyAvailabilityView com gerencia_id (Issue #382)
- AvailabilityBlockViewSet filtro por gerência (Issue #383)
"""

import pytest
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory

from apps.core.models import (
    AvailabilityBlock,
    EquipeGerencia,
    Gerencia,
    Usuario,
)
from apps.core.permissions import HasSectorAccess


class MockView:
    """Mock view for permission testing."""

    def __init__(self, kwargs=None):
        self.kwargs = kwargs or {}


@pytest.mark.django_db
class TestHasSectorAccessPermission(TestCase):
    """Testes para HasSectorAccess permission."""

    def setUp(self):
        """Cria fixtures de teste."""
        self.factory = APIRequestFactory()
        self.permission = HasSectorAccess()

        # Criar grupos
        self.controle_group = Group.objects.create(name="Controle")
        self.formador_group = Group.objects.create(name="Formador")

        # Criar gerências
        self.gerencia_vidas = Gerencia.objects.create(
            nome="GERENCIA 2", nome_setor="Vidas"
        )
        self.gerencia_fluir = Gerencia.objects.create(
            nome="GERENCIA 3", nome_setor="Fluir"
        )

        # Criar usuários
        self.superuser = Usuario.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            cpf="00000000000",
        )

        self.user_controle = Usuario.objects.create_user(
            username="controle_user",
            email="controle@test.com",
            password="test123",
            cpf="11111111111",
        )
        self.user_controle.groups.add(self.controle_group)

        self.user_vidas = Usuario.objects.create_user(
            username="vidas_user",
            email="vidas@test.com",
            password="test123",
            cpf="22222222222",
        )
        EquipeGerencia.objects.create(
            gerencia=self.gerencia_vidas,
            usuario=self.user_vidas,
            papel="FORMADOR",
        )

        self.user_fluir = Usuario.objects.create_user(
            username="fluir_user",
            email="fluir@test.com",
            password="test123",
            cpf="33333333333",
        )
        EquipeGerencia.objects.create(
            gerencia=self.gerencia_fluir,
            usuario=self.user_fluir,
            papel="FORMADOR",
        )

        self.user_sem_gerencia = Usuario.objects.create_user(
            username="sem_gerencia",
            email="sem@test.com",
            password="test123",
            cpf="44444444444",
        )

    def test_superuser_can_access_any_gerencia(self):
        """Superuser deve acessar qualquer gerência."""
        request = self.factory.get("/")
        request.user = self.superuser
        request.query_params = {"gerencia_id": str(self.gerencia_vidas.id)}

        view = MockView()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_controle_user_is_blocked(self):
        """Usuário do grupo Controle deve ser bloqueado."""
        request = self.factory.get("/")
        request.user = self.user_controle
        request.query_params = {"gerencia_id": str(self.gerencia_vidas.id)}

        view = MockView()
        self.assertFalse(self.permission.has_permission(request, view))

    def test_user_can_access_own_gerencia(self):
        """Usuário pode acessar sua própria gerência."""
        request = self.factory.get("/")
        request.user = self.user_vidas
        request.query_params = {"gerencia_id": str(self.gerencia_vidas.id)}

        view = MockView()
        self.assertTrue(self.permission.has_permission(request, view))

    def test_user_cannot_access_other_gerencia(self):
        """Usuário não pode acessar gerência de outro setor."""
        request = self.factory.get("/")
        request.user = self.user_vidas
        request.query_params = {"gerencia_id": str(self.gerencia_fluir.id)}

        view = MockView()
        self.assertFalse(self.permission.has_permission(request, view))

    def test_user_without_gerencia_id_but_with_gerencia_is_allowed(self):
        """Requisição sem gerencia_id mas com gerência vinculada é permitida."""
        request = self.factory.get("/")
        request.user = self.user_vidas
        request.query_params = {}

        view = MockView()
        # Deve permitir pois user_vidas tem gerência vinculada
        self.assertTrue(self.permission.has_permission(request, view))

    def test_user_without_gerencia_and_without_gerencia_id_is_denied(self):
        """Requisição sem gerencia_id e sem gerência vinculada é negada."""
        request = self.factory.get("/")
        request.user = self.user_sem_gerencia
        request.query_params = {}

        view = MockView()
        self.assertFalse(self.permission.has_permission(request, view))


@pytest.mark.django_db
class TestMonthlyAvailabilityViewMultiSector(TestCase):
    """Testes para MonthlyAvailabilityView com gerencia_id."""

    def setUp(self):
        """Cria fixtures de teste."""
        self.client = APIClient()

        # Criar grupos
        self.controle_group = Group.objects.create(name="Controle")

        # Criar gerências
        self.gerencia_vidas = Gerencia.objects.create(
            nome="GERENCIA 2", nome_setor="Vidas"
        )

        # Criar usuários
        self.superuser = Usuario.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            cpf="00000000000",
        )

        self.user_vidas = Usuario.objects.create_user(
            username="vidas_user",
            email="vidas@test.com",
            password="test123",
            cpf="22222222222",
        )
        EquipeGerencia.objects.create(
            gerencia=self.gerencia_vidas,
            usuario=self.user_vidas,
            papel="FORMADOR",
        )

        self.user_controle = Usuario.objects.create_user(
            username="controle_user",
            email="controle@test.com",
            password="test123",
            cpf="11111111111",
        )
        self.user_controle.groups.add(self.controle_group)

    def test_superuser_can_access_any_gerencia(self):
        """Superuser pode acessar qualquer gerência."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            "/api/availability/monthly/",
            {"year": 2025, "month": 1, "role": "FORMADOR", "gerencia_id": self.gerencia_vidas.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("days", response.data)

    def test_superuser_can_access_without_gerencia_id(self):
        """Superuser pode acessar sem gerencia_id (fallback SUPER)."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            "/api/availability/monthly/",
            {"year": 2025, "month": 1, "role": "FORMADOR"},
        )
        self.assertEqual(response.status_code, 200)

    def test_user_with_gerencia_can_access_own_sector(self):
        """Usuário com gerência pode acessar seu próprio setor."""
        self.client.force_authenticate(user=self.user_vidas)
        response = self.client.get(
            "/api/availability/monthly/",
            {"year": 2025, "month": 1, "role": "FORMADOR", "gerencia_id": self.gerencia_vidas.id},
        )
        self.assertEqual(response.status_code, 200)

    def test_user_defaults_to_own_gerencia(self):
        """Usuário sem gerencia_id usa sua própria gerência como default."""
        self.client.force_authenticate(user=self.user_vidas)
        response = self.client.get(
            "/api/availability/monthly/",
            {"year": 2025, "month": 1, "role": "FORMADOR"},
        )
        self.assertEqual(response.status_code, 200)

    def test_controle_user_is_blocked(self):
        """Usuário do grupo Controle deve ser bloqueado."""
        self.client.force_authenticate(user=self.user_controle)
        response = self.client.get(
            "/api/availability/monthly/",
            {"year": 2025, "month": 1, "role": "FORMADOR", "gerencia_id": self.gerencia_vidas.id},
        )
        self.assertEqual(response.status_code, 403)


@pytest.mark.django_db
class TestAvailabilityBlockViewSetMultiSector(TestCase):
    """Testes para AvailabilityBlockViewSet filtro por gerência."""

    def setUp(self):
        """Cria fixtures de teste."""
        self.client = APIClient()

        # Criar grupos (get_or_create para evitar duplicatas)
        self.controle_group, _ = Group.objects.get_or_create(name="Controle")

        # Criar gerências com nomes únicos para este teste
        self.gerencia_vidas, _ = Gerencia.objects.get_or_create(
            nome="TEST_GERENCIA_VIDAS", defaults={"nome_setor": "Test Vidas"}
        )
        self.gerencia_fluir, _ = Gerencia.objects.get_or_create(
            nome="TEST_GERENCIA_FLUIR", defaults={"nome_setor": "Test Fluir"}
        )

        # Criar usuários com CPF único
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]

        self.superuser = Usuario.objects.create_superuser(
            username=f"admin_block_{unique_suffix}",
            email=f"admin_block_{unique_suffix}@test.com",
            password="admin123",
            cpf=f"99{unique_suffix[:9]}",
        )

        self.user_vidas = Usuario.objects.create_user(
            username=f"vidas_block_{unique_suffix}",
            email=f"vidas_block_{unique_suffix}@test.com",
            password="test123",
            cpf=f"88{unique_suffix[:9]}",
        )
        EquipeGerencia.objects.create(
            gerencia=self.gerencia_vidas,
            usuario=self.user_vidas,
            papel="FORMADOR",
        )

        self.user_fluir = Usuario.objects.create_user(
            username=f"fluir_block_{unique_suffix}",
            email=f"fluir_block_{unique_suffix}@test.com",
            password="test123",
            cpf=f"77{unique_suffix[:9]}",
        )
        EquipeGerencia.objects.create(
            gerencia=self.gerencia_fluir,
            usuario=self.user_fluir,
            papel="FORMADOR",
        )

        self.user_controle = Usuario.objects.create_user(
            username=f"controle_block_{unique_suffix}",
            email=f"controle_block_{unique_suffix}@test.com",
            password="test123",
            cpf=f"66{unique_suffix[:9]}",
        )
        self.user_controle.groups.add(self.controle_group)

        # Criar bloqueios para os usuários de teste
        self.block_vidas = AvailabilityBlock.objects.create(
            usuario=self.user_vidas,
            inicio="2025-01-15T09:00:00Z",
            fim="2025-01-15T18:00:00Z",
            tipo="T",
            status="aprovado",
        )
        self.block_fluir = AvailabilityBlock.objects.create(
            usuario=self.user_fluir,
            inicio="2025-01-16T09:00:00Z",
            fim="2025-01-16T18:00:00Z",
            tipo="P",
            status="aprovado",
        )

    def test_superuser_sees_all_blocks(self):
        """Superuser deve ver todos os bloqueios (incluindo os criados no teste)."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get("/api/availability-blocks/")
        self.assertEqual(response.status_code, 200)
        # Resposta é paginada, acessar results
        results = response.data.get("results", response.data)
        block_ids = [b["id"] for b in results]
        self.assertIn(self.block_vidas.id, block_ids)
        self.assertIn(self.block_fluir.id, block_ids)

    def test_user_sees_only_same_gerencia_blocks(self):
        """Usuário deve ver apenas bloqueios da sua gerência."""
        self.client.force_authenticate(user=self.user_vidas)
        response = self.client.get("/api/availability-blocks/")
        self.assertEqual(response.status_code, 200)
        # Resposta é paginada, acessar results
        results = response.data.get("results", response.data)
        block_ids = [b["id"] for b in results]
        self.assertIn(self.block_vidas.id, block_ids)
        # Verificar que NÃO vê o bloqueio de outra gerência
        self.assertNotIn(self.block_fluir.id, block_ids)

    def test_controle_user_sees_no_blocks(self):
        """Usuário do grupo Controle não deve ver bloqueios."""
        self.client.force_authenticate(user=self.user_controle)
        response = self.client.get("/api/availability-blocks/")
        self.assertEqual(response.status_code, 200)
        # Resposta é paginada, acessar results ou count
        results = response.data.get("results", response.data)
        count = response.data.get("count", len(results))
        self.assertEqual(count, 0)

    def test_user_can_create_own_block(self):
        """Usuário pode criar bloqueio para si mesmo."""
        self.client.force_authenticate(user=self.user_vidas)
        response = self.client.post(
            "/api/availability-blocks/",
            {
                "inicio": "2025-01-20T09:00:00Z",
                "fim": "2025-01-20T18:00:00Z",
                "tipo": "T",
                "motivo": "Férias",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["usuario"], self.user_vidas.id)
        self.assertEqual(response.data["status"], "aprovado")
