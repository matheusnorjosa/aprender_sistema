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

echo "Build completed successfully!"