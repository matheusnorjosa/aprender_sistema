#!/usr/bin/env bash
# Build script for Render

set -o errexit  # Exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Setting up groups if needed..."
python manage.py shell -c "
from django.contrib.auth.models import Group

groups = ['coordenador', 'superintendencia', 'controle', 'formador', 'diretoria', 'admin']
for group_name in groups:
    Group.objects.get_or_create(name=group_name)
    print(f'Group {group_name} ready')
"

echo "Build completed successfully!"