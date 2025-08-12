#!/bin/sh
# entrypoint.sh

echo "Waiting for postgres..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# Executa o comando principal da aplicação (python manage.py runserver)
exec "$@"
