"""
AS v2 — Google OAuth 2.0 Service

Implementa fluxo OAuth 2.0 para Google Calendar com segurança reforçada:
- Criptografia Fernet com chave dedicada (GCAL_ENCRYPTION_KEY)
- Refresh thread-safe com select_for_update (GAP-1: Concorrência)
- Validação de domínio (@aprendereditora.com.br)
- Auditoria completa (AuditLog)
- Rotação de chave zero-downtime

Refs:
- Sprint 1 (Issue #1): Core OAuth Backend
- GAP-1: Concorrência com select_for_update
- GAP-2: Encryption key dedicada
- GAP-3: Rate limiting (aplicado nas views)
- PA-05: Auditoria obrigatória
"""

import os
import base64
import logging
import requests
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from cryptography.fernet import Fernet, InvalidToken

from apps.core.models import GoogleOAuthCredential, AuditLog

logger = logging.getLogger(__name__)


# ============================================================================
# ENCRYPTION (GAP-2: Chave dedicada)
# ============================================================================

def _get_fernet_key():
    """
    Retorna chave Fernet dedicada para criptografia de tokens OAuth.

    Prioridade:
    1. GCAL_ENCRYPTION_KEY (obrigatória em produção)
    2. Fallback: SECRET_KEY (apenas dev/staging com warning)

    Raises:
        ValueError: Se nenhuma chave válida for encontrada
    """
    key = os.getenv("GCAL_ENCRYPTION_KEY")

    if key:
        return key.encode('utf-8')

    # Fallback para SECRET_KEY (dev/staging apenas)
    if settings.ENVIRONMENT != "production":
        logger.warning(
            "⚠️ GCAL_ENCRYPTION_KEY não definida. Usando SECRET_KEY (não recomendado). "
            "Defina GCAL_ENCRYPTION_KEY para produção."
        )
        # Derivar chave Fernet-compatible de SECRET_KEY
        from hashlib import sha256
        return base64.urlsafe_b64encode(
            sha256(settings.SECRET_KEY.encode()).digest()
        )

    raise ValueError(
        "❌ GCAL_ENCRYPTION_KEY obrigatória em produção. "
        "Gere com: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )


def _encrypt_token(token: str) -> bytes:
    """
    Criptografa token usando Fernet (AES-128-CBC + HMAC-SHA256).

    Args:
        token: Token em plaintext (access_token ou refresh_token)

    Returns:
        bytes: Token criptografado (formato Fernet)

    Raises:
        ValueError: Se chave de criptografia não estiver configurada
    """
    fernet = Fernet(_get_fernet_key())
    return fernet.encrypt(token.encode('utf-8'))


def _decrypt_token(encrypted: bytes) -> str:
    """
    Descriptografa token criptografado com Fernet.

    Args:
        encrypted: Token criptografado (bytes)

    Returns:
        str: Token em plaintext

    Raises:
        InvalidToken: Se token estiver corrompido ou chave incorreta
    """
    fernet = Fernet(_get_fernet_key())
    return fernet.decrypt(encrypted).decode('utf-8')


# ============================================================================
# SECURITY HELPERS
# ============================================================================

def _is_safe_url(url: str) -> bool:
    """
    Valida se URL é segura para redirect (previne open redirect).

    Args:
        url: URL a ser validada

    Returns:
        bool: True se segura, False caso contrário

    Security:
        - Apenas caminhos internos (começam com "/")
        - Rejeita URLs absolutas (http://, https://, //)
        - Rejeita javascript:, data:, etc.
    """
    if not url:
        return False

    # Permitir apenas caminhos internos
    if url.startswith("/") and not url.startswith("//"):
        return True

    # Rejeitar qualquer URL absoluta ou protocolo
    return False


def validate_oauth_state(state: str, user_id: int) -> dict:
    """
    Valida state token do OAuth callback (previne CSRF).

    Args:
        state: State string recebido no callback (formato: csrf_token|return_to|user_id)
        user_id: ID do usuário autenticado

    Returns:
        dict: {
            "valid": bool,
            "return_to": str,
            "error": str | None
        }

    Security:
        - Valida CSRF token contra cache (one-time use)
        - Verifica user_id match
        - Valida return_to (previne open redirect)
        - Remove state do cache após validação
    """
    from django.core.cache import cache

    try:
        # Parse state
        parts = state.split('|')
        if len(parts) != 3:
            return {"valid": False, "return_to": "/pre-agenda", "error": "State format invalid"}

        csrf_token, return_to, state_user_id_str = parts
        state_user_id = int(state_user_id_str)

        # Verificar user_id match
        if state_user_id != user_id:
            logger.error(
                f"❌ OAuth state validation: user_id mismatch "
                f"(state={state_user_id}, authenticated={user_id})"
            )
            return {"valid": False, "return_to": "/pre-agenda", "error": "User ID mismatch"}

        # Buscar state no cache
        cache_key = f"oauth_state:{csrf_token}"
        cached_state = cache.get(cache_key)

        if not cached_state:
            logger.error(f"❌ OAuth state validation: token not found or expired ({csrf_token[:8]}...)")
            return {"valid": False, "return_to": "/pre-agenda", "error": "State token invalid or expired"}

        # Validar return_to
        cached_return_to = cached_state.get("return_to", "/pre-agenda")
        if not _is_safe_url(cached_return_to):
            logger.warning(f"⚠️ OAuth state validation: unsafe return_to in cache ({cached_return_to})")
            cached_return_to = "/pre-agenda"

        # Remover state do cache (one-time use)
        cache.delete(cache_key)
        logger.info(f"✅ OAuth state validado: {csrf_token[:8]}... (user={user_id})")

        return {"valid": True, "return_to": cached_return_to, "error": None}

    except (ValueError, IndexError) as e:
        logger.error(f"❌ OAuth state validation: parse error ({e})")
        return {"valid": False, "return_to": "/pre-agenda", "error": "State parse error"}


# ============================================================================
# OAUTH 2.0 FLOW
# ============================================================================

def build_authorization_url(user, return_to: str = "/pre-agenda") -> str:
    """
    Gera URL de autorização OAuth 2.0 do Google.

    Args:
        user: Instância de Usuario (para CSRF state)
        return_to: URL de retorno após callback (default: /pre-agenda)

    Returns:
        str: URL completa de redirecionamento para Google OAuth

    Security:
        - State token armazenado em cache (Redis) com TTL 10min
        - return_to validado (apenas caminhos internos)

    Example:
        >>> url = build_authorization_url(request.user, return_to="/pre-agenda")
        >>> return redirect(url)
    """
    from django.core.cache import cache

    client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
    redirect_uri = os.getenv("GCAL_OAUTH_REDIRECT_URI")

    if not client_id or not redirect_uri:
        raise ValueError(
            "❌ GCAL_OAUTH_CLIENT_ID e GCAL_OAUTH_REDIRECT_URI obrigatórias. "
            "Configure no Google Cloud Console e defina no .env"
        )

    # Validar return_to para prevenir open redirect
    if not _is_safe_url(return_to):
        logger.warning(f"⚠️ return_to rejeitado (open redirect attempt): {return_to}")
        return_to = "/pre-agenda"

    # State: CSRF token + return_to + user_id (formato: "csrf_token|return_to|user_id")
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    state = f"{csrf_token}|{return_to}|{user.id}"

    # Armazenar CSRF token em cache (Redis) com TTL 10min
    cache_key = f"oauth_state:{csrf_token}"
    cache.set(cache_key, {
        "user_id": user.id,
        "return_to": return_to,
        "created_at": timezone.now().isoformat(),
    }, timeout=600)  # 10 minutos

    logger.info(f"🔐 OAuth state criado: {csrf_token[:8]}... (user={user.id})")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar",
        "access_type": "offline",  # Obter refresh_token
        "prompt": "consent",  # Forçar tela de consentimento (garantir refresh_token)
        "state": state,
    }

    base_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """
    Troca authorization code por access_token e refresh_token.

    Args:
        code: Authorization code retornado pelo Google OAuth callback

    Returns:
        dict: {
            "access_token": str,
            "refresh_token": str,
            "expires_in": int (segundos),
            "token_type": "Bearer",
            "scope": str,
            "email": str,  # Email da conta Google
        }

    Raises:
        ValueError: Se code inválido ou configuração incorreta
        Exception: Se Google API retornar erro

    Example:
        >>> tokens = exchange_code_for_tokens(request.GET['code'])
        >>> GoogleOAuthCredential.objects.create(
        ...     user=request.user,
        ...     access_token_encrypted=_encrypt_token(tokens['access_token']),
        ...     refresh_token_encrypted=_encrypt_token(tokens['refresh_token']),
        ...     token_expiry=timezone.now() + timedelta(seconds=tokens['expires_in']),
        ...     google_email=tokens['email'],
        ... )
    """
    import requests

    client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GCAL_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GCAL_OAUTH_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError("❌ Variáveis OAuth não configuradas (client_id, client_secret, redirect_uri)")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    logger.info(f"🔐 Trocando authorization code por tokens (grant_type=authorization_code)")

    try:
        response = requests.post(token_url, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Validar presence de refresh_token (crítico)
        if "refresh_token" not in data:
            raise ValueError(
                "❌ refresh_token não retornado pelo Google. "
                "Possível causa: prompt=consent ausente ou usuário já autorizou antes. "
                "Revogue acesso no Google Account e tente novamente."
            )

        # Obter email da conta Google via UserInfo endpoint
        access_token = data["access_token"]
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = requests.get(userinfo_url, headers=headers, timeout=10)
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()

        email = userinfo.get("email")
        if not email:
            raise ValueError("❌ Email não retornado pela API Google UserInfo")

        # Validar domínio permitido
        allowed_domain = os.getenv("GCAL_ALLOWED_DOMAIN", "aprendereditora.com.br")
        if not email.endswith(f"@{allowed_domain}"):
            raise ValueError(
                f"❌ Domínio não permitido: {email}. "
                f"Apenas contas @{allowed_domain} são aceitas."
            )

        return {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data.get("expires_in", 3600),  # Default: 1h
            "token_type": data.get("token_type", "Bearer"),
            "scope": data.get("scope", ""),
            "email": email,
        }

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao trocar code por tokens: {e}")
        raise Exception(f"Falha na troca de tokens com Google: {str(e)}")


def refresh_access_token_safe(credential: GoogleOAuthCredential) -> GoogleOAuthCredential:
    """
    Atualiza access_token usando refresh_token (thread-safe).

    **Concorrência (GAP-1)**:
    - Usa select_for_update() para row-level lock (PostgreSQL)
    - Double-check pattern: verifica se outro thread já refrescou
    - Previne race conditions em refresh simultâneos

    Args:
        credential: Instância de GoogleOAuthCredential a ser atualizada

    Returns:
        GoogleOAuthCredential: Credencial atualizada (re-fetched do DB)

    Raises:
        ValueError: Se refresh_token inválido (invalid_grant)
        Exception: Se Google API retornar erro

    Example:
        >>> credential = request.user.google_oauth
        >>> if credential.is_expired():
        ...     credential = refresh_access_token_safe(credential)
        >>> # Usar credential.access_token_encrypted atualizado
    """
    import requests

    with transaction.atomic():
        # Row-level lock (GAP-1: Concorrência)
        cred = GoogleOAuthCredential.objects.select_for_update().get(id=credential.id)

        # Double-check: outro thread já refrescou?
        if cred.token_expiry > timezone.now() + timedelta(minutes=5):
            logger.info(
                f"✅ Token já válido (outro thread refrescou). "
                f"Expira em: {cred.token_expiry}"
            )
            return cred

        # Refresh via Google API
        client_id = os.getenv("GCAL_OAUTH_CLIENT_ID")
        client_secret = os.getenv("GCAL_OAUTH_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("❌ GCAL_OAUTH_CLIENT_ID e GCAL_OAUTH_CLIENT_SECRET não configuradas")

        refresh_token = _decrypt_token(cred.refresh_token_encrypted)

        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        logger.info(f"🔄 Refreshing access token para {cred.google_email}")

        try:
            response = requests.post(token_url, data=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Atualizar credencial
            cred.access_token_encrypted = _encrypt_token(data["access_token"])
            cred.token_expiry = timezone.now() + timedelta(seconds=data.get("expires_in", 3600))
            cred.save(update_fields=["access_token_encrypted", "token_expiry", "updated_at"])

            logger.info(
                f"✅ Access token refreshed. Nova expiração: {cred.token_expiry}"
            )

            # Auditoria (PA-05)
            AuditLog.objects.create(
                usuario=cred.user,
                action="GOOGLE_REFRESH_TOKEN",
                model_name="GoogleOAuthCredential",
                details={
                    "google_email": cred.google_email,
                    "new_expiry": cred.token_expiry.isoformat(),
                    "status": "success",
                }
            )

            return cred

        except requests.exceptions.HTTPError as e:
            # invalid_grant: refresh_token revogado pelo usuário
            if e.response.status_code == 400:
                error_data = e.response.json()
                if error_data.get("error") == "invalid_grant":
                    logger.error(
                        f"❌ Refresh token inválido (revogado pelo usuário): {cred.google_email}"
                    )

                    # Remover credencial (usuário precisa reconectar)
                    cred.delete()

                    # Auditoria (PA-05)
                    AuditLog.objects.create(
                        usuario=cred.user,
                        action="GOOGLE_DISCONNECT",
                        model_name="GoogleOAuthCredential",
                        details={
                            "google_email": cred.google_email,
                            "reason": "invalid_grant (refresh token revogado pelo usuário)",
                            "status": "auto_removed",
                        }
                    )

                    raise ValueError(
                        "Sua conexão com o Google foi revogada. "
                        "Reconecte sua conta em Pré-agenda > Integrações."
                    )

            logger.error(f"❌ Erro ao refresh access token: {e}")
            raise Exception(f"Falha ao atualizar token Google: {str(e)}")


def revoke_token(credential: GoogleOAuthCredential) -> bool:
    """
    Revoga refresh_token no Google e remove credencial local.

    Args:
        credential: Instância de GoogleOAuthCredential a ser revogada

    Returns:
        bool: True se revogado com sucesso, False caso contrário

    Example:
        >>> credential = request.user.google_oauth
        >>> if revoke_token(credential):
        ...     messages.success(request, "Conta Google desconectada com sucesso")
    """
    import requests

    try:
        # Descriptografar refresh_token
        refresh_token = _decrypt_token(credential.refresh_token_encrypted)

        # Revogar no Google
        revoke_url = "https://oauth2.googleapis.com/revoke"
        payload = {"token": refresh_token}

        logger.info(f"🔓 Revogando refresh token para {credential.google_email}")

        response = requests.post(revoke_url, data=payload, timeout=10)

        # 200 OK: revogado com sucesso
        # 400 Bad Request: token já inválido (ok, continuar)
        if response.status_code not in [200, 400]:
            logger.warning(f"⚠️ Revoke retornou status {response.status_code}")

        # Remover credencial local
        user = credential.user
        google_email = credential.google_email
        credential.delete()

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=user,
            action="GOOGLE_DISCONNECT",
            model_name="GoogleOAuthCredential",
            details={
                "google_email": google_email,
                "reason": "user_requested",
                "status": "success",
            }
        )

        logger.info(f"✅ Credencial removida: {google_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Erro ao revogar token: {e}")
        return False


# ============================================================================
# KEY ROTATION (GAP-2)
# ============================================================================

def rotate_encryption_key(old_key: str, new_key: str) -> int:
    """
    Rotaciona GCAL_ENCRYPTION_KEY sem downtime.

    **Processo zero-downtime**:
    1. Descriptografa todos os tokens com chave antiga
    2. Re-criptografa com chave nova
    3. Salva no banco
    4. Atualizar .env com nova chave
    5. Restart aplicação

    Args:
        old_key: Chave Fernet antiga (base64-encoded)
        new_key: Chave Fernet nova (base64-encoded)

    Returns:
        int: Número de credenciais atualizadas

    Raises:
        InvalidToken: Se chave antiga incorreta

    Usage:
        # Management command: python manage.py rotate_gcal_encryption_key

        >>> from cryptography.fernet import Fernet
        >>> old_key = os.getenv("GCAL_ENCRYPTION_KEY")
        >>> new_key = Fernet.generate_key().decode()
        >>> count = rotate_encryption_key(old_key, new_key)
        >>> print(f"✅ {count} credenciais atualizadas")
        >>> # Atualizar .env e restart
    """
    old_fernet = Fernet(old_key.encode('utf-8'))
    new_fernet = Fernet(new_key.encode('utf-8'))

    credentials = GoogleOAuthCredential.objects.all()
    count = 0

    logger.info(f"🔄 Iniciando rotação de chave ({credentials.count()} credenciais)")

    for cred in credentials:
        try:
            # Descriptografar com chave antiga
            access_token = old_fernet.decrypt(cred.access_token_encrypted).decode('utf-8')
            refresh_token = old_fernet.decrypt(cred.refresh_token_encrypted).decode('utf-8')

            # Re-criptografar com chave nova
            cred.access_token_encrypted = new_fernet.encrypt(access_token.encode('utf-8'))
            cred.refresh_token_encrypted = new_fernet.encrypt(refresh_token.encode('utf-8'))
            cred.save(update_fields=["access_token_encrypted", "refresh_token_encrypted"])

            count += 1
            logger.info(f"  ✅ Rotacionada: {cred.google_email}")

        except InvalidToken:
            logger.error(f"  ❌ Chave antiga incorreta para: {cred.google_email}")
            raise
        except Exception as e:
            logger.error(f"  ❌ Erro ao rotacionar {cred.google_email}: {e}")
            raise

    logger.info(f"✅ Rotação concluída: {count}/{credentials.count()} credenciais atualizadas")

    # Auditoria (PA-05)
    AuditLog.objects.create(
        usuario=None,
        action="GCAL_ENCRYPTION_KEY_ROTATION",
        model_name="GoogleOAuthCredential",
        details={
            "credentials_updated": count,
            "status": "success",
        }
    )

    return count
