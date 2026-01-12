#!/bin/bash
#
# setup_vm02.sh — Setup script for VM02_Banco (PostgreSQL)
# Referência: PLAN_infrastructure_scaling.md
#
# Usage:
#   sudo ./setup_vm02.sh
#

set -e

echo "=== Setup VM02_Banco ==="
echo "Date: $(date)"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

# Install PostgreSQL 15
echo "--- Installing PostgreSQL 15 ---"
apt update
apt install -y postgresql-15 postgresql-contrib-15

# Create WAL archive directory
echo "--- Creating WAL archive directory ---"
mkdir -p /var/lib/postgresql/wal_archive
chown postgres:postgres /var/lib/postgresql/wal_archive

# Create backup directory
echo "--- Creating backup directory ---"
mkdir -p /var/backups/aprender
chown postgres:postgres /var/backups/aprender

# Copy configuration files
echo "--- Copying configuration files ---"
PG_CONF_DIR="/etc/postgresql/15/main"

if [ -f "configs/vm02/postgresql.conf" ]; then
    cp configs/vm02/postgresql.conf "$PG_CONF_DIR/conf.d/99-aprender.conf"
    echo "PostgreSQL config copied"
fi

if [ -f "configs/vm02/pg_hba.conf" ]; then
    # Backup original
    cp "$PG_CONF_DIR/pg_hba.conf" "$PG_CONF_DIR/pg_hba.conf.bak"
    cp configs/vm02/pg_hba.conf "$PG_CONF_DIR/pg_hba.conf"
    echo "pg_hba.conf copied"
fi

# Restart PostgreSQL
echo "--- Restarting PostgreSQL ---"
systemctl restart postgresql

# Create database and user
echo "--- Creating database and user ---"
sudo -u postgres psql <<EOF
-- Create user (change password!)
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'aprender_user') THEN
        CREATE USER aprender_user WITH PASSWORD 'CHANGE_ME_STRONG_PASSWORD';
    END IF;
END
\$\$;

-- Create database
SELECT 'CREATE DATABASE aprender_db OWNER aprender_user'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'aprender_db')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE aprender_db TO aprender_user;

\c aprender_db
GRANT ALL ON SCHEMA public TO aprender_user;
EOF

echo ""
echo "=== VM02 Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Change aprender_user password: ALTER USER aprender_user PASSWORD 'new_password';"
echo "2. Update listen_addresses in postgresql.conf if needed"
echo "3. Configure firewall to allow connections from VM01 only"
echo "4. Setup backup cron job"
