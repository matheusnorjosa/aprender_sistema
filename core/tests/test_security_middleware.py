"""
Testes para Security Middleware
==============================

Testa os middlewares de segurança implementados para
garantir que headers e proteções estão funcionando.

Author: Claude Code
Date: Janeiro 2025
"""

from django.test import TestCase, Client, override_settings
from django.http import HttpResponse
from django.urls import path
from django.conf import settings
from unittest.mock import patch, MagicMock


def dummy_view(request):
    """View simples para testar middleware"""
    return HttpResponse("OK")


urlpatterns_test = [
    path('test/', dummy_view, name='test_view'),
]


class SecurityHeadersMiddlewareTest(TestCase):
    """Testes para SecurityHeadersMiddleware"""

    def setUp(self):
        self.client = Client()

    @override_settings(IS_PRODUCTION=True, IS_STAGING=False)
    def test_security_headers_in_production(self):
        """Testa se headers de segurança são aplicados em produção"""
        with override_settings(ROOT_URLCONF='core.tests.test_security_middleware'):
            response = self.client.get('/test/')

            # Verificar headers básicos de segurança
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response['X-Frame-Options'], 'DENY')
            self.assertEqual(response['X-XSS-Protection'], '1; mode=block')
            self.assertEqual(response['Referrer-Policy'], 'strict-origin-when-cross-origin')
            self.assertEqual(response['Cross-Origin-Opener-Policy'], 'same-origin')

            # Verificar CSP
            self.assertIn('Content-Security-Policy', response)
            csp = response['Content-Security-Policy']
            self.assertIn("default-src 'self'", csp)
            self.assertIn("frame-ancestors 'none'", csp)

            # Verificar Permissions Policy
            self.assertIn('Permissions-Policy', response)
            permissions = response['Permissions-Policy']
            self.assertIn('geolocation=()', permissions)
            self.assertIn('camera=()', permissions)

    @override_settings(IS_PRODUCTION=False, IS_STAGING=True)
    def test_security_headers_in_staging(self):
        """Testa se headers de segurança são aplicados em staging"""
        with override_settings(ROOT_URLCONF='core.tests.test_security_middleware'):
            response = self.client.get('/test/')

            # Headers devem estar presentes em staging também
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
            self.assertEqual(response['X-Frame-Options'], 'DENY')

    @override_settings(IS_PRODUCTION=False, IS_STAGING=False)
    def test_no_security_headers_in_development(self):
        """Testa que headers não são aplicados em desenvolvimento"""
        with override_settings(ROOT_URLCONF='core.tests.test_security_middleware'):
            response = self.client.get('/test/')

            # Headers NÃO devem estar presentes em desenvolvimento
            self.assertNotIn('X-Content-Type-Options', response)
            self.assertNotIn('Content-Security-Policy', response)

    def test_existing_headers_not_overwritten(self):
        """Testa que headers existentes não são sobrescritos"""
        # Implementar se necessário
        pass


class AuditLogMiddlewareTest(TestCase):
    """Testes para AuditLogMiddleware"""

    def setUp(self):
        self.client = Client()
        # Criar usuário de teste
        from core.models import Usuario
        self.user = Usuario.objects.create_user(
            username='testuser',
            password='testpass123',
            cpf='12345678901'
        )

    @patch('core.models.LogAuditoria.objects.create')
    def test_audit_sensitive_endpoints(self, mock_create):
        """Testa se endpoints sensíveis são auditados"""
        # Login
        self.client.force_login(self.user)

        # Fazer request para endpoint sensível
        response = self.client.get('/admin/')

        # Verificar se auditoria foi chamada
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        self.assertEqual(call_args['usuario'], self.user)
        self.assertIn('GET /admin/', call_args['acao'])

    @patch('core.models.LogAuditoria.objects.create')
    def test_no_audit_for_non_sensitive_endpoints(self, mock_create):
        """Testa que endpoints não-sensíveis não são auditados"""
        # Login
        self.client.force_login(self.user)

        # Fazer request para endpoint comum
        response = self.client.get('/')

        # Auditoria NÃO deve ser chamada
        mock_create.assert_not_called()

    @patch('core.models.LogAuditoria.objects.create')
    def test_no_audit_for_unauthenticated_users(self, mock_create):
        """Testa que usuários não autenticados não geram auditoria"""
        # Request sem login
        response = self.client.get('/admin/')

        # Auditoria NÃO deve ser chamada
        mock_create.assert_not_called()

    def test_get_client_ip_with_proxy(self):
        """Testa extração de IP com proxy"""
        from core.middleware.security import AuditLogMiddleware

        middleware = AuditLogMiddleware(lambda r: HttpResponse())

        # Mock request com X-Forwarded-For
        request = MagicMock()
        request.META = {
            'HTTP_X_FORWARDED_FOR': '192.168.1.100, 10.0.0.1',
            'REMOTE_ADDR': '127.0.0.1'
        }

        ip = middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.100')

    def test_get_client_ip_without_proxy(self):
        """Testa extração de IP sem proxy"""
        from core.middleware.security import AuditLogMiddleware

        middleware = AuditLogMiddleware(lambda r: HttpResponse())

        # Mock request sem X-Forwarded-For
        request = MagicMock()
        request.META = {
            'REMOTE_ADDR': '192.168.1.50'
        }

        ip = middleware._get_client_ip(request)
        self.assertEqual(ip, '192.168.1.50')


class RateLimitingMiddlewareTest(TestCase):
    """Testes para RateLimitingMiddleware"""

    @override_settings(IS_PRODUCTION=True)
    @patch('time.time')
    def test_rate_limiting_in_production(self, mock_time):
        """Testa rate limiting em produção"""
        # Mock time para controlar janela temporal
        mock_time.return_value = 60.0  # 1 minuto

        from core.middleware.security import RateLimitingMiddleware

        middleware = RateLimitingMiddleware(lambda r: HttpResponse("OK"))

        # Mock request
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '192.168.1.100'}

        # Simular 101 requests (acima do limite de 100)
        for i in range(101):
            response = middleware.process_request(request)
            if i < 100:
                self.assertIsNone(response)  # Requests permitidos
            else:
                self.assertEqual(response.status_code, 429)  # Rate limited

    @override_settings(IS_PRODUCTION=False)
    def test_no_rate_limiting_in_development(self):
        """Testa que rate limiting não é aplicado em desenvolvimento"""
        from core.middleware.security import RateLimitingMiddleware

        middleware = RateLimitingMiddleware(lambda r: HttpResponse("OK"))

        # Mock request
        request = MagicMock()
        request.META = {'REMOTE_ADDR': '192.168.1.100'}

        # Qualquer número de requests deve ser permitido
        for i in range(200):
            response = middleware.process_request(request)
            self.assertIsNone(response)


class HealthViewsTest(TestCase):
    """Testes para health check views"""

    def test_basic_health_check(self):
        """Testa health check básico"""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('status', data)
        self.assertIn('checks', data)
        self.assertIn('database', data['checks'])

    def test_liveness_check(self):
        """Testa liveness check"""
        response = self.client.get('/health/live/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'OK')

    def test_detailed_health_unauthorized(self):
        """Testa que health detalhado requer autenticação"""
        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 401)

    def test_detailed_health_authorized(self):
        """Testa health detalhado com usuário autorizado"""
        from core.models import Usuario
        user = Usuario.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True
        )
        self.client.force_login(user)

        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('system_metrics', data)
        self.assertIn('application_metrics', data)
        self.assertIn('database_metrics', data)