"""
#1742 PR-C (S4): `revoke_token` (oauth/token_manager) apagava a credencial local
com `credential.delete()` MESMO quando o revoke remoto no Google retornava status
!= 200/400 — deixando o refresh_token vivo no Google e orfao localmente (sem como
retentar). O fix: so apaga se o Google confirmar (200 = revogado, 400 = ja invalido);
qualquer outro status preserva a credencial e retorna False.

RED no codigo antigo: status 500 ainda caia no delete + retornava True.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

import pytest

from apps.core.models import GoogleOAuthCredential
from apps.core.services.oauth.token_manager import revoke_token
from apps.core.tests.factories import UsuarioFactory


@pytest.fixture
def cred(db):
    user = UsuarioFactory(username="oauth_revoke_1742", cpf="11144477735")
    return GoogleOAuthCredential.objects.create(
        user=user,
        google_email="revoke@aprendereditora.com.br",
        access_token_encrypted=b"enc-access",
        refresh_token_encrypted=b"enc-refresh",
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )


@pytest.mark.django_db
class TestRevokeTokenAtomicidade:
    """S4 (#1742): delete local so quando o Google confirma a revogacao."""

    @patch("apps.core.services.oauth.token_manager.decrypt_token", return_value="ref")
    @patch("apps.core.services.oauth.token_manager.requests.post")
    def test_status_500_preserva_credencial(self, mock_post, _mock_decrypt, cred):
        """RED: antes o delete rodava e retornava True mesmo em 500."""
        mock_post.return_value = MagicMock(status_code=500)
        cid = cred.id

        result = revoke_token(cred)

        assert result is False
        assert GoogleOAuthCredential.objects.filter(id=cid).exists()

    @patch("apps.core.services.oauth.token_manager.decrypt_token", return_value="ref")
    @patch("apps.core.services.oauth.token_manager.requests.post")
    def test_status_200_apaga_credencial(self, mock_post, _mock_decrypt, cred):
        mock_post.return_value = MagicMock(status_code=200)
        cid = cred.id

        result = revoke_token(cred)

        assert result is True
        assert not GoogleOAuthCredential.objects.filter(id=cid).exists()

    @patch("apps.core.services.oauth.token_manager.decrypt_token", return_value="ref")
    @patch("apps.core.services.oauth.token_manager.requests.post")
    def test_status_400_apaga_credencial(self, mock_post, _mock_decrypt, cred):
        """400 = token ja invalido no Google (efetivamente revogado) -> apaga local."""
        mock_post.return_value = MagicMock(status_code=400)
        cid = cred.id

        result = revoke_token(cred)

        assert result is True
        assert not GoogleOAuthCredential.objects.filter(id=cid).exists()
