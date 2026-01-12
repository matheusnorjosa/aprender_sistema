#!/bin/bash
# Deploy script for Aprender Sistema v2
# Run on VM01_App to deploy latest code
#
# Usage: ./deploy.sh [--skip-frontend] [--skip-migrations]

set -e

DEPLOY_DIR="/var/www/aprender"
BACKEND_DIR="$DEPLOY_DIR/backend"
FRONTEND_DIR="$DEPLOY_DIR/frontend"
VENV="$DEPLOY_DIR/venv"
BRANCH="${BRANCH:-main}"

# Parse arguments
SKIP_FRONTEND=false
SKIP_MIGRATIONS=false
for arg in "$@"; do
    case $arg in
        --skip-frontend)
            SKIP_FRONTEND=true
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            ;;
    esac
done

echo "=== Deploy AS v2 ==="
echo "Branch: $BRANCH"
echo "Skip frontend: $SKIP_FRONTEND"
echo "Skip migrations: $SKIP_MIGRATIONS"
echo ""

# Check if running as aprender user
if [ "$USER" != "aprender" ]; then
    echo "Warning: Not running as aprender user. Some operations may fail."
fi

# 1. Pull latest code
echo "--- Pulling latest code ---"
cd $DEPLOY_DIR
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

# 2. Backend setup
echo "--- Backend setup ---"
cd $BACKEND_DIR
source $VENV/bin/activate

echo "Installing Python dependencies..."
pip install -r requirements.txt --quiet

if [ "$SKIP_MIGRATIONS" = false ]; then
    echo "Running migrations..."
    python manage.py migrate --noinput
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# 3. Frontend build (if not skipped)
if [ "$SKIP_FRONTEND" = false ]; then
    echo "--- Frontend build ---"
    cd $FRONTEND_DIR

    if [ -f "package-lock.json" ]; then
        npm ci --quiet
    else
        npm install --quiet
    fi

    npm run build
fi

# 4. Restart services
echo "--- Restarting services ---"
sudo systemctl restart aprender-gunicorn
sudo systemctl restart aprender-celery
sudo systemctl restart aprender-celerybeat
sudo systemctl reload nginx

# 5. Health check
echo "--- Health check ---"
sleep 5

HEALTH_URL="http://localhost/healthz/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo "Health check passed!"
else
    echo "Health check failed! HTTP code: $HTTP_CODE"
    echo "Check logs: journalctl -u aprender-gunicorn -n 50"
    exit 1
fi

# 6. Print status
echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Service status:"
systemctl is-active aprender-gunicorn || true
systemctl is-active aprender-celery || true
systemctl is-active aprender-celerybeat || true
systemctl is-active nginx || true
