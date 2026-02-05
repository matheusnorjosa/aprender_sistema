"""
Tests for IDOR protection in AvailabilityBlockViewSet.

Issue #560 (C-03): Users should not be able to edit/delete blocks of other users.

Security rules:
- Regular users can only edit/delete their own blocks
- Controle, Superintendência, and superusers can manage any block
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Usuario


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def grupo_controle(db):
    """Grupo Controle."""
    return Group.objects.get_or_create(name="Controle")[0]


@pytest.fixture
def grupo_superintendencia(db):
    """Grupo Superintendência."""
    return Group.objects.get_or_create(name="Superintendência")[0]


@pytest.fixture
def usuario_comum(db):
    """Usuário comum sem privilégios especiais."""
    return Usuario.objects.create_user(
        username="comum",
        email="comum@example.com",
        password="testpass123",
        cpf="11111111111",
    )


@pytest.fixture
def outro_usuario(db):
    """Outro usuário comum."""
    return Usuario.objects.create_user(
        username="outro",
        email="outro@example.com",
        password="testpass123",
        cpf="22222222222",
    )


@pytest.fixture
def usuario_controle(db, grupo_controle):
    """Usuário com permissão Controle."""
    user = Usuario.objects.create_user(
        username="controle",
        email="controle@example.com",
        password="testpass123",
        cpf="33333333333",
    )
    user.groups.add(grupo_controle)
    return user


@pytest.fixture
def usuario_super(db, grupo_superintendencia):
    """Usuário com permissão Superintendência."""
    user = Usuario.objects.create_user(
        username="super",
        email="super@example.com",
        password="testpass123",
        cpf="44444444444",
    )
    user.groups.add(grupo_superintendencia)
    return user


@pytest.fixture
def superuser(db):
    """Superuser."""
    return Usuario.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="testpass123",
        cpf="55555555555",
    )


@pytest.fixture
def bloqueio_outro_usuario(db, outro_usuario):
    """Bloqueio criado por outro usuário."""
    agora = timezone.now()
    return AvailabilityBlock.objects.create(
        usuario=outro_usuario,
        tipo="T",
        inicio=agora + timedelta(days=1),
        fim=agora + timedelta(days=1, hours=4),
        motivo="Bloqueio de outro usuário",
    )


@pytest.mark.django_db
class TestAvailabilityBlockIDOR:
    """
    C-03: Tests for IDOR protection in AvailabilityBlockViewSet.
    """

    # =========================================================================
    # Tests for regular users (should be blocked)
    # =========================================================================

    def test_usuario_comum_cannot_update_other_users_block(self, api_client, usuario_comum, bloqueio_outro_usuario):
        """
        C-03: Regular user should NOT be able to update another user's block.
        """
        api_client.force_authenticate(usuario_comum)

        response = api_client.patch(
            f"/api/disponibilidade/{bloqueio_outro_usuario.id}/",
            {"motivo": "Tentativa de alteração maliciosa"},
            format="json",
        )

        assert response.status_code == 403
        assert "permissão" in response.data["detail"].lower()

    def test_usuario_comum_cannot_delete_other_users_block(self, api_client, usuario_comum, bloqueio_outro_usuario):
        """
        C-03: Regular user should NOT be able to delete another user's block.
        """
        api_client.force_authenticate(usuario_comum)

        response = api_client.delete(f"/api/disponibilidade/{bloqueio_outro_usuario.id}/")

        assert response.status_code == 403
        assert "permissão" in response.data["detail"].lower()

        # Verify block still exists
        assert AvailabilityBlock.objects.filter(id=bloqueio_outro_usuario.id).exists()

    def test_usuario_comum_can_update_own_block(self, api_client, usuario_comum, db):
        """
        C-03: Regular user CAN update their own block.
        """
        # Create a block owned by usuario_comum
        agora = timezone.now()
        meu_bloqueio = AvailabilityBlock.objects.create(
            usuario=usuario_comum,
            tipo="P",
            inicio=agora + timedelta(days=2),
            fim=agora + timedelta(days=2, hours=2),
            motivo="Meu bloqueio",
        )

        api_client.force_authenticate(usuario_comum)

        response = api_client.patch(
            f"/api/disponibilidade/{meu_bloqueio.id}/",
            {"motivo": "Motivo atualizado"},
            format="json",
        )

        assert response.status_code == 200
        meu_bloqueio.refresh_from_db()
        assert meu_bloqueio.motivo == "Motivo atualizado"

    def test_usuario_comum_can_delete_own_block(self, api_client, usuario_comum, db):
        """
        C-03: Regular user CAN delete their own block.
        """
        agora = timezone.now()
        meu_bloqueio = AvailabilityBlock.objects.create(
            usuario=usuario_comum,
            tipo="P",
            inicio=agora + timedelta(days=3),
            fim=agora + timedelta(days=3, hours=2),
            motivo="Bloqueio a deletar",
        )
        block_id = meu_bloqueio.id

        api_client.force_authenticate(usuario_comum)

        response = api_client.delete(f"/api/disponibilidade/{block_id}/")

        assert response.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()

    # =========================================================================
    # Tests for privileged users (should be allowed)
    # =========================================================================

    def test_controle_can_update_other_users_block(self, api_client, usuario_controle, bloqueio_outro_usuario):
        """
        C-03: Controle CAN update another user's block.
        """
        api_client.force_authenticate(usuario_controle)

        response = api_client.patch(
            f"/api/disponibilidade/{bloqueio_outro_usuario.id}/",
            {"motivo": "Atualizado pelo Controle"},
            format="json",
        )

        assert response.status_code == 200
        bloqueio_outro_usuario.refresh_from_db()
        assert bloqueio_outro_usuario.motivo == "Atualizado pelo Controle"

    def test_controle_can_delete_other_users_block(self, api_client, usuario_controle, bloqueio_outro_usuario):
        """
        C-03: Controle CAN delete another user's block.
        """
        block_id = bloqueio_outro_usuario.id
        api_client.force_authenticate(usuario_controle)

        response = api_client.delete(f"/api/disponibilidade/{block_id}/")

        assert response.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()

    def test_superintendencia_can_update_other_users_block(self, api_client, usuario_super, bloqueio_outro_usuario):
        """
        C-03: Superintendência CAN update another user's block.
        """
        api_client.force_authenticate(usuario_super)

        response = api_client.patch(
            f"/api/disponibilidade/{bloqueio_outro_usuario.id}/",
            {"motivo": "Atualizado pela Superintendência"},
            format="json",
        )

        assert response.status_code == 200

    def test_superuser_can_update_other_users_block(self, api_client, superuser, bloqueio_outro_usuario):
        """
        C-03: Superuser CAN update any block.
        """
        api_client.force_authenticate(superuser)

        response = api_client.patch(
            f"/api/disponibilidade/{bloqueio_outro_usuario.id}/",
            {"motivo": "Atualizado pelo admin"},
            format="json",
        )

        assert response.status_code == 200

    def test_superuser_can_delete_other_users_block(self, api_client, superuser, bloqueio_outro_usuario):
        """
        C-03: Superuser CAN delete any block.
        """
        block_id = bloqueio_outro_usuario.id
        api_client.force_authenticate(superuser)

        response = api_client.delete(f"/api/disponibilidade/{block_id}/")

        assert response.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()
