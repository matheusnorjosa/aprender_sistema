#!/usr/bin/env bash
set -euo pipefail

cd /app

# Espera banco subir
python - <<'PY'
import os, time, psycopg2
host=os.getenv("POSTGRES_HOST","db")
db=os.getenv("POSTGRES_DB","aprender_db")
user=os.getenv("POSTGRES_USER","aprender_user")
pwd=os.getenv("POSTGRES_PASSWORD","aprender_pass")
for i in range(60):
    try:
        psycopg2.connect(host=host, dbname=db, user=user, password=pwd).close()
        print("DB OK"); break
    except Exception as e:
        print("Aguardando DB...", e); time.sleep(1)
PY

python manage.py migrate

MODE="${RUN_MODE:-dev}"
if [ "$MODE" = "prod" ]; then
  echo "Iniciando Gunicorn (prod)"
  exec gunicorn aprender_sistema.wsgi:application -b 0.0.0.0:8000 --workers 3 --timeout 120
else
  echo "Iniciando runserver (dev)"
  exec python manage.py runserver 0.0.0.0:8000
fi
