FROM python:3.11-slim
WORKDIR /app

# Copy requirements first (better layer caching)
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements-dev.txt /app/requirements-dev.txt

# Install production dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# === DEVTOOLS (opcional) =======================================================
ARG INSTALL_DEVTOOLS=0
RUN if [ "$INSTALL_DEVTOOLS" = "1" ]; then \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      jq httpie vim nano tree less && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r /app/requirements-dev.txt; \
    fi
# ===============================================================================

COPY backend /app
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
