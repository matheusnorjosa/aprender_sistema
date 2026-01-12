"""
URL configuration for AS v2 project.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpRequest, JsonResponse
from django.urls import include, path

from apps.core.admin_site import admin_site  # Custom admin site (superusers only)


def healthz(request: HttpRequest) -> JsonResponse:
    """Health check endpoint for Docker/K8s"""
    return JsonResponse(
        {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "debug": settings.DEBUG,
            "timezone": settings.TIME_ZONE,
        }
    )


def healthz_detailed(request: HttpRequest) -> JsonResponse:
    """
    Detailed health check for monitoring (Gap 7 - PLAN_maturity_gaps.md).

    Checks database, Redis cache, and GCal circuit breaker status.
    Use this endpoint for comprehensive health monitoring.
    """
    from django.core.cache import cache
    from django.db import connection

    checks: dict[str, Any] = {}

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    # Redis cache check
    try:
        cache.set("health_check_key", "ok", 1)
        result = cache.get("health_check_key")
        checks["redis"] = "ok" if result == "ok" else "fail"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"

    # GCal circuit breaker check
    try:
        from apps.core.services.gcal.circuit_breaker import get_circuit_state
        checks["gcal_circuit"] = get_circuit_state()
    except ImportError:
        checks["gcal_circuit"] = "not_configured"
    except Exception as e:
        checks["gcal_circuit"] = f"error: {str(e)[:100]}"

    # Determine overall status
    core_checks = [checks.get("database"), checks.get("redis")]
    if all(c == "ok" for c in core_checks):
        status = "ok"
    elif any(c and c.startswith("error") for c in core_checks):
        status = "unhealthy"
    else:
        status = "degraded"

    return JsonResponse({
        "status": status,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    })


urlpatterns = [
    # Admin (Custom - Superusers only, Fase 1 Plano DAT/GCal)
    path("admin/", admin_site.urls),
    # Health check
    path("healthz/", healthz, name="healthz"),
    path("healthz/detailed/", healthz_detailed, name="healthz_detailed"),
    # Prometheus metrics (MP1) - django_prometheus.urls defines 'metrics' internally
    path("", include("django_prometheus.urls")),
    # API
    path("api/", include("apps.core.urls")),
]

# Incluir URLs do ETL apenas se o app estiver instalado (INCLUDE_ETL=true)
if "apps.dat_ingest" in settings.INSTALLED_APPS:
    urlpatterns.append(
        path("api/", include("apps.dat_ingest.urls")),  # Fase 5: ETL Observability
    )

# Static/Media files (development only)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Debug Toolbar (DEBUG mode only)
if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns.insert(0, path("__debug__/", include(debug_toolbar.urls)))

# Django Silk (Staging profiler)
if settings.ENVIRONMENT == "staging" and "silk" in settings.INSTALLED_APPS:
    urlpatterns.append(path("silk/", include("silk.urls", namespace="silk")))
