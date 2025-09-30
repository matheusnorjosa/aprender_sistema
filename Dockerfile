# ======================================
# 🐳 DOCKERFILE UNIFICADO - SISTEMA APRENDER
# Multi-stage build para Dev/Prod/Test
# ======================================

# =============================================================================
# BASE STAGE - Dependências comuns
# =============================================================================
FROM python:3.13-slim as base

# Metadados
LABEL maintainer="Sistema Aprender <aprender-sistema@aprendereditora.com.br>"
LABEL description="Sistema Aprender - Dockerfile Unificado"
LABEL version="2.0.0"

# Variáveis de ambiente base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Essenciais
    curl \
    netcat-openbsd \
    ca-certificates \
    # PostgreSQL
    postgresql-client \
    libpq-dev \
    # Build tools (para algumas dependências Python)
    gcc \
    build-essential \
    # Processamento de imagem
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m -s /bin/bash appuser

# Definir diretório de trabalho
WORKDIR /app

# =============================================================================
# DEVELOPMENT STAGE - Para desenvolvimento local
# =============================================================================
FROM base as development

# Instalar ferramentas de desenvolvimento
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements padrão
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install django-debug-toolbar django-extensions ipython pytest pytest-django

# Copiar código fonte
COPY --chown=appuser:appuser . .

# Criar diretórios necessários
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appuser /app

# Health check para desenvolvimento
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Definir usuário
USER appuser

# Expor porta
EXPOSE 8000

# Comando padrão para desenvolvimento
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# =============================================================================
# BUILDER STAGE - Para construir dependências de produção
# =============================================================================
FROM base as builder

# Instalar dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt ./

# Instalar dependências Python no diretório local do usuário
USER appuser
RUN pip install --user --upgrade pip \
    && pip install --user -r requirements.txt \
    && pip install --user gunicorn whitenoise

# =============================================================================
# PRODUCTION STAGE - Para produção otimizada
# =============================================================================
FROM base as production

# Instalar dependências de produção
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    supervisor \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependências Python do builder
COPY --from=builder /home/appuser/.local /home/appuser/.local

# Copiar código fonte
COPY --chown=appuser:appuser . .

# Configurações nginx e supervisor
COPY docker/configs/nginx/ /etc/nginx/
COPY docker/configs/supervisor/ /etc/supervisor/

# Criar diretórios necessários
RUN mkdir -p /app/staticfiles /app/media /app/logs /var/log/supervisor \
    && chown -R appuser:appuser /app

# Coletar arquivos estáticos como appuser
USER appuser
RUN python manage.py collectstatic --noinput --clear

# Voltar para root para supervisor
USER root

# Health check para produção
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/health/ || exit 1

# Expor portas
EXPOSE 80 443

# Script de inicialização
COPY docker/configs/scripts/entrypoint-prod.sh /entrypoint-prod.sh
RUN chmod +x /entrypoint-prod.sh

# Comando padrão para produção
ENTRYPOINT ["/entrypoint-prod.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]

# =============================================================================
# TEST STAGE - Para testes automatizados
# =============================================================================
FROM development as test

# Instalar dependências de teste
USER appuser
RUN pip install --user coverage factory-boy mock pytest-cov

# Comando padrão para testes
CMD ["python", "manage.py", "test"]
