# ========= Base =========
FROM python:3.13-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Fortaleza
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libffi-dev curl netcat-traditional tzdata ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

# ========= Runtime (usa em dev e prod) =========
FROM base AS runtime
WORKDIR /app
COPY . /app
# entrypoint decide runserver vs gunicorn
RUN chmod +x entrypoint.sh || true \
    && mkdir -p /app/logs /app/staticfiles \
    && chown -R 1000:1000 /app/logs /app/staticfiles \
    && chmod 777 /app/logs /app/staticfiles
ENV DJANGO_SETTINGS_MODULE=aprender_sistema.settings \
    STATIC_ROOT=/app/staticfiles
EXPOSE 8000

# ========= Build estáticos (prod-like) =========
FROM runtime AS static_build
WORKDIR /app
RUN python manage.py collectstatic --noinput || true

# ========= Prod final =========
FROM python:3.13-slim AS prod
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Fortaleza
RUN apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=base /usr/local/lib/python3.13 /usr/local/lib/python3.13
COPY --from=base /usr/local/bin /usr/local/bin
COPY . /app
COPY --from=static_build /app/staticfiles /app/staticfiles
RUN chmod +x entrypoint.sh || true
ENV DJANGO_SETTINGS_MODULE=aprender_sistema.settings \
    STATIC_ROOT=/app/staticfiles
EXPOSE 8000
CMD ["bash","-lc","./entrypoint.sh"]
