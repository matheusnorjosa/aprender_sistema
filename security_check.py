#!/usr/bin/env python
import json
import os
import sys

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")
django.setup()

from django.conf import settings


def analyze_security_settings():
    """Analisa as configurações de segurança do Django"""

    security_config = {
        "DEBUG": getattr(settings, "DEBUG", None),
        "SECRET_KEY_LENGTH": len(getattr(settings, "SECRET_KEY", "")),
        "SECRET_KEY_PREFIX": (
            getattr(settings, "SECRET_KEY", "")[:20] + "..."
            if hasattr(settings, "SECRET_KEY")
            else None
        ),
        "SECRET_KEY_SECURE": not getattr(settings, "SECRET_KEY", "").startswith(
            "django-insecure-"
        ),
        "ALLOWED_HOSTS": getattr(settings, "ALLOWED_HOSTS", []),
        "SECURE_SSL_REDIRECT": getattr(settings, "SECURE_SSL_REDIRECT", False),
        "SECURE_HSTS_SECONDS": getattr(settings, "SECURE_HSTS_SECONDS", None),
        "SESSION_COOKIE_SECURE": getattr(settings, "SESSION_COOKIE_SECURE", False),
        "CSRF_COOKIE_SECURE": getattr(settings, "CSRF_COOKIE_SECURE", False),
        "SECURE_CONTENT_TYPE_NOSNIFF": getattr(
            settings, "SECURE_CONTENT_TYPE_NOSNIFF", False
        ),
        "SECURE_BROWSER_XSS_FILTER": getattr(
            settings, "SECURE_BROWSER_XSS_FILTER", False
        ),
        "X_FRAME_OPTIONS": getattr(settings, "X_FRAME_OPTIONS", None),
        "MIDDLEWARE": getattr(settings, "MIDDLEWARE", []),
        "INSTALLED_APPS": getattr(settings, "INSTALLED_APPS", []),
    }

    # Análise de risco
    security_issues = []

    if security_config["DEBUG"]:
        security_issues.append(
            {
                "level": "HIGH",
                "issue": "DEBUG=True em produção",
                "description": "Pode expor informações sensíveis",
            }
        )

    if security_config["SECRET_KEY_LENGTH"] < 50:
        security_issues.append(
            {
                "level": "HIGH",
                "issue": "SECRET_KEY muito curta",
                "description": f'Comprimento: {security_config["SECRET_KEY_LENGTH"]} (recomendado: 50+)',
            }
        )

    if not security_config["SECRET_KEY_SECURE"]:
        security_issues.append(
            {
                "level": "HIGH",
                "issue": "SECRET_KEY insegura",
                "description": "Usando chave gerada automaticamente pelo Django",
            }
        )

    if not security_config["SECURE_SSL_REDIRECT"]:
        security_issues.append(
            {
                "level": "MEDIUM",
                "issue": "SECURE_SSL_REDIRECT=False",
                "description": "Não força redirecionamento HTTPS",
            }
        )

    if not security_config["SESSION_COOKIE_SECURE"]:
        security_issues.append(
            {
                "level": "MEDIUM",
                "issue": "SESSION_COOKIE_SECURE=False",
                "description": "Cookies de sessão podem ser transmitidos via HTTP",
            }
        )

    if not security_config["CSRF_COOKIE_SECURE"]:
        security_issues.append(
            {
                "level": "MEDIUM",
                "issue": "CSRF_COOKIE_SECURE=False",
                "description": "Cookies CSRF podem ser transmitidos via HTTP",
            }
        )

    return security_config, security_issues


if __name__ == "__main__":
    config, issues = analyze_security_settings()

    result = {
        "timestamp": "2025-08-30T05:00:00Z",
        "security_config": config,
        "security_issues": issues,
        "risk_level": (
            "HIGH"
            if any(i["level"] == "HIGH" for i in issues)
            else "MEDIUM" if issues else "LOW"
        ),
    }

    print(json.dumps(result, indent=2))
