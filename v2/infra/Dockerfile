# ================================================================
# AS v2 — Multi-Stage Dockerfile
# ================================================================
# Stage 1: Builder (dependencies)
# Stage 2: Runtime (production)
# ================================================================

# ================================================================
# STAGE 1: Builder
# ================================================================
FROM python:3.13-slim AS builder

# Metadados
LABEL maintainer="Equipe Aprender <dev@aprender.com.br>"
LABEL description="Aprender Sistema v2 — Builder stage"

# Variáveis de build
ARG DEBIAN_FRONTEND=noninteractive
ARG PIP_NO_CACHE_DIR=1
ARG PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependências de sistema (apenas para build)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar requirements
COPY backend/requirements-minimal.txt /tmp/requirements.txt

# Instalar dependências Python
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# ================================================================
# STAGE 2: Runtime
# ================================================================
FROM python:3.13-slim AS runtime

# Metadados
LABEL maintainer="Equipe Aprender <dev@aprender.com.br>"
LABEL description="Aprender Sistema v2 — Runtime"
LABEL version="2.0.0"

# Argumentos de build
ARG APP_HOME=/app
ARG APP_USER=appuser
ARG APP_GROUP=appgroup
ARG DEBIAN_FRONTEND=noninteractive

# Variáveis de ambiente globais
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Instalar dependências de runtime (mínimas)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN groupadd --gid 1000 ${APP_GROUP} && \
    useradd --uid 1000 --gid ${APP_GROUP} --shell /bin/bash --create-home ${APP_USER}

# Criar diretórios da aplicação
RUN mkdir -p ${APP_HOME} \
    ${APP_HOME}/static \
    ${APP_HOME}/media \
    ${APP_HOME}/logs \
    && chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Copiar virtualenv do builder
COPY --from=builder /opt/venv /opt/venv

# Definir workdir
WORKDIR ${APP_HOME}

# Copiar código da aplicação
COPY --chown=${APP_USER}:${APP_GROUP} backend/ ${APP_HOME}/
COPY --chown=${APP_USER}:${APP_GROUP} infra/entrypoint.sh ${APP_HOME}/entrypoint.sh

# Dar permissão de execução ao entrypoint
RUN chmod +x ${APP_HOME}/entrypoint.sh

# Coletar arquivos estáticos (build time)
# RUN python manage.py collectstatic --noinput

# Criar arquivo .dockerenv para detecção (REQUIRE_DOCKER guard)
RUN touch /.dockerenv

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Trocar para usuário não-root
USER ${APP_USER}

# Expor porta
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Comando padrão (pode ser sobrescrito)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
