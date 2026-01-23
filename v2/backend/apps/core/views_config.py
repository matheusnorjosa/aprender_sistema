"""
Config API View — GET/PUT /api/config/

Issue #187: UI para Configurações do Sistema

Endpoints:
- GET /api/config/ - Retorna configurações consolidadas (flat dict)
- PUT /api/config/ - Atualiza configurações + AuditLog

Permissions:
- IsDAT | IsSuperintendencia (RBAC)

Cache:
- Invalidação automática via signal post_save (apps/core/signals.py)
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false

from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.models import AuditLog, Config
from apps.core.permissions import IsDAT, IsSuperintendencia
from apps.core.serializers import ConfigSerializer
from apps.core.services.config_service import bust_cfg, get_cfg


@api_view(["GET", "PUT"])
@permission_classes([IsDAT | IsSuperintendencia])
def config_view(request: Request) -> Response:
    """
    GET: Lê configurações consolidadas do Config model.
    PUT: Atualiza configurações + cria AuditLog.

    Permissions: IsDAT | IsSuperintendencia

    GET Response (200):
        {
            "TRAVEL_BUFFER_MINUTES": 120,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 8,
            ...
        }

    PUT Request:
        {
            "TRAVEL_BUFFER_MINUTES": 90,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 10,
            ...
        }

    PUT Response (200):
        {
            "TRAVEL_BUFFER_MINUTES": 90,
            "AVAILABILITY_DAILY_LIMIT_HOURS": 10,
            ...
        }

    PUT Response (400):
        {
            "TRAVEL_BUFFER_MINUTES": ["Ensure this value is greater than or equal to 0."],
            ...
        }
    """

    if request.method == "GET":
        # Ler de cada chave do Config model via get_cfg (cache-enabled)
        availability = get_cfg("availability", {})
        gcal_sync = get_cfg("gcal_sync", {})
        session_settings = get_cfg("session_settings", {})
        features = get_cfg("features", {})

        # Consolidar em um dict flat
        data = {
            # Availability
            "TRAVEL_BUFFER_MINUTES": availability.get("TRAVEL_BUFFER_MINUTES", 120),
            "AVAILABILITY_DAILY_LIMIT_HOURS": availability.get("AVAILABILITY_DAILY_LIMIT_HOURS", 8),
            "ALLOW_ADJACENT_EVENTS": availability.get("ALLOW_ADJACENT_EVENTS", True),
            "BLOCK_AUTO_APPROVE": availability.get("BLOCK_AUTO_APPROVE", True),
            # GCal
            "BATCH_SIZE": gcal_sync.get("BATCH_SIZE", 200),
            "LOCK_TTL_SECONDS": gcal_sync.get("LOCK_TTL_SECONDS", 300),
            "AUTO_RETRY_ON_ERROR": gcal_sync.get("AUTO_RETRY_ON_ERROR", True),
            "MAX_RETRIES": gcal_sync.get("MAX_RETRIES", 3),
            "SEND_UPDATES": gcal_sync.get("SEND_UPDATES", "none"),
            # Session
            "SESSION_COOKIE_AGE": session_settings.get("SESSION_COOKIE_AGE", 1800),
            "SESSION_WARNING_THRESHOLD": session_settings.get("SESSION_WARNING_THRESHOLD", 300),
            "AUTOCOMPLETE_DEBOUNCE_MS": session_settings.get("AUTOCOMPLETE_DEBOUNCE_MS", 300),
            # Features
            "ENABLE_MULTI_CALENDAR": features.get("ENABLE_MULTI_CALENDAR", False),
            "ENABLE_BATCH_ACTIONS": features.get("ENABLE_BATCH_ACTIONS", False),
            "ENABLE_ADVANCED_FILTERS": features.get("ENABLE_ADVANCED_FILTERS", False),
        }

        serializer = ConfigSerializer(data)
        return Response(serializer.data)

    elif request.method == "PUT":
        serializer = ConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        vd: dict[str, Any] = serializer.validated_data

        # Separar por categoria e salvar no Config model
        Config.objects.update_or_create(
            key="availability",
            defaults={
                "value": {
                    "TRAVEL_BUFFER_MINUTES": vd["TRAVEL_BUFFER_MINUTES"],
                    "AVAILABILITY_DAILY_LIMIT_HOURS": vd["AVAILABILITY_DAILY_LIMIT_HOURS"],
                    "ALLOW_ADJACENT_EVENTS": vd["ALLOW_ADJACENT_EVENTS"],
                    "BLOCK_AUTO_APPROVE": vd["BLOCK_AUTO_APPROVE"],
                },
                "effective_at": timezone.now(),
            },
        )

        Config.objects.update_or_create(
            key="gcal_sync",
            defaults={
                "value": {
                    "BATCH_SIZE": vd["BATCH_SIZE"],
                    "LOCK_TTL_SECONDS": vd["LOCK_TTL_SECONDS"],
                    "AUTO_RETRY_ON_ERROR": vd["AUTO_RETRY_ON_ERROR"],
                    "MAX_RETRIES": vd["MAX_RETRIES"],
                    "SEND_UPDATES": vd["SEND_UPDATES"],
                },
                "effective_at": timezone.now(),
            },
        )

        Config.objects.update_or_create(
            key="session_settings",
            defaults={
                "value": {
                    "SESSION_COOKIE_AGE": vd["SESSION_COOKIE_AGE"],
                    "SESSION_WARNING_THRESHOLD": vd["SESSION_WARNING_THRESHOLD"],
                    "AUTOCOMPLETE_DEBOUNCE_MS": vd["AUTOCOMPLETE_DEBOUNCE_MS"],
                },
                "effective_at": timezone.now(),
            },
        )

        Config.objects.update_or_create(
            key="features",
            defaults={
                "value": {
                    "ENABLE_MULTI_CALENDAR": vd["ENABLE_MULTI_CALENDAR"],
                    "ENABLE_BATCH_ACTIONS": vd["ENABLE_BATCH_ACTIONS"],
                    "ENABLE_ADVANCED_FILTERS": vd["ENABLE_ADVANCED_FILTERS"],
                },
                "effective_at": timezone.now(),
            },
        )

        # AuditLog (Issue #187 requirement)
        AuditLog.objects.create(
            usuario=request.user,
            action="UPDATE_CONFIG",
            model_name="Config",
            details={
                "changed_fields": list(vd.keys()),
                "ip_address": request.META.get("REMOTE_ADDR", "unknown"),
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:200],
            },
        )

        # Invalidar cache (automático via signal, mas garantir)
        for key in ["availability", "gcal_sync", "session_settings", "features"]:
            bust_cfg(key)

        return Response(serializer.data, status=status.HTTP_200_OK)

    # Should never reach here due to @api_view decorator
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
