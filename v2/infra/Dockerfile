FROM python:3.11-slim
WORKDIR /app

# Copy requirements first (better layer caching)
COPY backend/requirements.txt /app/requirements.txt
COPY backend/requirements-dev.txt /app/requirements-dev.txt

# Install production dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# === Dev tools sempre instaladas (modo único) ===
RUN apt-get update && apt-get install -y --no-install-recommends \
    jq httpie vim nano tree less tzdata ca-certificates libpq5 \
 && rm -rf /var/lib/apt/lists/*

# === Python pacotes de dados/cli (modo único) ===
RUN pip install --no-cache-dir \
    ipython==8.26.0 \
    pgcli==4.1.0 \
    pandas==2.2.2 \
    openpyxl==3.1.5 \
    pyarrow==15.0.2 \
    rapidfuzz==3.6.1 \
    requests==2.32.3 \
    tqdm==4.66.4 \
    csvkit==1.3.0 \
    pytest-watch==4.2.0

COPY backend /app

# === BUILD INFO ===
ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
RUN python - <<'PY2'
import json, os
with open("/app/BUILD_INFO.json","w") as f:
    json.dump({
      "git_sha": os.environ.get("GIT_SHA","unknown"),
      "build_date": os.environ.get("BUILD_DATE","unknown"),
      "note": "Single-mode image. Rebuild web após mudanças."
    }, f, indent=2)
print("Wrote /app/BUILD_INFO.json")
PY2

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
