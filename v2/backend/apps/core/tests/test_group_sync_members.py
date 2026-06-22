"""
Testes para endpoint /api/grupos/{id}/sync-members/ (Issue #947).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Usuario
from apps.core.tests.factories import GroupFactory, UsuarioFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def usuario_dat(db) -> Usuario:
    return UsuarioFactory(
        username="dat_sync",
        email="dat_sync@example.com",
        password="senha123",
        cpf="81234567890",
        groups=["DAT"],
    )


@pytest.fixture
def usuario_sem_dat(db) -> Usuario:
    user = UsuarioFactory(
        username="comum_sync",
        email="comum_sync@example.com",
        password="senha123",
        cpf="81234567891",
    )
    GroupFactory(name="Formador")
    return user


@pytest.fixture
def grupo_alvo(db) -> Group:
    return GroupFactory(name="Grupo Operacional X")


@pytest.fixture
def usuarios_alvo(db) -> list[Usuario]:
    users = []
    for idx in range(3):
        users.append(
            UsuarioFactory(
                username=f"user_sync_{idx}",
                email=f"user_sync_{idx}@example.com",
                password="senha123",
                cpf=f"9234567890{idx}",
            )
        )
    return users


@pytest.mark.django_db
class TestGroupSyncMembersAPI:
    def test_dat_can_sync_group_members(
        self, api_client: APIClient, usuario_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        api_client.force_authenticate(user=usuario_dat)

        payload = {"user_ids": [usuarios_alvo[0].id, usuarios_alvo[1].id]}
        response = api_client.post(f"/api/grupos/{grupo_alvo.id}/sync-members/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["members_count"] == 2
        assert response.data["added"] == 2
        assert response.data["removed"] == 0
        assert set(grupo_alvo.user_set.values_list("id", flat=True)) == {usuarios_alvo[0].id, usuarios_alvo[1].id}

    def test_sync_members_replaces_existing_members(
        self, api_client: APIClient, usuario_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        grupo_alvo.user_set.set([usuarios_alvo[0], usuarios_alvo[1]])
        api_client.force_authenticate(user=usuario_dat)

        payload = {"user_ids": [usuarios_alvo[2].id]}
        response = api_client.post(f"/api/grupos/{grupo_alvo.id}/sync-members/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["members_count"] == 1
        assert response.data["added"] == 1
        assert response.data["removed"] == 2
        assert set(grupo_alvo.user_set.values_list("id", flat=True)) == {usuarios_alvo[2].id}

    def test_sync_members_is_idempotent(
        self, api_client: APIClient, usuario_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        grupo_alvo.user_set.set([usuarios_alvo[0], usuarios_alvo[1]])
        api_client.force_authenticate(user=usuario_dat)

        payload = {"user_ids": [usuarios_alvo[0].id, usuarios_alvo[1].id]}
        first = api_client.post(f"/api/grupos/{grupo_alvo.id}/sync-members/", payload, format="json")
        second = api_client.post(f"/api/grupos/{grupo_alvo.id}/sync-members/", payload, format="json")

        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_200_OK
        assert second.data["added"] == 0
        assert second.data["removed"] == 0

    def test_sync_members_rejects_nonexistent_users(
        self, api_client: APIClient, usuario_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        api_client.force_authenticate(user=usuario_dat)

        response = api_client.post(
            f"/api/grupos/{grupo_alvo.id}/sync-members/",
            {"user_ids": [usuarios_alvo[0].id, 999999]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Users not found" in response.data["error"]

    def test_sync_members_requires_dat_permission(
        self, api_client: APIClient, usuario_sem_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        api_client.force_authenticate(user=usuario_sem_dat)

        response = api_client.post(
            f"/api/grupos/{grupo_alvo.id}/sync-members/",
            {"user_ids": [usuarios_alvo[0].id]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_sync_members_creates_audit_log(
        self, api_client: APIClient, usuario_dat: Usuario, grupo_alvo: Group, usuarios_alvo: list[Usuario]
    ) -> None:
        api_client.force_authenticate(user=usuario_dat)
        AuditLog.objects.all().delete()

        response = api_client.post(
            f"/api/grupos/{grupo_alvo.id}/sync-members/",
            {"user_ids": [usuarios_alvo[0].id, usuarios_alvo[1].id]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        log = AuditLog.objects.filter(action="SYNC_GROUP_MEMBERS", model_name="Group").order_by("-created_at").first()
        assert log is not None
        assert log.usuario_id == usuario_dat.id
        assert log.details["group_id"] == grupo_alvo.id
        assert log.details["target_user_ids"] == sorted([usuarios_alvo[0].id, usuarios_alvo[1].id])
