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
# Account Lockout (Security Audit 2025-01, SEC-AUTH-01)
# ================================================================
# Two-level lockout:
# 1. Per IP+username (threshold=10, 15min) — prevents single-source brute force
# 2. Global per username (threshold=50, 30min) — prevents distributed credential stuffing

_GLOBAL_LOCKOUT_THRESHOLD = 50
_GLOBAL_LOCKOUT_DURATION = 1800  # 30 minutes


def _get_lockout_key(username: str, ip: str = "") -> str:
    """Gera chave Redis para tracking de tentativas de login por IP+username."""
    if ip:
        return f"login_attempts:{username.lower()}:{ip}"
    return f"login_attempts_global:{username.lower()}"


def _get_failed_attempts(username: str, ip: str = "") -> int:
    """Retorna número de tentativas falhas de login."""
    key = _get_lockout_key(username, ip)
    attempts = cache.get(key)
    return int(attempts) if attempts else 0


def _increment_failed_attempts(username: str, ip: str) -> int:
    """
    Incrementa contadores de tentativas falhas (IP-specific e global).
    Retorna o novo total de tentativas IP-specific.
    """
    lockout_duration = getattr(settings, "ACCOUNT_LOCKOUT_DURATION", 900)

    # Increment IP-specific counter
    ip_key = _get_lockout_key(username, ip)
    ip_attempts = _safe_increment(ip_key, lockout_duration)

    # Increment global counter
    global_key = _get_lockout_key(username)
    _safe_increment(global_key, _GLOBAL_LOCKOUT_DURATION)

    return ip_attempts


def _safe_increment(key: str, timeout: int) -> int:
    """Safely increment a Redis counter with TTL."""
    try:
        current = cache.get(key)
        if current is None:
            cache.set(key, 1, timeout=timeout)
            return 1
        new_value = int(current) + 1
        cache.set(key, new_value, timeout=timeout)
        return new_value
    except Exception:
        return 1


def _clear_failed_attempts(username: str, ip: str) -> None:
    """Limpa contadores de tentativas após login bem-sucedido."""
    cache.delete(_get_lockout_key(username, ip))
    cache.delete(_get_lockout_key(username))


def _is_account_locked(username: str, ip: str) -> bool:
    """Verifica se a conta está bloqueada (IP-specific OU global)."""
    threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)

    # Check IP-specific lockout
    if _get_failed_attempts(username, ip) >= threshold:
        return True

    # Check global lockout (distributed attack protection)
    if _get_failed_attempts(username) >= _GLOBAL_LOCKOUT_THRESHOLD:
        return True

    return False


def _get_lockout_remaining_time(username: str, ip: str) -> int | None:
    """Retorna tempo restante de bloqueio em segundos, ou None se não bloqueado."""
    # Check IP-specific first, then global
    for key in [_get_lockout_key(username, ip), _get_lockout_key(username)]:
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
    Rate limiting para endpoint de login — configurado por ambiente.

    Em **produção**: 10 tentativas/minuto por IP (brute-force protection).
    Em **dev/staging**: relaxado para não bloquear testes E2E multi-role
    e fluxos de desenvolvimento manual (12+ logins em sequência).

    A taxa é lida de `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"]`
    em `config/settings.py` — `10/minute` por padrão, sobrescrito para
    `1000/minute` quando `ENVIRONMENT=development`.
    """

    # Escopo dedicado — DRF resolve a taxa via DEFAULT_THROTTLE_RATES[scope].
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

    # SEC-AUTH-01: compound lockout key (IP + username)
    client_ip = _get_client_ip(request)

    # Security hardening #745:
    # - Keep a generic client response for all auth failures
    # - Preserve detailed reason only in AuditLog
    is_locked = _is_account_locked(username, client_ip)

    user = authenticate(request, username=username, password=password)
    if user is None:
        # Dummy hash to reduce timing differences between existing/non-existing users.
        make_password(password)

    if is_locked:
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)
        attempts = _get_failed_attempts(username, client_ip)
        lockout_remaining_seconds = _get_lockout_remaining_time(username, client_ip)

        # Log tentativa de login em conta bloqueada (detalhes só internamente)
        AuditLog.objects.create(
            usuario=None,
            action=AuditLog.Action.LOGIN_BLOCKED,
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": client_ip,
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
        attempts = _increment_failed_attempts(username, client_ip)
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)

        # Log tentativa falha
        AuditLog.objects.create(
            usuario=None,
            action=AuditLog.Action.LOGIN_FAILED,
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "reason": "invalid_credentials",
                "attempts": attempts,
                "threshold": threshold,
            },
        )

        return _invalid_credentials_response()

    if not user.is_active:
        # Defensive fallback for alternate backends that might return inactive users.
        attempts = _increment_failed_attempts(username, client_ip)
        threshold = getattr(settings, "ACCOUNT_LOCKOUT_THRESHOLD", 10)
        AuditLog.objects.create(
            usuario=None,
            action=AuditLog.Action.LOGIN_FAILED,
            model_name="Usuario",
            details={
                "username": username,
                "ip_address": client_ip,
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
                "reason": "inactive_user",
                "attempts": attempts,
                "threshold": threshold,
            },
        )
        return _invalid_credentials_response()

    # Login bem-sucedido: limpa contadores de tentativas (IP-specific e global)
    _clear_failed_attempts(username, client_ip)

    # Realiza login
    django_login(request, user)

    # PA-05: Auditoria de login
    AuditLog.objects.create(
        usuario=user,
        action=AuditLog.Action.LOGIN,
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
        action=AuditLog.Action.LOGOUT,
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
