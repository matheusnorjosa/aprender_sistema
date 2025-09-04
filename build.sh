#!/usr/bin/env bash
# Build script for Render

set -o errexit  # Exit on error

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running migrations..."
python manage.py migrate

echo "Setting up production data..."
python manage.py setup_production --with-sample-data

echo "Setting up Django superuser if needed..."
echo "from core.models import Usuario; Usuario.objects.filter(is_superuser=True).exists() or Usuario.objects.create_superuser('admin', 'admin@aprender.local', 'admin123456')" | python manage.py shell

echo "Build completed successfully!"