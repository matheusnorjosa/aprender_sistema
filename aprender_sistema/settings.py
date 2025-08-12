# aprender_sistema/settings.py
from pathlib import Path
import os

# Diretórios base
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------
# Segurança / Debug
# -------------------------------------------------------------------
# ⚠️ NÃO deixe a SECRET_KEY fixa em produção.
# Defina no ambiente (compose) e mantenha um fallback apenas para dev.
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "dev-insecure-key-only-for-local"
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("1", "true", "yes", "on")

# Em dev no Docker, manter hosts locais:
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

# Opcional: se for acessar via http://localhost:8000 no navegador
# e tiver POST/CSRF, isto evita aviso de CSRF em proxies/ports
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
]

# -------------------------------------------------------------------
# Aplicativos
# -------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Seus apps
    "core",
    "relatorios",
    "api",
]

# Ativa django-extensions apenas em ambiente de desenvolvimento
if os.getenv("DJANGO_ENV", "development") == "development":
    INSTALLED_APPS.append("django_extensions")

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
        "DIRS": [BASE_DIR / "templates"],  # opcional: crie a pasta templates/
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

# -------------------------------------------------------------------
# Banco de Dados (casado com docker-compose)
# -------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "aprender_sistema_db"),
        "USER": os.getenv("DB_USER", "adm_aprender"),
        "PASSWORD": os.getenv("DB_PASSWORD", "aprender123456"),
        "HOST": os.getenv("DB_HOST", "db"),   # serviço do compose
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# -------------------------------------------------------------------
# Autenticação
# -------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "core.Usuario"  # seu user custom

# -------------------------------------------------------------------
# i18n / L10n
# -------------------------------------------------------------------
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True  # mantém dados em UTC no banco; exibição ajusta ao TIME_ZONE

# -------------------------------------------------------------------
# Arquivos estáticos e mídia
# -------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"      # destino do collectstatic (prod)
STATICFILES_DIRS = [BASE_DIR / "static"]    # pasta de estáticos do projeto (dev)

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# -------------------------------------------------------------------
# Default primary key
# -------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -------------------------------------------------------------------
# Logging simples (útil em dev)
# -------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
}
