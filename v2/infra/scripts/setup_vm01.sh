#!/bin/bash
# Setup VM01_App - Initial server configuration
# Run once on a fresh Ubuntu Server 22.04/24.04
#
# Usage: sudo ./setup_vm01.sh

set -e

echo "=== Setup VM01_App ==="

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Update system
echo "--- Updating system ---"
apt update && apt upgrade -y

# Install dependencies
echo "--- Installing dependencies ---"
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    nginx \
    git \
    build-essential \
    libpq-dev \
    curl \
    htop \
    vim

# Create application user
echo "--- Creating aprender user ---"
if ! id "aprender" &>/dev/null; then
    useradd -r -s /bin/false -m -d /var/www/aprender aprender
fi

# Create directory structure
echo "--- Creating directories ---"
mkdir -p /var/www/aprender/{backend,frontend,static,media}
mkdir -p /var/log/aprender
mkdir -p /run/aprender
mkdir -p /etc/aprender

# Setup Python virtual environment
echo "--- Setting up virtualenv ---"
python3.12 -m venv /var/www/aprender/venv
/var/www/aprender/venv/bin/pip install --upgrade pip wheel setuptools

# Set permissions
echo "--- Setting permissions ---"
chown -R aprender:aprender /var/www/aprender
chown -R aprender:aprender /var/log/aprender
chown -R aprender:aprender /run/aprender
chmod 755 /var/www/aprender
chmod 755 /var/log/aprender

# Setup logrotate
echo "--- Setting up logrotate ---"
cat > /etc/logrotate.d/aprender << 'EOF'
/var/log/aprender/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 aprender aprender
    sharedscripts
    postrotate
        systemctl reload aprender-gunicorn > /dev/null 2>&1 || true
    endscript
}
EOF

# Create tmpfiles.d for runtime directory
echo "--- Setting up tmpfiles.d ---"
cat > /etc/tmpfiles.d/aprender.conf << 'EOF'
d /run/aprender 0755 aprender aprender -
EOF
systemd-tmpfiles --create

echo ""
echo "=== VM01 Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy nginx config to /etc/nginx/"
echo "2. Copy gunicorn config to /etc/aprender/"
echo "3. Copy systemd services to /etc/systemd/system/"
echo "4. Enable services: systemctl enable aprender-gunicorn aprender-celery aprender-celerybeat"
echo "5. Configure SSL certificates"
echo "6. Run deploy.sh"
