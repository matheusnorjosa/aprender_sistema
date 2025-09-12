# ======================================
# 🚀 DOCKERFILE - PRODUÇÃO (MULTI-STAGE)
# Sistema Aprender - Ambiente Otimizado
# ======================================

# ==========================================
# STAGE 1: Build Dependencies
# ==========================================
FROM python:3.13-slim as builder

# Build environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg-dev \
        libpng-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --user --no-warn-script-location -r requirements.txt

# ==========================================
# STAGE 2: Runtime Production
# ==========================================
FROM python:3.13-slim as production

# Metadata
LABEL maintainer="Sistema Aprender Team"
LABEL version="1.0.0" 
LABEL description="Production container for Sistema Aprender"
LABEL environment="production"

# Production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH" \
    ENVIRONMENT=production \
    DEBUG=false

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Database client
        postgresql-client \
        # Web server
        nginx \
        # Process management
        supervisor \
        # Utilities
        curl \
        netcat-openbsd \
        # SSL certificates
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Create non-root user for security
RUN groupadd -r appuser \
    && useradd -r -g appuser -d /app -s /bin/bash appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories with proper permissions
RUN mkdir -p \
        /app/staticfiles \
        /app/media \
        /app/logs \
        /var/log/supervisor \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker/prod/entrypoint.sh

# Collect static files
USER appuser
RUN python manage.py collectstatic --noinput --clear

# Switch back to root for supervisor
USER root

# Copy configuration files
COPY docker/prod/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/prod/nginx.conf /etc/nginx/sites-available/default

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost/health/ || exit 1

# Expose ports
EXPOSE 80 443

# Use supervisor as main process
ENTRYPOINT ["/app/docker/prod/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]