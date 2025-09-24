"""
Health Check Views for Aprender Sistema
======================================

Views para monitoramento da saúde do sistema, verificação de
componentes críticos e diagnósticos.

Author: Claude Code
Date: Janeiro 2025
"""

import logging
from datetime import datetime, timedelta

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.db import connection, connections
from django.core.cache import cache
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from core.services import UsuarioService


logger = logging.getLogger(__name__)


@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check básico do sistema

    Retorna:
    - Status HTTP 200 se tudo OK
    - Status HTTP 503 se algum componente crítico falhou
    """
    health_status = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "checks": {}
    }

    overall_healthy = True

    # Check 1: Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": 0  # Poderia medir tempo real
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False

    # Check 2: Cache
    try:
        cache_key = "health_check_test"
        cache.set(cache_key, "test_value", 30)
        cached_value = cache.get(cache_key)

        if cached_value == "test_value":
            health_status["checks"]["cache"] = {"status": "healthy"}
        else:
            raise Exception("Cache write/read test failed")

    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        health_status["checks"]["cache"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False

    # Check 3: Google Calendar (se configurado)
    if getattr(settings, 'FEATURE_GOOGLE_SYNC', False):
        try:
            from core.services.integrations.google_calendar import GoogleCalendarService
            cal_service = GoogleCalendarService()
            # Test básico de conectividade (sem criar eventos)
            cal_service.get_calendar()
            health_status["checks"]["google_calendar"] = {"status": "healthy"}
        except Exception as e:
            logger.warning(f"Google Calendar health check failed: {e}")
            health_status["checks"]["google_calendar"] = {
                "status": "warning",
                "error": str(e)
            }
            # Google Calendar não é crítico para operação básica

    # Check 4: File System
    try:
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=True) as tmp_file:
            tmp_file.write(b"health_check_test")
            tmp_file.flush()

            # Verificar se consegue ler
            with open(tmp_file.name, 'rb') as read_file:
                content = read_file.read()
                if content == b"health_check_test":
                    health_status["checks"]["filesystem"] = {"status": "healthy"}
                else:
                    raise Exception("File write/read test failed")

    except Exception as e:
        logger.error(f"Filesystem health check failed: {e}")
        health_status["checks"]["filesystem"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False

    # Status final
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status, status=200)


@never_cache
@require_http_methods(["GET"])
def detailed_health(request):
    """
    Health check detalhado com métricas do sistema

    Inclui informações sobre:
    - CPU, memória, disco
    - Conexões de database
    - Estatísticas da aplicação
    """

    # Verificar se usuário tem permissão para ver detalhes
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    detailed_status = {
        "timestamp": timezone.now().isoformat(),
        "environment": getattr(settings, 'ENVIRONMENT', 'unknown'),
        "system_metrics": {},
        "application_metrics": {},
        "database_metrics": {}
    }

    # System Metrics
    try:
        if PSUTIL_AVAILABLE:
            # CPU e Memória
            detailed_status["system_metrics"] = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
            }
        else:
            detailed_status["system_metrics"] = {
                "note": "psutil não disponível - instale para métricas detalhadas"
            }
    except Exception as e:
        logger.error(f"System metrics collection failed: {e}")
        detailed_status["system_metrics"] = {"error": str(e)}

    # Application Metrics
    try:
        from core.models import Usuario, Solicitacao, LogAuditoria

        # Contadores básicos
        detailed_status["application_metrics"] = {
            "total_users": Usuario.objects.count(),
            "active_users": UsuarioService.ativos().count(),
            "total_solicitacoes": Solicitacao.objects.count(),
            "solicitacoes_pendentes": Solicitacao.objects.filter(
                status='pendente'
            ).count(),
            "recent_audit_logs": LogAuditoria.objects.filter(
                timestamp__gte=timezone.now() - timedelta(hours=24)
            ).count(),
        }

        # Estatísticas dos últimos 7 dias
        week_ago = timezone.now() - timedelta(days=7)
        detailed_status["application_metrics"]["weekly_stats"] = {
            "new_solicitacoes": Solicitacao.objects.filter(
                data_criacao__gte=week_ago
            ).count(),
            "approved_solicitacoes": Solicitacao.objects.filter(
                status='aprovado',
                data_criacao__gte=week_ago
            ).count(),
        }

    except Exception as e:
        logger.error(f"Application metrics collection failed: {e}")
        detailed_status["application_metrics"] = {"error": str(e)}

    # Database Metrics
    try:
        db_metrics = {}

        # Para cada conexão configurada
        for alias in connections:
            try:
                conn = connections[alias]
                with conn.cursor() as cursor:
                    # PostgreSQL específico
                    if 'postgresql' in conn.settings_dict['ENGINE']:
                        cursor.execute("""
                            SELECT
                                count(*) as active_connections,
                                sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active_queries
                            FROM pg_stat_activity
                            WHERE datname = current_database()
                        """)
                        row = cursor.fetchone()
                        db_metrics[alias] = {
                            "active_connections": row[0] if row else 0,
                            "active_queries": row[1] if row else 0,
                        }
                    else:
                        db_metrics[alias] = {"status": "connected"}

            except Exception as e:
                db_metrics[alias] = {"error": str(e)}

        detailed_status["database_metrics"] = db_metrics

    except Exception as e:
        logger.error(f"Database metrics collection failed: {e}")
        detailed_status["database_metrics"] = {"error": str(e)}

    return JsonResponse(detailed_status, status=200)


@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check para Kubernetes/Docker

    Verifica se a aplicação está pronta para receber tráfego.
    Diferente do liveness check, verifica dependências externas.
    """

    checks = []
    ready = True

    # Database deve estar acessível
    try:
        from core.models import Usuario
        Usuario.objects.exists()  # Query simples
        checks.append({"name": "database", "status": "ready"})
    except Exception as e:
        checks.append({"name": "database", "status": "not_ready", "error": str(e)})
        ready = False

    # Migrations devem estar aplicadas
    try:
        from django.core.management import execute_from_command_line
        from django.db.migrations.executor import MigrationExecutor
        from django.db import DEFAULT_DB_ALIAS

        executor = MigrationExecutor(connections[DEFAULT_DB_ALIAS])
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            checks.append({
                "name": "migrations",
                "status": "not_ready",
                "error": f"{len(plan)} migrations pending"
            })
            ready = False
        else:
            checks.append({"name": "migrations", "status": "ready"})

    except Exception as e:
        checks.append({"name": "migrations", "status": "not_ready", "error": str(e)})
        ready = False

    response_data = {
        "ready": ready,
        "checks": checks,
        "timestamp": timezone.now().isoformat()
    }

    status_code = 200 if ready else 503
    return JsonResponse(response_data, status=status_code)


@never_cache
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check para Kubernetes/Docker

    Verificação básica se a aplicação está viva e respondendo.
    Não verifica dependências externas.
    """

    return HttpResponse("OK", content_type="text/plain", status=200)