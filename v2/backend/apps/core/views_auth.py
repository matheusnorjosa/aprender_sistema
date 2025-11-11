"""
Views de Autenticação - AS v2

Endpoints:
- POST /api/auth/login/ - Login com username/password
- POST /api/auth/logout/ - Logout
"""

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AuditLog


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    """
    Endpoint de login com username/password.

    POST /api/auth/login/
    Body: {
        "username": "string",
        "password": "string"
    }

    Returns:
        200: Login bem-sucedido com dados do usuário
        400: Credenciais inválidas
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
