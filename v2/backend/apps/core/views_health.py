"""
Health Check and Features Views
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportAttributeAccessIssue=false, reportReturnType=false, reportArgumentType=false, reportUntypedBaseClass=false, reportMissingTypeArgument=false

from __future__ import annotations
from typing import Any
from django.db.models import QuerySet
from rest_framework.request import Request
from rest_framework.response import Response

import os

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def readyz(request: Request) -> Response:
    """
    Health check: DB + Redis.

    Returns 200 OK if database is responsive.
    Returns 503 Service Unavailable if database check fails.
    Cache failures are warnings only (don't cause 503).

    GET /api/readyz/

    Response format:
    {
        "status": "healthy" | "unhealthy",
        "checks": {
            "database": "ok" | "error: <message>",
            "cache": "ok" | "warning: <message>"
        }
    }
    """
    checks = {}

    # Database check (critical - causes 503 if fails)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                checks["database"] = "ok"
            else:
                checks["database"] = "error: unexpected result"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Redis/Cache check (optional - warnings only)
    try:
        cache.set("_healthcheck", "ok", 10)
        result = cache.get("_healthcheck")
        if result == "ok":
            checks["cache"] = "ok"
        else:
            checks["cache"] = "warning: set/get failed"
    except Exception as e:
        checks["cache"] = f"warning: {str(e)}"

    # Only database failures cause unhealthy status
    db_ok = checks["database"] == "ok"
    status_code = 200 if db_ok else 503
    status = "healthy" if db_ok else "unhealthy"

    return JsonResponse({
        "status": status,
        "checks": checks
    }, status=status_code)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def features(request: Request) -> Response:
    """
    Returns feature flags and environment configuration.

    Requires authentication for security.

    GET /api/features/

    Response example:
    {
        "USE_V2_ONLY": true,
        "GCAL_MODE": "fake",
        "PREVIEW_ONLY": true,
        "METRICS_ENABLED": true,
        "SHOW_PRE_AGENDA": true,
        "GCAL_CLIENT": "fake",
        "apply_blocked": true,
        "ENVIRONMENT": "development",
        "realtime_check_enabled": false
    }

    Security:
    - Requires authentication (returns 403 if not authenticated)
    - apply_blocked is true when GCAL_CLIENT != "google" to prevent accidental calendar operations
    - PREVIEW_ONLY=True blocks write operations in UI

    Config overrides:
    - Values in Config(key="features") override environment variables
    """
    from django.conf import settings as django_settings

    # Environment configuration (defaults)
    gcal_client = getattr(django_settings, "GCAL_CLIENT", "fake")
    gcal_mode = os.getenv("GCAL_MODE", gcal_client)  # GCAL_MODE defaults to GCAL_CLIENT
    environment = os.getenv("ENVIRONMENT", "development")

    # Feature flags (safe defaults for go-live)
    use_v2_only = os.getenv("USE_V2_ONLY", "1") == "1"  # Default true
    preview_only = os.getenv("PREVIEW_ONLY", "1") == "1"  # Default true (blocks writes)
    metrics_enabled = os.getenv("METRICS_ENABLED", "1") == "1"  # Default true
    show_pre_agenda = os.getenv("SHOW_PRE_AGENDA", "1") == "1"  # Default true
    realtime_check_enabled = os.getenv("REALTIME_CHECK_ENABLED", "0") == "1"  # Default false (manual flow via Grade Mensal)

    # Check for Config overrides from database
    try:
        from apps.core.models import Config
        config = Config.objects.filter(key="features").first()
        if config and isinstance(config.value, dict):
            # Override with Config values
            gcal_mode = config.value.get("GCAL_MODE", gcal_mode)
            preview_only = config.value.get("PREVIEW_ONLY", preview_only)
            use_v2_only = config.value.get("USE_V2_ONLY", use_v2_only)
            metrics_enabled = config.value.get("METRICS_ENABLED", metrics_enabled)
            show_pre_agenda = config.value.get("SHOW_PRE_AGENDA", show_pre_agenda)
            realtime_check_enabled = config.value.get("REALTIME_CHECK_ENABLED", realtime_check_enabled)
    except Exception:
        # If Config model doesn't exist or query fails, just use env vars
        pass

    # Security: block apply operations when not using real Google Calendar client
    apply_blocked = gcal_client != "google"

    # Auto-apply GCal (Celery task preview_then_apply_gcal) - Fase 3
    # Default: False (desativado) - governança consolidada via /pre-agenda
    # Usar settings efetivo (runtime) ao invés de os.getenv direto
    from django.conf import settings as django_settings
    auto_apply_enabled = getattr(django_settings, "FEATURE_AUTO_APPLY_ENABLED", False)

    # Check for Config overrides for auto_apply_enabled
    try:
        from apps.core.models import Config
        config = Config.objects.filter(key="features").first()
        if config and isinstance(config.value, dict):
            auto_apply_enabled = config.value.get("auto_apply_enabled", auto_apply_enabled)
    except Exception:
        pass

    return Response({
        "USE_V2_ONLY": use_v2_only,
        "GCAL_MODE": gcal_mode,
        "PREVIEW_ONLY": preview_only,
        "METRICS_ENABLED": metrics_enabled,
        "SHOW_PRE_AGENDA": show_pre_agenda,
        "GCAL_CLIENT": gcal_client,
        "apply_blocked": apply_blocked,
        "auto_apply_enabled": auto_apply_enabled,
        "ENVIRONMENT": environment,
        "realtime_check_enabled": realtime_check_enabled,
    })
