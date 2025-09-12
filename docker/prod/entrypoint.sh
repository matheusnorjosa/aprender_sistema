#!/bin/bash
# ======================================
# 🚀 PRODUCTION ENTRYPOINT
# Sistema Aprender - Produção
# ======================================

set -e

echo "🚀 Starting Sistema Aprender - Production Mode"
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
    exit 1
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Validate required environment variables
print_step "Validating environment variables..."
required_vars=(
    "SECRET_KEY"
    "DATABASE_URL"
    "ALLOWED_HOSTS"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable $var is not set"
    fi
done
print_status "Environment variables validated!"

# Wait for database to be ready
if [[ $DATABASE_URL == *"postgresql"* ]]; then
    print_step "Waiting for PostgreSQL..."
    # Extract host and port from DATABASE_URL
    db_host=$(python -c "
import os
from urllib.parse import urlparse
url = urlparse(os.environ['DATABASE_URL'])
print(url.hostname)
")
    db_port=$(python -c "
import os
from urllib.parse import urlparse
url = urlparse(os.environ['DATABASE_URL'])
print(url.port or 5432)
")
    
    while ! nc -z "$db_host" "$db_port"; do
        sleep 1
        echo -n "."
    done
    print_status "Database is ready!"
fi

# Apply database migrations
print_step "Applying database migrations..."
python manage.py migrate --noinput || print_error "Database migration failed"

# Collect static files
print_step "Collecting static files..."
python manage.py collectstatic --noinput --clear || print_error "Static files collection failed"

# Validate Django configuration
print_step "Validating Django configuration..."
python manage.py check --deploy || print_error "Django configuration validation failed"

# Configure Nginx
print_step "Configuring Nginx..."
nginx -t || print_error "Nginx configuration test failed"

# Set proper permissions
print_step "Setting file permissions..."
chown -R appuser:appuser /app/logs
chown -R appuser:appuser /app/media
chown -R www-data:www-data /app/staticfiles

print_status "========================================="
print_status "🎉 Sistema Aprender ready for production!"
print_status "🌐 Application: http://$(hostname)"
print_status "📊 Health check: http://$(hostname)/health/"
print_status "========================================="

# Execute the main command
exec "$@"