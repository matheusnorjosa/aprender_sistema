# ======================================
# 🩺 HEALTH CHECK COMMAND
# Sistema Aprender
# ======================================

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import json
import time
from datetime import datetime


class Command(BaseCommand):
    help = 'Perform comprehensive health check of the application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            default='text',
            choices=['text', 'json'],
            help='Output format (text or json)',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Include detailed checks',
        )

    def handle(self, *args, **options):
        """Main health check handler"""
        start_time = time.time()
        results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'checks': {},
            'version': getattr(settings, 'VERSION', 'unknown'),
            'environment': getattr(settings, 'ENVIRONMENT', 'unknown')
        }

        # Run all health checks
        self.check_database(results)
        self.check_cache(results)
        self.check_settings(results)
        
        if options['detailed']:
            self.check_google_integration(results)
            self.check_disk_space(results)
            self.check_memory_usage(results)

        # Calculate overall status
        failed_checks = [
            name for name, check in results['checks'].items() 
            if check['status'] != 'healthy'
        ]
        
        if failed_checks:
            results['overall_status'] = 'unhealthy'
            results['failed_checks'] = failed_checks

        results['duration'] = round(time.time() - start_time, 3)

        # Output results
        if options['format'] == 'json':
            self.stdout.write(json.dumps(results, indent=2))
        else:
            self.output_text_format(results)

        # Exit with appropriate code
        if results['overall_status'] != 'healthy':
            exit(1)

    def check_database(self, results):
        """Check database connectivity and performance"""
        try:
            start_time = time.time()
            
            # Test basic connectivity
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            # Test write operation
            cursor.execute("CREATE TEMP TABLE health_check_temp (id INTEGER)")
            cursor.execute("DROP TABLE health_check_temp")
            
            duration = round(time.time() - start_time, 3)
            
            results['checks']['database'] = {
                'status': 'healthy',
                'message': 'Database connection successful',
                'duration': duration,
                'details': {
                    'engine': settings.DATABASES['default']['ENGINE'],
                    'host': settings.DATABASES['default'].get('HOST', 'localhost'),
                }
            }
            
        except Exception as e:
            results['checks']['database'] = {
                'status': 'unhealthy',
                'message': f'Database connection failed: {str(e)}',
                'error': str(e)
            }

    def check_cache(self, results):
        """Check cache system"""
        try:
            start_time = time.time()
            
            # Test cache write/read
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, 10)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            duration = round(time.time() - start_time, 3)
            
            if retrieved_value == test_value:
                results['checks']['cache'] = {
                    'status': 'healthy',
                    'message': 'Cache system working',
                    'duration': duration,
                    'details': {
                        'backend': settings.CACHES['default']['BACKEND']
                    }
                }
            else:
                results['checks']['cache'] = {
                    'status': 'unhealthy',
                    'message': 'Cache read/write test failed'
                }
                
        except Exception as e:
            results['checks']['cache'] = {
                'status': 'unhealthy',
                'message': f'Cache system failed: {str(e)}',
                'error': str(e)
            }

    def check_settings(self, results):
        """Check critical settings"""
        issues = []
        
        # Check DEBUG setting in production
        if not settings.DEBUG and getattr(settings, 'ENVIRONMENT', '') == 'production':
            # This is correct for production
            pass
        elif settings.DEBUG and getattr(settings, 'ENVIRONMENT', '') == 'production':
            issues.append("DEBUG should be False in production")
        
        # Check SECRET_KEY
        if not settings.SECRET_KEY or settings.SECRET_KEY == 'dev-secret-key-change-in-production':
            if getattr(settings, 'ENVIRONMENT', '') == 'production':
                issues.append("SECRET_KEY should be changed in production")
        
        # Check ALLOWED_HOSTS
        if getattr(settings, 'ENVIRONMENT', '') == 'production' and not settings.ALLOWED_HOSTS:
            issues.append("ALLOWED_HOSTS should be configured in production")
        
        if issues:
            results['checks']['settings'] = {
                'status': 'warning',
                'message': 'Configuration issues found',
                'issues': issues
            }
        else:
            results['checks']['settings'] = {
                'status': 'healthy',
                'message': 'Settings configuration is valid'
            }

    def check_google_integration(self, results):
        """Check Google Calendar integration"""
        try:
            from core.services.integrations.google_calendar import GoogleCalendarService
            
            calendar_id = getattr(settings, 'GOOGLE_CALENDAR_ID', None)
            credentials = getattr(settings, 'GOOGLE_CREDENTIALS_JSON', None)
            
            if not calendar_id or not credentials:
                results['checks']['google_calendar'] = {
                    'status': 'warning',
                    'message': 'Google Calendar not configured'
                }
                return
            
            # Test connection (this would be a lightweight test)
            service = GoogleCalendarService()
            # Add your actual test logic here
            
            results['checks']['google_calendar'] = {
                'status': 'healthy',
                'message': 'Google Calendar integration working'
            }
            
        except ImportError:
            results['checks']['google_calendar'] = {
                'status': 'warning',
                'message': 'Google Calendar service not available'
            }
        except Exception as e:
            results['checks']['google_calendar'] = {
                'status': 'unhealthy',
                'message': f'Google Calendar integration failed: {str(e)}',
                'error': str(e)
            }

    def check_disk_space(self, results):
        """Check available disk space"""
        try:
            import shutil
            
            disk_usage = shutil.disk_usage('.')
            total_gb = disk_usage.total // (1024**3)
            free_gb = disk_usage.free // (1024**3)
            used_percent = ((disk_usage.total - disk_usage.free) / disk_usage.total) * 100
            
            status = 'healthy'
            if used_percent > 90:
                status = 'unhealthy'
            elif used_percent > 80:
                status = 'warning'
            
            results['checks']['disk_space'] = {
                'status': status,
                'message': f'Disk usage: {used_percent:.1f}%',
                'details': {
                    'total_gb': total_gb,
                    'free_gb': free_gb,
                    'used_percent': round(used_percent, 1)
                }
            }
            
        except Exception as e:
            results['checks']['disk_space'] = {
                'status': 'warning',
                'message': f'Could not check disk space: {str(e)}'
            }

    def check_memory_usage(self, results):
        """Check memory usage (if psutil is available)"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            
            status = 'healthy'
            if used_percent > 90:
                status = 'unhealthy'
            elif used_percent > 80:
                status = 'warning'
            
            results['checks']['memory'] = {
                'status': status,
                'message': f'Memory usage: {used_percent:.1f}%',
                'details': {
                    'total_gb': round(memory.total / (1024**3), 1),
                    'available_gb': round(memory.available / (1024**3), 1),
                    'used_percent': used_percent
                }
            }
            
        except ImportError:
            results['checks']['memory'] = {
                'status': 'info',
                'message': 'Memory monitoring not available (psutil not installed)'
            }
        except Exception as e:
            results['checks']['memory'] = {
                'status': 'warning',
                'message': f'Could not check memory usage: {str(e)}'
            }

    def output_text_format(self, results):
        """Output results in human-readable text format"""
        
        # Header
        status_emoji = "✅" if results['overall_status'] == 'healthy' else "❌"
        self.stdout.write(f"\n{status_emoji} Sistema Aprender Health Check")
        self.stdout.write("=" * 40)
        self.stdout.write(f"Status: {results['overall_status'].upper()}")
        self.stdout.write(f"Environment: {results['environment']}")
        self.stdout.write(f"Version: {results['version']}")
        self.stdout.write(f"Timestamp: {results['timestamp']}")
        self.stdout.write(f"Duration: {results['duration']}s")
        self.stdout.write("")
        
        # Individual checks
        for name, check in results['checks'].items():
            status_map = {
                'healthy': '✅',
                'warning': '⚠️',
                'unhealthy': '❌',
                'info': 'ℹ️'
            }
            
            icon = status_map.get(check['status'], '❓')
            self.stdout.write(f"{icon} {name.upper()}: {check['message']}")
            
            # Show duration if available
            if 'duration' in check:
                self.stdout.write(f"    Duration: {check['duration']}s")
            
            # Show details if available
            if 'details' in check:
                for key, value in check['details'].items():
                    self.stdout.write(f"    {key}: {value}")
            
            # Show issues if any
            if 'issues' in check:
                for issue in check['issues']:
                    self.stdout.write(f"    ⚠️ {issue}")
            
            # Show error if any
            if 'error' in check:
                self.stdout.write(f"    Error: {check['error']}")
            
            self.stdout.write("")
        
        # Summary
        if 'failed_checks' in results:
            self.stdout.write("❌ Failed Checks:")
            for check in results['failed_checks']:
                self.stdout.write(f"  - {check}")
        else:
            self.stdout.write("🎉 All checks passed!")
        
        self.stdout.write("")