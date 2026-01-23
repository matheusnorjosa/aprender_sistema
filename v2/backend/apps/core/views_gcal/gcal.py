"""
AS v2 — GCal Core Views

Views for GCal basic operations: list calendars, health check.
Type-checked with Pyright (strict mode).
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportUntypedFunctionDecorator=false, reportMissingTypeStubs=false

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.exceptions import ServiceUnavailableError
from apps.core.services.gcal_client_factory import get_gcal_client_and_calendar_id

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def gcal_calendars(request: Request) -> Response:
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
def gcal_health(request: Request) -> Response:
    """
    GET /api/gcal/health/

    Health check da integração com Google Calendar.

    Autenticação: Obrigatória
    Permissões: Qualquer usuário autenticado

    Returns:
        200: Service healthy
        503: Service unavailable (unhealthy or error)

    Response format:
        {
            "status": "healthy"|"unhealthy",
            "client_type": "fake"|"google",
            "details": "..."
        }
    """
    try:
        client, _ = get_gcal_client_and_calendar_id()
        health_status = client.health_check()

        # Return 503 if unhealthy, 200 if healthy
        if health_status.get("status") == "unhealthy":
            raise ServiceUnavailableError(
                service="Google Calendar",
                details=health_status.get("details", "Service unhealthy"),
            )

        return Response(health_status, status=status.HTTP_200_OK)

    except ServiceUnavailableError:
        raise  # Re-raise for custom exception handler
    except Exception as e:
        logger.error(f"Error checking GCal health: {e}", exc_info=True)
        raise ServiceUnavailableError(
            service="Google Calendar",
            details=str(e),
        )
