"""
Django settings for aprender_sistema project - CONFIGURAÇÃO UNIFICADA
==========================================

Esta configuração única funciona para desenvolvimento, homologação e produção
usando variáveis de ambiente para diferenciar os comportamentos.

Ambientes suportados:
- ENVIRONMENT=development (padrão) - PostgreSQL local, DEBUG=True
- ENVIRONMENT=staging - PostgreSQL Docker, DEBUG=True
- ENVIRONMENT=production - PostgreSQL produção, SSL, DEBUG=False

Para usar:
- Desenvolvimento: ENVIRONMENT=development
- Docker: ENVIRONMENT=staging
- Produção: ENVIRONMENT=production + variáveis necessárias
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv("config_unificado.env")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# CONFIGURAÇÃO DE AMBIENTE
# ======================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_STAGING = ENVIRONMENT == "staging"
IS_PRODUCTION = ENVIRONMENT == "production"

# ======================
# CONFIGURAÇÕES DE SEGURANÇA
# ======================

# Secret Key - Usa chave segura em produção
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-insecure-key-only-for-local-development-do-not-use-in-production-51-chars",
)

# Debug
DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes", "on")

# Allowed Hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

# ======================
# CONFIGURAÇÃO DE DATABASE UNIFICADA
# ======================

# Configuração única para todos os ambientes
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "aprender_sistema_db"),
        "USER": os.getenv("DB_USER", "adm_aprender"),
        "PASSWORD": os.getenv("DB_PASSWORD", "aprender123456"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 60,
        },
    }
}

# SSL obrigatório em produção
if IS_PRODUCTION:
    DATABASES["default"]["OPTIONS"]["sslmode"] = "require"

# ======================
# CONFIGURAÇÃO DE CACHE UNIFICADA
# ======================

CACHES = {
    "default": {
        "BACKEND": os.getenv("CACHE_BACKEND", "django_redis.cache.RedisCache"),
        "LOCATION": os.getenv("CACHE_LOCATION", "redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# ======================
# CONFIGURAÇÃO DE EMAIL UNIFICADA
# ======================

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("1", "true", "yes", "on")

# ======================
# CONFIGURAÇÃO DE CELERY UNIFICADA
# ======================

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ======================
# CONFIGURAÇÕES DJANGO PADRÃO
# ======================

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_celery_beat",
    "django_celery_results",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.security.SecurityMiddleware",
]

ROOT_URLCONF = "aprender_sistema.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aprender_sistema.wsgi.application"

# ======================
# CONFIGURAÇÕES DE INTERNACIONALIZAÇÃO
# ======================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

# ======================
# CONFIGURAÇÕES DE ARQUIVOS ESTÁTICOS
# ======================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================
# CONFIGURAÇÕES DE SEGURANÇA
# ======================

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

# CSRF
CSRF_COOKIE_SECURE = IS_PRODUCTION
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

# Session
SESSION_COOKIE_SECURE = IS_PRODUCTION
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"

# ======================
# CONFIGURAÇÕES DE LOGGING
# ======================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.getenv("LOG_FILE", "logs/django.log"),
            "formatter": "verbose",
        },
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# ======================
# CONFIGURAÇÕES DJANGO REST FRAMEWORK
# ======================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# ======================
# CONFIGURAÇÕES ESPECÍFICAS DO PROJETO
# ======================

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE", "google_oauth_token.json"
)
GOOGLE_SHEETS_CONTROLE_ID = os.getenv(
    "GOOGLE_SHEETS_CONTROLE_ID", "1P6YG3sIAEpiAPIQL9bKBaIznNl3V9VLan9CpVnrEOgA"
)
GOOGLE_SHEETS_AGENDA_ID = os.getenv(
    "GOOGLE_SHEETS_AGENDA_ID", "16ul8qvHb-1CRs5Z7zYcVP9Rh2munCefWWNsAiJfZYYU"
)

# MCP Server
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "3001"))
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST", "localhost")

# Streamlit - removido
# STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
# STREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "localhost")

# ======================
# RESUMO DA CONFIGURAÇÃO
# ======================

if DEBUG:
    print("=" * 60)
    print("🔧 CONFIGURAÇÃO UNIFICADA CARREGADA")
    print("=" * 60)
    print(f"🌍 Ambiente: {ENVIRONMENT}")
    print(f"🐛 Debug: {DEBUG}")
    print(f"🗄️ Database: {DATABASES['default']['ENGINE']}")
    print(f"🗄️ Database Host: {DATABASES['default']['HOST']}")
    print(f"🗄️ Database Port: {DATABASES['default']['PORT']}")
    print(f"🗄️ Database Name: {DATABASES['default']['NAME']}")
    print(f"💾 Cache: {CACHES['default']['BACKEND']}")
    print(f"📧 Email: {EMAIL_BACKEND}")
    print(f"🔑 Secret Key: {'***' if len(SECRET_KEY) > 10 else SECRET_KEY}")
    print("=" * 60)
