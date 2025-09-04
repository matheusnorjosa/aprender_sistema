#!/usr/bin/env python
"""
VALIDAÇÃO 5: Teste de Segurança HTTPS e Cookies
"""
import importlib
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aprender_sistema.settings")


def test_security_features():
    print("=== VALIDAÇÃO 5: SEGURANÇA HTTPS & COOKIES ===")

    # 1. TESTAR CONFIGURAÇÕES DE DESENVOLVIMENTO
    print("\n1. Testando configuracoes de desenvolvimento...")
    os.environ["ENVIRONMENT"] = "development"
    django.setup()

    from django.conf import settings

    print(f'OK ENVIRONMENT: {os.getenv("ENVIRONMENT", "development")}')
    print(f"OK DEBUG: {settings.DEBUG}")
    print(f'OK SECURE_SSL_REDIRECT: {getattr(settings, "SECURE_SSL_REDIRECT", False)}')
    print(
        f'OK SESSION_COOKIE_SECURE: {getattr(settings, "SESSION_COOKIE_SECURE", False)}'
    )
    print(f'OK CSRF_COOKIE_SECURE: {getattr(settings, "CSRF_COOKIE_SECURE", False)}')
    print(f'OK SECURE_HSTS_SECONDS: {getattr(settings, "SECURE_HSTS_SECONDS", 0)}')

    # 2. SIMULAR CONFIGURAÇÕES DE PRODUÇÃO
    print("\n2. Simulando configuracoes de producao...")

    # Recarregar settings com produção
    import django.conf

    os.environ.update(
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "test-production-key-with-more-than-50-characters-for-security-validation-purposes",
            "ALLOWED_HOSTS": "exemplo.com,www.exemplo.com",
            "DB_PASSWORD": "test_password",
        }
    )

    # Limpar cache do settings
    if hasattr(django.conf.settings, "_wrapped"):
        delattr(django.conf.settings, "_wrapped")

    django.setup()
    from django.conf import settings

    print(f'OK ENVIRONMENT: {os.getenv("ENVIRONMENT")}')
    print(f"OK DEBUG: {settings.DEBUG}")
    print(f'OK SECURE_SSL_REDIRECT: {getattr(settings, "SECURE_SSL_REDIRECT", False)}')
    print(
        f'OK SESSION_COOKIE_SECURE: {getattr(settings, "SESSION_COOKIE_SECURE", False)}'
    )
    print(f'OK CSRF_COOKIE_SECURE: {getattr(settings, "CSRF_COOKIE_SECURE", False)}')
    print(f'OK SECURE_HSTS_SECONDS: {getattr(settings, "SECURE_HSTS_SECONDS", 0)}')
    print(
        f'OK SECURE_CONTENT_TYPE_NOSNIFF: {getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False)}'
    )
    print(
        f'OK SECURE_BROWSER_XSS_FILTER: {getattr(settings, "SECURE_BROWSER_XSS_FILTER", False)}'
    )
    print(f'OK X_FRAME_OPTIONS: {getattr(settings, "X_FRAME_OPTIONS", "SAMEORIGIN")}')

    # 3. VERIFICAR OUTRAS CONFIGURAÇÕES DE SEGURANÇA
    print("\n3. Verificando outras configuracoes de seguranca...")
    print(f"OK ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"OK SECRET_KEY length: {len(settings.SECRET_KEY)} chars")
    print(
        f'OK CSRF_COOKIE_HTTPONLY: {getattr(settings, "CSRF_COOKIE_HTTPONLY", False)}'
    )
    print(
        f'OK SESSION_COOKIE_HTTPONLY: {getattr(settings, "SESSION_COOKIE_HTTPONLY", True)}'
    )

    # 4. VALIDAR HEADERS DE SEGURANÇA
    print("\n4. Validando headers de seguranca esperados...")

    security_headers = [
        ("SECURE_SSL_REDIRECT", "Redireciona HTTP -> HTTPS"),
        ("SESSION_COOKIE_SECURE", "Cookies de sessão apenas HTTPS"),
        ("CSRF_COOKIE_SECURE", "Cookies CSRF apenas HTTPS"),
        ("SECURE_HSTS_SECONDS", "HTTP Strict Transport Security"),
        ("SECURE_CONTENT_TYPE_NOSNIFF", "Previne MIME sniffing"),
        ("SECURE_BROWSER_XSS_FILTER", "Proteção XSS browser"),
        ("X_FRAME_OPTIONS", "Proteção clickjacking"),
    ]

    for header, desc in security_headers:
        value = getattr(settings, header, None)
        status = "OK" if value else "X"
        print(f"  {status} {header}: {value} - {desc}")

    # 5. MIDDLEWARE DE SEGURANÇA
    print("\n5. Verificando middleware de seguranca...")
    security_middlewares = [
        "django.middleware.security.SecurityMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
    ]

    for middleware in security_middlewares:
        if middleware in settings.MIDDLEWARE:
            print(f"  OK {middleware}")
        else:
            print(f"  X {middleware} - NÃO ENCONTRADO")

    # 6. CHECKLIST FINAL DE SEGURANÇA
    print("\n6. Checklist final de seguranca:")

    checklist = [
        ("Debug desabilitado em produção", not settings.DEBUG),
        ("SSL redirect habilitado", getattr(settings, "SECURE_SSL_REDIRECT", False)),
        (
            "Cookies seguros habilitados",
            getattr(settings, "SESSION_COOKIE_SECURE", False),
        ),
        ("HSTS configurado", getattr(settings, "SECURE_HSTS_SECONDS", 0) > 0),
        ("Secret key segura", len(settings.SECRET_KEY) >= 50),
        ("Allowed hosts configurado", len(settings.ALLOWED_HOSTS) > 0),
        ("XSS protection", getattr(settings, "SECURE_BROWSER_XSS_FILTER", False)),
        (
            "Content type nosniff",
            getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False),
        ),
    ]

    passed = 0
    for check, status in checklist:
        status_symbol = "OK" if status else "X"
        print(f"  {status_symbol} {check}")
        if status:
            passed += 1

    print(f"\nRESULTADO: {passed}/{len(checklist)} checks de segurança passaram")

    print("\n=== VALIDAÇÃO 5 CONCLUÍDA ===")
    return passed == len(checklist)


if __name__ == "__main__":
    test_security_features()
