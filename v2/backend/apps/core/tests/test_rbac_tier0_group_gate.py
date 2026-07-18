"""
P0-1 Tier-0 (D-1=2a): administração de grupo / matriz Grupo×Capability /
membership é **superuser-only**.

Auditoria 2026-07-17 §4.2: um não-superuser (DAT/Controle) editava a matriz via
`permissao_funcional_ids`, cunhava aprovadores via `sync_members`/`assign_groups`
e criava/renomeava/excluía grupos — tudo sob `manage_purchases_and_materials`.

Invariante: só superuser cria/edita/exclui grupo, edita a matriz, ou muta
membership (sync_members, assign_groups, `group_ids` no cadastro de usuário).
DAT mantém: CRUD de conta comum + LEITURA de grupos (a tela fica read-only).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import PermissaoFuncional, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def dat(db):
    """Não-superuser com manage_admin_registries + manage_purchases_and_materials."""
    user = UsuarioFactory(username="dat_gate", cpf="91000000001")
    user.groups.add(GroupFactory(name="DAT"))
    return user


@pytest.fixture
def root(db):
    return UsuarioFactory(username="root_gate", cpf="91000000009", superuser=True)


@pytest.mark.django_db
class TestGroupViewSetTier0Gate:
    def test_dat_cannot_create_group(self, api_client, dat):
        api_client.force_authenticate(dat)
        resp = api_client.post("/api/grupos/", {"name": "NovoGrupo", "group_type_input": "setor"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert not Group.objects.filter(name="NovoGrupo").exists()

    def test_dat_cannot_edit_group_matrix(self, api_client, dat):
        grupo = GroupFactory(name="Controle")
        perm = PermissaoFuncional.objects.create(
            codename="rbac.gate_test", label="Gate", description="", category="operacao", is_system=False
        )
        api_client.force_authenticate(dat)
        resp = api_client.patch(f"/api/grupos/{grupo.id}/", {"permissao_funcional_ids": [perm.id]}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # A cap que o DAT tentou adicionar NÃO entrou (grupo do seed já tem caps próprias).
        assert not grupo.permissoes_funcionais.filter(id=perm.id).exists()

    def test_dat_cannot_delete_group(self, api_client, dat):
        grupo = GroupFactory(name="GrupoDescartavel")
        api_client.force_authenticate(dat)
        resp = api_client.delete(f"/api/grupos/{grupo.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert Group.objects.filter(id=grupo.id).exists()

    def test_dat_cannot_sync_members(self, api_client, dat):
        grupo = GroupFactory(name="Superintendência")
        api_client.force_authenticate(dat)
        resp = api_client.post(f"/api/grupos/{grupo.id}/sync-members/", {"user_ids": [dat.id]}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert grupo.user_set.count() == 0

    def test_dat_can_still_list_and_retrieve_groups(self, api_client, dat):
        grupo = GroupFactory(name="DAT")
        api_client.force_authenticate(dat)
        assert api_client.get("/api/grupos/").status_code == status.HTTP_200_OK
        assert api_client.get(f"/api/grupos/{grupo.id}/").status_code == status.HTTP_200_OK

    def test_superuser_can_create_group(self, api_client, root):
        api_client.force_authenticate(root)
        resp = api_client.post("/api/grupos/", {"name": "NovoSuper", "group_type_input": "setor"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_superuser_can_edit_group_matrix(self, api_client, root):
        grupo = GroupFactory(name="Coordenador")
        perm = PermissaoFuncional.objects.create(
            codename="rbac.gate_super", label="GateS", description="", category="operacao", is_system=False
        )
        api_client.force_authenticate(root)
        resp = api_client.patch(f"/api/grupos/{grupo.id}/", {"permissao_funcional_ids": [perm.id]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert grupo.permissoes_funcionais.count() == 1


@pytest.mark.django_db
class TestAssignGroupsTier0Gate:
    def test_dat_cannot_assign_groups(self, api_client, dat):
        grupo = GroupFactory(name="Formador")
        target = UsuarioFactory(username="alvo_assign", cpf="91000000003")
        api_client.force_authenticate(dat)
        resp = api_client.post(
            f"/api/usuarios-admin/{target.id}/assign_groups/", {"group_ids": [grupo.id]}, format="json"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        target.refresh_from_db()
        assert target.groups.count() == 0

    def test_superuser_can_assign_groups(self, api_client, root):
        grupo = GroupFactory(name="Formador")
        target = UsuarioFactory(username="alvo_assign2", cpf="91000000004")
        api_client.force_authenticate(root)
        resp = api_client.post(
            f"/api/usuarios-admin/{target.id}/assign_groups/", {"group_ids": [grupo.id]}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert set(target.groups.values_list("name", flat=True)) == {"Formador"}


@pytest.mark.django_db
class TestUserGroupIdsTier0Gate:
    """`group_ids` no cadastro de usuário é superuser-only (membership)."""

    def test_dat_create_user_group_ids_ignored(self, api_client, dat):
        grupo = GroupFactory(name="Superintendência")
        api_client.force_authenticate(dat)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_comum",
                "email": "novo_comum@example.com",
                "cpf": "91000000005",
                "password": "SecurePass123!",
                "group_ids": [grupo.id],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        novo = Usuario.objects.get(username="novo_comum")
        assert novo.groups.count() == 0  # membership ignorada p/ não-superuser

    def test_dat_update_user_group_ids_ignored(self, api_client, dat):
        target = UsuarioFactory(username="alvo_update", cpf="91000000006")
        grupo = GroupFactory(name="Gerente")
        api_client.force_authenticate(dat)
        resp = api_client.patch(f"/api/usuarios-admin/{target.id}/", {"group_ids": [grupo.id]}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.groups.count() == 0

    def test_dat_can_still_update_common_user_cadastral(self, api_client, dat):
        target = UsuarioFactory(username="alvo_cad", cpf="91000000007")
        api_client.force_authenticate(dat)
        resp = api_client.patch(f"/api/usuarios-admin/{target.id}/", {"telefone": "85911110000"}, format="json")
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.telefone == "85911110000"

    def test_superuser_create_user_with_group_ids_applies(self, api_client, root):
        grupo = GroupFactory(name="Formador")
        api_client.force_authenticate(root)
        resp = api_client.post(
            "/api/usuarios-admin/",
            {
                "username": "novo_super",
                "email": "novo_super@example.com",
                "cpf": "91000000008",
                "password": "SecurePass123!",
                "group_ids": [grupo.id],
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert Usuario.objects.get(username="novo_super").groups.count() == 1
