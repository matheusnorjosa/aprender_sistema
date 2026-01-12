#!/bin/bash
#
# setup_vm03.sh — Setup script for VM03_Redis
# Referência: PLAN_infrastructure_scaling.md
#
# Usage:
#   sudo ./setup_vm03.sh
#

set -e

echo "=== Setup VM03_Redis ==="
echo "Date: $(date)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Install Redis
echo "--- Installing Redis ---"
apt update
apt install -y redis-server

# Create log directory
echo "--- Creating directories ---"
mkdir -p /var/log/redis
chown redis:redis /var/log/redis

# Copy configuration
echo "--- Copying configuration ---"
if [ -f "configs/vm03/redis.conf" ]; then
    cp /etc/redis/redis.conf /etc/redis/redis.conf.bak
    cp configs/vm03/redis.conf /etc/redis/redis.conf
    chown redis:redis /etc/redis/redis.conf
    echo "Redis config copied"
fi

# Restart Redis
echo "--- Restarting Redis ---"
systemctl restart redis-server
systemctl enable redis-server

# Test connection
echo "--- Testing Redis ---"
sleep 2
if redis-cli -a CHANGE_ME_STRONG_PASSWORD ping | grep -q PONG; then
    echo "Redis is running and responding"
else
    echo "Warning: Redis may not be configured correctly"
fi

echo ""
echo "=== VM03 Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Change Redis password in /etc/redis/redis.conf"
echo "2. Update bind address if needed"
echo "3. Configure firewall to allow connections from VM01 only"
