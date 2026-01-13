"""
Testes unitários para o sistema RBAC (Setor + Função).

Fase 5.1 do plano RBAC_SETOR_FUNCAO.md

Testa:
- SETOR_GROUPS e FUNCAO_GROUPS constants
- Lógica de can_approve_super
- Endpoint /api/me/ com diferentes combinações de grupos
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from apps.core.models import Usuario
from apps.core.views_basic import FUNCAO_GROUPS, SETOR_GROUPS


class TestRBACConstants(TestCase):
    """Testa as constantes SETOR_GROUPS e FUNCAO_GROUPS."""

    def test_setor_groups_contains_expected_setores(self):
        """SETOR_GROUPS deve conter todos os setores esperados."""
        expected_setores = [
            'Superintendência',
            'Vidas',
            'Fluir',
            'ACerta',
            'Brincando',
            'Sou da Paz',
            'DAT',
            'Controle',
            'Gerência',
            'Diretoria',
        ]
        for setor in expected_setores:
            self.assertIn(setor, SETOR_GROUPS, f"Setor '{setor}' não encontrado em SETOR_GROUPS")

    def test_setor_groups_count(self):
        """SETOR_GROUPS deve ter exatamente 10 setores."""
        self.assertEqual(len(SETOR_GROUPS), 10)

    def test_funcao_groups_contains_expected_funcoes(self):
        """FUNCAO_GROUPS deve conter todas as funções esperadas."""
        expected_funcoes = ['Formador', 'Coordenador', 'Apoio de Coordenação', 'Gerente']
        for funcao in expected_funcoes:
            self.assertIn(funcao, FUNCAO_GROUPS, f"Função '{funcao}' não encontrada em FUNCAO_GROUPS")

    def test_funcao_groups_count(self):
        """FUNCAO_GROUPS deve ter exatamente 4 funções."""
        self.assertEqual(len(FUNCAO_GROUPS), 4)

    def test_no_overlap_between_setor_and_funcao(self):
        """Não deve haver sobreposição entre SETOR_GROUPS e FUNCAO_GROUPS."""
        overlap = set(SETOR_GROUPS) & set(FUNCAO_GROUPS)
        self.assertEqual(len(overlap), 0, f"Grupos em ambas as listas: {overlap}")


@pytest.mark.django_db
class TestCanApproveSuperLogic(TestCase):
    """Testa a lógica de can_approve_super via endpoint /api/me/."""

    def setUp(self):
        """Cria grupos e cliente de teste."""
        self.client = APIClient()

        # Criar todos os grupos
        for setor in SETOR_GROUPS:
            Group.objects.get_or_create(name=setor)
        for funcao in FUNCAO_GROUPS:
            Group.objects.get_or_create(name=funcao)

    def _create_user_with_groups(self, username: str, setores: list, funcoes: list, is_superuser: bool = False) -> Usuario:
        """Helper para criar usuário com grupos específicos."""
        user = Usuario.objects.create_user(
            username=username,
            email=f"{username}@test.com",
            password="test123",
            cpf=f"{hash(username) % 10000000000:011d}",
            is_superuser=is_superuser,
        )
        for setor in setores:
            group = Group.objects.get(name=setor)
            user.groups.add(group)
        for funcao in funcoes:
            group = Group.objects.get(name=funcao)
            user.groups.add(group)
        return user

    def test_superuser_can_approve_super(self):
        """Superuser sempre pode aprovar SUPER, independente de grupos."""
        user = self._create_user_with_groups(
            "superuser_test",
            setores=[],
            funcoes=[],
            is_superuser=True,
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_approve_super"])
        self.assertTrue(response.data["is_superuser"])

    def test_gerente_superintendencia_can_approve_super(self):
        """Gerente + Superintendência pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "gerente_super",
            setores=["Superintendência"],
            funcoes=["Gerente"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_approve_super"])
        self.assertIn("Gerente", response.data["funcoes"])
        self.assertIn("Superintendência", response.data["setores"])

    def test_gerente_dat_cannot_approve_super(self):
        """Gerente de DAT NÃO pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "gerente_dat",
            setores=["DAT"],
            funcoes=["Gerente"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])
        self.assertIn("Gerente", response.data["funcoes"])
        self.assertIn("DAT", response.data["setores"])

    def test_gerente_controle_cannot_approve_super(self):
        """Gerente de Controle NÃO pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "gerente_controle",
            setores=["Controle"],
            funcoes=["Gerente"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])

    def test_formador_superintendencia_cannot_approve_super(self):
        """Formador da Superintendência NÃO pode aprovar SUPER (não é Gerente)."""
        user = self._create_user_with_groups(
            "formador_super",
            setores=["Superintendência"],
            funcoes=["Formador"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])
        self.assertIn("Superintendência", response.data["setores"])
        self.assertIn("Formador", response.data["funcoes"])

    def test_coordenador_superintendencia_cannot_approve_super(self):
        """Coordenador da Superintendência NÃO pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "coord_super",
            setores=["Superintendência"],
            funcoes=["Coordenador"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])

    def test_apoio_superintendencia_cannot_approve_super(self):
        """Apoio de Coordenação da Superintendência NÃO pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "apoio_super",
            setores=["Superintendência"],
            funcoes=["Apoio de Coordenação"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])

    def test_gerente_vidas_cannot_approve_super(self):
        """Gerente da gerência Vidas NÃO pode aprovar SUPER (não é Superintendência)."""
        user = self._create_user_with_groups(
            "gerente_vidas",
            setores=["Vidas"],
            funcoes=["Gerente"],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])

    def test_user_with_no_groups_cannot_approve_super(self):
        """Usuário sem grupos NÃO pode aprovar SUPER."""
        user = self._create_user_with_groups(
            "no_groups",
            setores=[],
            funcoes=[],
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_approve_super"])
        self.assertEqual(response.data["setores"], [])
        self.assertEqual(response.data["funcoes"], [])


@pytest.mark.django_db
class TestApiMeEndpoint(TestCase):
    """Testa o endpoint /api/me/ para estrutura de resposta RBAC."""

    def setUp(self):
        """Cria grupos e usuário de teste."""
        self.client = APIClient()

        # Criar grupos
        for setor in SETOR_GROUPS:
            Group.objects.get_or_create(name=setor)
        for funcao in FUNCAO_GROUPS:
            Group.objects.get_or_create(name=funcao)

    def test_api_me_returns_setores_and_funcoes(self):
        """Endpoint /api/me/ deve retornar setores e funcoes separados."""
        user = Usuario.objects.create_user(
            username="test_user",
            email="test@test.com",
            password="test123",
            cpf="12345678901",
        )
        user.groups.add(Group.objects.get(name="Superintendência"))
        user.groups.add(Group.objects.get(name="Gerente"))

        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("setores", response.data)
        self.assertIn("funcoes", response.data)
        self.assertIn("can_approve_super", response.data)
        self.assertIn("is_superintendencia", response.data)

    def test_api_me_separates_groups_correctly(self):
        """Endpoint /api/me/ deve separar corretamente setores e funções."""
        user = Usuario.objects.create_user(
            username="mixed_user",
            email="mixed@test.com",
            password="test123",
            cpf="98765432101",
        )
        # Adicionar múltiplos setores e funções
        user.groups.add(Group.objects.get(name="Superintendência"))
        user.groups.add(Group.objects.get(name="DAT"))
        user.groups.add(Group.objects.get(name="Gerente"))
        user.groups.add(Group.objects.get(name="Coordenador"))

        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Superintendência", response.data["setores"])
        self.assertIn("DAT", response.data["setores"])
        self.assertIn("Gerente", response.data["funcoes"])
        self.assertIn("Coordenador", response.data["funcoes"])
        # groups deve conter todos
        self.assertEqual(len(response.data["groups"]), 4)

    def test_api_me_unauthenticated_returns_403(self):
        """Endpoint /api/me/ sem autenticação deve retornar 401/403."""
        response = self.client.get("/api/me/")
        self.assertIn(response.status_code, [401, 403])

    def test_is_superintendencia_with_setor(self):
        """is_superintendencia deve ser True se usuário está no setor Superintendência."""
        user = Usuario.objects.create_user(
            username="super_user",
            email="super@test.com",
            password="test123",
            cpf="11111111111",
        )
        user.groups.add(Group.objects.get(name="Superintendência"))

        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_superintendencia"])

    def test_is_superintendencia_with_superuser(self):
        """is_superintendencia deve ser True se usuário é superuser."""
        user = Usuario.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="test123",
            cpf="22222222222",
            is_superuser=True,
        )

        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["is_superintendencia"])

    def test_is_superintendencia_without_setor(self):
        """is_superintendencia deve ser False se usuário não está no setor."""
        user = Usuario.objects.create_user(
            username="dat_user",
            email="dat@test.com",
            password="test123",
            cpf="33333333333",
        )
        user.groups.add(Group.objects.get(name="DAT"))

        self.client.force_authenticate(user=user)
        response = self.client.get("/api/me/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["is_superintendencia"])
