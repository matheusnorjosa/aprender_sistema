"""
Security Middleware for Aprender Sistema
=======================================

Implementa headers de segurança adicionais para proteção contra
vulnerabilidades web comuns.

Author: Claude Code
Date: Janeiro 2025
"""

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware que adiciona headers de segurança customizados

    Headers implementados:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: controle de APIs do browser
    - Content-Security-Policy: política básica de segurança
    """

    # Compatibilidade com Django 5.2+
    async_mode = False
    sync_mode = True

    def process_response(self, request, response):
        """Adiciona headers de segurança na resposta"""

        # Só aplicar em produção e staging
        if not (getattr(settings, 'IS_PRODUCTION', False) or
                getattr(settings, 'IS_STAGING', False)):
            return response

        # Headers básicos de segurança
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Cross-Origin-Opener-Policy': 'same-origin',
            # Removido Cross-Origin-Embedder-Policy que bloqueia recursos externos
        }

        # Permissions Policy
        permissions_policy = [
            'geolocation=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'fullscreen=(self)',
            'autoplay=()',
        ]
        security_headers['Permissions-Policy'] = ', '.join(permissions_policy)

        # Content Security Policy - usar configurações do settings.py
        if not response.get('Content-Security-Policy'):
            csp_directives = []
            
            # Usar configurações do settings.py se disponíveis
            if hasattr(settings, 'CSP_DEFAULT_SRC'):
                csp_directives.append(f"default-src {' '.join(settings.CSP_DEFAULT_SRC)}")
            else:
                csp_directives.append("default-src 'self'")
                
            if hasattr(settings, 'CSP_SCRIPT_SRC'):
                csp_directives.append(f"script-src {' '.join(settings.CSP_SCRIPT_SRC)}")
            else:
                csp_directives.append("script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://d3js.org")
                
            if hasattr(settings, 'CSP_STYLE_SRC'):
                csp_directives.append(f"style-src {' '.join(settings.CSP_STYLE_SRC)}")
            else:
                csp_directives.append("style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com")
                
            if hasattr(settings, 'CSP_IMG_SRC'):
                csp_directives.append(f"img-src {' '.join(settings.CSP_IMG_SRC)}")
            else:
                csp_directives.append("img-src 'self' data: https:")
                
            if hasattr(settings, 'CSP_FONT_SRC'):
                csp_directives.append(f"font-src {' '.join(settings.CSP_FONT_SRC)}")
            else:
                csp_directives.append("font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.gstatic.com")
                
            if hasattr(settings, 'CSP_CONNECT_SRC'):
                csp_directives.append(f"connect-src {' '.join(settings.CSP_CONNECT_SRC)}")
            else:
                csp_directives.append("connect-src 'self' https://cdn.jsdelivr.net")
            
            # Diretivas adicionais
            csp_directives.extend([
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'",
            ])
            
            security_headers['Content-Security-Policy'] = '; '.join(csp_directives)

        # Aplicar todos os headers
        for header, value in security_headers.items():
            if not response.get(header):
                response[header] = value

        return response


class RateLimitingMiddleware(MiddlewareMixin):
    """
    Middleware simples de rate limiting por IP

    Limita requests por IP para prevenir abuse.
    Em produção seria melhor usar Redis/Memcached.
    """

    # Compatibilidade com Django 5.2+
    async_mode = False
    sync_mode = True

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # Em produção usar cache distribuído

    def process_request(self, request):
        """Verifica rate limiting por IP"""

        # Só aplicar em produção
        if not getattr(settings, 'IS_PRODUCTION', False):
            return None

        # Obter IP real (considerando proxies)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Rate limiting simples (100 requests por minuto)
        # Em produção implementar com sliding window no Redis
        import time
        current_time = int(time.time() / 60)  # Janela de 1 minuto

        key = f"{ip}:{current_time}"
        self.request_counts[key] = self.request_counts.get(key, 0) + 1

        # Limpar entradas antigas
        keys_to_remove = [k for k in self.request_counts.keys()
                         if int(k.split(':')[1]) < current_time - 5]
        for k in keys_to_remove:
            del self.request_counts[k]

        # Verificar limite
        if self.request_counts[key] > 100:
            from django.http import HttpResponseTooManyRequests
            return HttpResponseTooManyRequests(
                "Rate limit exceeded. Try again later.",
                content_type="text/plain"
            )

        return None


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware para auditoria de requests sensíveis

    Registra automaticamente requests para endpoints críticos
    no LogAuditoria do sistema E em logs estruturados.
    """

    # Compatibilidade com Django 5.2+
    async_mode = False
    sync_mode = True

    SENSITIVE_PATHS = [
        '/admin/',
        '/api/',
        '/controle/',
        '/aprovacoes/',
        '/health/detailed/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        # Logger específico para auditoria
        import logging
        self.audit_logger = logging.getLogger('core.audit')
        self.security_logger = logging.getLogger('core.security')

    def process_response(self, request, response):
        """Registra requests para endpoints sensíveis"""

        # Verificar se é endpoint sensível
        path = request.path_info
        is_sensitive = any(path.startswith(sensitive) for sensitive in self.SENSITIVE_PATHS)

        if is_sensitive:
            audit_data = {
                'event_type': 'request_audit',
                'method': request.method,
                'path': path,
                'status_code': response.status_code,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                'user_id': request.user.id if request.user.is_authenticated else None,
                'username': request.user.username if request.user.is_authenticated else 'anonymous',
                'session_key': request.session.session_key if hasattr(request, 'session') else None,
                'referer': request.META.get('HTTP_REFERER', '')[:200],
                'content_length': response.get('Content-Length', 0),
                'response_time_ms': getattr(request, '_start_time', None) and
                                  int((timezone.now().timestamp() - request._start_time) * 1000) or None,
            }

            # Log estruturado para monitoramento
            self.audit_logger.info(
                f"Audit: {request.method} {path} -> {response.status_code}",
                extra=audit_data
            )

            # Log de segurança para requests suspeitos
            if response.status_code >= 400 or not request.user.is_authenticated:
                self.security_logger.warning(
                    f"Security: Suspicious request {request.method} {path} -> {response.status_code}",
                    extra=audit_data
                )

            # Registrar no banco (só se usuário autenticado e sucesso)
            if request.user.is_authenticated and response.status_code < 400:
                try:
                    from core.models import LogAuditoria
                    LogAuditoria.objects.create(
                        usuario=request.user,
                        acao=f"{request.method} {path}",
                        detalhes={
                            'ip': audit_data['ip_address'],
                            'user_agent': audit_data['user_agent'],
                            'status_code': audit_data['status_code'],
                            'referer': audit_data['referer'],
                        }
                    )
                except Exception as e:
                    # Log error mas não quebrar request
                    self.audit_logger.error(
                        f"Failed to save audit log to database: {e}",
                        extra={'error': str(e), **audit_data}
                    )

        return response

    def process_request(self, request):
        """Adiciona timestamp para medir response time"""
        from django.utils import timezone
        request._start_time = timezone.now().timestamp()
        return None

    def _get_client_ip(self, request):
        """Obtém IP real do cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')