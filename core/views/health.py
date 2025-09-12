# ======================================
# 🩺 HEALTH CHECK VIEWS
# Sistema Aprender
# ======================================

from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
import time
import json
from datetime import datetime


@never_cache
@require_GET
def health_check(request):
    """
    Simple health check endpoint for load balancers.
    Returns 200 if basic services are working.
    """
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return HttpResponse(
            "OK", 
            content_type="text/plain",
            status=200
        )
        
    except Exception as e:
        return HttpResponse(
            f"ERROR: {str(e)}", 
            content_type="text/plain",
            status=503
        )


@never_cache
@require_GET
def health_detailed(request):
    """
    Detailed health check with comprehensive system status.
    """
    start_time = time.time()
    
    health_data = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': getattr(settings, 'VERSION', 'unknown'),
        'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
        'checks': {}
    }
    
    # Database check
    try:
        db_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        health_data['checks']['database'] = {
            'status': 'healthy',
            'response_time': round(time.time() - db_start, 3),
            'message': 'Database connection successful'
        }
    except Exception as e:
        health_data['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e),
            'message': 'Database connection failed'
        }
        health_data['status'] = 'unhealthy'
    
    # Cache check
    try:
        cache_start = time.time()
        test_key = 'health_check_test'
        cache.set(test_key, 'test', 5)
        cache.get(test_key)
        cache.delete(test_key)
        
        health_data['checks']['cache'] = {
            'status': 'healthy',
            'response_time': round(time.time() - cache_start, 3),
            'message': 'Cache system working'
        }
    except Exception as e:
        health_data['checks']['cache'] = {
            'status': 'warning',
            'error': str(e),
            'message': 'Cache system issue'
        }
    
    # Settings validation
    settings_issues = []
    
    if settings.DEBUG and getattr(settings, 'ENVIRONMENT', '') == 'production':
        settings_issues.append('DEBUG enabled in production')
    
    if not settings.SECRET_KEY or settings.SECRET_KEY == 'dev-secret-key-change-in-production':
        if getattr(settings, 'ENVIRONMENT', '') == 'production':
            settings_issues.append('Default SECRET_KEY in production')
    
    if settings_issues:
        health_data['checks']['settings'] = {
            'status': 'warning',
            'issues': settings_issues,
            'message': 'Configuration issues detected'
        }
    else:
        health_data['checks']['settings'] = {
            'status': 'healthy',
            'message': 'Settings configuration valid'
        }
    
    # System info
    health_data['system'] = {
        'python_version': '.'.join(map(str, __import__('sys').version_info[:3])),
        'django_version': __import__('django').get_version(),
    }
    
    # Total response time
    health_data['response_time'] = round(time.time() - start_time, 3)
    
    # Determine HTTP status code
    status_code = 200
    if health_data['status'] == 'unhealthy':
        status_code = 503
    elif any(check.get('status') == 'warning' for check in health_data['checks'].values()):
        status_code = 200  # Warnings don't affect availability
    
    return JsonResponse(health_data, status=status_code)


@never_cache 
@require_GET
def health_ready(request):
    """
    Readiness probe - checks if the application is ready to serve requests.
    Used by Kubernetes readiness probes.
    """
    try:
        # Database connectivity (required for app to function)
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Check critical settings
        if not settings.SECRET_KEY:
            raise Exception("SECRET_KEY not configured")
        
        return JsonResponse({
            'status': 'ready',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=503)


@never_cache
@require_GET  
def health_live(request):
    """
    Liveness probe - checks if the application is alive.
    Used by Kubernetes liveness probes.
    Should be very lightweight.
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    })


@never_cache
@require_GET
def health_metrics(request):
    """
    Basic metrics endpoint for monitoring systems.
    """
    try:
        # Database metrics
        db_start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_session")
            session_count = cursor.fetchone()[0]
        db_response_time = time.time() - db_start
        
        # Cache metrics (if available)
        cache_metrics = {}
        try:
            cache_start = time.time()
            cache.set('metrics_test', '1', 1)
            cache.get('metrics_test')
            cache_metrics['response_time'] = round(time.time() - cache_start, 3)
            cache_metrics['status'] = 'available'
        except:
            cache_metrics['status'] = 'unavailable'
        
        metrics = {
            'database': {
                'response_time': round(db_response_time, 3),
                'active_sessions': session_count
            },
            'cache': cache_metrics,
            'application': {
                'environment': getattr(settings, 'ENVIRONMENT', 'unknown'),
                'debug_mode': settings.DEBUG,
                'version': getattr(settings, 'VERSION', 'unknown')
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return JsonResponse(metrics)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)