"""
URL configuration for AS v2 project.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportReturnType=false

from __future__ import annotations

import ipaddress
import logging
from typing import Any

from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.urls import include, path

from apps.core.admin_site import admin_site  # Custom admin site (superusers only)
from apps.core.utils.net import get_client_ip

logger = logging.getLogger(__name__)


def _is_internal_ip(ip: str) -> bool:
    """True only for RFC1918 / loopback addresses.

    Uses ``ipaddress`` instead of a ``str.startswith`` prefix match: the old
    check accepted spoofable strings such as ``"10.evil"`` and treated the whole
    ``172.0.0.0/8`` as internal instead of just ``172.16.0.0/12``.
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_private or addr.is_loopback


def _metrics_gate(request: HttpRequest) -> HttpResponse:
    """SEC-RECON-02: Proxy to django_prometheus only for staff or internal IPs."""
    # SEC/#1660: resolve the client behind NUM_PROXIES trusted hops instead of
    # trusting the first (client-controlled) X-Forwarded-For entry. A forged
    # "X-Forwarded-For: 127.0.0.1" is pushed left by the trusted proxies and
    # never selected, so it can no longer fake an internal origin.
    is_internal = _is_internal_ip(get_client_ip(request))
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
    # SEC-RECON-01 / #1660: restrict to superuser or internal network, resolving
    # the real client behind NUM_PROXIES trusted proxies. A forged
    # X-Forwarded-For can no longer fake an internal IP.
    is_internal = _is_internal_ip(get_client_ip(request))
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
    except Exception:
        logger.exception("healthz_detailed: falha no check de banco")
        checks["database"] = "error"

    # Redis cache check
    try:
        cache.set("health_check_key", "ok", 1)
        result = cache.get("health_check_key")
        checks["redis"] = "ok" if result == "ok" else "fail"
    except Exception:
        logger.exception("healthz_detailed: falha no check de redis")
        checks["redis"] = "error"

    # GCal circuit breaker check
    try:
        from apps.core.services.gcal.circuit_breaker import get_circuit_state

        checks["gcal_circuit"] = get_circuit_state()
    except ImportError:
        checks["gcal_circuit"] = "not_configured"
    except Exception:
        logger.exception("healthz_detailed: falha no check do circuit breaker do GCal")
        checks["gcal_circuit"] = "error"

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
