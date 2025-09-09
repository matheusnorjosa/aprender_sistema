"""
Advanced Monitoring System for Aprender Sistema
================================================

Comprehensive monitoring and observability stack featuring:
- OpenTelemetry instrumentation
- Sentry error tracking  
- Prometheus metrics
- Structured logging
- Performance monitoring
- Health checks

Author: Claude Code
Date: Janeiro 2025
"""

import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

# Sentry
try:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
except ImportError:
    sentry_sdk = None

# Prometheus
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client.core import CollectorRegistry
except ImportError:
    Counter = None
    Histogram = None
    Gauge = None

# Structured Logging
try:
    import structlog
except ImportError:
    structlog = None

# OpenTelemetry (already installed in TIER 1)
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.instrumentation.django import DjangoInstrumentation
    from opentelemetry.instrumentation.requests import RequestsInstrumentation
except ImportError:
    trace = None
    metrics = None

from core.models import LogAuditoria, Solicitacao, Formador

logger = logging.getLogger(__name__)


class SentryMonitoring:
    """
    Advanced Sentry integration for error tracking and performance monitoring
    """
    
    def __init__(self):
        self.enabled = sentry_sdk is not None
        if not self.enabled:
            logger.warning("Sentry SDK not available - install with: pip install sentry-sdk")
            return
        
        self._setup_sentry()
    
    def _setup_sentry(self):
        """Configure Sentry with advanced settings"""
        dsn = getattr(settings, 'SENTRY_DSN', None)
        if not dsn:
            logger.warning("SENTRY_DSN not configured")
            return
        
        try:
            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    DjangoIntegration(
                        transaction_style='url',
                        middleware_spans=True,
                        signals_spans=True,
                        cache_spans=True,
                    ),
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    ),
                    RedisIntegration(),
                ],
                # Performance monitoring
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
                
                # Error filtering
                before_send=self._filter_errors,
                
                # Environment settings
                environment=getattr(settings, 'ENVIRONMENT', 'development'),
                release=getattr(settings, 'VERSION', 'unknown'),
                
                # Custom tags
                tags={
                    'component': 'aprender_sistema',
                    'service': 'educational_platform'
                }
            )
            
            logger.info("Sentry monitoring initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
            self.enabled = False
    
    def _filter_errors(self, event, hint):
        """Filter out noisy errors"""
        # Skip common errors that don't need tracking
        ignore_patterns = [
            'DisallowedHost',
            'SuspiciousOperation',
            'PermissionDenied'
        ]
        
        exception = hint.get('exc_info', [None, None, None])[1]
        if exception:
            for pattern in ignore_patterns:
                if pattern in str(exception):
                    return None
        
        return event
    
    def capture_educational_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        solicitacao_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Capture educational system events in Sentry"""
        if not self.enabled:
            return
        
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("event_type", event_type)
            scope.set_context("educational_event", {
                "event_type": event_type,
                "user_id": user_id,
                "solicitacao_id": solicitacao_id,
                "timestamp": datetime.now().isoformat(),
                "extra_data": extra_data or {}
            })
            
            sentry_sdk.capture_message(
                f"Educational Event: {event_type}",
                level="info"
            )
    
    def capture_performance_issue(
        self,
        operation: str,
        duration_ms: float,
        threshold_ms: float = 1000
    ):
        """Capture performance issues"""
        if not self.enabled or duration_ms < threshold_ms:
            return
        
        sentry_sdk.capture_message(
            f"Performance Issue: {operation} took {duration_ms:.2f}ms",
            level="warning",
            extras={
                "operation": operation,
                "duration_ms": duration_ms,
                "threshold_ms": threshold_ms
            }
        )


class PrometheusMetrics:
    """
    Advanced Prometheus metrics collection
    """
    
    def __init__(self):
        self.enabled = Counter is not None
        if not self.enabled:
            logger.warning("Prometheus client not available - install with: pip install prometheus-client")
            return
        
        self.registry = CollectorRegistry()
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        # HTTP Request metrics
        self.http_requests_total = Counter(
            'aprender_sistema_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'aprender_sistema_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Educational system metrics
        self.solicitacoes_total = Counter(
            'aprender_sistema_solicitacoes_total',
            'Total solicitações created',
            ['status', 'projeto'],
            registry=self.registry
        )
        
        self.formador_events_total = Counter(
            'aprender_sistema_formador_events_total',
            'Total events by formador',
            ['formador_id'],
            registry=self.registry
        )
        
        self.calendar_operations_total = Counter(
            'aprender_sistema_calendar_operations_total',
            'Total calendar operations',
            ['operation', 'status'],
            registry=self.registry
        )
        
        # System health metrics
        self.active_users = Gauge(
            'aprender_sistema_active_users',
            'Number of active users',
            registry=self.registry
        )
        
        self.database_connections = Gauge(
            'aprender_sistema_database_connections',
            'Number of database connections',
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'aprender_sistema_cache_hit_rate',
            'Cache hit rate',
            registry=self.registry
        )
        
        logger.info("Prometheus metrics initialized")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not self.enabled:
            return
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint, 
            status_code=status_code
        ).inc()
        
        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_solicitacao_created(self, status: str, projeto: str):
        """Record solicitação creation"""
        if not self.enabled:
            return
        
        self.solicitacoes_total.labels(
            status=status,
            projeto=projeto
        ).inc()
    
    def record_formador_event(self, formador_id: str):
        """Record formador event"""
        if not self.enabled:
            return
        
        self.formador_events_total.labels(
            formador_id=formador_id
        ).inc()
    
    def record_calendar_operation(self, operation: str, status: str):
        """Record calendar operation"""
        if not self.enabled:
            return
        
        self.calendar_operations_total.labels(
            operation=operation,
            status=status
        ).inc()
    
    def update_system_metrics(self):
        """Update system health metrics"""
        if not self.enabled:
            return
        
        try:
            # Update active users (approximate)
            active_count = cache.get('active_users_count', 0)
            self.active_users.set(active_count)
            
            # Update database connections
            db_connections = len(connection.queries)
            self.database_connections.set(db_connections)
            
            # Cache hit rate (mock calculation)
            cache_hits = cache.get('cache_hits', 0)
            cache_misses = cache.get('cache_misses', 1)
            hit_rate = cache_hits / (cache_hits + cache_misses)
            self.cache_hit_rate.set(hit_rate)
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def get_metrics(self) -> str:
        """Get Prometheus metrics in text format"""
        if not self.enabled:
            return ""
        
        self.update_system_metrics()
        return generate_latest(self.registry).decode('utf-8')


class StructuredLogger:
    """
    Advanced structured logging with contextual information
    """
    
    def __init__(self):
        self.enabled = structlog is not None
        if not self.enabled:
            logger.warning("Structlog not available - install with: pip install structlog")
            return
        
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure structured logging"""
        try:
            structlog.configure(
                processors=[
                    structlog.contextvars.merge_contextvars,
                    structlog.processors.add_log_level,
                    structlog.processors.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer()
                ],
                wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
                logger_factory=structlog.WriteLoggerFactory(),
                cache_logger_on_first_use=True,
            )
            
            self.logger = structlog.get_logger("aprender_sistema")
            logger.info("Structured logging initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup structured logging: {e}")
            self.enabled = False
    
    def log_educational_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        solicitacao_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log educational system events with structure"""
        if not self.enabled:
            return
        
        self.logger.info(
            "educational_event",
            event_type=event_type,
            user_id=user_id,
            solicitacao_id=solicitacao_id,
            details=details or {}
        )
    
    def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        context: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics"""
        if not self.enabled:
            return
        
        self.logger.info(
            "performance_metric",
            operation=operation,
            duration_ms=duration_ms,
            context=context or {}
        )
    
    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events"""
        if not self.enabled:
            return
        
        self.logger.warning(
            "security_event",
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {}
        )


class HealthCheckService:
    """
    Comprehensive health check system
    """
    
    def __init__(self):
        self.checks = {}
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check("database", self._check_database)
        self.register_check("cache", self._check_cache)
        self.register_check("disk_space", self._check_disk_space)
        self.register_check("memory_usage", self._check_memory_usage)
    
    def register_check(self, name: str, check_function: Callable[[], Dict[str, Any]]):
        """Register a health check function"""
        self.checks[name] = check_function
        logger.info(f"Registered health check: {name}")
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            return {"status": "healthy", "response_time_ms": 1}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def _check_cache(self) -> Dict[str, Any]:
        """Check cache system"""
        try:
            test_key = "health_check_test"
            test_value = f"test_{int(time.time())}"
            
            cache.set(test_key, test_value, 10)
            retrieved = cache.get(test_key)
            
            if retrieved == test_value:
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "error": "Cache value mismatch"}
                
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def _check_disk_space(self) -> Dict[str, Any]:
        """Check disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            
            free_percentage = (free / total) * 100
            
            status = "healthy" if free_percentage > 10 else "warning" if free_percentage > 5 else "critical"
            
            return {
                "status": status,
                "free_percentage": round(free_percentage, 2),
                "free_gb": round(free / (1024**3), 2)
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def _check_memory_usage(self) -> Dict[str, Any]:
        """Check memory usage"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            
            status = "healthy" if memory.percent < 80 else "warning" if memory.percent < 90 else "critical"
            
            return {
                "status": status,
                "usage_percentage": memory.percent,
                "available_gb": round(memory.available / (1024**3), 2)
            }
        except ImportError:
            return {"status": "unknown", "error": "psutil not installed"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        results = {}
        overall_status = "healthy"
        
        for name, check_func in self.checks.items():
            try:
                start_time = time.time()
                result = check_func()
                result["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
                
                results[name] = result
                
                # Update overall status
                if result["status"] in ["unhealthy", "critical"]:
                    overall_status = "unhealthy"
                elif result["status"] == "warning" and overall_status != "unhealthy":
                    overall_status = "warning"
                    
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "response_time_ms": 0
                }
                overall_status = "unhealthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": results
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get health check summary"""
        results = self.run_all_checks()
        
        summary = {
            "status": results["overall_status"],
            "timestamp": results["timestamp"],
            "healthy_checks": sum(1 for check in results["checks"].values() if check["status"] == "healthy"),
            "total_checks": len(results["checks"]),
            "failing_checks": [name for name, check in results["checks"].items() if check["status"] in ["unhealthy", "critical", "error"]]
        }
        
        return summary


class PerformanceMonitor:
    """
    Advanced performance monitoring and profiling
    """
    
    def __init__(self):
        self.metrics = {}
        self.slow_queries = []
        self.performance_alerts = []
    
    def measure_execution_time(self, operation_name: str):
        """Context manager for measuring execution time"""
        class ExecutionTimer:
            def __init__(self, monitor, name):
                self.monitor = monitor
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = (time.time() - self.start_time) * 1000
                self.monitor.record_execution_time(self.name, duration)
        
        return ExecutionTimer(self, operation_name)
    
    def record_execution_time(self, operation: str, duration_ms: float):
        """Record execution time for an operation"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append({
            'duration_ms': duration_ms,
            'timestamp': datetime.now()
        })
        
        # Keep only last 100 measurements
        self.metrics[operation] = self.metrics[operation][-100:]
        
        # Alert on slow operations
        if duration_ms > 1000:  # 1 second threshold
            self.performance_alerts.append({
                'operation': operation,
                'duration_ms': duration_ms,
                'timestamp': datetime.now(),
                'type': 'slow_operation'
            })
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance metrics summary"""
        summary = {}
        
        for operation, measurements in self.metrics.items():
            if measurements:
                durations = [m['duration_ms'] for m in measurements]
                summary[operation] = {
                    'count': len(durations),
                    'avg_ms': round(sum(durations) / len(durations), 2),
                    'min_ms': round(min(durations), 2),
                    'max_ms': round(max(durations), 2),
                    'p95_ms': round(sorted(durations)[int(len(durations) * 0.95)], 2) if len(durations) > 1 else durations[0]
                }
        
        return summary
    
    def get_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent performance alerts"""
        return sorted(
            self.performance_alerts,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]


# Global service instances
sentry_monitoring = SentryMonitoring()
prometheus_metrics = PrometheusMetrics()
structured_logger = StructuredLogger()
health_checker = HealthCheckService()
performance_monitor = PerformanceMonitor()


# Convenience functions
def capture_educational_event(event_type: str, **kwargs):
    """Capture educational event across all monitoring systems"""
    sentry_monitoring.capture_educational_event(event_type, **kwargs)
    structured_logger.log_educational_event(event_type, **kwargs)


def record_performance_metric(operation: str, duration_ms: float, **kwargs):
    """Record performance metric across monitoring systems"""
    performance_monitor.record_execution_time(operation, duration_ms)
    structured_logger.log_performance_metric(operation, duration_ms, kwargs)
    
    # Alert if slow
    if duration_ms > 1000:
        sentry_monitoring.capture_performance_issue(operation, duration_ms)


def get_system_health() -> Dict[str, Any]:
    """Get comprehensive system health status"""
    return health_checker.run_all_checks()


def get_performance_metrics() -> str:
    """Get Prometheus metrics"""
    return prometheus_metrics.get_metrics()


# Monitoring context manager
def monitor_operation(operation_name: str):
    """Context manager for comprehensive operation monitoring"""
    return performance_monitor.measure_execution_time(operation_name)