"""Testes do endpoint self-service de troca de senha: POST /api/me/change-password/.

Cobre: sucesso + auditoria, senha atual errada, senha nova fraca (validate_password
do Django), nova == atual, e não autenticado. Login do sistema é por CPF + senha
(auth_backends.CPFOrUsernameBackend); qualquer usuário logado pode trocar a própria senha.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportUnknownParameterType=false, reportMissingParameterType=false

from __future__ import annotations

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog
from apps.core.tests.factories import UsuarioFactory

URL = "/api/me/change-password/"


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestChangePassword:
    def test_troca_com_sucesso_e_audita(self):
        user = UsuarioFactory(password="SenhaAtual123!")
        resp = _client(user).post(
            URL, {"old_password": "SenhaAtual123!", "new_password": "N0vaSenh@Forte"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password("N0vaSenh@Forte")
        assert not user.check_password("SenhaAtual123!")
        audit = AuditLog.objects.filter(usuario=user, action=AuditLog.Action.CHANGE_PASSWORD)
        assert audit.exists()
        # A senha NUNCA pode vazar nos detalhes do audit.
        details_str = str(audit.first().details)
        assert "N0vaSenh@Forte" not in details_str
        assert "SenhaAtual123!" not in details_str

    def test_senha_atual_incorreta_400_e_nao_altera(self):
        user = UsuarioFactory(password="SenhaAtual123!")
        resp = _client(user).post(URL, {"old_password": "errada", "new_password": "N0vaSenh@Forte"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "old_password" in resp.data["errors"]
        user.refresh_from_db()
        assert user.check_password("SenhaAtual123!")  # inalterada

    def test_senha_nova_fraca_dispara_validate_password_400(self):
        # "12345678": passa no min-length mas o NumericPasswordValidator do Django rejeita.
        user = UsuarioFactory(password="SenhaAtual123!")
        resp = _client(user).post(URL, {"old_password": "SenhaAtual123!", "new_password": "12345678"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in resp.data["errors"]
        user.refresh_from_db()
        assert user.check_password("SenhaAtual123!")

    def test_senha_nova_igual_atual_400(self):
        user = UsuarioFactory(password="SenhaAtual123!")
        resp = _client(user).post(
            URL, {"old_password": "SenhaAtual123!", "new_password": "SenhaAtual123!"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in resp.data["errors"]

    def test_campos_faltando_400(self):
        user = UsuarioFactory(password="SenhaAtual123!")
        resp = _client(user).post(URL, {"old_password": "SenhaAtual123!"}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in resp.data["errors"]

    def test_nao_autenticado_rejeitado(self):
        resp = APIClient().post(URL, {"old_password": "x", "new_password": "N0vaSenh@Forte"}, format="json")
        assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
