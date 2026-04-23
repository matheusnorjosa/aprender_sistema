"""
Testes para endpoint assign_groups (GAP-003).

Fase 1 Iteração 3 - Plano DAT/GCal 2025-10-29

Security tests added for Issue #561 (C-04):
- Self-modification blocked (403)
- Groups whitelist validation (400 for invalid groups)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import PermissaoFuncional, Usuario


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def usuario_dat(db):
    """Usuário com permissão DAT."""
    user = Usuario.objects.create_user(
        username="dat_user",
        email="dat@example.com",
        password="testpass123",
        cpf="11111111111",
    )
    grupo_dat, _ = Group.objects.get_or_create(name="DAT")
    user.groups.add(grupo_dat)
    return user


@pytest.fixture
def usuario_formador(db):
    """Usuário formador sem grupos."""
    return Usuario.objects.create_user(
        username="formador1",
        email="formador1@example.com",
        password="testpass123",
        cpf="22222222222",
    )


@pytest.fixture
def usuario_comum(db):
    """Usuário sem permissão DAT."""
    return Usuario.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="testpass123",
        cpf="33333333333",
    )


@pytest.mark.django_db
class TestAssignGroups:
    """Testes para o endpoint assign_groups."""

    def test_assign_groups_success(self, api_client, usuario_dat, usuario_formador):
        """Deve atribuir grupos com sucesso (200)."""
        # Criar grupos
        grupo1, _ = Group.objects.get_or_create(name="Formador")
        grupo2, _ = Group.objects.get_or_create(name="Coordenador")

        # Login como DAT
        api_client.force_authenticate(usuario_dat)

        # Atribuir grupos
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo1.id, grupo2.id]},
            format="json",
        )

        assert response.status_code == 200
        assert "groups" in response.data

        # Verificar que usuário tem os 2 grupos
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 2
        assert set(usuario_formador.groups.values_list("id", flat=True)) == {
            grupo1.id,
            grupo2.id,
        }

    def test_assign_groups_nonexistent_group(self, api_client, usuario_dat, usuario_formador):
        """Deve retornar 400 quando grupo não existe."""
        grupo1, _ = Group.objects.get_or_create(name="Formador")

        api_client.force_authenticate(usuario_dat)

        # Tentar atribuir grupo inexistente (ID 9999)
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo1.id, 9999]},
            format="json",
        )

        assert response.status_code == 400
        assert "error" in response.data
        assert "not found" in response.data["error"].lower()
        assert "9999" in str(response.data["error"])

    def test_assign_groups_empty_list(self, api_client, usuario_dat, usuario_formador):
        """Deve remover todos os grupos quando lista vazia (200)."""
        # Adicionar grupo inicial
        grupo1, _ = Group.objects.get_or_create(name="Formador")
        usuario_formador.groups.add(grupo1)
        assert usuario_formador.groups.count() == 1

        api_client.force_authenticate(usuario_dat)

        # Enviar lista vazia
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": []},
            format="json",
        )

        assert response.status_code == 200

        # Verificar que todos os grupos foram removidos
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 0

    def test_assign_groups_duplicates(self, api_client, usuario_dat, usuario_formador):
        """Deve ignorar IDs duplicados e atribuir apenas uma vez."""
        grupo1, _ = Group.objects.get_or_create(name="Formador")

        api_client.force_authenticate(usuario_dat)

        # Enviar IDs duplicados
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo1.id, grupo1.id, grupo1.id]},
            format="json",
        )

        assert response.status_code == 200

        # Verificar que grupo foi atribuído apenas uma vez
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 1
        assert usuario_formador.groups.first().id == grupo1.id

    def test_assign_groups_permission_denied(self, api_client, usuario_comum, usuario_formador):
        """Deve retornar 403 quando usuário não tem permissão DAT."""
        grupo1, _ = Group.objects.get_or_create(name="Formador")

        # Login como usuário comum (sem DAT)
        api_client.force_authenticate(usuario_comum)

        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo1.id]},
            format="json",
        )

        assert response.status_code == 403

    def test_assign_groups_invalid_payload(self, api_client, usuario_dat, usuario_formador):
        """Deve retornar 400 quando payload é inválido."""
        api_client.force_authenticate(usuario_dat)

        # Teste 1: group_ids não é lista
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": "not a list"},
            format="json",
        )

        assert response.status_code == 400
        assert "must be a list" in response.data["error"]

        # Teste 2: group_ids contém strings não-numéricas
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": ["abc", "def"]},
            format="json",
        )

        assert response.status_code == 400
        assert "integers" in response.data["error"]

    def test_assign_groups_replaces_existing(self, api_client, usuario_dat, usuario_formador):
        """Deve substituir grupos existentes (não adicionar)."""
        # Configurar grupos iniciais
        grupo1, _ = Group.objects.get_or_create(name="Formador")
        grupo2, _ = Group.objects.get_or_create(name="Coordenador")
        grupo3, _ = Group.objects.get_or_create(name="Gerência")

        usuario_formador.groups.set([grupo1, grupo2])
        assert usuario_formador.groups.count() == 2

        api_client.force_authenticate(usuario_dat)

        # Atribuir apenas grupo3 (deve remover grupo1 e grupo2)
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo3.id]},
            format="json",
        )

        assert response.status_code == 200

        # Verificar que apenas grupo3 está atribuído
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 1
        assert usuario_formador.groups.first().id == grupo3.id

    # =========================================================================
    # Security Tests (Issue #561 C-04)
    # =========================================================================

    def test_assign_groups_self_modification_blocked(self, api_client, usuario_dat):
        """
        C-04: Deve bloquear auto-modificação de grupos (403).

        Security: Usuários não podem modificar seus próprios grupos,
        mesmo que tenham permissão DAT.
        """
        # Criar grupo válido da whitelist
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")

        api_client.force_authenticate(usuario_dat)

        # DAT tentando modificar seus próprios grupos
        response = api_client.post(
            f"/api/usuarios-admin/{usuario_dat.id}/assign_groups/",
            {"group_ids": [grupo_formador.id]},
            format="json",
        )

        assert response.status_code == 403
        assert "próprios grupos" in response.data["error"]

    def test_assign_groups_whitelist_validation(self, api_client, usuario_dat, usuario_formador):
        """
        C-04: Deve rejeitar grupos fora da whitelist (400).

        Security: Apenas grupos em ALLOWED_USER_GROUPS podem ser atribuídos.
        """
        # Criar grupo que NÃO está na whitelist
        grupo_invalido, _ = Group.objects.get_or_create(name="GrupoInvalido")

        api_client.force_authenticate(usuario_dat)

        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo_invalido.id]},
            format="json",
        )

        assert response.status_code == 400
        assert "não permitido" in response.data["error"]
        assert "GrupoInvalido" in response.data["error"]

    def test_assign_groups_with_valid_whitelist_groups(self, api_client, usuario_dat, usuario_formador):
        """
        C-04: Deve permitir atribuição de grupos válidos da whitelist (200).

        Valida que grupos como 'Formador', 'Coordenador', 'DAT' funcionam.
        """
        # Criar grupos válidos da whitelist
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")
        grupo_coordenador, _ = Group.objects.get_or_create(name="Coordenador")

        api_client.force_authenticate(usuario_dat)

        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo_formador.id, grupo_coordenador.id]},
            format="json",
        )

        assert response.status_code == 200

        # Verificar que grupos foram atribuídos
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 2
        group_names = set(usuario_formador.groups.values_list("name", flat=True))
        assert group_names == {"Formador", "Coordenador"}

    def test_assign_groups_mixed_valid_invalid_groups(self, api_client, usuario_dat, usuario_formador):
        """
        C-04: Deve rejeitar se qualquer grupo estiver fora da whitelist (400).

        Mesmo que alguns grupos sejam válidos, se um for inválido,
        toda a operação deve falhar.
        """
        # Criar um grupo válido e um inválido
        grupo_formador, _ = Group.objects.get_or_create(name="Formador")
        grupo_invalido, _ = Group.objects.get_or_create(name="GrupoHacker")

        api_client.force_authenticate(usuario_dat)

        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo_formador.id, grupo_invalido.id]},
            format="json",
        )

        assert response.status_code == 400
        assert "GrupoHacker" in response.data["error"]

        # Verificar que nenhum grupo foi alterado (operação atômica)
        usuario_formador.refresh_from_db()
        assert usuario_formador.groups.count() == 0

    def test_assign_groups_allows_dynamic_group_with_functional_permission(
        self, api_client, usuario_dat, usuario_formador
    ):
        """
        #832 - Grupo fora do fallback estatico deve ser permitido se tiver permissao funcional vinculada.
        """

        grupo_dinamico, _ = Group.objects.get_or_create(name="GrupoDinamicoRBAC")
        permissao, _ = PermissaoFuncional.objects.get_or_create(
            codename="pode_operar_grupo_dinamico",
            defaults={
                "label": "Pode operar grupo dinâmico",
                "description": "Permissão para validar whitelist dinâmica.",
                "category": "cadastros_administrativos",
                "is_system": False,
            },
        )
        permissao.groups.add(grupo_dinamico)

        api_client.force_authenticate(usuario_dat)

        response = api_client.post(
            f"/api/usuarios-admin/{usuario_formador.id}/assign_groups/",
            {"group_ids": [grupo_dinamico.id]},
            format="json",
        )

        assert response.status_code == 200
        usuario_formador.refresh_from_db()
        assert set(usuario_formador.groups.values_list("name", flat=True)) == {"GrupoDinamicoRBAC"}
