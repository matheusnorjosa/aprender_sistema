"""
Views de Autenticação - AS v2

Endpoints:
- GET /api/csrf/ - Obter CSRF token (Issue #135)
- POST /api/auth/login/ - Login com username/password
- POST /api/auth/logout/ - Logout
- POST /api/auth/ping/ - Renovar sessão (CP5 - Issue #164)

Security Audit 2025-01:
- Account Lockout após N tentativas falhas
- Tracking de tentativas via Redis cache
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.core.views.utils import _get_client_ip

from .models import AuditLog


# ================================================================
# Account Lockout (Security Audit 2025-01)
# ================================================================
def _get_lockout_key(username: str) -> str:
    """Gera chave Redis para tracking de tentativas de login."""
    return f"login_attempts:{username.lower()}"


def _get_failed_attempts(username: str) -> int:
    """Retorna número de tentativas falhas de login."""
    key = _get_lockout_key(username)
    attempts = cache.get(key)
    return int(attempts) if attempts else 0


def _increment_failed_attempts(username: str) -> int:
    """
    Incrementa contador de tentativas falhas.
    Retorna o novo total de tentativas.
    """
    key = _get_lockout_key(username)
    lockout_duration = getattr(settings, "ACCOUNT_LOCKOUT_DURATION", 900)

    # Usa Redis INCR com TTL
    try:
        # Se a chave não existe, cria com valor 1
        current = cache.get(key)
        if current is None:
            cache.set(key, 1, timeout=lockout_duration)
            return 1
        else:
            new_value = int(current) + 1
            cache.set(key, new_value, timeout=lockout_duration)
            return new_value
    except Exception:
        # Fallback: apenas retorna 1 se cache falhar
        return 1


def _clear_failed_attempts(username: str) -> None:
    """Limpa contador de tentativas após login bem-sucedido."""
    key = _get_lockout_key(username)
    cache.delete(key)


def _is_account_locked(username: str) -> bool:
    """Verifica se a conta está bloqueada por excesso de tentativas."""
    threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)
    attempts = _get_failed_attempts(username)
    return attempts >= threshold


def _get_lockout_remaining_time(username: str) -> int | None:
    """Retorna tempo restante de bloqueio em segundos, ou None se não bloqueado."""
    key = _get_lockout_key(username)
    ttl = cache.ttl(key) if hasattr(cache, "ttl") else None
    if ttl and ttl > 0:
        return ttl
    return None


def _invalid_credentials_response() -> Response:
    """
    Generic authentication failure response to prevent account enumeration.

    OWASP recommendation: never disclose whether username exists, password is wrong,
    or account is locked.
    """
    return Response({"error": "Credenciais inválidas."}, status=status.HTTP_400_BAD_REQUEST)


# Issue #135: CSRF token endpoint (SEC-P2)
@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf_token(request: Request) -> Response:
    """
    Retorna CSRF token para uso com CSRF_COOKIE_HTTPONLY=True.

    GET /api/csrf/

    Comportamento:
    - Define o cookie 'csrftoken' via @ensure_csrf_cookie (pode ser HttpOnly)
    - Retorna o token no body da resposta (acessível ao JavaScript)
    - Permite que frontend use o token mesmo com HttpOnly cookie

    Issue #135: Habilita CSRF_COOKIE_HTTPONLY=True (proteção XSS) sem quebrar frontend.

    Returns:
        200: {"csrfToken": "..."}
    """
    return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)


# Issue #133: Rate limiting para prevenir brute force (SEC-P1)
class LoginThrottle(AnonRateThrottle):
    """
    Rate limiting para endpoint de login: 10 tentativas por minuto por IP.

    Previne brute force attacks mantendo taxa aceitável para uso legítimo.
    """

    rate = "10/minute"
    # Usar escopo dedicado para evitar colisão com throttle anon global
    scope = "login"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])  # Issue #133: Rate limiting (10 req/min)
def login(request: Request) -> Response:
    """
    Endpoint de login com username/password.

    POST /api/auth/login/
    Body: {
        "username": "string",
        "password": "string"
    }

    Security:
    - Rate Limiting: 10 tentativas por minuto por IP (previne brute force)
    - Account Lockout: Bloqueia após 10 tentativas falhas por 15 minutos

    Returns:
        200: Login bem-sucedido com dados do usuário
        400: Falha de autenticação (resposta genérica)
        429: Too Many Requests (rate limit excedido)
    """
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "Username e password são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)

    # Security hardening #745:
    # - Keep a generic client response for all auth failures
    # - Preserve detailed reason only in AuditLog
    is_locked = _is_account_locked(username)

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Dummy hash to reduce timing differences between existing/non-existing users.
        make_password(password)

    if is_locked:
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)
        attempts = _get_failed_attempts(username)
        lockout_remaining_seconds = _get_lockout_remaining_time(username)

        # Log tentativa de login em conta bloqueada (detalhes só internamente)
        AuditLog.objects.create(
            usuario=None,
            action="LOGIN_BLOCKED",
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": _get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "reason": "account_locked",
                "attempts": attempts,
                "threshold": threshold,
                "lockout_remaining_seconds": lockout_remaining_seconds,
            },
        )

        return _invalid_credentials_response()

    if user is None:
        # Incrementa contador de tentativas falhas (estado interno)
        attempts = _increment_failed_attempts(username)
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)

        # Log tentativa falha
        AuditLog.objects.create(
            usuario=None,
            action="LOGIN_FAILED",
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": _get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "reason": "invalid_credentials",
                "attempts": attempts,
                "threshold": threshold,
            },
        )

        return _invalid_credentials_response()

    if not user.is_active:
        # Defensive fallback for alternate backends that might return inactive users.
        attempts = _increment_failed_attempts(username)
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)
        AuditLog.objects.create(
            usuario=None,
            action="LOGIN_FAILED",
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": _get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "reason": "inactive_user",
                "attempts": attempts,
                "threshold": threshold,
            },
        )
        return _invalid_credentials_response()

    # Login bem-sucedido: limpa contador de tentativas
    _clear_failed_attempts(username)

    # Realiza login
    django_login(request, user)

    # PA-05: Auditoria de login
    AuditLog.objects.create(
        usuario=user,
        action="LOGIN",
        model_name="Usuario",
        details={
            "ip_address": _get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
        },
    )

    # Retorna dados do usuário
    groups = list(user.groups.values_list("name", flat=True))

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "name": user.get_full_name() or user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_superuser": user.is_superuser,
            "is_staff": user.is_staff,
            "groups": groups,
            "is_superintendencia": user.is_superuser or "Superintendência" in groups,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request: Request) -> Response:
    """
    Endpoint de logout.

    POST /api/auth/logout/

    Returns:
        200: Logout bem-sucedido
    """
    # PA-05: Auditoria de logout
    AuditLog.objects.create(
        usuario=request.user,
        action="LOGOUT",
        model_name="Usuario",
        details={
            "ip_address": _get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
        },
    )

    django_logout(request)

    return Response({"message": "Logout realizado com sucesso."}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ping(request: Request) -> Response:
    """
    Endpoint para renovar sessão (keep-alive).

    POST /api/auth/ping/

    CP5 (Issue #164): Monitor de sessão - permite que frontend renove sessão
    antes da expiração (30 min desde CP2).

    Comportamento:
    - Apenas toca a sessão (request.session.modified = True)
    - SESSION_SAVE_EVERY_REQUEST=True já renova automaticamente
    - Retorna tempo restante da sessão (se disponível)

    Returns:
        200: {"message": "Session renewed", "session_age": 1800}
    """
    # Django com SESSION_SAVE_EVERY_REQUEST=True já renova a sessão
    # Basta acessar request.session para trigger o save
    request.session.modified = True

    # Retornar configuração de timeout (do settings)
    from django.conf import settings

    session_age = getattr(settings, "SESSION_COOKIE_AGE", 1800)

    return Response(
        {"message": "Session renewed", "session_age": session_age},  # Em segundos (default: 1800 = 30 min)
        status=status.HTTP_200_OK,
    )
