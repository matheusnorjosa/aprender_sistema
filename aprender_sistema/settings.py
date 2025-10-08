"""
Django settings for aprender_sistema project - DOCKER CENTRALIZED
==================================================================

Sistema centralizado 100% em Docker com Django REST Framework
Configuração unificada para desenvolvimento e produção

Para mais informações: docs/DOCKER_CENTRALIZED.md
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ========================================
# DOCUMENTATION ROOT
# ========================================
# Diretório centralizado para toda documentação gerada
DOCS_ROOT = Path(os.getenv("DOCS_ROOT", BASE_DIR / "docs"))
DOCS_ROOT.mkdir(parents=True, exist_ok=True)

# ========================================
# ENVIRONMENT CONFIGURATION
# ========================================
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_DEVELOPMENT = ENVIRONMENT == "development"
IS_PRODUCTION = ENVIRONMENT == "production"

# ========================================
# SECURITY SETTINGS
# ========================================
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-insecure-key-only-for-local-development-do-not-use-in-production-51-chars",
)

DEBUG = os.getenv("DEBUG", "True") == "True" if IS_DEVELOPMENT else False

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

# ========================================
# APPLICATION DEFINITION
# ========================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    # Local apps
    "core",
    "api",
    "ingestao",  # Canonical import commands (Hotfix Dia 3)
    "dashboard",  # KPIs canônicos (Auditoria Full)
]

# Custom User Model
AUTH_USER_MODEL = "core.Usuario"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS deve vir antes do CommonMiddleware
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
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aprender_sistema.wsgi.application"

# ========================================
# DATABASE (DOCKER POSTGRESQL)
# ========================================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "aprender_sistema_db"),
        "USER": os.getenv("DB_USER", "adm_aprender"),
        "PASSWORD": os.getenv("DB_PASSWORD", "aprender123456"),
        "HOST": os.getenv("DB_HOST", "db"),  # Nome do serviço Docker
        "PORT": os.getenv("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Fallback para SQLite em desenvolvimento local (temporário)
if IS_DEVELOPMENT and os.getenv("USE_SQLITE", "False") == "True":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ========================================
# PASSWORD VALIDATION
# ========================================
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ========================================
# INTERNATIONALIZATION
# ========================================
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True

# ========================================
# STATIC FILES (CSS, JavaScript, Images)
# ========================================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ========================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ========================================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ========================================
# AUTHENTICATION
# ========================================
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Custom User Model
AUTH_USER_MODEL = "core.Usuario"

# ========================================
# DJANGO REST FRAMEWORK
# ========================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DATE_FORMAT": "%Y-%m-%d",
    "TIME_FORMAT": "%H:%M:%S",
}

# ========================================
# CORS CONFIGURATION (para React)
# ========================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # Django
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

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

# ========================================
# CACHE (Redis via django-redis em todos os ambientes)
# ========================================
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://redis:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,  # Fallback para DB se Redis falhar
        },
        "KEY_PREFIX": "aprender",
        "TIMEOUT": 300,  # 5 minutos padrão
    }
}

# ========================================
# LOGGING
# ========================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO" if IS_PRODUCTION else "DEBUG",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file"],
            "level": "DEBUG" if IS_DEVELOPMENT else "INFO",
            "propagate": False,
        },
    },
}

# ========================================
# SECURITY SETTINGS (Produção)
# ========================================
if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ========================================
# GOOGLE APIS (para importação de planilhas)
# ========================================
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_SHEETS_CREDENTIALS_FILE",
    str(BASE_DIR / "credentials" / "google_sheets_credentials.json"),
)

# ========================================
# DOCKER SPECIFIC SETTINGS
# ========================================
# Ajustar timeouts para containers Docker
SESSION_COOKIE_AGE = 3600 * 24 * 7  # 7 dias
SESSION_SAVE_EVERY_REQUEST = True

# ========================================
# SYSTEM INFORMATION (para debug)
# ========================================
SYSTEM_INFO = {
    "ENVIRONMENT": ENVIRONMENT,
    "DEBUG": DEBUG,
    "DATABASE": DATABASES["default"]["ENGINE"],
    "CACHE": CACHES["default"]["BACKEND"],
    "DOCKER_MODE": os.getenv("DOCKER_MODE", "True") == "True",
}

# ========================================
# FEATURE FLAGS
# ========================================
# Controle de funcionalidades experimentais e ferramentas de desenvolvimento

# MCP Tools - Apenas em desenvolvimento ou com flag explícita
MCP_TOOLS_ENABLED = (
    os.getenv("MCP_TOOLS_ENABLED", "False" if IS_PRODUCTION else "True") == "True"
)
MCP_DEBUG_MODE = (
    os.getenv("MCP_DEBUG_MODE", "False" if IS_PRODUCTION else "True") == "True"
)

# Google Integrations
GOOGLE_CALENDAR_ENABLED = os.getenv("GOOGLE_CALENDAR_ENABLED", "True") == "True"
GOOGLE_SHEETS_ENABLED = os.getenv("GOOGLE_SHEETS_ENABLED", "True") == "True"

# Analytics e Dashboards
ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "True") == "True"
DASHBOARD_DEBUG = (
    os.getenv("DASHBOARD_DEBUG", "False" if IS_PRODUCTION else "True") == "True"
)

# APIs Experimentais
EXPERIMENTAL_APIS_ENABLED = (
    os.getenv("EXPERIMENTAL_APIS_ENABLED", "False" if IS_PRODUCTION else "True")
    == "True"
)

# Logs e Auditoria
AUDIT_LOGS_ENABLED = os.getenv("AUDIT_LOGS_ENABLED", "True") == "True"
DETAILED_LOGGING = (
    os.getenv("DETAILED_LOGGING", "False" if IS_PRODUCTION else "True") == "True"
)

# ========================================
# FEATURE FLAGS VALIDATION
# ========================================
# Garantir que MCP tools não sejam expostos em produção
if IS_PRODUCTION and MCP_TOOLS_ENABLED:
    import warnings

    warnings.warn(
        "MCP_TOOLS_ENABLED está ativo em produção! "
        "Isso pode expor ferramentas de desenvolvimento.",
        UserWarning,
    )

# Exibir info no console (apenas em desenvolvimento)
if IS_DEVELOPMENT and DEBUG:
    print("\n" + "=" * 60)
    print("🐳 SISTEMA APRENDER - DOCKER CENTRALIZED")
    print("=" * 60)
    for key, value in SYSTEM_INFO.items():
        print(f"  {key}: {value}")

    print("\n🔧 FEATURE FLAGS:")
    print(f"  MCP_TOOLS_ENABLED: {MCP_TOOLS_ENABLED}")
    print(f"  GOOGLE_CALENDAR_ENABLED: {GOOGLE_CALENDAR_ENABLED}")
    print(f"  GOOGLE_SHEETS_ENABLED: {GOOGLE_SHEETS_ENABLED}")
    print(f"  ANALYTICS_ENABLED: {ANALYTICS_ENABLED}")
    print(f"  EXPERIMENTAL_APIS_ENABLED: {EXPERIMENTAL_APIS_ENABLED}")
    print("=" * 60 + "\n")

# ========================================
# FEATURE FLAGS (Hotfix 06/10)
# ========================================
FEATURE_SUPER_FALLBACK = (
    False  # Mostra todos formadores+coordenadores atÃ© backfill de setores
)
FEATURE_MAP_DESLOCAMENTOS_ENABLED = (
    True  # Desabilitado atÃ© migration de Deslocamento->Usuario
)

# ========================================
# GOOGLE SHEETS INTEGRATION
# ========================================
# Caminho para Service Account (JSON)
# Pode ser configurado via ENV ou usar o caminho padrão em /app/creds/
import os as _os

GSHEETS_SA_PATH = _os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS", "/app/creds/gsheet_sa.json"
)
