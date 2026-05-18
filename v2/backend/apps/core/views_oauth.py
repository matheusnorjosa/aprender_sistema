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

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging
from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from django.conf import settings
from django.shortcuts import redirect
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.core.models import AuditLog, GoogleOAuthCredential
from apps.core.rbac.policies import CanUseGcal
from apps.core.services.google_oauth import build_authorization_url, exchange_code_for_tokens, revoke_token
from apps.core.services.oauth.oauth_flow import _is_safe_url as is_safe_url  # noqa: PLC2701
from apps.core.services.oauth.token_manager import encrypt_token

logger = logging.getLogger(__name__)

# OAuth error codes whitelist (RFC 6749 §4.1.2.1 + OpenID Connect Core 1.0 §3.1.2.6)
# Qualquer outro valor recebido em ?error= no callback é normalizado para "unknown"
# antes de virar query string, evitando URL injection / log poisoning.
SAFE_OAUTH_ERROR_CODES: frozenset[str] = frozenset(
    {
        "access_denied",
        "invalid_request",
        "unauthorized_client",
        "unsupported_response_type",
        "invalid_scope",
        "server_error",
        "temporarily_unavailable",
        "interaction_required",
        "login_required",
        "consent_required",
        "account_selection_required",
    }
)

# Hosts permitidos como destino do redirect em ``google_oauth_start`` — defesa
# em profundidade contra ``build_authorization_url`` retornar URL inesperada
# (CodeQL py/url-redirection #3). Sempre HTTPS, hostname exato.
GOOGLE_OAUTH_AUTHORIZED_HOSTS: frozenset[str] = frozenset({"accounts.google.com"})


def _is_google_oauth_authorize_url(url: str | None) -> bool:
    """``True`` se ``url`` aponta para o consent screen do Google.

    Aceita ``https://accounts.google.com/...``. Rejeita qualquer outro host
    (inclusive subdomain spoofing ``accounts.google.com.evil.com``),
    qualquer scheme não-HTTPS, e protocolo-relativo ``//evil.com``.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return False
    return parsed.scheme == "https" and parsed.hostname in GOOGLE_OAUTH_AUTHORIZED_HOSTS


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _safe_return_to(value: str | None, default: str = "/pre-agenda") -> str:
    """
    Sanitiza ``return_to`` antes de propagar para Google OAuth.

    Aceita:
      - caminhos relativos seguros (``/path``) — não ``//evil.com``;
      - URLs absolutas cujo origin esteja em ``CORS_ALLOWED_ORIGINS`` ou
        ``OAUTH_ALLOWED_RETURN_ORIGINS`` (delegado a ``is_safe_url``).

    Rejeita tudo o mais (incluindo ``javascript:``, ``data:``, hosts externos).
    Em rejeição, faz fallback para ``default`` e loga warning (apenas tamanho/prefixo,
    não a string completa).
    """
    if not value:
        return default
    if not is_safe_url(value):
        logger.warning("OAuth return_to rejeitado (open redirect prevention): len=%d", len(value))
        return default
    return value


def _safe_oauth_error_reason(value: str | None) -> str:
    """Normaliza ?error= do callback Google para a allowlist RFC 6749."""
    if not value:
        return "unknown"
    return value if value in SAFE_OAUTH_ERROR_CODES else "unknown"


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
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))


def _build_frontend_redirect_url(path: str) -> str:
    """
    Constrói URL absoluta do frontend para redirecionamento OAuth.

    Args:
        path: Caminho relativo (ex: "/pre-agenda?google=connected") ou URL absoluta

    Returns:
        URL absoluta para redirect

    Example:
        _build_frontend_redirect_url("/pre-agenda?google=connected")
        → "http://localhost:5173/pre-agenda?google=connected" (dev)
        → "https://sistema.aprendereditora.com.br/pre-agenda?google=connected" (prod)

    Security:
        - Caminhos relativos são convertidos para URL do frontend (CORS_ALLOWED_ORIGINS[0])
        - URLs absolutas são preservadas (já validadas por is_safe_url)
    """
    import os

    # Se já for URL absoluta, validar antes de usar
    parsed = urlparse(path)
    if parsed.scheme and parsed.netloc:
        if not is_safe_url(path):
            logger.warning(f"URL absoluta rejeitada (open redirect): {path}")
            return "/pre-agenda?google=error&reason=invalid_redirect"
        return path

    # Caminho relativo: construir URL do frontend
    # Usar primeira origem do CORS_ALLOWED_ORIGINS (geralmente o frontend)
    frontend_origin = os.getenv("FRONTEND_URL", "").strip()

    if not frontend_origin and settings.CORS_ALLOWED_ORIGINS:
        # Issue #442: Use settings instead of hardcoded ports
        frontend_port = getattr(settings, "FRONTEND_DEV_PORT", "5173")
        backend_port = getattr(settings, "BACKEND_PORT", "8002")

        # Priorizar frontend dev port (Vite dev server padrão)
        for origin in settings.CORS_ALLOWED_ORIGINS:
            if f":{frontend_port}" in origin:
                frontend_origin = origin
                break

        # Se não encontrou frontend port, pegar primeira origem que não seja backend port
        if not frontend_origin:
            for origin in settings.CORS_ALLOWED_ORIGINS:
                if f":{backend_port}" not in origin:
                    frontend_origin = origin
                    break

    # Fallback para frontend URL (dev)
    if not frontend_origin:
        frontend_port = getattr(settings, "FRONTEND_DEV_PORT", "5173")
        frontend_origin = f"http://localhost:{frontend_port}"

    # SECURITY: Validar origin antes de usar (previne env injection)
    if not is_safe_url(frontend_origin):
        logger.error(f"Frontend origin não confiável, usando path relativo: {frontend_origin}")
        return path

    # Construir URL absoluta
    full_url = f"{frontend_origin}{path}"
    logger.info(f"🔗 Redirect construído: {full_url} (frontend_origin={frontend_origin})")
    return full_url


# ============================================================================
# RATE LIMITING (GAP-3)
# ============================================================================


class OAuthThrottle(UserRateThrottle):
    """
    Rate limiting específico para endpoints OAuth.

    GAP-3: Prevenir abuso com 10 requests/hora por usuário.
    """

    rate = "10/hour"
    scope = "oauth"


# ============================================================================
# OAUTH 2.0 ENDPOINTS
# ============================================================================


@api_view(["GET"])
@permission_classes([CanUseGcal])
@throttle_classes([OAuthThrottle])
def google_oauth_start(request: Request) -> Response:
    """
    Inicia fluxo OAuth 2.0 com Google.

    **Permissão**: HasPerm("import_spreadsheet") (apenas grupo Controle ou Superintendência)
    **Throttling**: 10 requests/hour por usuário (GAP-3)

    Query Params:
        return_to (str, opcional): URL de retorno após callback (default: /pre-agenda)

    Returns:
        302 Redirect: Redireciona para Google OAuth Consent Screen

    Example:
        GET /oauth/google/start/?return_to=/pre-agenda

        → Redirects to: https://accounts.google.com/o/oauth2/v2/auth?...
    """
    # Security: ``return_to`` é user-controlled — validar contra allowlist
    # antes de injetar no fluxo OAuth (CodeQL py/url-redirection).
    return_to = _safe_return_to(request.GET.get("return_to"))

    try:
        # Gerar URL de autorização
        auth_url = build_authorization_url(request.user, return_to=return_to)

        # Security: segunda barreira antes do redirect — confirma que o URL
        # gerado aponta para o consent screen do Google (CodeQL
        # py/url-redirection #3). Defesa em profundidade contra mudança
        # acidental do serviço retornar URL inesperada.
        if not _is_google_oauth_authorize_url(auth_url):
            logger.error("OAuth start: build_authorization_url returned unexpected host")
            return Response(
                {"error": "Configuração OAuth inválida. Contate o administrador."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"🔐 OAuth start: {request.user.username} → Google consent screen")

        return redirect(auth_url)

    except ValueError as e:
        logger.error(f"❌ OAuth start falhou: {e}")
        return Response(
            {"error": "Configuração OAuth incompleta. Contate o administrador."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
def google_oauth_callback(request: Request) -> Response:
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
        return Response({"error": "HTTPS obrigatório em produção"}, status=status.HTTP_403_FORBIDDEN)

    # Verificar erro do Google (ex: usuário negou permissão)
    # Security: ``error`` vem via query string user-modificável.
    # Normalizar para allowlist antes de propagar à URL (CodeQL py/url-redirection).
    # Não logar o valor para evitar log poisoning / vazamento (CodeQL
    # py/clear-text-logging-sensitive-data) — a allowlist pode ser auditada
    # via AuditLog se houver caso de uso.
    if request.GET.get("error"):
        safe_reason = _safe_oauth_error_reason(request.GET.get("error"))
        logger.warning("⚠️ OAuth callback: Google retornou error param (sanitized)")
        redirect_path = _merge_query_params("/pre-agenda", google="error", reason=safe_reason)
        redirect_url = _build_frontend_redirect_url(redirect_path)
        return redirect(redirect_url)

    # Obter parâmetros
    code = request.GET.get("code")
    state = request.GET.get("state")

    if not code or not state:
        logger.error("❌ OAuth callback: code ou state ausente")
        redirect_url = _build_frontend_redirect_url("/pre-agenda?google=error&reason=missing_params")
        return redirect(redirect_url)

    # Verificar autenticação
    if not request.user.is_authenticated:
        logger.error("❌ OAuth callback: usuário não autenticado")
        redirect_url = _build_frontend_redirect_url("/pre-agenda?google=error&reason=unauthenticated")
        return redirect(redirect_url)

    # Validar state token (CSRF + user_id + return_to)
    from apps.core.services.google_oauth import validate_oauth_state

    validation = validate_oauth_state(state, request.user.id)

    if not validation["valid"]:
        # Security: ``validation['error']`` pode propagar fragmentos do state token
        # ou do refresh token. Não logar o valor — quem precisar de detalhes
        # usa AuditLog dedicado (CodeQL py/clear-text-logging-sensitive-data).
        logger.error("❌ OAuth callback: state validation failed (details not logged)")
        redirect_url = _build_frontend_redirect_url("/pre-agenda?google=error&reason=invalid_state")
        return redirect(redirect_url)

    # State válido - usar return_to validado
    return_to = validation["return_to"]

    try:
        # Trocar code por tokens
        tokens = exchange_code_for_tokens(code)

        # Criar ou atualizar credencial
        _, created = GoogleOAuthCredential.objects.update_or_create(
            user=request.user,
            defaults={
                "google_email": tokens["email"],
                "access_token_encrypted": encrypt_token(tokens["access_token"]),
                "refresh_token_encrypted": encrypt_token(tokens["refresh_token"]),
                "token_expiry": timezone.now() + timedelta(seconds=tokens["expires_in"]),
                "scope": tokens["scope"],
            },
        )

        action = "created" if created else "updated"
        logger.info(f"✅ OAuth callback: credencial {action} para " f"{request.user.username} ({tokens['email']})")

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=request.user,
            action=AuditLog.Action.GOOGLE_CONNECT,
            model_name="GoogleOAuthCredential",
            details={
                "google_email": tokens["email"],
                "action": action,
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        # Redirecionar para return_to (merge query params)
        redirect_path = _merge_query_params(return_to, google="connected")
        redirect_url = _build_frontend_redirect_url(redirect_path)
        return redirect(redirect_url)

    except ValueError as e:
        # Erro de validação (ex: domínio inválido)
        logger.error(f"❌ OAuth callback falhou (validação): {e}")
        redirect_path = _merge_query_params(return_to, google="error", reason="validation")
        redirect_url = _build_frontend_redirect_url(redirect_path)
        return redirect(redirect_url)

    except Exception as e:
        # Erro genérico
        logger.error(f"❌ OAuth callback falhou: {e}")
        redirect_path = _merge_query_params(return_to, google="error", reason="server_error")
        redirect_url = _build_frontend_redirect_url(redirect_path)
        return redirect(redirect_url)


@api_view(["GET"])
@permission_classes([CanUseGcal])
def google_oauth_status(request: Request) -> Response:
    """
    Retorna status da conexão OAuth do usuário.

    **Permissão**: HasPerm("import_spreadsheet")

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

        return Response(
            {
                "connected": True,
                "google_email": credential.google_email,
                "token_expiry": credential.token_expiry.isoformat(),
                "expires_in_days": credential.days_until_expiry(),
                "is_expired": credential.is_expired(),
                "default_calendar_id": credential.default_calendar_id or None,
            }
        )

    except GoogleOAuthCredential.DoesNotExist:
        return Response(
            {
                "connected": False,
                "google_email": None,
                "token_expiry": None,
                "expires_in_days": None,
                "is_expired": False,
                "default_calendar_id": None,
            }
        )


@api_view(["POST"])
@permission_classes([CanUseGcal])
def google_oauth_disconnect(request: Request) -> Response:
    """
    Desconecta conta Google (revoga refresh_token).

    **Permissão**: HasPerm("import_spreadsheet")

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
            logger.info(f"✅ OAuth disconnect: {request.user.username} ({google_email})")

            return Response({"message": "Conta Google desconectada com sucesso", "google_email": google_email})
        else:
            logger.warning(f"⚠️ OAuth disconnect: falha ao revogar token ({google_email})")

            return Response(
                {
                    "message": "Credencial removida localmente, mas falha ao revogar no Google",
                    "google_email": google_email,
                },
                status=status.HTTP_200_OK,
            )

    except GoogleOAuthCredential.DoesNotExist:
        return Response({"error": "Nenhuma conexão Google encontrada"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([CanUseGcal])
def google_oauth_list_events(request: Request) -> Response:
    """
    Lista eventos de um calendário Google do usuário.

    **Permissão**: HasPerm("import_spreadsheet")

    Query Params:
        calendar_id (str, opcional): ID do calendário (default: default_calendar_id ou "primary")
        time_min (str, opcional): Data início ISO 8601 (ex: 2026-04-01)
        time_max (str, opcional): Data fim ISO 8601 (ex: 2026-04-30)
        max_results (int, opcional): Máximo de eventos (default: 100)

    Returns:
        200 OK: Lista de eventos
        404 Not Found: Nenhuma conexão encontrada
        500 Error: Erro ao listar eventos
    """
    try:
        credential = GoogleOAuthCredential.objects.get(user=request.user)

        from apps.core.services.gcal_oauth_client import OAuthCalendarClient

        client = OAuthCalendarClient(credential)

        calendar_id = request.query_params.get("calendar_id") or credential.default_calendar_id or "primary"

        # Converter datas ISO para RFC3339 se fornecidas
        time_min = request.query_params.get("time_min")
        time_max = request.query_params.get("time_max")
        if time_min and "T" not in time_min:
            time_min = f"{time_min}T00:00:00-03:00"
        if time_max and "T" not in time_max:
            time_max = f"{time_max}T23:59:59-03:00"

        max_results = min(int(request.query_params.get("max_results", "100")), 2500)

        events = client.list_events(
            calendar_id,
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
        )

        logger.info(f"📅 Listed {len(events)} events from {calendar_id} for {request.user.username}")

        return Response({"events": events, "calendar_id": calendar_id, "count": len(events)})

    except GoogleOAuthCredential.DoesNotExist:
        return Response({"error": "Nenhuma conexão Google encontrada"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ Erro ao listar eventos: {e}")
        return Response({"error": "Erro ao listar eventos"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([CanUseGcal])
def google_oauth_list_calendars(request: Request) -> Response:
    """
    Lista calendários disponíveis do usuário OAuth.

    **Permissão**: HasPerm("import_spreadsheet")

    Returns:
        200 OK: Lista de calendários
        404 Not Found: Nenhuma conexão encontrada
        500 Error: Erro ao listar calendários

    Example:
        GET /api/integrations/google/calendars/

        Response:
        {
            "calendars": [
                {
                    "id": "operacional1@aprendereditora.com.br",
                    "summary": "operacional1@aprendereditora.com.br",
                    "primary": true
                },
                {
                    "id": "agenda-formacoes@aprendereditora.com.br",
                    "summary": "Agenda Formações",
                    "primary": false
                }
            ]
        }
    """
    try:
        credential = GoogleOAuthCredential.objects.get(user=request.user)

        # Criar cliente OAuth e listar calendários
        from apps.core.services.gcal_oauth_client import OAuthCalendarClient

        client = OAuthCalendarClient(credential)
        calendars = client.list_calendars()

        logger.info(f"📅 Listed {len(calendars)} calendars for {request.user.username}")
        for cal in calendars:
            logger.info(
                f"  📅 {cal['summary']}: id={cal['id']}, "
                f"primary={cal.get('primary', False)}, accessRole={cal.get('accessRole', 'N/A')}"
            )

        return Response({"calendars": calendars})

    except GoogleOAuthCredential.DoesNotExist:
        return Response({"error": "Nenhuma conexão Google encontrada"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"❌ Erro ao listar calendários: {e}")
        return Response({"error": "Erro ao listar calendários"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
@permission_classes([CanUseGcal])
def google_oauth_select_calendar(request: Request) -> Response:
    """
    Salva calendário selecionado pelo usuário.

    **Permissão**: HasPerm("import_spreadsheet")

    Request Body:
        {
            "calendar_id": "agenda-formacoes@aprendereditora.com.br"
        }

    Returns:
        200 OK: Calendário salvo com sucesso
        400 Bad Request: calendar_id não fornecido
        404 Not Found: Nenhuma conexão encontrada

    Example:
        POST /api/integrations/google/select-calendar/
        {
            "calendar_id": "agenda-formacoes@aprendereditora.com.br"
        }

        Response:
        {
            "message": "Calendário selecionado com sucesso",
            "calendar_id": "agenda-formacoes@aprendereditora.com.br"
        }
    """
    try:
        credential = GoogleOAuthCredential.objects.get(user=request.user)

        calendar_id = request.data.get("calendar_id")
        if not calendar_id:
            return Response({"error": "calendar_id é obrigatório"}, status=status.HTTP_400_BAD_REQUEST)

        # Atualizar calendário padrão
        credential.default_calendar_id = calendar_id
        credential.save(update_fields=["default_calendar_id", "updated_at"])

        logger.info(f"📅 Calendar selected: {request.user.username} → {calendar_id}")

        # Auditoria (PA-05)
        AuditLog.objects.create(
            usuario=request.user,
            action=AuditLog.Action.GOOGLE_SELECT_CALENDAR,
            model_name="GoogleOAuthCredential",
            details={
                "calendar_id": calendar_id,
                "ip_address": request.META.get("REMOTE_ADDR", ""),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        return Response({"message": "Calendário selecionado com sucesso", "calendar_id": calendar_id})

    except GoogleOAuthCredential.DoesNotExist:
        return Response({"error": "Nenhuma conexão Google encontrada"}, status=status.HTTP_404_NOT_FOUND)
