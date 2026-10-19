"""
Tests for IDOR protection in AvailabilityBlockViewSet.

Issue #560 (C-03): Users should not be able to edit/delete blocks of other users.

Regras (o poder vem da lotação desde o PR 12):
- Quem não é privilegiado (a formadora, com o papel FORMADOR vigente) só edita e apaga os próprios
  bloqueios; o de terceiro dá 404, mesmo na mesma gerência, sem revelar que existe.
- O superusuário edita e apaga qualquer bloqueio.
- Editar ou apagar bloqueio de terceiro como privilegiado (Controle, DAT) segue o gate de delegação
  (GAP-1): `test_availability_block_gap1_mutation_gate.py` e
  `test_rbac_papel_da_poder.py::TestBloqueioDelegado`.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, Gerencia
from apps.core.tests.factories import UsuarioFactory, com_papel


@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def gerencia_vidas(db):
    """Gerência de lotação da formadora."""
    return Gerencia.objects.create(nome="GERENCIA 2", nome_setor="Vidas")


@pytest.fixture
def usuario_comum(db, gerencia_vidas):
    """Formadora: o papel FORMADOR vigente, sem privilégio."""
    user = UsuarioFactory(
        username="comum",
        email="comum@example.com",
        password="testpass123",
        cpf="11111111111",
    )
    com_papel(user, "FORMADOR", gerencia_vidas)
    return user


@pytest.fixture
def outro_usuario(db):
    """Outro usuário comum."""
    return UsuarioFactory(
        username="outro",
        email="outro@example.com",
        password="testpass123",
        cpf="22222222222",
    )


@pytest.fixture
def usuarios_mesma_gerencia(db, gerencia_vidas, usuario_comum, outro_usuario):
    """As duas formadoras na mesma gerência."""
    com_papel(outro_usuario, "FORMADOR", gerencia_vidas)
    return (usuario_comum, outro_usuario)


@pytest.fixture
def superuser(db):
    """Superuser."""
    return UsuarioFactory(superuser=True)


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
    """C-03: proteção contra IDOR no AvailabilityBlockViewSet (permission_classes = IsAuthenticated)."""

    # =========================================================================
    # Tests for regular users (should be blocked)
    # =========================================================================

    def test_usuario_comum_cannot_update_other_users_block(self, api_client, usuario_comum, bloqueio_outro_usuario):
        """
        C-03: Regular user should NOT be able to update another user's block.

        Note: Returns 404 (not 403) because get_queryset() filters to only show
        user's own blocks. This is more secure as it doesn't reveal object existence.
        """
        api_client.force_authenticate(usuario_comum)

        response = api_client.patch(
            f"/api/availability-blocks/{bloqueio_outro_usuario.id}/",
            {"motivo": "Tentativa de alteração maliciosa"},
            format="json",
        )

        # 404 - block not visible in user's queryset (more secure than 403)
        assert response.status_code == 404

        # Verify block still exists unchanged
        assert AvailabilityBlock.objects.filter(id=bloqueio_outro_usuario.id).exists()
        bloqueio_outro_usuario.refresh_from_db()
        assert bloqueio_outro_usuario.motivo == "Bloqueio de outro usuário"

    def test_usuario_comum_cannot_delete_other_users_block(self, api_client, usuario_comum, bloqueio_outro_usuario):
        """
        C-03: Regular user should NOT be able to delete another user's block.

        Note: Returns 404 (not 403) because get_queryset() filters to only show
        user's own blocks. This is more secure as it doesn't reveal object existence.
        """
        api_client.force_authenticate(usuario_comum)

        response = api_client.delete(f"/api/availability-blocks/{bloqueio_outro_usuario.id}/")

        # 404 - block not visible in user's queryset (more secure than 403)
        assert response.status_code == 404

        # Verify block still exists
        assert AvailabilityBlock.objects.filter(id=bloqueio_outro_usuario.id).exists()

    def test_usuario_comum_mesma_gerencia_cannot_update_other_users_block(
        self, api_client, usuarios_mesma_gerencia, bloqueio_outro_usuario
    ):
        """
        C-03: Mesmo na mesma gerência, usuário comum não pode editar bloqueio de terceiro.
        """
        usuario_comum, _ = usuarios_mesma_gerencia
        api_client.force_authenticate(usuario_comum)

        response = api_client.patch(
            f"/api/availability-blocks/{bloqueio_outro_usuario.id}/",
            {"motivo": "Tentativa indevida"},
            format="json",
        )

        assert response.status_code == 404
        bloqueio_outro_usuario.refresh_from_db()
        assert bloqueio_outro_usuario.motivo == "Bloqueio de outro usuário"

    def test_usuario_comum_mesma_gerencia_cannot_delete_other_users_block(
        self, api_client, usuarios_mesma_gerencia, bloqueio_outro_usuario
    ):
        """
        C-03: Mesmo na mesma gerência, usuário comum não pode deletar bloqueio de terceiro.
        """
        usuario_comum, _ = usuarios_mesma_gerencia
        api_client.force_authenticate(usuario_comum)

        response = api_client.delete(f"/api/availability-blocks/{bloqueio_outro_usuario.id}/")

        assert response.status_code == 404
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
            f"/api/availability-blocks/{meu_bloqueio.id}/",
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

        response = api_client.delete(f"/api/availability-blocks/{block_id}/")

        assert response.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()

    # =========================================================================
    # Superusuário (o privilegiado sem gate de delegação: ver GAP-1 no docstring do módulo)
    # =========================================================================

    def test_superuser_can_update_other_users_block(self, api_client, superuser, bloqueio_outro_usuario):
        """
        C-03: Superuser CAN update any block.
        """
        api_client.force_authenticate(superuser)

        response = api_client.patch(
            f"/api/availability-blocks/{bloqueio_outro_usuario.id}/",
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

        response = api_client.delete(f"/api/availability-blocks/{block_id}/")

        assert response.status_code == 204
        assert not AvailabilityBlock.objects.filter(id=block_id).exists()
