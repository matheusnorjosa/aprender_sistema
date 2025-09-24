"""
API Views for Health Checking
============================

Views de API REST para health checks e monitoramento do sistema,
documentadas com OpenAPI/Swagger.

Author: Claude Code
Date: Janeiro 2025
"""

try:
    from rest_framework.views import APIView
    from rest_framework.response import Response
    from rest_framework import status
    from rest_framework.permissions import IsAuthenticated, IsAdminUser
    from drf_spectacular.utils import extend_schema, OpenApiExample
    from drf_spectacular.openapi import OpenApiTypes
    from ..serializers import (
        HealthCheckSerializer,
        SystemMetricsSerializer,
        ApplicationMetricsSerializer
    )
    from ..views.health_views import (
        health_check as health_check_function,
        detailed_health as detailed_health_function
    )
    from django.http import JsonResponse
    import json

    class HealthCheckAPIView(APIView):
        """
        API endpoint para health check básico do sistema

        Retorna informações sobre o status geral do sistema,
        incluindo checks de database, cache e integrações externas.
        """

        permission_classes = []  # Endpoint público

        @extend_schema(
            summary="Health Check Básico",
            description="""
            Verifica o status básico do sistema, incluindo:
            - Conectividade com database
            - Status do cache
            - Integrações externas (Google Calendar)
            - Status do filesystem

            Este endpoint é público e pode ser usado por sistemas
            de monitoramento externos.
            """,
            responses={
                200: HealthCheckSerializer,
                503: HealthCheckSerializer,
            },
            examples=[
                OpenApiExample(
                    "Sistema Saudável",
                    summary="Resposta quando sistema está funcionando",
                    description="Exemplo de resposta com todos os checks passando",
                    value={
                        "status": "healthy",
                        "timestamp": "2025-09-20T21:30:00.000Z",
                        "environment": "staging",
                        "checks": {
                            "database": {"status": "healthy", "response_time_ms": 5},
                            "cache": {"status": "healthy"},
                            "filesystem": {"status": "healthy"},
                            "google_calendar": {"status": "warning", "error": "API not configured"}
                        }
                    },
                    response_only=True,
                    status_codes=["200"]
                ),
                OpenApiExample(
                    "Sistema com Problemas",
                    summary="Resposta quando há falhas críticas",
                    description="Exemplo de resposta com falhas no sistema",
                    value={
                        "status": "unhealthy",
                        "timestamp": "2025-09-20T21:30:00.000Z",
                        "environment": "staging",
                        "checks": {
                            "database": {"status": "unhealthy", "error": "Connection refused"},
                            "cache": {"status": "healthy"},
                            "filesystem": {"status": "healthy"}
                        }
                    },
                    response_only=True,
                    status_codes=["503"]
                )
            ],
            tags=["Health"]
        )
        def get(self, request):
            """Executar health check básico"""
            # Usar a função existente mas adaptar para API
            mock_request = type('MockRequest', (), {
                'user': request.user,
                'META': request.META
            })()

            response = health_check_function(mock_request)
            data = json.loads(response.content.decode())

            # Determinar status code baseado no resultado
            status_code = status.HTTP_200_OK
            if data.get('status') == 'unhealthy':
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE

            return Response(data, status=status_code)

    class DetailedHealthAPIView(APIView):
        """
        API endpoint para health check detalhado

        Retorna métricas detalhadas do sistema incluindo CPU,
        memória, métricas de aplicação e database.

        Requer autenticação de usuário administrativo.
        """

        permission_classes = [IsAuthenticated, IsAdminUser]

        @extend_schema(
            summary="Health Check Detalhado",
            description="""
            Retorna informações detalhadas sobre o sistema, incluindo:
            - Métricas de sistema (CPU, memória, disco)
            - Métricas de aplicação (usuários, solicitações, etc.)
            - Métricas de database (conexões ativas, queries)

            **Requer autenticação de administrador.**
            """,
            responses={
                200: OpenApiTypes.OBJECT,
                401: OpenApiTypes.OBJECT,
                403: OpenApiTypes.OBJECT,
            },
            examples=[
                OpenApiExample(
                    "Métricas Detalhadas",
                    summary="Resposta com métricas completas do sistema",
                    value={
                        "timestamp": "2025-09-20T21:30:00.000Z",
                        "environment": "staging",
                        "system_metrics": {
                            "cpu_percent": 25.5,
                            "memory_percent": 67.2,
                            "disk_usage_percent": 45.0,
                            "load_average": [1.2, 1.5, 1.8]
                        },
                        "application_metrics": {
                            "total_users": 193,
                            "active_users": 162,
                            "total_solicitacoes": 2067,
                            "solicitacoes_pendentes": 1921,
                            "recent_audit_logs": 45,
                            "weekly_stats": {
                                "new_solicitacoes": 25,
                                "approved_solicitacoes": 18
                            }
                        },
                        "database_metrics": {
                            "default": {
                                "active_connections": 8,
                                "active_queries": 2
                            }
                        }
                    },
                    response_only=True,
                    status_codes=["200"]
                )
            ],
            tags=["Health"]
        )
        def get(self, request):
            """Executar health check detalhado"""
            # Usar a função existente mas adaptar para API
            response = detailed_health_function(request)

            if response.status_code == 401:
                return Response(
                    {"error": "Authentication required"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            data = json.loads(response.content.decode())
            return Response(data, status=status.HTTP_200_OK)

    class ReadinessAPIView(APIView):
        """
        API endpoint para readiness check

        Usado por orquestradores como Kubernetes para verificar
        se a aplicação está pronta para receber tráfego.
        """

        permission_classes = []  # Endpoint público

        @extend_schema(
            summary="Readiness Check",
            description="""
            Verifica se a aplicação está pronta para receber tráfego.

            Diferente do liveness check, verifica dependências externas como:
            - Database acessível
            - Migrations aplicadas
            - Configurações necessárias

            Usado por sistemas de orquestração como Kubernetes.
            """,
            responses={
                200: OpenApiTypes.OBJECT,
                503: OpenApiTypes.OBJECT,
            },
            examples=[
                OpenApiExample(
                    "Sistema Pronto",
                    value={
                        "ready": True,
                        "checks": [
                            {"name": "database", "status": "ready"},
                            {"name": "migrations", "status": "ready"}
                        ],
                        "timestamp": "2025-09-20T21:30:00.000Z"
                    },
                    response_only=True,
                    status_codes=["200"]
                ),
                OpenApiExample(
                    "Sistema Não Pronto",
                    value={
                        "ready": False,
                        "checks": [
                            {"name": "database", "status": "ready"},
                            {"name": "migrations", "status": "not_ready", "error": "2 migrations pending"}
                        ],
                        "timestamp": "2025-09-20T21:30:00.000Z"
                    },
                    response_only=True,
                    status_codes=["503"]
                )
            ],
            tags=["Health"]
        )
        def get(self, request):
            """Executar readiness check"""
            from ..views.health_views import readiness_check
            response = readiness_check(request)
            data = json.loads(response.content.decode())

            status_code = status.HTTP_200_OK
            if not data.get('ready', False):
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE

            return Response(data, status=status_code)

    class LivenessAPIView(APIView):
        """
        API endpoint para liveness check

        Verificação básica se a aplicação está viva e respondendo.
        Usado por orquestradores para decidir se devem reiniciar o container.
        """

        permission_classes = []  # Endpoint público

        @extend_schema(
            summary="Liveness Check",
            description="""
            Verificação básica se a aplicação está viva e respondendo.

            Não verifica dependências externas - apenas se o processo
            está funcionando e consegue responder a requests.

            Usado por sistemas de orquestração para decidir se
            devem reiniciar o container/processo.
            """,
            responses={
                200: OpenApiTypes.STR,
            },
            examples=[
                OpenApiExample(
                    "Sistema Vivo",
                    value="OK",
                    response_only=True,
                    status_codes=["200"]
                )
            ],
            tags=["Health"]
        )
        def get(self, request):
            """Executar liveness check"""
            return Response("OK", status=status.HTTP_200_OK)

except ImportError:
    # DRF não disponível - criar classes vazias
    class HealthCheckAPIView:
        pass

    class DetailedHealthAPIView:
        pass

    class ReadinessAPIView:
        pass

    class LivenessAPIView:
        pass