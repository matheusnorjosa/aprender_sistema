"""
OAuth Flow - §7 Epic #459

Handles OAuth 2.0 authorization flow with Google.
Extracted from google_oauth.py to separate flow concerns.

Security features:
- State token validation (CSRF prevention)
- Open redirect prevention (_is_safe_url)
- Domain validation (@aprendereditora.com.br)
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false, reportIndexIssue=false, reportOperatorIssue=false, reportUnknownLambdaType=false, reportMissingTypeArgument=false, reportUndefinedVariable=false

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlencode, urlparse

from django.conf import settings
from django.utils import timezone

import requests

logger: logging.Logger = logging.getLogger(__name__)


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
        - Caminhos relativos (começam com "/" mas não "//") são permitidos
        - URLs absolutas permitidas se origin estiver em CORS_ALLOWED_ORIGINS ou OAUTH_ALLOWED_RETURN_ORIGINS
        - Rejeita javascript:, data:, etc.

    Example:
        >>> _is_safe_url("/pre-agenda")  # True (caminho relativo)
        >>> _is_safe_url("http://localhost:5173/pre-agenda")  # True (se em CORS_ALLOWED_ORIGINS)
        >>> _is_safe_url("http://malicious.com/steal")  # False
    """
    if not url:
        return False

    # 1. Permitir caminhos relativos (começam com "/" mas não "//")
    if url.startswith("/") and not url.startswith("//"):
        return True

    # 2. Permitir URLs absolutas de origens confiáveis
    try:
        parsed: Any = urlparse(url)

        # Rejeitar protocolos perigosos
        if parsed.scheme in ["javascript", "data", "vbscript", "file"]:
            return False

        # Rejeitar URLs sem scheme ou netloc (ex: "//malicious.com")
        if not parsed.scheme or not parsed.netloc:
            return False

        # Rejeitar se não for http/https
        if parsed.scheme not in ["http", "https"]:
            return False

        # Reconstruir origin (scheme://host:port)
        origin: str = f"{parsed.scheme}://{parsed.netloc}"

        # Obter origens confiáveis de settings.CORS_ALLOWED_ORIGINS
        allowed_origins: list[str] = getattr(settings, "CORS_ALLOWED_ORIGINS", [])

        # Adicionar origens de OAUTH_ALLOWED_RETURN_ORIGINS (env var opcional)
        extra_origins_str: str = os.getenv("OAUTH_ALLOWED_RETURN_ORIGINS", "")
        if extra_origins_str:
            extra_origins = [o.strip() for o in extra_origins_str.split(",") if o.strip()]
            allowed_origins = list(allowed_origins) + extra_origins

        # Verificar se origin está na lista de origens confiáveis
        if origin in allowed_origins:
            logger.debug(f"✅ URL absoluta aceita (origin confiável): {origin}")
            return True
        else:
            logger.warning(f"⚠️ URL absoluta rejeitada (origin não confiável): {origin}")
            return False

    except Exception as e:
        logger.warning(f"⚠️ Erro ao validar URL: {url} ({e})")
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
        parts: list[str] = state.split("|")
        if len(parts) != 3:
            return {"valid": False, "return_to": "/pre-agenda", "error": "State format invalid"}

        csrf_token, return_to, state_user_id_str = parts
        state_user_id: int = int(state_user_id_str)

        # Verificar user_id match
        if state_user_id != user_id:
            logger.error(
                f"❌ OAuth state validation: user_id mismatch " f"(state={state_user_id}, authenticated={user_id})"
            )
            return {"valid": False, "return_to": "/pre-agenda", "error": "User ID mismatch"}

        # Buscar state no cache
        cache_key: str = f"oauth_state:{csrf_token}"
        cached_state: Any = cache.get(cache_key)

        if not cached_state:
            logger.error(f"❌ OAuth state validation: token not found or expired ({csrf_token[:8]}...)")
            return {
                "valid": False,
                "return_to": "/pre-agenda",
                "error": "State token invalid or expired",
            }

        # Validar return_to
        cached_return_to: str = cached_state.get("return_to", "/pre-agenda")
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
    import secrets

    from django.core.cache import cache

    client_id: str | None = os.getenv("GCAL_OAUTH_CLIENT_ID")
    redirect_uri: str | None = os.getenv("GCAL_OAUTH_REDIRECT_URI")

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
    csrf_token: str = secrets.token_urlsafe(32)
    state: str = f"{csrf_token}|{return_to}|{user.id}"

    # Armazenar CSRF token em cache (Redis) com TTL 10min
    cache_key: str = f"oauth_state:{csrf_token}"
    cache.set(
        cache_key,
        {
            "user_id": user.id,
            "return_to": return_to,
            "created_at": timezone.now().isoformat(),
        },
        timeout=600,
    )  # 10 minutos

    logger.info(f"🔐 OAuth state criado: {csrf_token[:8]}... (user={user.id})")

    params: dict[str, str] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email",
        "access_type": "offline",  # Obter refresh_token
        "prompt": "consent",  # Forçar tela de consentimento (garantir refresh_token)
        "state": state,
    }

    base_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
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
        ...     access_token_encrypted=encrypt_token(tokens['access_token']),
        ...     refresh_token_encrypted=encrypt_token(tokens['refresh_token']),
        ...     token_expiry=timezone.now() + timedelta(seconds=tokens['expires_in']),
        ...     google_email=tokens['email'],
        ... )
    """
    from typing import Any

    client_id: str | None = os.getenv("GCAL_OAUTH_CLIENT_ID")
    client_secret: str | None = os.getenv("GCAL_OAUTH_CLIENT_SECRET")
    redirect_uri: str | None = os.getenv("GCAL_OAUTH_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise ValueError("❌ Variáveis OAuth não configuradas (client_id, client_secret, redirect_uri)")

    token_url: str = "https://oauth2.googleapis.com/token"
    payload: dict[str, str] = {  # type: ignore[assignment]
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    logger.info("🔐 Trocando authorization code por tokens (grant_type=authorization_code)")

    try:
        response: requests.Response = requests.post(token_url, data=payload, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT)
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        # Validar presence de refresh_token (crítico)
        if "refresh_token" not in data:
            raise ValueError(
                "❌ refresh_token não retornado pelo Google. "
                "Possível causa: prompt=consent ausente ou usuário já autorizou antes. "
                "Revogue acesso no Google Account e tente novamente."
            )

        # Obter email da conta Google via UserInfo endpoint
        access_token: str = data["access_token"]
        userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}
        userinfo_response: requests.Response = requests.get(
            userinfo_url, headers=headers, timeout=settings.GCAL_OAUTH_TOKEN_TIMEOUT
        )
        userinfo_response.raise_for_status()
        userinfo: dict[str, Any] = userinfo_response.json()

        email: str | None = userinfo.get("email")
        if not email:
            raise ValueError("❌ Email não retornado pela API Google UserInfo")

        # Validar domínio permitido
        allowed_domain: str = os.getenv("GCAL_ALLOWED_DOMAIN", "aprendereditora.com.br")
        if not email.endswith(f"@{allowed_domain}"):
            raise ValueError(f"❌ Domínio não permitido: {email}. " f"Apenas contas @{allowed_domain} são aceitas.")

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
