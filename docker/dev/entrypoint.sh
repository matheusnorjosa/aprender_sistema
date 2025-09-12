#!/bin/bash
# ======================================
# 🛠️ DEVELOPMENT ENTRYPOINT
# Sistema Aprender - Desenvolvimento
# ======================================

set -e

echo "🚀 Starting Sistema Aprender - Development Mode"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Wait for PostgreSQL to be ready
print_step "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
    sleep 0.5
    echo -n "."
done
print_status "PostgreSQL is ready!"

# Apply database migrations
print_step "Applying database migrations..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Create superuser if it doesn't exist
print_step "Checking for superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@aprender.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️  Superuser already exists')
"

# Load initial data if fixtures exist
if [ -d "fixtures" ] && [ "$(ls -A fixtures)" ]; then
    print_step "Loading initial data..."
    python manage.py loaddata fixtures/*.json
    print_status "Initial data loaded!"
fi

# Collect static files for development
print_step "Collecting static files..."
python manage.py collectstatic --noinput --clear || print_warning "Static files collection failed (non-critical in development)"

# Install pre-commit hooks if in development
if [ "$ENVIRONMENT" = "development" ]; then
    print_step "Installing pre-commit hooks..."
    if command -v pre-commit &> /dev/null; then
        pre-commit install || print_warning "Pre-commit installation failed (non-critical)"
    else
        print_warning "Pre-commit not available"
    fi
fi

print_status "========================================="
print_status "🎉 Sistema Aprender ready for development!"
print_status "📝 Admin panel: http://localhost:8000/admin"
print_status "👤 Superuser: admin / admin123"
print_status "🏠 Main app: http://localhost:8000/"
print_status "========================================="

# Execute the main command
exec "$@"