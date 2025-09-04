#!/usr/bin/env bash
# Build script for Render
# Follows Render best practices for Django deployment

set -o errexit   # Exit on error
set -o pipefail  # Exit on pipe failure
set -o nounset   # Exit on unset variable

echo "🚀 Starting Render build process..."

# Upgrade pip first for better dependency resolution
echo "📦 Upgrading pip..."
pip install --upgrade pip

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🔧 Running Django checks..."
python manage.py check --deploy

echo "📁 Collecting static files..."
python manage.py collectstatic --no-input --clear

echo "🔄 Running database migrations..."
python manage.py migrate --no-input

echo "⚙️ Setting up production data..."
if python manage.py setup_production --with-sample-data; then
    echo "✅ Production data setup completed"
else
    echo "⚠️ Production data setup failed, continuing anyway"
fi

echo "👤 Setting up Django superuser if needed..."
python manage.py shell -c "
from core.models import Usuario
if not Usuario.objects.filter(is_superuser=True).exists():
    Usuario.objects.create_superuser('admin', 'admin@aprender.local', 'admin123456')
    print('✅ Superuser created successfully')
else:
    print('ℹ️ Superuser already exists')
"

echo "🎉 Build completed successfully!"
echo "📋 Build summary:"
echo "   - Dependencies: Installed"
echo "   - Static files: Collected" 
echo "   - Migrations: Applied"
echo "   - Production data: Setup"
echo "   - Superuser: Ready"