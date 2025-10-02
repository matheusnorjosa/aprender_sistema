"""
API Health Check View

Endpoint para healthcheck do Docker Compose.
Verifica conectividade com PostgreSQL e Redis.
"""

from django.db import connections
from django.http import JsonResponse

from django_redis import get_redis_connection


def api_health(request):
    """
    Healthcheck endpoint para Docker.

    Retorna:
        200 OK: {"ok": true, "db": true, "redis": true}
        503 Service Unavailable: {"ok": false, "db": false/true, "redis": false/true}
    """
    db_ok = True
    redis_ok = True

    # Check PostgreSQL
    try:
        with connections["default"].cursor() as cur:
            cur.execute("SELECT 1;")
    except Exception:
        db_ok = False

    # Check Redis
    try:
        get_redis_connection("default").ping()
    except Exception:
        redis_ok = False

    overall = db_ok and redis_ok
    return JsonResponse(
        {"ok": overall, "db": db_ok, "redis": redis_ok},
        status=200 if overall else 503,
    )


def api_root(request):
    """
    API Root endpoint.

    Retorna informações sobre a API e links para os principais endpoints.
    """
    return JsonResponse({
        "message": "Aprender Sistema API",
        "version": "v1",
        "endpoints": {
            "health": "/api/health/",
            "api_v1": "/api/v1/",
            "usuarios": "/api/v1/usuarios/",
            "projetos": "/api/v1/projetos/",
            "municipios": "/api/v1/municipios/",
            "tipos-evento": "/api/v1/tipos-evento/",
            "formadores": "/api/v1/formadores/",
            "solicitacoes": "/api/v1/solicitacoes/",
            "aprovacoes": "/api/v1/aprovacoes/",
            "eventos-google": "/api/v1/eventos-google/",
            "disponibilidade": "/api/v1/disponibilidade/",
            "logs-auditoria": "/api/v1/logs-auditoria/",
            "estatisticas": "/api/v1/estatisticas/",
        },
        "auth": {
            "token": "/api/auth/token/",
            "login": "/api/auth/login/",
        }
    })
