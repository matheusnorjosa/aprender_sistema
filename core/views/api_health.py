"""
API Health Check - Endpoint para React testar conexão
"""

from datetime import datetime

import django
from django.db import connection

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])  # Público para health check
def api_health_check(request):
    """
    Health check endpoint para frontend React.
    Retorna status da API e informações do sistema.
    """
    try:
        # Testar conexão com banco
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"

    return Response(
        {
            "status": "ok",
            "django_version": django.get_version(),
            "database": database_status,
            "timestamp": datetime.now().isoformat(),
            "message": "API Django funcionando corretamente",
        }
    )
