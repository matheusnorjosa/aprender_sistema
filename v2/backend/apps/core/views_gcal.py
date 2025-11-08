"""
Views para endpoints GCal (Sprint 2 - Issue #65)

Endpoints:
- GET /api/gcal/calendars/ - Lista calendários disponíveis
- GET /api/gcal/health/ - Health check da integração GCal
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gcal_calendars(request):
    """
    GET /api/gcal/calendars/

    Lista calendários disponíveis.

    Autenticação: Obrigatória
    Permissões: Qualquer usuário autenticado

    Returns:
        200: Lista de calendários
        [
            {"id": "primary", "summary": "...", "primary": true},
            ...
        ]
    """
    try:
        client, _ = get_gcal_client_and_calendar_id()
        calendars = client.list_calendars()

        return Response(calendars, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error listing calendars: {e}", exc_info=True)
        return Response(
            {"error": "Failed to list calendars", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gcal_health(request):
    """
    GET /api/gcal/health/

    Health check da integração com Google Calendar.

    Autenticação: Obrigatória
    Permissões: Qualquer usuário autenticado

    Returns:
        200: Health check bem-sucedido
        {
            "status": "healthy"|"unhealthy",
            "client_type": "fake"|"google",
            "details": "..."
        }
    """
    try:
        client, _ = get_gcal_client_and_calendar_id()
        health_status = client.health_check()

        # Retornar 200 sempre (health status está no body)
        return Response(health_status, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error checking GCal health: {e}", exc_info=True)
        return Response(
            {
                "status": "unhealthy",
                "client_type": "unknown",
                "details": f"Error: {str(e)}",
            },
            status=status.HTTP_200_OK,  # 200 mesmo com erro (status no body)
        )
