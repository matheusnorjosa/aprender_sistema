"""
Configurações de produção para o Sistema Aprender.
Este arquivo sobrescreve as configurações de development para uso em produção.

Para usar em produção, defina: DJANGO_SETTINGS_MODULE=aprender_sistema.settings_production
"""

from .settings import *
import secrets

# ======================
# CONFIGURAÇÕES CRÍTICAS DE SEGURANÇA
# ======================

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# SECURITY WARNING: generate a secure secret key for production!
# Gerar nova chave: python -c "import secrets; print(secrets.token_urlsafe(50))"
SECRET_KEY = os.getenv(
    "SECRET_KEY_PRODUCTION",
    secrets.token_urlsafe(50)  # Gera automaticamente uma chave segura
)

# Hosts permitidos em produção - DEVE ser configurado com domínios reais
ALLOWED_HOSTS = os.getenv(
    "ALLOWED_HOSTS_PRODUCTION", 
    "yourdomain.com,www.yourdomain.com,your-server-ip"
).split(",")

# ======================
# CONFIGURAÇÕES SSL/HTTPS
# ======================

# Força redirecionamento HTTPS
SECURE_SSL_REDIRECT = True

# Headers de segurança SSL
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookies seguros
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Headers de segurança adicionais
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Content Security Policy básica
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ======================
# CONFIGURAÇÕES DE DATABASE PRODUÇÃO
# ======================

# PostgreSQL para produção (recomendado)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME_PRODUCTION', 'aprender_sistema_prod'),
        'USER': os.getenv('DB_USER_PRODUCTION', 'aprender_user'),
        'PASSWORD': os.getenv('DB_PASSWORD_PRODUCTION', 'change-this-password'),
        'HOST': os.getenv('DB_HOST_PRODUCTION', 'localhost'),
        'PORT': os.getenv('DB_PORT_PRODUCTION', '5432'),
        'OPTIONS': {
            'sslmode': 'require',  # SSL obrigatório para produção
        },
    }
}

# ======================
# CONFIGURAÇÕES DE CACHE (PRODUÇÃO)
# ======================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CONNECTION_POOL_KWARGS': {
                'ssl_cert_reqs': None,
            },
        }
    }
}

# Session storage usando cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ======================
# CONFIGURAÇÕES DE EMAIL (PRODUÇÃO)
# ======================

# Configurações SMTP para produção
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'your-email@domain.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Sistema Aprender <noreply@yourdomain.com>')

# ======================
# CONFIGURAÇÕES DE ARQUIVOS ESTÁTICOS
# ======================

# Configurações para servir arquivos estáticos em produção
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configurações de media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ======================
# CONFIGURAÇÕES DE LOGGING (PRODUÇÃO)
# ======================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file_error': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'error.log'),
            'formatter': 'verbose',
        },
        'file_info': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'info.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file_error', 'file_info', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['file_error', 'file_info', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# ======================
# CONFIGURAÇÕES ESPECÍFICAS DA APLICAÇÃO
# ======================

# Feature flags para produção
FEATURE_GOOGLE_SYNC = os.getenv('FEATURE_GOOGLE_SYNC_PROD', '1') == '1'

# CSRF trusted origins para produção
CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
    # Adicionar seus domínios reais aqui
]

# ======================
# CONFIGURAÇÕES DE PERFORMANCE
# ======================

# Compressão de resposta
USE_GZIP = True

# Session timeout (30 minutos)
SESSION_COOKIE_AGE = 1800

# ======================
# CONFIGURAÇÕES DE BACKUP
# ======================

# Configurações para backup automático
DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
DBBACKUP_STORAGE_OPTIONS = {'location': '/var/backups/aprender-sistema/'}

# ======================
# VALIDAÇÕES FINAIS
# ======================

# Verificar se variáveis críticas estão configuradas
required_env_vars = [
    'SECRET_KEY_PRODUCTION',
    'ALLOWED_HOSTS_PRODUCTION', 
    'DB_PASSWORD_PRODUCTION',
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Variáveis de ambiente obrigatórias não configuradas: {missing_vars}")

print("✅ Configurações de produção carregadas com sucesso!")
print(f"✅ DEBUG: {DEBUG}")
print(f"✅ SECRET_KEY length: {len(SECRET_KEY)} chars")
print(f"✅ ALLOWED_HOSTS: {ALLOWED_HOSTS[:2]}...")  # Não expor hosts completos no log