"""
AS v2 — Google OAuth 2.0 Endpoints

Implementa fluxo OAuth 2.0 para Google Calendar:
- GET /oauth/google/start/ → Redireciona para Google OAuth
- GET /oauth/google/callback/ → Callback após autorização
- GET /api/integrations/google/status/ → Status da conexão
- POST /api/integrations/google/disconnect/ → Desconectar conta

Refs:
- Sprint 1 (Issue #1): Endpoints OAuth
- GAP-3: Rate limiting com UserRateThrottle
- PA-05: Auditoria obrigatória (AuditLog)
"""

import logging
from datetime import timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.core.permissions import IsControleOrSuper
from apps.core.models import GoogleOAuthCredential, AuditLog
from apps.core.services.google_oauth import (
    build_authorization_url,
    exchange_code_for_tokens,
    revoke_token,
    _encrypt_token,
)

logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _merge_query_params(url: str, **params) -> str:
    """
    Merge query parameters into URL, preserving existing parameters.

    Args:
        url: Base URL (may contain existing query params)
        **params: Query parameters to add/update

    Returns:
        URL with merged query parameters

    Example:
        _merge_query_params("/pre-agenda?tab=integrations", google="connected")
        → "/pre-agenda?tab=integrations&google=connected"

        _merge_query_params("/pre-agenda", google="error", reason="validation")
        → "/pre-agenda?google=error&reason=validation"
    """
    parsed = urlparse(url)
    query_dict = parse_qs(parsed.query)

    # Add new parameters
    for key, value in params.items():
        query_dict[key] = [value]

    # Rebuild query string
    new_query = urlencode(query_dict, doseq=True)

    # Rebuild URL
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))


# ============================================================================
# RATE LIMITING (GAP-3)
# ============================================================================

class OAuthThrottle(UserRateThrottle):
    """
    Rate limiting específico para endpoints OAuth.

    GAP-3: Prevenir abuso com 10 requests/hora por usuário.
    """
    rate = '10/hour'
    scope = 'oauth'


# ============================================================================
# OAUTH 2.0 ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsControleOrSuper])
@throttle_classes([OAuthThrottle])
def google_oauth_start(request):
    """
    Inicia fluxo OAuth 2.0 com Google.

    **Permissão**: IsControleOrSuper (apenas grupo Controle ou Superintendência)
    **Throttling**: 10 requests/hour por usuário (GAP-3)

    Query Params:
        return_to (str, opcional): URL de retorno após callback (default: /pre-agenda)

    Returns:
        302 Redirect: Redireciona para Google OAuth Consent Screen

    Example:
        GET /oauth/google/start/?return_to=/pre-agenda

        → Redirects to: https://accounts.google.com/o/oauth2/v2/auth?...
    """
    return_to = request.GET.get('return_to', '/pre-agenda')

    try:
        # Gerar URL de autorização
        auth_url = build_authorization_url(request.user, return_to=return_to)

        logger.info(
            f"🔐 OAuth start: {request.user.username} → Google consent screen"
        )

        return redirect(auth_url)

    except ValueError as e:
        logger.error(f"❌ OAuth start falhou: {e}")
        return Response(
            {
                "error": "Configuração OAuth incompleta. Contate o administrador.",
                "detail": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def google_oauth_callback(request):
    """
    Callback OAuth 2.0 após autorização do usuário no Google.

    **HTTPS obrigatório em produção** (validação incluída).
    **CSRF protection** via state parameter.

    Query Params:
        code (str): Authorization code retornado pelo Google
        state (str): CSRF token + return_to + user_id (formato: "csrf|return_to|user_id")
        error (str, opcional): Erro retornado pelo Google (ex: access_denied)

    Returns:
        302 Redirect: Redireciona para return_to com query params:
            - ?google=connected (sucesso)
            - ?google=error&reason=<reason> (erro)

    Security:
        - HTTPS obrigatório em produção
        - CSRF token validado via state
        - Domínio validado (@aprendereditora.com.br)
        - Tokens criptografados com Fernet (GCAL_ENCRYPTION_KEY)
        - AuditLog criado (PA-05)

    Example:
        GET /oauth/google/callback/?code=4/0AfJohXk...&state=abc123|/pre-agenda|42

        → Creates GoogleOAuthCredential
        → Redirects to: /pre-agenda?google=connected
    """
    # Validação HTTPS em produção
    if settings.ENVIRONMENT == "production" and not request.is_secure():
        logger.error("❌ OAuth callback rejeitado: HTTPS obrigatório em produção")
        return Response(
            {"error": "HTTPS obrigatório em produção"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Verificar erro do Google (ex: usuário negou permissão)
    error = request.GET.get('error')
    if error:
        logger.warning(f"⚠️ OAuth callback erro: {error}")
        return redirect(f"/pre-agenda?google=error&reason={error}")

    # Obter parâmetros
    code = request.GET.get('code')
    state = request.GET.get('state')

    if not code or not state:
        logger.error("❌ OAuth callback: code ou state ausente")
        return redirect("/pre-agenda?google=error&reason=missing_params")

    # Verificar autenticação
    if not request.user.is_authenticated:
        logger.error("❌ OAuth callback: usuário não autenticado")
        return redirect("/pre-agenda?google=error&reason=unauthenticated")

    # Validar state token (CSRF + user_id + return_to)
    from apps.core.services.google_oauth import validate_oauth_state
    validation = validate_oauth_state(state, request.user.id)

    if not validation["valid"]:
        logger.error(f"❌ OAuth callback: state validation failed ({validation['error']})")
        return redirect("/pre-agenda?google=error&reason=invalid_state")

    # State válido - usar return_to validado
    return_to = validation["return_to"]

    try:
        # Trocar code por tokens
        tokens = exchange_code_for_tokens(code)

        # Criar ou atualizar credencial
        credential, created = GoogleOAuthCredential.objects.update_or_create(
            user=request.user,
            defaults={
                "google_email": tokens["email"],
                "access_token_encrypted": _encrypt_token(tokens["access_token"]),
                "refresh_token_encrypted": _encrypt_token(tokens["refresh_token"]),
                "token_expiry": timezone.now() + timedelta(seconds=tokens["expires_in"]),
                "scope": tokens["scope"],
            }
        )

        action = "created" if created else "updated"
        logger.info(
            f"✅ OAuth callback: credencial {action} para "
            f"{request.user.username} ({tokens['email']})"
        )

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=request.user,
            action="GOOGLE_CONNECT",
            model_name="GoogleOAuthCredential",
            details={
                "google_email": tokens["email"],
                "action": action,
                "ip_address": request.META.get('REMOTE_ADDR', ''),
                "user_agent": request.META.get('HTTP_USER_AGENT', '')[:200],
            }
        )

        # Redirecionar para return_to (merge query params)
        redirect_url = _merge_query_params(return_to, google="connected")
        return redirect(redirect_url)

    except ValueError as e:
        # Erro de validação (ex: domínio inválido)
        logger.error(f"❌ OAuth callback falhou (validação): {e}")
        redirect_url = _merge_query_params(return_to, google="error", reason="validation")
        return redirect(redirect_url)

    except Exception as e:
        # Erro genérico
        logger.error(f"❌ OAuth callback falhou: {e}")
        redirect_url = _merge_query_params(return_to, google="error", reason="server_error")
        return redirect(redirect_url)


@api_view(['GET'])
@permission_classes([IsControleOrSuper])
def google_oauth_status(request):
    """
    Retorna status da conexão OAuth do usuário.

    **Permissão**: IsControleOrSuper

    Returns:
        200 OK: {
            "connected": bool,
            "google_email": str | null,
            "token_expiry": str (ISO 8601) | null,
            "expires_in_days": int | null,
            "is_expired": bool
        }

    Example:
        GET /api/integrations/google/status/

        Response (conectado):
        {
            "connected": true,
            "google_email": "operacional1@aprendereditora.com.br",
            "token_expiry": "2025-11-05T15:30:00Z",
            "expires_in_days": 45,
            "is_expired": false
        }

        Response (desconectado):
        {
            "connected": false,
            "google_email": null,
            "token_expiry": null,
            "expires_in_days": null,
            "is_expired": false
        }
    """
    try:
        credential = GoogleOAuthCredential.objects.get(user=request.user)

        return Response({
            "connected": True,
            "google_email": credential.google_email,
            "token_expiry": credential.token_expiry.isoformat(),
            "expires_in_days": credential.days_until_expiry(),
            "is_expired": credential.is_expired(),
        })

    except GoogleOAuthCredential.DoesNotExist:
        return Response({
            "connected": False,
            "google_email": None,
            "token_expiry": None,
            "expires_in_days": None,
            "is_expired": False,
        })


@api_view(['POST'])
@permission_classes([IsControleOrSuper])
def google_oauth_disconnect(request):
    """
    Desconecta conta Google (revoga refresh_token).

    **Permissão**: IsControleOrSuper

    Returns:
        200 OK: {"message": "Conta Google desconectada com sucesso"}
        404 Not Found: {"error": "Nenhuma conexão Google encontrada"}

    Example:
        POST /api/integrations/google/disconnect/

        Response (sucesso):
        {
            "message": "Conta Google desconectada com sucesso",
            "google_email": "operacional1@aprendereditora.com.br"
        }
    """
    try:
        credential = GoogleOAuthCredential.objects.get(user=request.user)
        google_email = credential.google_email

        # Revogar token no Google e remover credencial local
        success = revoke_token(credential)

        if success:
            logger.info(
                f"✅ OAuth disconnect: {request.user.username} ({google_email})"
            )

            return Response({
                "message": "Conta Google desconectada com sucesso",
                "google_email": google_email
            })
        else:
            logger.warning(
                f"⚠️ OAuth disconnect: falha ao revogar token ({google_email})"
            )

            return Response({
                "message": "Credencial removida localmente, mas falha ao revogar no Google",
                "google_email": google_email
            }, status=status.HTTP_200_OK)

    except GoogleOAuthCredential.DoesNotExist:
        return Response(
            {"error": "Nenhuma conexão Google encontrada"},
            status=status.HTTP_404_NOT_FOUND
        )
