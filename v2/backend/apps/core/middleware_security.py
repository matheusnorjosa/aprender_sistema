"""
Security Middleware - AS v2

Implementa headers de segurança adicionais não cobertos pelo Django.

Security Audit 2025-01:
- Content-Security-Policy (CSP)
- Permissions-Policy

Refs:
- https://github.com/shieldfy/API-Security-Checklist
- https://github.com/astoj/vibe-security
- OWASP Secure Headers Project
"""

from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse


class SecurityHeadersMiddleware:
    """
    Middleware que adiciona headers de segurança às respostas HTTP.

    Headers implementados:
    - Content-Security-Policy: Previne XSS e injeção de código
    - Permissions-Policy: Restringe APIs do browser

    Uso:
        MIDDLEWARE = [
            ...
            'apps.core.middleware_security.SecurityHeadersMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        # Skip para respostas de streaming
        if getattr(response, "streaming", False):
            return response

        # ================================================================
        # Content-Security-Policy (CSP)
        # ================================================================
        # Política restritiva mas compatível com Ant Design e React.
        # Para /api/docs/ e /api/redoc/ liberamos somente os CDNs usados
        # pelas páginas de documentação do drf-spectacular.
        is_api_docs = request.path.startswith("/api/docs") or request.path.startswith("/api/redoc")

        # - 'self': Permite recursos do mesmo domínio
        # - 'unsafe-inline': Necessário para Ant Design inline styles
        # - data:: Necessário para imagens base64 (ícones, avatars)
        # - blob:: Necessário para download de arquivos
        script_src = "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
        style_src = "style-src 'self' 'unsafe-inline'"
        font_src = "font-src 'self' data:"
        img_src = "img-src 'self' data: blob: https:"
        worker_src = None

        if is_api_docs:
            script_src += " https://cdn.jsdelivr.net"
            style_src += " https://cdn.jsdelivr.net https://fonts.googleapis.com"
            font_src += " https://fonts.gstatic.com"
            img_src += " https://cdn.jsdelivr.net"
            # ReDoc usa Web Worker em URL blob: para parsing do schema.
            worker_src = "worker-src 'self' blob:"

        csp_directives = [
            "default-src 'self'",
            script_src,  # React em dev precisa de eval
            style_src,  # Ant Design usa inline styles
            img_src,  # Imagens de qualquer HTTPS
            font_src,  # Fontes locais e data URIs
            "connect-src 'self' https://api.github.com",  # APIs permitidas
            "frame-ancestors 'none'",  # Previne clickjacking (como X-Frame-Options)
            "base-uri 'self'",  # Previne ataques de base tag
            "form-action 'self'",  # Forms só podem submeter para o mesmo domínio
            "object-src 'none'",  # Bloqueia plugins (Flash, etc)
            "upgrade-insecure-requests",  # Força upgrade HTTP -> HTTPS
        ]

        if worker_src:
            csp_directives.insert(5, worker_src)

        response["Content-Security-Policy"] = "; ".join(csp_directives)

        # ================================================================
        # Permissions-Policy (antiga Feature-Policy)
        # ================================================================
        # Restringe APIs do browser que podem ser abusadas
        # Formato: feature=(allowlist)
        permissions_directives = [
            "accelerometer=()",  # Não usa acelerômetro
            "autoplay=()",  # Não precisa de autoplay
            "camera=()",  # Não usa câmera
            "cross-origin-isolated=()",
            "display-capture=()",  # Não captura tela
            "encrypted-media=()",
            "fullscreen=(self)",  # Fullscreen só no próprio domínio
            "geolocation=()",  # Não usa geolocalização
            "gyroscope=()",  # Não usa giroscópio
            "magnetometer=()",  # Não usa magnetômetro
            "microphone=()",  # Não usa microfone
            "midi=()",  # Não usa MIDI
            "payment=()",  # Não usa Payment API
            "picture-in-picture=()",  # Não usa PiP
            "publickey-credentials-get=()",  # WebAuthn desativado
            "screen-wake-lock=()",  # Não precisa manter tela ligada
            "usb=()",  # Não usa USB
            "xr-spatial-tracking=()",  # Não usa XR
        ]

        response["Permissions-Policy"] = ", ".join(permissions_directives)

        return response
