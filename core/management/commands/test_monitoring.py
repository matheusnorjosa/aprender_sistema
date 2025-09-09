"""
Django Management Command - Test Monitoring System
===================================================

Command to test and validate the comprehensive monitoring stack:
- Health checks
- Performance monitoring  
- Metrics collection
- Structured logging
- Alert system

Usage:
    python manage.py test_monitoring --health-check
    python manage.py test_monitoring --performance-test
    python manage.py test_monitoring --metrics-test
    python manage.py test_monitoring --all

Author: Claude Code
Date: Janeiro 2025
"""

import time
import random
from django.core.management.base import BaseCommand, CommandError
from core.services.monitoring_system import (
    sentry_monitoring,
    prometheus_metrics,
    structured_logger,
    health_checker,
    performance_monitor,
    capture_educational_event,
    record_performance_metric,
    get_system_health,
    get_performance_metrics,
    monitor_operation
)


class Command(BaseCommand):
    help = "Test comprehensive monitoring system"

    def add_arguments(self, parser):
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Run system health checks'
        )
        
        parser.add_argument(
            '--performance-test',
            action='store_true',
            help='Run performance monitoring tests'
        )
        
        parser.add_argument(
            '--metrics-test',
            action='store_true',
            help='Test metrics collection'
        )
        
        parser.add_argument(
            '--logging-test',
            action='store_true',
            help='Test structured logging'
        )
        
        parser.add_argument(
            '--sentry-test',
            action='store_true',
            help='Test Sentry integration'
        )
        
        parser.add_argument(
            '--load-test',
            action='store_true',
            help='Run load testing simulation'
        )
        
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all monitoring tests'
        )

    def handle(self, *args, **options):
        self.stdout.write("Testing Comprehensive Monitoring System...")
        
        if options['all']:
            self.test_health_checks()
            self.test_performance_monitoring()
            self.test_metrics_collection()
            self.test_structured_logging()
            self.test_sentry_integration()
            self.test_load_simulation()
        elif options['health_check']:
            self.test_health_checks()
        elif options['performance_test']:
            self.test_performance_monitoring()
        elif options['metrics_test']:
            self.test_metrics_collection()
        elif options['logging_test']:
            self.test_structured_logging()
        elif options['sentry_test']:
            self.test_sentry_integration()
        elif options['load_test']:
            self.test_load_simulation()
        else:
            raise CommandError("Please specify a test to run. Use --help for options.")
    
    def test_health_checks(self):
        """Test system health checks"""
        self.stdout.write("=" * 60)
        self.stdout.write("TESTING SYSTEM HEALTH CHECKS")
        self.stdout.write("=" * 60)
        
        try:
            # Test individual health checks
            self.stdout.write("Testing individual health checks...")
            
            # Database check
            db_result = health_checker._check_database()
            self.stdout.write(f"[{self._get_status_symbol(db_result['status'])}] Database: {db_result['status']}")
            if 'response_time_ms' in db_result:
                self.stdout.write(f"     Response time: {db_result['response_time_ms']}ms")
            
            # Cache check
            cache_result = health_checker._check_cache()
            self.stdout.write(f"[{self._get_status_symbol(cache_result['status'])}] Cache: {cache_result['status']}")
            
            # Disk space check
            disk_result = health_checker._check_disk_space()
            self.stdout.write(f"[{self._get_status_symbol(disk_result['status'])}] Disk Space: {disk_result['status']}")
            if 'free_percentage' in disk_result:
                self.stdout.write(f"     Free space: {disk_result['free_percentage']}%")
            
            # Memory check
            memory_result = health_checker._check_memory_usage()
            self.stdout.write(f"[{self._get_status_symbol(memory_result['status'])}] Memory: {memory_result['status']}")
            if 'usage_percentage' in memory_result:
                self.stdout.write(f"     Usage: {memory_result['usage_percentage']}%")
            
            # Comprehensive health check
            self.stdout.write("\nRunning comprehensive health check...")
            health_status = get_system_health()
            
            overall_status = health_status['overall_status']
            self.stdout.write(f"[{self._get_status_symbol(overall_status)}] Overall Status: {overall_status}")
            
            healthy_count = sum(1 for check in health_status['checks'].values() if check['status'] == 'healthy')
            total_count = len(health_status['checks'])
            self.stdout.write(f"     Healthy checks: {healthy_count}/{total_count}")
            
            if health_status['checks']:
                self.stdout.write("\nDetailed results:")
                for name, result in health_status['checks'].items():
                    status_symbol = self._get_status_symbol(result['status'])
                    self.stdout.write(f"     {status_symbol} {name}: {result['status']} ({result.get('response_time_ms', 0):.1f}ms)")
                    if 'error' in result:
                        self.stdout.write(f"       Error: {result['error']}")
            
            # Test health check summary
            self.stdout.write("\nTesting health check summary...")
            summary = health_checker.get_summary()
            self.stdout.write(f"[OK] Summary generated: {summary['healthy_checks']}/{summary['total_checks']} checks healthy")
            
            if summary['failing_checks']:
                self.stdout.write(f"     Failing checks: {', '.join(summary['failing_checks'])}")
            
            self.stdout.write("[OK] Health checks test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Health checks test failed: {e}")
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING PERFORMANCE MONITORING")
        self.stdout.write("=" * 60)
        
        try:
            # Test performance monitor context manager
            self.stdout.write("Testing performance monitoring context manager...")
            
            with monitor_operation("test_database_query"):
                # Simulate database query
                time.sleep(0.1)
                self.stdout.write("[OK] Simulated database query (100ms)")
            
            with monitor_operation("test_api_call"):
                # Simulate API call
                time.sleep(0.05)
                self.stdout.write("[OK] Simulated API call (50ms)")
            
            with monitor_operation("test_slow_operation"):
                # Simulate slow operation
                time.sleep(0.2)
                self.stdout.write("[OK] Simulated slow operation (200ms)")
            
            # Test manual performance recording
            self.stdout.write("\nTesting manual performance recording...")
            record_performance_metric("manual_test_operation", 150.5)
            record_performance_metric("another_operation", 75.2)
            self.stdout.write("[OK] Manual performance metrics recorded")
            
            # Get performance summary
            self.stdout.write("\nTesting performance summary...")
            summary = performance_monitor.get_performance_summary()
            
            if summary:
                self.stdout.write("[OK] Performance summary generated:")
                for operation, stats in summary.items():
                    self.stdout.write(f"     {operation}:")
                    self.stdout.write(f"       Count: {stats['count']}")
                    self.stdout.write(f"       Average: {stats['avg_ms']}ms")
                    self.stdout.write(f"       Min: {stats['min_ms']}ms")
                    self.stdout.write(f"       Max: {stats['max_ms']}ms")
                    self.stdout.write(f"       P95: {stats['p95_ms']}ms")
            else:
                self.stdout.write("[WARNING] No performance data collected")
            
            # Test performance alerts
            self.stdout.write("\nTesting performance alerts...")
            
            # Trigger a slow operation alert
            with monitor_operation("intentionally_slow_operation"):
                time.sleep(1.1)  # Trigger 1000ms+ alert
            
            alerts = performance_monitor.get_alerts(5)
            if alerts:
                self.stdout.write(f"[OK] Performance alerts generated: {len(alerts)}")
                for alert in alerts[:3]:  # Show first 3
                    self.stdout.write(f"     Alert: {alert['operation']} took {alert['duration_ms']}ms")
            else:
                self.stdout.write("[WARNING] No performance alerts generated")
            
            self.stdout.write("[OK] Performance monitoring test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Performance monitoring test failed: {e}")
    
    def test_metrics_collection(self):
        """Test Prometheus metrics collection"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING METRICS COLLECTION")
        self.stdout.write("=" * 60)
        
        try:
            if not prometheus_metrics.enabled:
                self.stdout.write("[WARNING] Prometheus metrics not available")
                return
            
            # Test HTTP request metrics
            self.stdout.write("Testing HTTP request metrics...")
            prometheus_metrics.record_http_request("GET", "/api/solicitacoes", 200, 0.15)
            prometheus_metrics.record_http_request("POST", "/api/solicitacoes", 201, 0.25)
            prometheus_metrics.record_http_request("GET", "/api/formadores", 200, 0.10)
            self.stdout.write("[OK] HTTP request metrics recorded")
            
            # Test educational metrics
            self.stdout.write("Testing educational system metrics...")
            prometheus_metrics.record_solicitacao_created("PENDENTE", "Django Course")
            prometheus_metrics.record_solicitacao_created("APROVADO", "Python Basics")
            prometheus_metrics.record_formador_event("formador_123")
            prometheus_metrics.record_calendar_operation("create_event", "success")
            self.stdout.write("[OK] Educational system metrics recorded")
            
            # Test system metrics update
            self.stdout.write("Testing system metrics update...")
            prometheus_metrics.update_system_metrics()
            self.stdout.write("[OK] System metrics updated")
            
            # Get metrics output
            self.stdout.write("Testing metrics export...")
            metrics_output = get_performance_metrics()
            
            if metrics_output:
                line_count = len(metrics_output.split('\n'))
                self.stdout.write(f"[OK] Metrics exported ({line_count} lines)")
                
                # Show sample metrics
                metrics_lines = metrics_output.split('\n')[:10]
                self.stdout.write("     Sample metrics:")
                for line in metrics_lines:
                    if line.strip() and not line.startswith('#'):
                        self.stdout.write(f"     {line[:80]}...")
                        break
            else:
                self.stdout.write("[WARNING] No metrics output generated")
            
            self.stdout.write("[OK] Metrics collection test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Metrics collection test failed: {e}")
    
    def test_structured_logging(self):
        """Test structured logging"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING STRUCTURED LOGGING")
        self.stdout.write("=" * 60)
        
        try:
            if not structured_logger.enabled:
                self.stdout.write("[WARNING] Structured logging not available")
                return
            
            # Test educational event logging
            self.stdout.write("Testing educational event logging...")
            structured_logger.log_educational_event(
                "solicitacao_created",
                user_id=123,
                solicitacao_id="test-123",
                details={"projeto": "Django Course", "municipio": "Fortaleza"}
            )
            self.stdout.write("[OK] Educational event logged")
            
            # Test performance logging
            self.stdout.write("Testing performance metric logging...")
            structured_logger.log_performance_metric(
                "database_query",
                125.5,
                context={"query_type": "SELECT", "table": "solicitacao"}
            )
            self.stdout.write("[OK] Performance metric logged")
            
            # Test security event logging
            self.stdout.write("Testing security event logging...")
            structured_logger.log_security_event(
                "login_attempt",
                user_id=456,
                ip_address="192.168.1.1",
                details={"success": True, "method": "password"}
            )
            self.stdout.write("[OK] Security event logged")
            
            # Test integrated logging
            self.stdout.write("Testing integrated event capture...")
            capture_educational_event(
                "event_approved",
                user_id=789,
                solicitacao_id="test-456",
                details={"approver": "superintendent"}
            )
            self.stdout.write("[OK] Integrated event capture completed")
            
            self.stdout.write("[OK] Structured logging test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Structured logging test failed: {e}")
    
    def test_sentry_integration(self):
        """Test Sentry integration"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING SENTRY INTEGRATION")
        self.stdout.write("=" * 60)
        
        try:
            if not sentry_monitoring.enabled:
                self.stdout.write("[WARNING] Sentry monitoring not available")
                self.stdout.write("     Configure SENTRY_DSN in settings for full functionality")
                return
            
            # Test educational event capture
            self.stdout.write("Testing Sentry educational event capture...")
            sentry_monitoring.capture_educational_event(
                "test_event",
                user_id=123,
                solicitacao_id="test-789",
                extra_data={"test": True, "environment": "testing"}
            )
            self.stdout.write("[OK] Educational event sent to Sentry")
            
            # Test performance issue capture
            self.stdout.write("Testing Sentry performance issue capture...")
            sentry_monitoring.capture_performance_issue(
                "test_slow_query",
                1500.0,  # 1.5 seconds
                1000.0   # 1 second threshold
            )
            self.stdout.write("[OK] Performance issue sent to Sentry")
            
            # Test error capture (optional - uncomment to test)
            # self.stdout.write("Testing Sentry error capture...")
            # try:
            #     raise ValueError("Test error for Sentry validation")
            # except ValueError:
            #     sentry_sdk.capture_exception()
            #     self.stdout.write("[OK] Test error sent to Sentry")
            
            self.stdout.write("[OK] Sentry integration test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Sentry integration test failed: {e}")
    
    def test_load_simulation(self):
        """Test system under simulated load"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("TESTING LOAD SIMULATION")
        self.stdout.write("=" * 60)
        
        try:
            operations = [
                "user_login",
                "create_solicitacao", 
                "approve_solicitacao",
                "calendar_sync",
                "generate_report",
                "search_formadores"
            ]
            
            self.stdout.write("Running load simulation (50 operations)...")
            
            for i in range(50):
                operation = random.choice(operations)
                
                # Simulate varying execution times
                base_time = random.uniform(0.01, 0.5)  # 10-500ms base
                if operation == "generate_report":
                    base_time += random.uniform(0.5, 1.0)  # Reports are slower
                
                with monitor_operation(f"load_test_{operation}"):
                    time.sleep(base_time)
                
                # Record additional metrics
                if prometheus_metrics.enabled:
                    status_codes = [200, 200, 200, 201, 400, 500]  # Mostly success
                    status = random.choice(status_codes)
                    prometheus_metrics.record_http_request("POST", f"/api/{operation}", status, base_time)
                
                # Occasional educational events
                if random.random() < 0.3:  # 30% chance
                    capture_educational_event(
                        f"load_test_{operation}",
                        user_id=random.randint(1, 100),
                        solicitacao_id=f"load-test-{i}"
                    )
                
                # Progress indicator
                if (i + 1) % 10 == 0:
                    self.stdout.write(f"     Completed {i + 1}/50 operations...")
            
            self.stdout.write("[OK] Load simulation completed")
            
            # Show results
            self.stdout.write("\nLoad simulation results:")
            
            # Performance summary
            perf_summary = performance_monitor.get_performance_summary()
            if perf_summary:
                total_operations = sum(stats['count'] for stats in perf_summary.values())
                avg_response_time = sum(stats['avg_ms'] * stats['count'] for stats in perf_summary.values()) / total_operations
                self.stdout.write(f"     Total operations: {total_operations}")
                self.stdout.write(f"     Average response time: {avg_response_time:.2f}ms")
                
                # Show top 3 slowest operations
                sorted_ops = sorted(perf_summary.items(), key=lambda x: x[1]['avg_ms'], reverse=True)
                self.stdout.write("     Slowest operations:")
                for op_name, stats in sorted_ops[:3]:
                    self.stdout.write(f"       {op_name}: {stats['avg_ms']}ms avg")
            
            # Health check after load
            self.stdout.write("\nHealth check after load test:")
            health_summary = health_checker.get_summary()
            self.stdout.write(f"     Overall status: {health_summary['status']}")
            
            self.stdout.write("[OK] Load simulation test completed!")
            
        except Exception as e:
            self.stdout.write(f"[ERROR] Load simulation test failed: {e}")
    
    def _get_status_symbol(self, status):
        """Get visual symbol for status"""
        symbols = {
            'healthy': 'OK',
            'warning': 'WARN',
            'unhealthy': 'ERROR',
            'critical': 'CRIT',
            'error': 'ERROR',
            'unknown': '?'
        }
        return symbols.get(status, '?')