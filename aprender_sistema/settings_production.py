"""
Django settings for aprender_sistema project - PRODUÇÃO
===============================================

Configuração específica para ambiente de produção com hardening de segurança.
Baseado no settings.py unificado, com adições específicas para produção.

REQUISITOS DE AMBIENTE:
- SECRET_KEY (obrigatório, 50+ caracteres)
- ALLOWED_HOSTS (obrigatório, separado por vírgula)
- DB_PASSWORD (obrigatório)
- CSRF_TRUSTED_ORIGINS (recomendado)

VALIDAÇÃO:
python manage.py check --deploy --settings=aprender_sistema.settings_production
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# CONFIGURAÇÕES DE SEGURANÇA CRÍTICAS
# ======================

# Secret Key - OBRIGATÓRIA em produção
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY é obrigatória em produção!")

if len(SECRET_KEY) < 50:
    raise ValueError("SECRET_KEY deve ter pelo menos 50 caracteres para produção!")

# Debug SEMPRE False em produção
DEBUG = False

# Allowed hosts
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise ValueError("ALLOWED_HOSTS é obrigatório em produção!")

# Remove espaços em branco dos hosts
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host.strip()]

# ======================
# HARDENING SSL/HTTPS AVANÇADO
# ======================

# Força redirecionamento HTTPS
SECURE_SSL_REDIRECT = True

# HTTP Strict Transport Security (1 ano)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Configurações de segurança adiciais
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Proxy reverso (se usar nginx/apache)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_TZ = True

# CSRF Trusted Origins
csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = csrf_origins.split(",") if csrf_origins else []
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in CSRF_TRUSTED_ORIGINS if origin.strip()
]

# ======================
# HASH DE SENHAS SEGURO (ARGON2)
# ======================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

# ======================
# APPLICATION DEFINITION
# ======================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "relatorios",
    "api",
]

# Middleware com ordem otimizada para produção
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aprender_sistema.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aprender_sistema.wsgi.application"

# ======================
# CONFIGURAÇÃO DE DATABASE PRODUÇÃO
# ======================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "aprender_sistema"),
        "USER": os.getenv("DB_USER", "aprender_user"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "sslmode": "require",
            "connect_timeout": 60,
        },
        "CONN_MAX_AGE": 600,  # Pool de conexões
    }
}

# Validar senha obrigatória
if not os.getenv("DB_PASSWORD"):
    raise ValueError("DB_PASSWORD é obrigatória em produção!")

# ======================
# CACHE REDIS PRODUÇÃO
# ======================

REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {
                    "ssl_cert_reqs": "required",
                    "retry_on_timeout": True,
                },
            },
            "TIMEOUT": 300,
            "KEY_PREFIX": "aprender_sistema",
        }
    }
    # Session usando cache
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Fallback para database sessions
    SESSION_ENGINE = "django.contrib.sessions.backends.db"

# ======================
# EMAIL PRODUÇÃO
# ======================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Sistema Aprender <noreply@yourdomain.com>"
)

# Timeout para emails
EMAIL_TIMEOUT = 30

# ======================
# VALIDAÇÃO DE SENHAS RIGOROSA
# ======================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,  # Mínimo 12 caracteres em produção
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ======================
# CONFIGURAÇÕES REGIONAIS
# ======================

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

# ======================
# ARQUIVOS ESTÁTICOS PRODUÇÃO
# ======================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

# Compressão e cache de arquivos estáticos
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ======================
# CONFIGURAÇÕES DO SISTEMA
# ======================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "core.Usuario"

# URLs de autenticação
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Configurações específicas da aplicação
TRAVEL_BUFFER_MINUTES = 90
MAX_DAILY_HOURS = 8

# Feature flags
FEATURE_GOOGLE_SYNC = bool(int(os.getenv("FEATURE_GOOGLE_SYNC", "0")))
GOOGLE_CALENDAR_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_CALENDAR_ID", "primary")

# ======================
# LOGGING PRODUÇÃO
# ======================

# Criar diretório de logs se não existir
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "error.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "info.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "security": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "security.log",
            "maxBytes": 10 * 1024 * 1024,  # 10MB
            "backupCount": 10,
            "formatter": "verbose",
        },
        "console": {
            "level": "ERROR",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file_error", "file_info", "console"],
            "level": "INFO",
            "propagate": True,
        },
        "django.security": {
            "handlers": ["security"],
            "level": "WARNING",
            "propagate": False,
        },
        "core": {
            "handlers": ["file_error", "file_info"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# ======================
# CONFIGURAÇÕES DE PERFORMANCE PRODUÇÃO
# ======================

# Session timeout (2 horas)
SESSION_COOKIE_AGE = 7200
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Configurações de cookies
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_SAMESITE = "Strict"

# Admin hardening
ADMIN_URL = os.getenv("ADMIN_URL", "admin/")  # Permitir URL personalizada

# ======================
# MONITORAMENTO E SAÚDE
# ======================

# Configurações para health checks
HEALTH_CHECK_TIMEOUT = 5

# ======================
# VALIDAÇÕES OBRIGATÓRIAS PRODUÇÃO
# ======================

required_env_vars = [
    "SECRET_KEY",
    "ALLOWED_HOSTS",
    "DB_PASSWORD",
]

# Verificar variáveis obrigatórias
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(
        f"Variáveis de ambiente obrigatórias para produção: {missing_vars}"
    )

# Verificações de segurança
if DEBUG:
    raise ValueError("DEBUG nunca deve ser True em produção!")

if not SECRET_KEY or len(SECRET_KEY) < 50:
    raise ValueError("SECRET_KEY deve ter pelo menos 50 caracteres!")

if not ALLOWED_HOSTS:
    raise ValueError("ALLOWED_HOSTS deve estar configurado!")

print("Configuracao de producao carregada com sucesso")
print(f"Hosts permitidos: {ALLOWED_HOSTS}")
print(f"Hash de senhas: Argon2")
print(f"SSL/HTTPS: Ativado")
print(f"Logs: {LOGS_DIR}")
