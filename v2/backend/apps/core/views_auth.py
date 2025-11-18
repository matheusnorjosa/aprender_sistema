"""
Views de Autenticação - AS v2

Endpoints:
- GET /api/csrf/ - Obter CSRF token (Issue #135)
- POST /api/auth/login/ - Login com username/password
- POST /api/auth/logout/ - Logout
- POST /api/auth/ping/ - Renovar sessão (CP5 - Issue #164)
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import AuditLog


# Issue #135: CSRF token endpoint (SEC-P2)
@ensure_csrf_cookie
@api_view(['GET'])
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
    return Response({
        'csrfToken': get_token(request)
    }, status=status.HTTP_200_OK)


# Issue #133: Rate limiting para prevenir brute force (SEC-P1)
class LoginThrottle(AnonRateThrottle):
    """
    Rate limiting para endpoint de login: 5 tentativas por minuto por IP.

    Previne brute force attacks mantendo taxa aceitável para uso legítimo.
    """
    rate = '5/minute'


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])  # Issue #133: Rate limiting (5 req/min)
def login(request: Request) -> Response:
    """
    Endpoint de login com username/password.

    POST /api/auth/login/
    Body: {
        "username": "string",
        "password": "string"
    }

    Rate Limiting: 5 tentativas por minuto por IP (previne brute force)

    Returns:
        200: Login bem-sucedido com dados do usuário
        400: Credenciais inválidas
        429: Too Many Requests (rate limit excedido)
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {'error': 'Username e password são obrigatórios.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = authenticate(request, username=username, password=password)

    if user is None:
        return Response(
            {'error': 'Credenciais inválidas.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not user.is_active:
        return Response(
            {'error': 'Usuário inativo.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Realiza login
    django_login(request, user)

    # PA-05: Auditoria de login
    AuditLog.objects.create(
        usuario=user,
        action='LOGIN',
        model_name='Usuario',
        details={
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
        }
    )

    # Retorna dados do usuário
    groups = list(user.groups.values_list('name', flat=True))

    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'name': user.get_full_name() or user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'groups': groups,
        'is_superintendencia': user.is_superuser or 'Superintendência' in groups,
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
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
        action='LOGOUT',
        model_name='Usuario',
        details={
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
        }
    )

    django_logout(request)

    return Response({
        'message': 'Logout realizado com sucesso.'
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
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
    session_age = getattr(settings, 'SESSION_COOKIE_AGE', 1800)

    return Response({
        'message': 'Session renewed',
        'session_age': session_age  # Em segundos (default: 1800 = 30 min)
    }, status=status.HTTP_200_OK)
