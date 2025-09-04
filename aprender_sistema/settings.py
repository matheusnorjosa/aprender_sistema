"""
Django settings for aprender_sistema project - VERSÃO UNIFICADA
==========================================

Esta configuração única funciona para desenvolvimento, homologação e produção
usando variáveis de ambiente para diferenciar os comportamentos.

Ambientes suportados:
- ENVIRONMENT=development (padrão) - SQLite, DEBUG=True
- ENVIRONMENT=production - PostgreSQL, SSL, DEBUG=False
- ENVIRONMENT=staging - Configurações intermediárias

Para usar:
- Desenvolvimento: Não precisa definir nada (padrão)
- Produção: ENVIRONMENT=production + variáveis necessárias
"""

import os
import secrets
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ======================
# CONFIGURAÇÃO DE AMBIENTE
# ======================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_PRODUCTION = ENVIRONMENT == "production"
IS_STAGING = ENVIRONMENT == "staging"

# ======================
# CONFIGURAÇÕES DE SEGURANÇA
# ======================

# Secret Key - Usa chave segura em produção
if IS_PRODUCTION:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY é obrigatória em produção!")
else:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-insecure-key-only-for-local-development-do-not-use-in-production-51-chars",
    )

# Debug
DEBUG = IS_DEVELOPMENT or os.getenv("DEBUG", "False").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# Aviso sobre ambiente
if DEBUG:
    print(f"AMBIENTE: {ENVIRONMENT.upper()}")
    print(f"DEBUG: {DEBUG}")
    if IS_DEVELOPMENT:
        print("MODO DESENVOLVIMENTO - Para producao defina ENVIRONMENT=production")

# Allowed hosts
if IS_PRODUCTION:
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
        raise ValueError("ALLOWED_HOSTS é obrigatório em produção!")
else:
    # Desenvolvimento + Self-hosting via tunneling
    default_hosts = "localhost,127.0.0.1,0.0.0.0,10.0.230.13,.localtunnel.me,.ngrok.io,.pinggy.io,.trycloudflare.com"
    ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", default_hosts).split(",")

# ======================
# CONFIGURAÇÕES SSL/HTTPS (PRODUÇÃO)
# ======================
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# CSRF Trusted Origins - Configuração avançada
if IS_PRODUCTION:
    csrf_origins = os.getenv("CSRF_TRUSTED_ORIGINS", "")
    CSRF_TRUSTED_ORIGINS = (
        [origin.strip() for origin in csrf_origins.split(",") if origin.strip()]
        if csrf_origins
        else []
    )

    # Configurações CSRF adicionais para produção
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_HTTPONLY = True
    CSRF_COOKIE_SAMESITE = "Strict"
    CSRF_USE_SESSIONS = False  # Usar cookie ao invés de sessão para melhor performance

elif IS_STAGING:
    csrf_origins = os.getenv(
        "CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    )
    CSRF_TRUSTED_ORIGINS = [
        origin.strip() for origin in csrf_origins.split(",") if origin.strip()
    ]
    CSRF_COOKIE_SECURE = True  # Assumir HTTPS em staging também
    CSRF_COOKIE_HTTPONLY = True

else:
    # Desenvolvimento - configuração flexível
    CSRF_TRUSTED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
    ]
    CSRF_COOKIE_SECURE = False
    CSRF_COOKIE_HTTPONLY = True  # Sempre HTTP-only por segurança

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
    # Local apps
    "core",
    "relatorios",
    "api",
]

# Adicionar DRF apps se disponíveis
try:
    import rest_framework

    INSTALLED_APPS.extend(
        [
            "rest_framework",
            "rest_framework.authtoken",
        ]
    )
except ImportError:
    pass

try:
    import django_filters

    INSTALLED_APPS.append("django_filters")
except ImportError:
    pass

try:
    import corsheaders

    INSTALLED_APPS.append("corsheaders")
except ImportError:
    pass

# Django extensions apenas em desenvolvimento
if IS_DEVELOPMENT:
    INSTALLED_APPS.append("django_extensions")

# Adicionar libraries de migração
try:
    import import_export

    INSTALLED_APPS.append("import_export")
except ImportError:
    pass

# Celery apps para processamento assíncrono
try:
    import django_celery_beat
    import django_celery_results

    INSTALLED_APPS.extend(
        [
            "django_celery_beat",
            "django_celery_results",
        ]
    )
except ImportError:
    pass

# MCP Server integration
try:
    import django_mcp_server

    INSTALLED_APPS.append("django_mcp_server")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Adicionar CORS middleware se disponível
try:
    import corsheaders

    MIDDLEWARE.insert(1, "corsheaders.middleware.CorsMiddleware")
except ImportError:
    pass

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
                "django.contrib.auth.context_processors.perms",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aprender_sistema.wsgi.application"

# ======================
# CONFIGURAÇÃO DE DATABASE
# ======================

if IS_PRODUCTION or IS_STAGING:
    # PostgreSQL para produção/staging
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "aprender_sistema"),
            "USER": os.getenv("DB_USER", "aprender_user"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

    # SSL em produção
    if IS_PRODUCTION:
        DATABASES["default"]["OPTIONS"] = {"sslmode": "require"}

    # Validar senha obrigatória
    if not os.getenv("DB_PASSWORD"):
        raise ValueError(f"DB_PASSWORD é obrigatória em ambiente {ENVIRONMENT}!")

else:
    # SQLite para desenvolvimento
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ======================
# CONFIGURAÇÃO DE CACHE
# ======================

REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL and (IS_PRODUCTION or IS_STAGING):
    # Redis para produção/staging
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CONNECTION_POOL_KWARGS": {
                    "ssl_cert_reqs": None if not IS_PRODUCTION else "required",
                },
            },
        }
    }
    # Session usando cache em produção
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
else:
    # Fallback para desenvolvimento
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unified-cache",
            "TIMEOUT": 300,
        }
    }

# ======================
# CONFIGURAÇÃO DE EMAIL
# ======================

if IS_PRODUCTION:
    # SMTP para produção
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
    DEFAULT_FROM_EMAIL = os.getenv(
        "DEFAULT_FROM_EMAIL", "Sistema Aprender <noreply@yourdomain.com>"
    )
else:
    # Console para desenvolvimento
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    DEFAULT_FROM_EMAIL = "nao-responda@aprender.local"

# ======================
# HASH DE SENHAS (ARGON2)
# ======================

# Hashers configurados por ambiente
if IS_PRODUCTION and "argon2" in os.environ.get("AVAILABLE_HASHERS", ""):
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.Argon2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
        "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
        "django.contrib.auth.hashers.ScryptPasswordHasher",
    ]
else:
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        "django.contrib.auth.hashers.Argon2PasswordHasher",  # Fallback se disponível
        "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
        "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
        "django.contrib.auth.hashers.ScryptPasswordHasher",
    ]

# ======================
# VALIDAÇÃO DE SENHAS
# ======================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8 if IS_DEVELOPMENT else 12,  # Mais rigoroso em produção
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
# ARQUIVOS ESTÁTICOS
# ======================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

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
TRAVEL_BUFFER_MINUTES = 90  # Buffer mínimo entre municípios diferentes
MAX_DAILY_HOURS = 8  # Máximo de horas por formador por dia

# Feature flags
FEATURE_GOOGLE_SYNC = bool(int(os.getenv("FEATURE_GOOGLE_SYNC", "0")))
GOOGLE_CALENDAR_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_CALENDAR_ID", "primary")

# ======================
# CONFIGURAÇÕES DE LOGGING
# ======================

if IS_PRODUCTION:
    # Logging em arquivos para produção
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
            "file_error": {
                "level": "ERROR",
                "class": "logging.FileHandler",
                "filename": os.path.join(BASE_DIR, "logs", "error.log"),
                "formatter": "verbose",
            },
            "file_info": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": os.path.join(BASE_DIR, "logs", "info.log"),
                "formatter": "verbose",
            },
            "console": {
                "level": "INFO",
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
            "core": {
                "handlers": ["file_error", "file_info", "console"],
                "level": "INFO",
                "propagate": True,
            },
        },
    }
else:
    # Logging no console para desenvolvimento
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "INFO",
            },
        },
    }

# ======================
# CONFIGURAÇÕES DE PERFORMANCE
# ======================

if IS_PRODUCTION:
    # Session timeout (30 minutos)
    SESSION_COOKIE_AGE = 1800

    # Compressão
    USE_GZIP = True

# ======================
# VALIDAÇÕES DE PRODUÇÃO
# ======================

if IS_PRODUCTION:
    required_env_vars = [
        "SECRET_KEY",
        "ALLOWED_HOSTS",
        "DB_PASSWORD",
    ]

    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Variáveis de ambiente obrigatórias para produção: {missing_vars}"
        )

# ======================
# RESUMO DA CONFIGURAÇÃO
# ======================

if DEBUG:
    print(f"Ambiente: {ENVIRONMENT}")
    print(f"Debug: {DEBUG}")
    print(f"Database: {DATABASES['default']['ENGINE']}")
    print(f"Cache: {CACHES['default']['BACKEND']}")
    print(f"Email: {EMAIL_BACKEND}")

# ======================
# CONFIGURAÇÕES DJANGO REST FRAMEWORK
# ======================

REST_FRAMEWORK = {
    # Autenticação
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    # Permissões padrão
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Paginação
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "MAX_PAGINATE_BY": 100,
    # Filtros
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # Renderização
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if IS_DEVELOPMENT else []),
    # Parsing
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # Throttling (rate limiting)
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": (
        {"anon": "100/hour", "user": "1000/hour"}
        if IS_PRODUCTION
        else {"anon": "1000/hour", "user": "10000/hour"}
    ),
    # Configurações de teste
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "TEST_REQUEST_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # Configurações de schema
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
}

# ======================
# CONFIGURAÇÕES CORS
# ======================

# CORS para desenvolvimento
if IS_DEVELOPMENT:
    CORS_ALLOW_ALL_ORIGINS = True
    CORS_ALLOW_CREDENTIALS = True
else:
    # CORS para produção - configurar origins específicas
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ======================
# CONFIGURAÇÕES DE CACHE PARA API
# ======================

# Cache específico para API em produção
if IS_PRODUCTION and REDIS_URL:
    CACHES["api"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CONNECTION_POOL_KWARGS": {
                "ssl_cert_reqs": "required",
            },
        },
        "TIMEOUT": 300,
        "KEY_PREFIX": "api",
    }

# ======================
# CONFIGURAÇÕES DE LOGGING PARA API
# ======================

# Adicionar logger para API se em produção
if IS_PRODUCTION and "LOGGING" in locals():
    LOGGING["loggers"]["api"] = {
        "handlers": ["file_error", "file_info"],
        "level": "INFO",
        "propagate": True,
    }
    LOGGING["loggers"]["rest_framework"] = {
        "handlers": ["file_error", "file_info"],
        "level": "WARNING",
        "propagate": True,
    }

# ======================
# CONFIGURAÇÕES DO CELERY
# ======================

# Celery Configuration
# Celery Broker Configuration
# Em desenvolvimento: usar database como broker
# Em produção: usar Redis (configurar CELERY_BROKER_URL no environment)
if os.getenv("ENVIRONMENT", "development") == "production":
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )
else:
    # Para desenvolvimento: usar database como broker (mais simples)
    CELERY_BROKER_URL = "django-db://"
    CELERY_RESULT_BACKEND = "django-db://"

# Celery Settings
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Celery Beat (tarefas agendadas)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Otimizações para migração massiva
CELERY_TASK_ROUTES = {
    "core.tasks.migrate_*": {"queue": "migration"},
    "core.tasks.sync_google_*": {"queue": "google_sync"},
}

# Configurações para processamento em lote
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# ======================
# CONFIGURAÇÕES DE IMPORTAÇÃO
# ======================

# django-import-export settings
IMPORT_EXPORT_USE_TRANSACTIONS = True
IMPORT_EXPORT_CHUNK_SIZE = 500  # Processar em chunks de 500 registros
IMPORT_EXPORT_SKIP_ADMIN_LOG = False  # Manter logs de importação
IMPORT_EXPORT_TMP_STORAGE_CLASS = "import_export.tmp_storages.TempFolderStorage"

# Configurações específicas para migração massiva
BULK_CREATE_BATCH_SIZE = 1000  # Para bulk_create otimizado
MIGRATION_BATCH_SIZE = 500  # Para processamento em lotes
MIGRATION_TIMEOUT = 300  # Timeout em segundos para operações longas

# ======================
# CONFIGURAÇÕES DJANGO MCP SERVER
# ======================

# django-mcp-server settings
MCP_SERVERS = {
    "default": {
        "name": "Aprender Sistema MCP Server",
        "description": "MCP Server para o sistema de gestão educacional Aprender",
        "toolsets": [
            "core.mcp.toolsets.CoreModelToolset",
            "core.mcp.toolsets.SolicitacaoToolset",
            "core.mcp.toolsets.FormadorToolset",
        ],
        "auth": {
            "required": True,
            "type": "django_session",  # Usar autenticação Django existente
        },
    }
}

# Configurações específicas para desenvolvimento
if IS_DEVELOPMENT:
    MCP_SERVERS["default"]["debug"] = True
    MCP_SERVERS["default"]["auth"]["required"] = False  # Facilitar desenvolvimento
