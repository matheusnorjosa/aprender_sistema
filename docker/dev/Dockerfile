# ======================================
# 🛠️ DOCKERFILE - DESENVOLVIMENTO
# Sistema Aprender - Ambiente Local
# ======================================

# Base image com Python 3.13
FROM python:3.13-slim as base

# Metadata
LABEL maintainer="Sistema Aprender Team"
LABEL version="1.0.0"
LABEL description="Development container for Sistema Aprender"

# Environment variables para desenvolvimento
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ENVIRONMENT=development \
    DEBUG=true

# Working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # Basic utilities
        curl \
        netcat-openbsd \
        # Development tools
        git \
        build-essential \
        # PostgreSQL client
        postgresql-client \
        # Image processing
        libjpeg-dev \
        libpng-dev \
        # SSL/TLS
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first (better Docker caching)
COPY requirements-dev.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements-dev.txt

# Copy application code
COPY --chown=appuser:appuser . .

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appuser /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Development entrypoint
ENTRYPOINT ["./docker/dev/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]