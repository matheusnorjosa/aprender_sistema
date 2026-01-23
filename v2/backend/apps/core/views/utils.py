"""
AS v2 — Core Views Utilities

Helper functions and API root endpoint.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false

from __future__ import annotations

from django.http import HttpRequest, JsonResponse


def _get_client_ip(request: HttpRequest) -> str:
    """
    Extrai o IP real do cliente, considerando proxies reversos.

    Prioridade:
    1. HTTP_X_FORWARDED_FOR (primeiro IP da lista)
    2. HTTP_X_REAL_IP
    3. REMOTE_ADDR

    Returns:
        str: IP do cliente
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # X-Forwarded-For pode conter múltiplos IPs: "client, proxy1, proxy2"
        # O primeiro é o IP real do cliente
        return x_forwarded_for.split(",")[0].strip()

    x_real_ip = request.META.get("HTTP_X_REAL_IP")
    if x_real_ip:
        return x_real_ip.strip()

    return request.META.get("REMOTE_ADDR", "unknown")


def api_root(request: HttpRequest) -> JsonResponse:
    """API root endpoint"""
    return JsonResponse(
        {
            "message": "AS v2 API",
            "version": "2.0.0",
            "endpoints": {
                "admin": "/admin/",
                "healthz": "/healthz/",
                "api": "/api/",
            },
        }
    )
