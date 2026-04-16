"""
URL configuration for AS v2 project.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportReturnType=false

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path

from apps.core.admin_site import admin_site  # Custom admin site (superusers only)


def _metrics_gate(request: HttpRequest) -> HttpResponse:
    """SEC-RECON-02: Proxy to django_prometheus only for staff or internal IPs."""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    if "," in ip:
        ip = ip.split(",")[0].strip()
    is_internal = ip.startswith(("127.", "10.", "172.", "192.168.", "::1"))
    is_staff = hasattr(request, "user") and request.user.is_authenticated and request.user.is_staff  # type: ignore[union-attr]

    if not is_internal and not is_staff:
        return JsonResponse({"error": "Forbidden"}, status=403)

    from django_prometheus.exports import ExportToDjangoView

    return ExportToDjangoView(request)


def healthz(request: HttpRequest) -> JsonResponse:
    """Health check endpoint for Docker/K8s — minimal payload (no sensitive data)."""
    return JsonResponse({"status": "ok"})


def healthz_detailed(request: HttpRequest) -> JsonResponse:
    """
    Detailed health check for monitoring — requires superuser or internal IP.

    Checks database, Redis cache, and GCal circuit breaker status.
    """
    # SEC-RECON-01: restrict to superuser or internal network
    ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", ""))
    if "," in ip:
        ip = ip.split(",")[0].strip()
    is_internal = ip.startswith(("127.", "10.", "172.", "192.168.", "::1"))
    is_superuser = hasattr(request, "user") and request.user.is_authenticated and request.user.is_superuser  # type: ignore[union-attr]

    if not is_internal and not is_superuser:
        return JsonResponse({"error": "Forbidden"}, status=403)

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

    return JsonResponse({"status": status, "checks": checks})


urlpatterns = [
    # Admin (Custom - Superusers only, Fase 1 Plano DAT/GCal)
    path("admin/", admin_site.urls),
    # Health check
    path("healthz/", healthz, name="healthz"),
    path("healthz/detailed/", healthz_detailed, name="healthz_detailed"),
    # Prometheus metrics (MP1) — SEC-RECON-02: protected by staff_member_required
    path("metrics", _metrics_gate, name="prometheus-metrics"),
    # API canonical: /api/* (#792)
    path("api/", include("apps.core.urls")),
    # DEPRECATED alias — will be removed after deprecation window (#797)
    path("api/v1/", include("apps.core.urls", namespace="core-v1")),
]

# Incluir URLs do ETL apenas se o app estiver instalado (INCLUDE_ETL=true)
if "apps.dat_ingest" in settings.INSTALLED_APPS:
    # DEPRECATED alias — will be removed after deprecation window (#797)
    urlpatterns.append(
        path("api/v1/", include("apps.dat_ingest.urls", namespace="dat-v1")),
    )
    # API canonical: /api/*
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
