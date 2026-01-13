"""
Tests for DAT Registros module.

Ref: v2/docs/SPEC_DAT_REGISTROS.md
"""
# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.models import DATRegistro, Municipio, Projeto, ProjetoGeral

User = get_user_model()


class ProjetoGeralModelTests(TestCase):
    """Tests for ProjetoGeral model."""

    def test_create_projeto_geral_por_aluno(self):
        """ProjetoGeral with tipo_calculo=por_aluno should be created correctly."""
        pg = ProjetoGeral.objects.create(
            nome="Test Project A",
            usa_avaliar=False,
            tipo_calculo_codigos="por_aluno",
            divisor_aluno=20,
        )
        self.assertEqual(pg.tipo_calculo_codigos, "por_aluno")
        self.assertEqual(pg.divisor_aluno, 20)
        self.assertFalse(pg.usa_avaliar)

    def test_create_projeto_geral_por_professor(self):
        """ProjetoGeral with tipo_calculo=por_professor should be created correctly."""
        pg = ProjetoGeral.objects.create(
            nome="Test Project B",
            usa_avaliar=True,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        self.assertEqual(pg.tipo_calculo_codigos, "por_professor")
        self.assertEqual(pg.multiplicador_professor, Decimal("1.1"))
        self.assertTrue(pg.usa_avaliar)

    def test_str_includes_avaliar_status(self):
        """ProjetoGeral __str__ should show usa_avaliar status."""
        pg_with = ProjetoGeral.objects.create(nome="With Avaliar", usa_avaliar=True)
        pg_without = ProjetoGeral.objects.create(nome="Without Avaliar", usa_avaliar=False)

        self.assertIn("✅", str(pg_with))
        self.assertIn("⭕", str(pg_without))


class DATRegistroModelTests(TestCase):
    """Tests for DATRegistro model."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        cls.municipio = Municipio.objects.create(nome="Test City", uf="CE")
        cls.projeto_geral_professor = ProjetoGeral.objects.create(
            nome="PG Professor",
            usa_avaliar=True,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        cls.projeto_geral_aluno = ProjetoGeral.objects.create(
            nome="PG Aluno",
            usa_avaliar=False,
            tipo_calculo_codigos="por_aluno",
            divisor_aluno=20,
        )
        cls.projeto = Projeto.objects.create(
            nome="Test Projeto",
            codigo="TEST",
            fluxo="NAO_SUPER",
            projeto_geral=cls.projeto_geral_professor,
        )
        cls.user = User.objects.create_user(username="testuser", password="test123")

    def test_nr_codigos_calculated_por_professor(self):
        """nr_codigos should be calculated using professor * multiplicador."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            created_by=self.user,
        )
        # 10 * 1.1 = 11 (ceiling)
        self.assertEqual(reg.nr_codigos, 11)

    def test_nr_codigos_calculated_por_aluno(self):
        """nr_codigos should be calculated using alunos / divisor."""
        projeto_aluno = Projeto.objects.create(
            nome="Test Projeto Aluno",
            codigo="TESTALUNO",
            fluxo="NAO_SUPER",
            projeto_geral=self.projeto_geral_aluno,
        )
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_aluno,
            projeto=projeto_aluno,
            aluno_qtde=200,
            created_by=self.user,
        )
        # 200 / 20 = 10 (ceiling)
        self.assertEqual(reg.nr_codigos, 10)

    def test_usa_avaliar_synced_from_projeto_geral(self):
        """usa_avaliar should be synced from projeto_geral on save."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,  # usa_avaliar=True
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            created_by=self.user,
        )
        self.assertTrue(reg.usa_avaliar)

    def test_avaliar_fields_set_to_nao_aplicavel_when_not_used(self):
        """Avaliar status fields should be 'nao_aplicavel' when usa_avaliar=False."""
        projeto_aluno = Projeto.objects.create(
            nome="Test Projeto Aluno 2",
            codigo="TESTALUNO2",
            fluxo="NAO_SUPER",
            projeto_geral=self.projeto_geral_aluno,  # usa_avaliar=False
        )
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_aluno,
            projeto=projeto_aluno,
            aluno_qtde=100,
            created_by=self.user,
        )
        self.assertFalse(reg.usa_avaliar)
        self.assertEqual(reg.alunos_recebidos_status, "nao_aplicavel")
        self.assertEqual(reg.alunos_validados_status, "nao_aplicavel")
        self.assertEqual(reg.alunos_importados_status, "nao_aplicavel")

    def test_turma_formar_url_generated(self):
        """turma_formar_url should generate correct URL."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            turma_formar_id=12345,
            created_by=self.user,
        )
        expected_url = "https://www.aprenderformar.com.br/plataforma/course/view.php?id=12345"
        self.assertEqual(reg.turma_formar_url, expected_url)

    def test_turma_formar_url_none_when_no_id(self):
        """turma_formar_url should be None when turma_formar_id is not set."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            created_by=self.user,
        )
        self.assertIsNone(reg.turma_formar_url)

    def test_status_geral_pendente_formar(self):
        """status_geral should be 'pendente_formar' when FORMAR not complete."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            chaves_inscricao_status="pendente",
            created_by=self.user,
        )
        self.assertEqual(reg.status_geral, "pendente_formar")

    def test_status_geral_pendente_avaliar(self):
        """status_geral should be 'pendente_avaliar' when AVALIAR not complete."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,  # usa_avaliar=True
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            chaves_inscricao_status="concluido",
            instrucoes_status="concluido",
            envio_codigos_status="concluido",
            alunos_recebidos_status="pendente",
            created_by=self.user,
        )
        self.assertEqual(reg.status_geral, "pendente_avaliar")

    def test_status_geral_completo(self):
        """status_geral should be 'completo' when all required fields are done."""
        reg = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            chaves_inscricao_status="concluido",
            instrucoes_status="concluido",
            envio_codigos_status="concluido",
            alunos_recebidos_status="concluido",
            alunos_validados_status="concluido",
            alunos_importados_status="concluido",
            created_by=self.user,
        )
        self.assertEqual(reg.status_geral, "completo")

    def test_unique_constraint_municipio_projeto(self):
        """Only one DATRegistro per municipio+projeto_geral+projeto combination."""
        DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral_professor,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            created_by=self.user,
        )
        # Try to create duplicate
        from django.db import IntegrityError

        with self.assertRaises(IntegrityError):
            DATRegistro.objects.create(
                municipio=self.municipio,
                projeto_geral=self.projeto_geral_professor,
                projeto=self.projeto,
                aluno_qtde=200,
                professor_qtde=20,
                created_by=self.user,
            )


class DATRegistroAPITests(APITestCase):
    """Tests for DATRegistro API endpoints."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        import uuid

        suffix = str(uuid.uuid4())[:8]

        cls.municipio = Municipio.objects.create(nome=f"API Test City {suffix}", uf="BA")
        cls.projeto_geral = ProjetoGeral.objects.create(
            nome=f"API PG {suffix}",
            usa_avaliar=True,
            tipo_calculo_codigos="por_professor",
            multiplicador_professor=Decimal("1.1"),
        )
        cls.projeto = Projeto.objects.create(
            nome=f"API Test Projeto {suffix}",
            codigo=f"APITEST{suffix}",
            fluxo="NAO_SUPER",
            projeto_geral=cls.projeto_geral,
        )

        # Create groups
        cls.dat_group, _ = Group.objects.get_or_create(name="DAT")
        cls.super_group, _ = Group.objects.get_or_create(name="Superintendência")

        # Create users with unique CPFs (11 chars max)
        cls.regular_user = User.objects.create_user(
            username=f"regular_{suffix}",
            password="test123",
            cpf=f"111{suffix[:8]}",  # 11 chars: 111 + 8 chars
        )
        cls.dat_user = User.objects.create_user(
            username=f"datuser_{suffix}",
            password="test123",
            cpf=f"222{suffix[:8]}",
        )
        cls.dat_user.groups.add(cls.dat_group)
        cls.super_user = User.objects.create_user(
            username=f"superuser_{suffix}",
            password="test123",
            cpf=f"333{suffix[:8]}",
        )
        cls.super_user.groups.add(cls.super_group)

    def test_list_requires_dat_permission(self):
        """GET /api/dat/registros/ should require DAT permission (IsDATOrSuper)."""
        url = reverse("core:dat-registro-list")
        # Unauthenticated
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Regular user (not DAT) should also get 403
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_allowed_for_dat_user(self):
        """GET /api/dat/registros/ should work for DAT users."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-registro-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_requires_dat_permission(self):
        """POST /api/dat/registros/ should require DAT permission."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:dat-registro-list")
        data = {
            "municipio": self.municipio.id,
            "projeto_geral": self.projeto_geral.id,
            "projeto": self.projeto.id,
            "aluno_qtde": 100,
            "professor_qtde": 10,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_allowed_for_dat_user(self):
        """POST /api/dat/registros/ should work for DAT users."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-registro-list")
        data = {
            "municipio": self.municipio.id,
            "projeto_geral": self.projeto_geral.id,
            "projeto": self.projeto.id,
            "aluno_qtde": 100,
            "professor_qtde": 10,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["aluno_qtde"], 100)

    def test_create_sets_created_by(self):
        """POST should set created_by to request user."""
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-registro-list")
        data = {
            "municipio": self.municipio.id,
            "projeto_geral": self.projeto_geral.id,
            "projeto": self.projeto.id,
            "aluno_qtde": 100,
            "professor_qtde": 10,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        registro = DATRegistro.objects.get(id=response.data["id"])
        self.assertEqual(registro.created_by, self.dat_user)

    def test_delete_requires_superintendencia(self):
        """DELETE /api/dat/registros/{id}/ should require Superintendência."""
        # Create a registro
        registro = DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            created_by=self.dat_user,
        )

        # DAT user should not be able to delete
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-registro-detail", args=[registro.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Super user should be able to delete
        self.client.force_authenticate(user=self.super_user)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_stats_endpoint_requires_dat(self):
        """GET /api/dat/registros/stats/ should require DAT permission."""
        url = reverse("core:dat-registro-stats")

        # Regular user should get 403
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stats_endpoint(self):
        """GET /api/dat/registros/stats/ should return aggregated stats for DAT users."""
        # Create some registros
        DATRegistro.objects.create(
            municipio=self.municipio,
            projeto_geral=self.projeto_geral,
            projeto=self.projeto,
            aluno_qtde=100,
            professor_qtde=10,
            chaves_inscricao_status="concluido",
            instrucoes_status="concluido",
            envio_codigos_status="concluido",
            created_by=self.dat_user,
        )

        # DAT user should get 200
        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:dat-registro-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total", response.data)
        self.assertIn("completos_formar", response.data)
        self.assertIn("usa_avaliar", response.data)
        self.assertIn("por_uf", response.data)


class ProjetoGeralAPITests(APITestCase):
    """Tests for ProjetoGeral API endpoints."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        import uuid

        suffix = str(uuid.uuid4())[:8]

        cls.dat_group, _ = Group.objects.get_or_create(name="DAT")
        cls.regular_user = User.objects.create_user(
            username=f"regular2_{suffix}",
            password="test123",
            cpf=f"444{suffix[:8]}",  # 11 chars
        )
        cls.dat_user = User.objects.create_user(
            username=f"datuser2_{suffix}",
            password="test123",
            cpf=f"555{suffix[:8]}",
        )
        cls.dat_user.groups.add(cls.dat_group)

    def test_list_projects_gerais(self):
        """GET /api/projetos-gerais/ should list all projetos gerais."""
        import uuid
        suffix = str(uuid.uuid4())[:8]
        ProjetoGeral.objects.create(nome=f"Test PG 1 {suffix}", usa_avaliar=True)
        ProjetoGeral.objects.create(nome=f"Test PG 2 {suffix}", usa_avaliar=False)

        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:projeto-geral-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should include seed data + 2 new
        self.assertGreaterEqual(len(response.data), 2)

    def test_list_minimal_option_serializer(self):
        """GET /api/projetos-gerais/?minimal=true should return minimal data."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:projeto-geral-list") + "?minimal=true"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response may be paginated (dict with 'results') or a list
        results = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        if results:
            first = results[0]
            # Should have minimal fields
            self.assertIn("id", first)
            self.assertIn("nome", first)
            self.assertIn("usa_avaliar", first)
            # Should not have full fields
            self.assertNotIn("created_at", first)

    def test_create_projeto_geral_requires_dat(self):
        """POST /api/projetos-gerais/ should require DAT permission."""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:projeto-geral-list")
        data = {"nome": "New PG", "usa_avaliar": True}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_projeto_geral_allowed_for_dat(self):
        """POST /api/projetos-gerais/ should work for DAT users."""
        import uuid
        suffix = str(uuid.uuid4())[:8]

        self.client.force_authenticate(user=self.dat_user)
        url = reverse("core:projeto-geral-list")
        data = {
            "nome": f"New PG by DAT {suffix}",
            "usa_avaliar": True,
            "tipo_calculo_codigos": "por_professor",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_projetos_action_lists_specific_projects(self):
        """GET /api/projetos-gerais/{id}/projetos/ should list linked projects."""
        import uuid
        suffix = str(uuid.uuid4())[:8]

        pg = ProjetoGeral.objects.create(nome=f"PG with Projects {suffix}", usa_avaliar=True)
        Projeto.objects.create(
            nome=f"Linked Project {suffix}",
            codigo=f"LINKED{suffix}",
            fluxo="NAO_SUPER",
            projeto_geral=pg,
        )

        self.client.force_authenticate(user=self.regular_user)
        url = reverse("core:projeto-geral-projetos", args=[pg.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIn("Linked Project", response.data[0]["nome"])
