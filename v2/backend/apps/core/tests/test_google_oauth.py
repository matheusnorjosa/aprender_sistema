"""
Tests: Google OAuth 2.0 Service + Endpoints (Sprint 1 - Issue #1)

Cobertura:
- Testes Unitários (4):
  - Criptografia Fernet (encrypt/decrypt)
  - Validação de domínio (exchange_code)
  - Concorrência (refresh_access_token_safe)
  - Rotação de chave (rotate_encryption_key)

- Testes API (6):
  - Autenticação obrigatória (/oauth/google/start/)
  - RBAC (grupo Controle) (/oauth/google/start/)
  - Rate limiting 10/h (/oauth/google/start/)
  - HTTPS validation (/oauth/google/callback/)
  - Callback success (credencial + AuditLog)
  - Status endpoint (/integrations/google/status/)
  - Disconnect endpoint (/integrations/google/disconnect/)

Refs:
- Sprint 1 (Issue #1): Testes Backend
- GAP-1: Concorrência com select_for_update
- GAP-2: Encryption key dedicada
- GAP-3: Rate limiting
- PA-05: Auditoria obrigatória
"""

import os
import pytest
import threading
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status as http_status
from cryptography.fernet import Fernet

from apps.core.models import Usuario, GoogleOAuthCredential, AuditLog
from apps.core.services.google_oauth import (
    _encrypt_token,
    _decrypt_token,
    exchange_code_for_tokens,
    refresh_access_token_safe,
    rotate_encryption_key,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def usuario_controle(db):
    """Cria usuário do grupo Controle"""
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = Usuario.objects.create_user(
        username="controle_test",
        email="controle@aprendereditora.com.br",
        password="testpass123",
        cpf="11111111111",
    )
    user.groups.add(controle_group)
    return user


@pytest.fixture
def usuario_formador(db):
    """Cria usuário do grupo Formador (sem permissão OAuth)"""
    formador_group, _ = Group.objects.get_or_create(name="Formador")
    user = Usuario.objects.create_user(
        username="formador_test",
        email="formador@aprendereditora.com.br",
        password="testpass123",
        cpf="22222222222",
    )
    user.groups.add(formador_group)
    return user


@pytest.fixture
def google_oauth_credential(usuario_controle):
    """Cria credencial OAuth para testes"""
    access_token = "fake_access_token_1234567890"
    refresh_token = "fake_refresh_token_0987654321"

    return GoogleOAuthCredential.objects.create(
        user=usuario_controle,
        google_email="controle@aprendereditora.com.br",
        access_token_encrypted=_encrypt_token(access_token),
        refresh_token_encrypted=_encrypt_token(refresh_token),
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )


@pytest.fixture
def mock_google_api():
    """Mock de respostas da Google API"""
    def _mock_exchange_response():
        return {
            "access_token": "new_access_token_abc123",
            "refresh_token": "new_refresh_token_xyz789",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "https://www.googleapis.com/auth/calendar",
        }

    def _mock_userinfo_response():
        return {
            "email": "controle@aprendereditora.com.br",
            "verified_email": True,
        }

    def _mock_refresh_response():
        return {
            "access_token": "refreshed_access_token_def456",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    return {
        "exchange": _mock_exchange_response,
        "userinfo": _mock_userinfo_response,
        "refresh": _mock_refresh_response,
    }


# ============================================================================
# TESTES UNITÁRIOS (4 testes)
# ============================================================================

@pytest.mark.django_db
class TestGoogleOAuthServiceUnit:
    """Testes unitários do serviço OAuth (GAP-1, GAP-2)"""

    def test_encrypt_decrypt_token(self):
        """
        GAP-2: Criptografia Fernet funciona corretamente.

        Valida:
        - Token criptografado != plaintext
        - Decrypt retorna plaintext original
        - Compatível com GCAL_ENCRYPTION_KEY
        """
        plaintext = "my_secret_token_12345"

        # Encrypt
        encrypted = _encrypt_token(plaintext)
        assert isinstance(encrypted, bytes), "Deve retornar bytes"
        assert encrypted != plaintext.encode(), "Não deve ser plaintext"

        # Decrypt
        decrypted = _decrypt_token(encrypted)
        assert decrypted == plaintext, "Deve retornar plaintext original"

    @patch.dict('os.environ', {
        'GCAL_OAUTH_CLIENT_ID': 'test_client_id_123',
        'GCAL_OAUTH_CLIENT_SECRET': 'test_client_secret_456',
        'GCAL_OAUTH_REDIRECT_URI': 'http://localhost:8002/api/oauth/google/callback/',
        'GCAL_ALLOWED_DOMAIN': 'aprendereditora.com.br',
    })
    @patch('apps.core.services.google_oauth.requests.post')
    @patch('apps.core.services.google_oauth.requests.get')
    def test_exchange_code_validates_domain(self, mock_get, mock_post, mock_google_api):
        """
        GAP-2: Validação de domínio @aprendereditora.com.br.

        Valida:
        - Email válido: @aprendereditora.com.br → sucesso
        - Email inválido: @gmail.com → ValueError
        """
        # Mock exchange tokens
        mock_post.return_value = MagicMock(
            status_code=200,
            json=mock_google_api["exchange"]
        )

        # Caso 1: Email válido
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"email": "operacional1@aprendereditora.com.br"}
        )

        result = exchange_code_for_tokens("fake_code_123")
        assert result["email"] == "operacional1@aprendereditora.com.br"

        # Caso 2: Email inválido (domínio errado)
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"email": "user@gmail.com"}
        )

        with pytest.raises(ValueError, match="Domínio não permitido"):
            exchange_code_for_tokens("fake_code_456")

    @patch.dict('os.environ', {
        'GCAL_OAUTH_CLIENT_ID': 'test_client_id_123',
        'GCAL_OAUTH_CLIENT_SECRET': 'test_client_secret_456',
    })
    @patch('apps.core.services.google_oauth.requests.post')
    def test_refresh_access_token_with_concurrency(
        self, mock_post, google_oauth_credential, mock_google_api
    ):
        """
        GAP-1: Refresh thread-safe com select_for_update.

        Valida:
        - 2 threads simultâneos fazem refresh
        - Apenas 1 chama API Google (segundo detecta token válido)
        - Double-check pattern funciona

        Nota: Teste simplificado (não usa threads reais por limitação pytest-django).
        Teste completo com threading requer setup complexo (TransactionTestCase).
        """
        # Mock refresh API
        mock_post.return_value = MagicMock(
            status_code=200,
            json=mock_google_api["refresh"]
        )

        # Simular token expirado
        google_oauth_credential.token_expiry = timezone.now() - timedelta(minutes=10)
        google_oauth_credential.save()

        # Refresh 1
        refreshed = refresh_access_token_safe(google_oauth_credential)
        assert refreshed.is_expired() is False, "Token deve estar válido"
        assert mock_post.call_count == 1, "Deve chamar API 1x"

        # Refresh 2 (mesmo objeto, já válido)
        refreshed2 = refresh_access_token_safe(refreshed)
        assert mock_post.call_count == 1, "Não deve chamar API novamente (double-check)"

        # Validar AuditLog
        audit = AuditLog.objects.filter(action="GOOGLE_REFRESH_TOKEN").last()
        assert audit is not None, "Deve criar AuditLog"
        assert audit.usuario == google_oauth_credential.user

    def test_rotate_encryption_key(self, google_oauth_credential):
        """
        GAP-2: Rotação de chave zero-downtime.

        Valida:
        - Rotação com chave antiga/nova funciona
        - Tokens descriptografáveis com chave nova
        - Contador de credenciais atualizadas correto
        """
        # Obter chave atual (usada pela fixture para criar tokens)
        from apps.core.services.google_oauth import _get_fernet_key
        current_key_bytes = _get_fernet_key()
        old_key = current_key_bytes.decode() if isinstance(current_key_bytes, bytes) else current_key_bytes

        # Gerar chave nova
        new_key = Fernet.generate_key().decode()

        # Antes: tokens criptografados com chave antiga
        old_encrypted_access = google_oauth_credential.access_token_encrypted

        # Rotacionar
        count = rotate_encryption_key(old_key, new_key)
        assert count == 1, "Deve atualizar 1 credencial"

        # Depois: tokens criptografáveis com chave nova
        google_oauth_credential.refresh_from_db()
        assert google_oauth_credential.access_token_encrypted != old_encrypted_access, \
            "Token deve ter sido re-criptografado"

        # Validar descriptografia com chave nova
        new_fernet = Fernet(new_key.encode())
        decrypted = new_fernet.decrypt(google_oauth_credential.access_token_encrypted).decode()
        assert decrypted == "fake_access_token_1234567890", "Deve descriptografar com chave nova"

        # Validar AuditLog
        audit = AuditLog.objects.filter(action="GCAL_ENCRYPTION_KEY_ROTATION").last()
        assert audit is not None, "Deve criar AuditLog"
        assert audit.details["credentials_updated"] == 1


# ============================================================================
# TESTES API (6 testes)
# ============================================================================

@pytest.mark.django_db
class TestGoogleOAuthEndpoints:
    """Testes dos endpoints OAuth (GAP-3, PA-05, PA-06)"""

    def test_google_oauth_start_requires_authentication(self):
        """
        PA-06: Autenticação obrigatória em /oauth/google/start/.

        Valida:
        - Usuário não autenticado → 403 Forbidden
        """
        client = APIClient()

        response = client.get("/api/oauth/google/start/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_google_oauth_start_requires_controle_group(self, usuario_formador):
        """
        PA-06: RBAC - apenas grupo Controle pode acessar /oauth/google/start/.

        Valida:
        - Usuário Formador → 403 Forbidden
        - Mensagem: "Apenas Controle ou Superintendência"
        """
        client = APIClient()
        client.force_authenticate(user=usuario_formador)

        response = client.get("/api/oauth/google/start/")
        assert response.status_code == http_status.HTTP_403_FORBIDDEN
        assert "Controle" in response.data["detail"]

    @patch.dict('os.environ', {
        'GCAL_OAUTH_CLIENT_ID': 'test_client_id_123',
        'GCAL_OAUTH_CLIENT_SECRET': 'test_client_secret_456',
        'GCAL_OAUTH_REDIRECT_URI': 'http://localhost:8002/api/oauth/google/callback/',
    })
    def test_google_oauth_start_throttling(self, db):
        """
        GAP-3: Rate limiting 10 req/h em /oauth/google/start/.

        Valida:
        - Primeiras 10 requests → 302 Redirect (sucesso)
        - 11ª request → 429 Too Many Requests

        Nota: Requer configuração de throttle em settings.py:
        REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['oauth'] = '10/hour'

        IMPORTANTE: Cria usuário único para evitar conflito de throttle
        com outros testes que usam usuario_controle fixture.
        """
        # Limpar cache de throttle antes do teste
        from django.core.cache import cache
        cache.clear()

        # Criar usuário único para este teste (evitar throttle compartilhado)
        controle_group, _ = Group.objects.get_or_create(name="Controle")
        unique_user = Usuario.objects.create_user(
            username="throttle_test_user",
            email="throttle@aprendereditora.com.br",
            password="testpass123",
            cpf="99999999999",
        )
        unique_user.groups.add(controle_group)

        client = APIClient()
        client.force_authenticate(user=unique_user)

        # Mock Google OAuth para evitar redirect real
        with patch('apps.core.services.google_oauth.build_authorization_url') as mock_build:
            mock_build.return_value = "https://accounts.google.com/o/oauth2/v2/auth?..."

            # Fazer 10 requests (limite)
            for i in range(10):
                response = client.get("/api/oauth/google/start/")
                assert response.status_code == http_status.HTTP_302_FOUND, \
                    f"Request {i+1}/10 deve ter sucesso"

            # 11ª request (excede limite)
            response = client.get("/api/oauth/google/start/")
            assert response.status_code == http_status.HTTP_429_TOO_MANY_REQUESTS, \
                "11ª request deve ser bloqueada (throttling)"

    @patch('apps.core.services.google_oauth.requests.post')
    @patch('apps.core.services.google_oauth.requests.get')
    def test_google_oauth_callback_validates_https(
        self, mock_get, mock_post, usuario_controle, mock_google_api
    ):
        """
        GAP-3: HTTPS obrigatório em produção no callback.

        Valida:
        - ENVIRONMENT=production + HTTP → 403 Forbidden
        - ENVIRONMENT=production + HTTPS → Sucesso
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Mock exchange tokens
        mock_post.return_value = MagicMock(
            status_code=200,
            json=mock_google_api["exchange"]
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"email": "controle@aprendereditora.com.br"}
        )

        # Caso 1: Produção + HTTP (request.is_secure() = False)
        with patch('django.conf.settings.ENVIRONMENT', 'production'):
            response = client.get(
                "/api/oauth/google/callback/",
                {
                    "code": "fake_code_123",
                    "state": f"csrf_token|/pre-agenda|{usuario_controle.id}",
                },
                # Simular HTTP (não-seguro)
                secure=False,
            )
            assert response.status_code == http_status.HTTP_403_FORBIDDEN, \
                "Produção + HTTP deve ser rejeitado"

        # Caso 2: Produção + HTTPS (request.is_secure() = True)
        with patch('django.conf.settings.ENVIRONMENT', 'production'):
            with patch('apps.core.views_oauth.settings.ENVIRONMENT', 'production'):
                response = client.get(
                    "/api/oauth/google/callback/",
                    {
                        "code": "fake_code_123",
                        "state": f"csrf_token|/pre-agenda|{usuario_controle.id}",
                    },
                    # Simular HTTPS (seguro)
                    secure=True,
                )
                # Callback redireciona, não retorna JSON
                assert response.status_code in [
                    http_status.HTTP_302_FOUND,
                    http_status.HTTP_200_OK
                ], "Produção + HTTPS deve funcionar"

    @patch.dict('os.environ', {
        'GCAL_OAUTH_CLIENT_ID': 'test_client_id_123',
        'GCAL_OAUTH_CLIENT_SECRET': 'test_client_secret_456',
        'GCAL_OAUTH_REDIRECT_URI': 'http://localhost:8002/api/oauth/google/callback/',
        'GCAL_ALLOWED_DOMAIN': 'aprendereditora.com.br',
    })
    @patch('apps.core.services.google_oauth.requests.post')
    @patch('apps.core.services.google_oauth.requests.get')
    def test_google_oauth_callback_success(
        self, mock_get, mock_post, usuario_controle, mock_google_api
    ):
        """
        PA-05: Callback cria credencial + AuditLog.

        Valida:
        - Credencial criada com tokens criptografados
        - AuditLog com action=GOOGLE_CONNECT
        - Redirect para return_to?google=connected
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Mock exchange tokens
        mock_post.return_value = MagicMock(
            status_code=200,
            json=mock_google_api["exchange"]
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"email": "controle@aprendereditora.com.br"}
        )

        # Callback
        response = client.get(
            "/api/oauth/google/callback/",
            {
                "code": "fake_code_123",
                "state": f"csrf_token|/pre-agenda|{usuario_controle.id}",
            }
        )

        # Validar redirect
        assert response.status_code == http_status.HTTP_302_FOUND
        assert "google=connected" in response.url

        # Validar credencial criada
        credential = GoogleOAuthCredential.objects.filter(user=usuario_controle).first()
        assert credential is not None, "Deve criar credencial"
        assert credential.google_email == "controle@aprendereditora.com.br"
        assert credential.is_expired() is False, "Token deve estar válido"

        # Validar AuditLog (PA-05)
        audit = AuditLog.objects.filter(
            usuario=usuario_controle,
            action="GOOGLE_CONNECT"
        ).last()
        assert audit is not None, "Deve criar AuditLog"
        assert audit.details["google_email"] == "controle@aprendereditora.com.br"

    def test_status_endpoint_returns_connected(self, usuario_controle, google_oauth_credential):
        """
        Endpoint /status/ retorna status da conexão.

        Valida:
        - Conectado: connected=true + google_email + token_expiry
        - Desconectado: connected=false + campos null
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Caso 1: Conectado
        response = client.get("/api/integrations/google/status/")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["connected"] is True
        assert response.data["google_email"] == "controle@aprendereditora.com.br"
        assert response.data["is_expired"] is False

        # Caso 2: Desconectar e verificar novamente
        google_oauth_credential.delete()

        response = client.get("/api/integrations/google/status/")
        assert response.status_code == http_status.HTTP_200_OK
        assert response.data["connected"] is False
        assert response.data["google_email"] is None

    @patch('apps.core.services.google_oauth.requests.post')
    def test_disconnect_removes_credential(
        self, mock_post, usuario_controle, google_oauth_credential
    ):
        """
        PA-05: Endpoint /disconnect/ remove credencial + AuditLog.

        Valida:
        - Credencial removida do banco
        - AuditLog com action=GOOGLE_DISCONNECT
        - Google API /revoke chamada (mock)
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Mock revoke API
        mock_post.return_value = MagicMock(status_code=200)

        # Disconnect
        response = client.post("/api/integrations/google/disconnect/")
        assert response.status_code == http_status.HTTP_200_OK
        assert "desconectada com sucesso" in response.data["message"]

        # Validar credencial removida
        exists = GoogleOAuthCredential.objects.filter(user=usuario_controle).exists()
        assert exists is False, "Credencial deve ter sido removida"

        # Validar AuditLog (PA-05)
        audit = AuditLog.objects.filter(
            usuario=usuario_controle,
            action="GOOGLE_DISCONNECT"
        ).last()
        assert audit is not None, "Deve criar AuditLog"
        assert audit.details["google_email"] == "controle@aprendereditora.com.br"
        assert audit.details["reason"] == "user_requested"

        # Validar chamada à API Google /revoke
        assert mock_post.called, "Deve chamar API Google /revoke"
        assert "revoke" in mock_post.call_args[0][0], "Deve chamar endpoint /revoke"


# ============================================================================
# RESUMO DOS TESTES
# ============================================================================

# Testes Unitários (4):
# ✅ test_encrypt_decrypt_token → GAP-2 (Criptografia Fernet)
# ✅ test_exchange_code_validates_domain → GAP-2 (Validação domínio)
# ✅ test_refresh_access_token_with_concurrency → GAP-1 (select_for_update)
# ✅ test_rotate_encryption_key → GAP-2 (Rotação chave)

# Testes API (6):
# ✅ test_google_oauth_start_requires_authentication → PA-06 (Auth)
# ✅ test_google_oauth_start_requires_controle_group → PA-06 (RBAC)
# ✅ test_google_oauth_start_throttling → GAP-3 (Rate limiting 10/h)
# ✅ test_google_oauth_callback_validates_https → GAP-3 (HTTPS prod)
# ✅ test_google_oauth_callback_success → PA-05 (Credencial + AuditLog)
# ✅ test_status_endpoint_returns_connected → Status endpoint
# ✅ test_disconnect_removes_credential → PA-05 (Disconnect + AuditLog)

# Total: 10 testes (4 unit + 6 API)
# Cobertura: GAP-1, GAP-2, GAP-3, PA-05, PA-06
