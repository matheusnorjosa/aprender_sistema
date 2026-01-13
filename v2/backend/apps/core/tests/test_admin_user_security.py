"""
P1.1 - Testes de Segurança para UsuarioAdminSerializer

Valida hardening do serializer de admin de usuários:
- is_staff e is_superuser são read_only
- Groups whitelist (DAT, Controle, Superintendência, Coordenador, Formador)
- Usuários não podem modificar próprios groups
- Campos com whitelist explícito (sem setattr indiscriminado)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIRequestFactory

from apps.core.models import Usuario
from apps.core.serializers import UsuarioAdminSerializer


class AdminUserSecurityTests(TestCase):
    """Testes de segurança para UsuarioAdminSerializer"""

    def setUp(self):
        """Setup: criar grupos e usuários de teste"""
        # Criar grupos padrão (usando get_or_create para idempotência)
        self.group_dat, _ = Group.objects.get_or_create(name="DAT")
        self.group_controle, _ = Group.objects.get_or_create(name="Controle")
        self.group_super, _ = Group.objects.get_or_create(name="Superintendência")
        self.group_coord, _ = Group.objects.get_or_create(name="Coordenador")
        self.group_formador, _ = Group.objects.get_or_create(name="Formador")
        self.group_gerencia, _ = Group.objects.get_or_create(name="Gerência")
        self.group_invalid, _ = Group.objects.get_or_create(name="GrupoInválido")  # Não na whitelist

        # Usuário DAT (quem administra usuários)
        self.user_dat = Usuario.objects.create_user(
            username="dat_user",
            email="dat@example.com",
            password="T3stP@ssw0rd!Qwerty#2025XyZ",
            cpf="11111111111",  # Unique CPF
        )
        self.user_dat.groups.add(self.group_dat)

        # Usuário comum para testar atribuição
        self.user_comum = Usuario.objects.create_user(
            username="comum_user",
            email="comum@example.com",
            password="T3stP@ssw0rd!Qwerty#2025XyZ",
            cpf="22222222222",  # Unique CPF
        )

        self.factory = APIRequestFactory()

    def test_dat_cannot_set_is_superuser_or_is_staff(self):
        """
        P1.1 - DAT não pode setar is_superuser ou is_staff via serializer

        Cenário:
        - DAT tenta criar usuário com is_staff=True
        - DAT tenta criar usuário com is_superuser=True

        Expectativa:
        - Campos são read_only, valores ignorados
        - Usuário criado com is_staff=False, is_superuser=False
        """
        data = {
            "username": "new_user",
            "email": "new@example.com",
            "password": "T3stP@ssw0rd!Qwerty#2025XyZ",
            "cpf": "33333333333",  # Required field
            "is_staff": True,  # Deve ser ignorado (read_only)
            "is_superuser": True,  # Deve ser ignorado (read_only)
        }

        request = self.factory.post("/api/usuarios/", data)
        request.user = self.user_dat

        serializer = UsuarioAdminSerializer(data=data, context={"request": request})
        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)  # Debug
        self.assertTrue(serializer.is_valid())

        usuario = serializer.save()

        # Validar que is_staff e is_superuser NÃO foram setados
        self.assertFalse(usuario.is_staff)
        self.assertFalse(usuario.is_superuser)

    def test_dat_cannot_change_own_groups(self):
        """
        P1.1 - DAT não pode modificar próprios grupos

        Cenário:
        - DAT tenta remover grupo DAT de si mesmo
        - DAT tenta adicionar grupo Superintendência a si mesmo

        Expectativa:
        - ValidationError: "Você não pode modificar seus próprios grupos"
        - Groups do DAT permanecem inalterados
        """
        data = {
            "group_ids": [self.group_super.id],  # Tentar trocar DAT → Super
        }

        request = self.factory.patch("/api/usuarios/me/", data)
        request.user = self.user_dat

        # Serializer com instance=self.user_dat (update de si mesmo)
        serializer = UsuarioAdminSerializer(
            instance=self.user_dat,
            data=data,
            partial=True,
            context={"request": request},
        )

        # Deve falhar na validação
        self.assertFalse(serializer.is_valid())
        self.assertIn("group_ids", serializer.errors)
        self.assertIn(
            "não pode modificar seus próprios grupos",
            str(serializer.errors["group_ids"][0]),
        )

    def test_dat_can_assign_whitelisted_groups_to_others(self):
        """
        P1.1 - DAT pode atribuir grupos da whitelist para OUTROS usuários

        Cenário:
        - DAT atualiza user_comum
        - DAT adiciona grupos: Coordenador, Formador (ambos na whitelist)

        Expectativa:
        - Update bem-sucedido
        - user_comum recebe os grupos
        """
        data = {
            "group_ids": [self.group_coord.id, self.group_formador.id],
        }

        request = self.factory.patch(f"/api/usuarios/{self.user_comum.id}/", data)
        request.user = self.user_dat

        # Update de OUTRO usuário (não de si mesmo)
        serializer = UsuarioAdminSerializer(
            instance=self.user_comum,
            data=data,
            partial=True,
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid())
        usuario = serializer.save()

        # Validar que grupos foram atribuídos
        group_names = set(usuario.groups.values_list("name", flat=True))
        self.assertEqual(group_names, {"Coordenador", "Formador"})

    def test_dat_cannot_assign_non_whitelisted_groups(self):
        """
        P1.1 - DAT não pode atribuir grupos FORA da whitelist

        Cenário:
        - DAT tenta atribuir grupo "GrupoInválido" (não na whitelist)

        Expectativa:
        - ValidationError: "Grupo 'GrupoInválido' não permitido"
        - Lista grupos válidos na mensagem de erro
        """
        data = {
            "group_ids": [self.group_invalid.id],
        }

        request = self.factory.patch(f"/api/usuarios/{self.user_comum.id}/", data)
        request.user = self.user_dat

        serializer = UsuarioAdminSerializer(
            instance=self.user_comum,
            data=data,
            partial=True,
            context={"request": request},
        )

        # Deve falhar na validação
        self.assertFalse(serializer.is_valid())
        self.assertIn("group_ids", serializer.errors)
        self.assertIn("GrupoInválido", str(serializer.errors["group_ids"]))
        self.assertIn("não permitido", str(serializer.errors["group_ids"]))

    def test_whitelist_explicit_fields_on_update(self):
        """
        P1.1 - Update usa whitelist explícito de campos

        Cenário:
        - DAT atualiza campos permitidos: first_name, last_name, email
        - Campos são atualizados corretamente

        Expectativa:
        - Apenas campos da whitelist são modificados
        - Sem uso de setattr() genérico
        """
        data = {
            "first_name": "João",
            "last_name": "Silva",
            "email": "joao.silva@example.com",
        }

        request = self.factory.patch(f"/api/usuarios/{self.user_comum.id}/", data)
        request.user = self.user_dat

        serializer = UsuarioAdminSerializer(
            instance=self.user_comum,
            data=data,
            partial=True,
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid())
        usuario = serializer.save()

        # Validar que campos foram atualizados
        self.assertEqual(usuario.first_name, "João")
        self.assertEqual(usuario.last_name, "Silva")
        self.assertEqual(usuario.email, "joao.silva@example.com")

    def test_groups_returns_names_not_ids(self):
        """
        API Design - groups retorna nomes (read-only), group_ids aceita IDs (write-only)

        Cenário:
        - DAT atribui grupos Coordenador e Formador via group_ids
        - Serializer retorna grupos como nomes (não IDs) no campo groups

        Expectativa:
        - Resposta contém groups: ["Coordenador", "Formador"] (nomes)
        - Não contém group_ids na resposta (write-only)
        """
        # Atribuir grupos via group_ids
        data = {
            "group_ids": [self.group_coord.id, self.group_formador.id],
        }

        request = self.factory.patch(f"/api/usuarios/{self.user_comum.id}/", data)
        request.user = self.user_dat

        serializer = UsuarioAdminSerializer(
            instance=self.user_comum,
            data=data,
            partial=True,
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid())
        usuario = serializer.save()

        # Serializar resposta (leitura)
        read_serializer = UsuarioAdminSerializer(usuario)
        response_data = read_serializer.data

        # Verificar que groups contém nomes (não IDs)
        self.assertIn("groups", response_data)
        self.assertIsInstance(response_data["groups"], list)
        self.assertEqual(set(response_data["groups"]), {"Coordenador", "Formador"})

        # Verificar que group_ids NÃO está na resposta (write-only)
        self.assertNotIn("group_ids", response_data)

    def test_gerencia_is_whitelisted(self):
        """
        Whitelist - Grupo Gerência deve estar permitido

        Cenário:
        - DAT atribui grupo Gerência a um usuário

        Expectativa:
        - Atribuição bem-sucedida (Gerência está na whitelist)
        - Usuário recebe o grupo Gerência
        """
        data = {
            "group_ids": [self.group_gerencia.id],
        }

        request = self.factory.patch(f"/api/usuarios/{self.user_comum.id}/", data)
        request.user = self.user_dat

        serializer = UsuarioAdminSerializer(
            instance=self.user_comum,
            data=data,
            partial=True,
            context={"request": request},
        )

        self.assertTrue(serializer.is_valid(), f"Expected valid, got errors: {serializer.errors}")
        usuario = serializer.save()

        # Verificar que Gerência foi atribuído
        group_names = set(usuario.groups.values_list("name", flat=True))
        self.assertEqual(group_names, {"Gerência"})
