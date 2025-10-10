"""
Endpoint público de healthcheck para Docker/K8s.

App: core
Stack: Python 3.13 | Django 5.2
TZ: America/Fortaleza

Este endpoint é público (sem autenticação) e usado para
healthchecks de containers Docker/Kubernetes.
"""

from django.db import connections
from django.http import JsonResponse


def healthz(_request):
    """
    Health check endpoint público.

    Verifica:
        - Conexão com banco de dados PostgreSQL

    Returns:
        JSON: {"status": "ok", "db": "ok"} - 200 OK
        JSON: {"status": "error", "db": "<erro>"} - 500 Internal Server Error
    """
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1;")
        return JsonResponse({"status": "ok", "db": "ok"})
    except Exception as e:
        return JsonResponse({"status": "error", "db": str(e)}, status=500)
