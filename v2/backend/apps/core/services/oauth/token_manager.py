"""
Token Manager - §7 Epic #459

Handles encryption, decryption, refresh, and rotation of OAuth tokens.
Extracted from google_oauth.py to separate token management concerns.

Security features:
- Fernet encryption (AES-128-CBC + HMAC-SHA256)
- Thread-safe refresh with select_for_update (GAP-1)
- Zero-downtime key rotation (GAP-2)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

from __future__ import annotations

import base64
import logging
import os
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

import requests
from cryptography.fernet import Fernet, InvalidToken

from apps.core.models import AuditLog, GoogleOAuthCredential, Usuario
from apps.core.services.db_retry import retry_on_deadlock

logger: logging.Logger = logging.getLogger(__name__)


# ============================================================================
# ENCRYPTION (GAP-2: Chave dedicada)
# ============================================================================


def _get_fernet_key() -> bytes:
    """
    Retorna chave Fernet dedicada para criptografia de tokens OAuth.

    Prioridade:
    1. GCAL_ENCRYPTION_KEY (obrigatória em produção)
    2. Fallback: SECRET_KEY (apenas dev/staging com warning)

    Raises:
        ValueError: Se nenhuma chave válida for encontrada
    """
    key: str | None = os.getenv("GCAL_ENCRYPTION_KEY")

    if key:
        return key.encode("utf-8")

    # Fallback para SECRET_KEY (dev/staging apenas)
    if settings.ENVIRONMENT != "production":
        logger.warning(
            "⚠️ GCAL_ENCRYPTION_KEY não definida. Usando SECRET_KEY (não recomendado). "
            "Defina GCAL_ENCRYPTION_KEY para produção."
        )
        # Derivar chave Fernet-compatible de SECRET_KEY
        from hashlib import sha256

        return base64.urlsafe_b64encode(sha256(settings.SECRET_KEY.encode()).digest())

    raise ValueError(
        "❌ GCAL_ENCRYPTION_KEY obrigatória em produção. "
        "Gere com: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
    )


def encrypt_token(token: str) -> bytes:
    """
    Criptografa token usando Fernet (AES-128-CBC + HMAC-SHA256).

    Args:
        token: Token em plaintext (access_token ou refresh_token)

    Returns:
        bytes: Token criptografado (formato Fernet)

    Raises:
        ValueError: Se chave de criptografia não estiver configurada
    """
    fernet: Fernet = Fernet(_get_fernet_key())
    return fernet.encrypt(token.encode("utf-8"))


def decrypt_token(encrypted: bytes | memoryview) -> str:
    """
    Descriptografa token criptografado com Fernet.

    Args:
        encrypted: Token criptografado (bytes ou memoryview do PostgreSQL)

    Returns:
        str: Token em plaintext

    Raises:
        InvalidToken: Se token estiver corrompido ou chave incorreta
    """
    if isinstance(encrypted, memoryview):
        encrypted = bytes(encrypted)
    fernet: Fernet = Fernet(_get_fernet_key())
    return fernet.decrypt(encrypted).decode("utf-8")


# Aliases for backward compatibility (used internally with underscore prefix)
_encrypt_token = encrypt_token
_decrypt_token = decrypt_token


# ============================================================================
# TOKEN REFRESH (GAP-1: Concorrência)
# ============================================================================


@retry_on_deadlock(operation="oauth.refresh_access_token")
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
    with transaction.atomic():
        # Row-level lock (GAP-1: Concorrência)
        cred: GoogleOAuthCredential = GoogleOAuthCredential.objects.select_for_update().get(id=credential.id)

        # Double-check: outro thread já refrescou?
        if cred.token_expiry > timezone.now() + timedelta(minutes=5):
            logger.info(f"✅ Token já válido (outro thread refrescou). " f"Expira em: {cred.token_expiry}")
            return cred

        # Refresh via Google API
        client_id: str | None = os.getenv("GCAL_OAUTH_CLIENT_ID")
        client_secret: str | None = os.getenv("GCAL_OAUTH_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError("❌ GCAL_OAUTH_CLIENT_ID e GCAL_OAUTH_CLIENT_SECRET não configuradas")

        refresh_token: str = decrypt_token(cred.refresh_token_encrypted)

        token_url: str = "https://oauth2.googleapis.com/token"
        payload: dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        logger.info(f"🔄 Refreshing access token para {cred.google_email}")

        try:
            response: requests.Response = requests.post(
                token_url, data=payload, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

            # Atualizar credencial
            cred.access_token_encrypted = encrypt_token(data["access_token"])
            cred.token_expiry = timezone.now() + timedelta(seconds=data.get("expires_in", 3600))
            cred.save(update_fields=["access_token_encrypted", "token_expiry", "updated_at"])

            logger.info(f"✅ Access token refreshed. Nova expiração: {cred.token_expiry}")

            # Auditoria (PA-05)
            AuditLog.objects.create(
                usuario=cred.user,
                action=AuditLog.Action.GOOGLE_REFRESH_TOKEN,
                model_name="GoogleOAuthCredential",
                details={
                    "google_email": cred.google_email,
                    "new_expiry": cred.token_expiry.isoformat(),
                    "status": "success",
                },
            )

            return cred

        except requests.exceptions.HTTPError as e:
            # invalid_grant: refresh_token revogado pelo usuário
            if e.response.status_code == 400:
                error_data: dict[str, Any] = e.response.json()
                if error_data.get("error") == "invalid_grant":
                    logger.error(f"❌ Refresh token inválido (revogado pelo usuário): {cred.google_email}")

                    # Remover credencial (usuário precisa reconectar)
                    cred.delete()

                    # Auditoria (PA-05)
                    AuditLog.objects.create(
                        usuario=cred.user,
                        action=AuditLog.Action.GOOGLE_DISCONNECT,
                        model_name="GoogleOAuthCredential",
                        details={
                            "google_email": cred.google_email,
                            "reason": "invalid_grant (refresh token revogado pelo usuário)",
                            "status": "auto_removed",
                        },
                    )

                    raise ValueError(
                        "Sua conexão com o Google foi revogada. " "Reconecte sua conta em Pré-agenda > Integrações."
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
    try:
        # Descriptografar refresh_token
        refresh_token: str = decrypt_token(credential.refresh_token_encrypted)

        # Revogar no Google
        revoke_url: str = "https://oauth2.googleapis.com/revoke"
        payload: dict[str, str] = {"token": refresh_token}

        logger.info(f"🔓 Revogando refresh token para {credential.google_email}")

        response: requests.Response = requests.post(revoke_url, data=payload, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT)

        # 200 OK: revogado com sucesso
        # 400 Bad Request: token já inválido (ok, continuar)
        if response.status_code not in [200, 400]:
            logger.warning(f"⚠️ Revoke retornou status {response.status_code}")

        # Remover credencial local
        user: Usuario = credential.user
        google_email: str = credential.google_email
        credential.delete()

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=user,
            action=AuditLog.Action.GOOGLE_DISCONNECT,
            model_name="GoogleOAuthCredential",
            details={
                "google_email": google_email,
                "reason": "user_requested",
                "status": "success",
            },
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
    old_fernet: Fernet = Fernet(old_key.encode("utf-8"))
    new_fernet: Fernet = Fernet(new_key.encode("utf-8"))

    credentials: Any = GoogleOAuthCredential.objects.all()
    count: int = 0

    logger.info(f"🔄 Iniciando rotação de chave ({credentials.count()} credenciais)")

    for cred in credentials:
        try:
            # Descriptografar com chave antiga
            access_token = old_fernet.decrypt(cred.access_token_encrypted).decode("utf-8")
            refresh_token = old_fernet.decrypt(cred.refresh_token_encrypted).decode("utf-8")

            # Re-criptografar com chave nova
            cred.access_token_encrypted = new_fernet.encrypt(access_token.encode("utf-8"))
            cred.refresh_token_encrypted = new_fernet.encrypt(refresh_token.encode("utf-8"))
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
        action=AuditLog.Action.GCAL_ENCRYPTION_KEY_ROTATION,
        model_name="GoogleOAuthCredential",
        details={
            "credentials_updated": count,
            "status": "success",
        },
    )

    return count
