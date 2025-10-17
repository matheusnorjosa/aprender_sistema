"""
Health Check and Features Views
"""

import os

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse


def readyz(request):
    """
    Health check: DB + Redis.

    Returns 200 OK if both DB and Redis are responsive.
    Returns 503 Service Unavailable if any check fails.

    GET /api/readyz/
    """
    checks = {}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = str(e)

    # Redis/Cache check
    try:
        cache.set("_healthcheck", "ok", 10)
        checks["redis"] = "ok" if cache.get("_healthcheck") == "ok" else "fail"
    except Exception as e:
        checks["redis"] = str(e)

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JsonResponse(checks, status=status_code)


def features(request):
    """
    Returns feature flags and environment configuration.

    GET /api/features/

    Response example:
    {
        "GCAL_CLIENT": "fake",
        "apply_blocked": true,
        "ENVIRONMENT": "staging"
    }
    """
    gcal_client = os.getenv("GCAL_CLIENT", "fake")
    preview_only = os.getenv("PREVIEW_ONLY", "false").lower() == "true"
    environment = os.getenv("ENVIRONMENT", "dev")

    return JsonResponse({
        "GCAL_CLIENT": gcal_client,
        "apply_blocked": preview_only,
        "ENVIRONMENT": environment,
    })
