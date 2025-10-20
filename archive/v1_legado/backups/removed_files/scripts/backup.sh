#!/bin/bash
# ======================================
# 💾 BACKUP SCRIPT - SISTEMA APRENDER
# Automated Database and Media Backup
# ======================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Variables
BACKUP_TYPE="${1:-full}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ENVIRONMENT="${ENVIRONMENT:-development}"

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "💾 Sistema Aprender - Backup Script"
    echo "Type: $BACKUP_TYPE"
    echo "Environment: $ENVIRONMENT"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[BACKUP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create backup directory
setup_backup_dir() {
    print_step "Setting up backup directory..."
    
    mkdir -p "$BACKUP_DIR"
    chmod 755 "$BACKUP_DIR"
    
    print_success "Backup directory ready: $BACKUP_DIR"
}

# Database backup
backup_database() {
    print_step "Creating database backup..."
    
    # Determine database connection parameters
    if [ -f ".env" ]; then
        source .env 2>/dev/null || true
    fi
    
    # Set defaults if not provided
    DB_HOST="${DB_HOST:-localhost}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-aprender_sistema}"
    DB_USER="${DB_USER:-postgres}"
    
    if [ -z "$DB_PASSWORD" ]; then
        print_error "DB_PASSWORD not set. Please set it in .env file or environment"
        exit 1
    fi
    
    # Create database backup
    DB_BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql"
    
    export PGPASSWORD="$DB_PASSWORD"
    
    if command -v docker-compose >/dev/null 2>&1 && [ -f "docker-compose.yml" ]; then
        # Use Docker Compose if available
        print_step "Using Docker Compose for database backup..."
        docker-compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" > "$DB_BACKUP_FILE"
    elif command -v docker >/dev/null 2>&1 && docker ps | grep -q postgres; then
        # Use Docker directly
        print_step "Using Docker for database backup..."
        CONTAINER_ID=$(docker ps | grep postgres | awk '{print $1}' | head -n1)
        docker exec -t "$CONTAINER_ID" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$DB_BACKUP_FILE"
    elif command -v pg_dump >/dev/null 2>&1; then
        # Use local PostgreSQL
        print_step "Using local PostgreSQL for backup..."
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" > "$DB_BACKUP_FILE"
    else
        print_error "No PostgreSQL backup method available"
        exit 1
    fi
    
    unset PGPASSWORD
    
    # Compress backup
    gzip "$DB_BACKUP_FILE"
    DB_BACKUP_FILE="$DB_BACKUP_FILE.gz"
    
    # Verify backup
    if [ -f "$DB_BACKUP_FILE" ] && [ -s "$DB_BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
        print_success "Database backup created: $DB_BACKUP_FILE ($BACKUP_SIZE)"
    else
        print_error "Database backup failed or is empty"
        exit 1
    fi
    
    # Create symlink to latest backup
    ln -sf "$(basename "$DB_BACKUP_FILE")" "$BACKUP_DIR/latest_db_backup.sql.gz"
}

# Media files backup
backup_media() {
    print_step "Creating media files backup..."
    
    MEDIA_DIR="${MEDIA_ROOT:-./media}"
    
    if [ ! -d "$MEDIA_DIR" ]; then
        print_warning "Media directory not found: $MEDIA_DIR"
        return 0
    fi
    
    # Check if media directory has content
    if [ -z "$(ls -A $MEDIA_DIR 2>/dev/null)" ]; then
        print_warning "Media directory is empty"
        return 0
    fi
    
    MEDIA_BACKUP_FILE="$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"
    
    # Create compressed archive of media files
    tar -czf "$MEDIA_BACKUP_FILE" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"
    
    if [ -f "$MEDIA_BACKUP_FILE" ] && [ -s "$MEDIA_BACKUP_FILE" ]; then
        BACKUP_SIZE=$(du -h "$MEDIA_BACKUP_FILE" | cut -f1)
        print_success "Media backup created: $MEDIA_BACKUP_FILE ($BACKUP_SIZE)"
    else
        print_error "Media backup failed"
        exit 1
    fi
    
    # Create symlink to latest backup
    ln -sf "$(basename "$MEDIA_BACKUP_FILE")" "$BACKUP_DIR/latest_media_backup.tar.gz"
}

# Static files backup (for production)
backup_static() {
    if [ "$ENVIRONMENT" != "development" ]; then
        print_step "Creating static files backup..."
        
        STATIC_DIR="${STATIC_ROOT:-./staticfiles}"
        
        if [ ! -d "$STATIC_DIR" ]; then
            print_warning "Static directory not found: $STATIC_DIR"
            return 0
        fi
        
        STATIC_BACKUP_FILE="$BACKUP_DIR/static_backup_$TIMESTAMP.tar.gz"
        
        tar -czf "$STATIC_BACKUP_FILE" -C "$(dirname "$STATIC_DIR")" "$(basename "$STATIC_DIR")"
        
        if [ -f "$STATIC_BACKUP_FILE" ] && [ -s "$STATIC_BACKUP_FILE" ]; then
            BACKUP_SIZE=$(du -h "$STATIC_BACKUP_FILE" | cut -f1)
            print_success "Static files backup created: $STATIC_BACKUP_FILE ($BACKUP_SIZE)"
        else
            print_warning "Static files backup failed (non-critical)"
        fi
    fi
}

# Configuration backup
backup_config() {
    print_step "Creating configuration backup..."
    
    CONFIG_BACKUP_FILE="$BACKUP_DIR/config_backup_$TIMESTAMP.tar.gz"
    
    # Files to backup
    CONFIG_FILES=(
        ".env.example"
        "docker-compose.yml"
        "docker-compose.dev.yml"
        "docker-compose.prod.yml"
        "requirements.txt"
        "requirements-dev.txt"
        "pyproject.toml"
        "Makefile"
    )
    
    # Add existing files to backup
    EXISTING_FILES=()
    for file in "${CONFIG_FILES[@]}"; do
        if [ -f "$file" ]; then
            EXISTING_FILES+=("$file")
        fi
    done
    
    if [ ${#EXISTING_FILES[@]} -gt 0 ]; then
        tar -czf "$CONFIG_BACKUP_FILE" "${EXISTING_FILES[@]}"
        
        if [ -f "$CONFIG_BACKUP_FILE" ] && [ -s "$CONFIG_BACKUP_FILE" ]; then
            BACKUP_SIZE=$(du -h "$CONFIG_BACKUP_FILE" | cut -f1)
            print_success "Configuration backup created: $CONFIG_BACKUP_FILE ($BACKUP_SIZE)"
        else
            print_warning "Configuration backup failed (non-critical)"
        fi
    else
        print_warning "No configuration files found to backup"
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    print_step "Cleaning up old backups (keeping $RETENTION_DAYS days)..."
    
    # Find and remove old backup files
    find "$BACKUP_DIR" -name "*_backup_*.gz" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*_backup_*.tar.gz" -type f -mtime +$RETENTION_DAYS -delete
    
    # Count remaining backups
    REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "*_backup_*" -type f | wc -l)
    
    print_success "Cleanup completed - $REMAINING_BACKUPS backup files remaining"
}

# Generate backup manifest
generate_manifest() {
    print_step "Generating backup manifest..."
    
    MANIFEST_FILE="$BACKUP_DIR/backup_manifest_$TIMESTAMP.txt"
    
    cat > "$MANIFEST_FILE" << EOF
Sistema Aprender - Backup Manifest
==================================
Date: $(date)
Environment: $ENVIRONMENT
Backup Type: $BACKUP_TYPE
Hostname: $(hostname)
User: $(whoami)

Backup Files Created:
EOF
    
    # List all backup files created in this session
    find "$BACKUP_DIR" -name "*_$TIMESTAMP*" -type f >> "$MANIFEST_FILE"
    
    # Add system information
    cat >> "$MANIFEST_FILE" << EOF

System Information:
- OS: $(uname -s)
- Kernel: $(uname -r)
- Architecture: $(uname -m)
- Disk Space: $(df -h $BACKUP_DIR | tail -n 1)

Database Information:
- Database: $DB_NAME
- Host: $DB_HOST:$DB_PORT
- User: $DB_USER

Notes:
- Retention period: $RETENTION_DAYS days
- Backup directory: $BACKUP_DIR
- All backups are compressed with gzip
EOF
    
    print_success "Backup manifest created: $MANIFEST_FILE"
}

# Upload to cloud storage (optional)
upload_to_cloud() {
    if [ -n "$AWS_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        print_step "Uploading backups to AWS S3..."
        
        # Upload database backup
        if [ -f "$BACKUP_DIR/latest_db_backup.sql.gz" ]; then
            aws s3 cp "$BACKUP_DIR/latest_db_backup.sql.gz" \
                "s3://$AWS_S3_BUCKET/backups/db/db_backup_$TIMESTAMP.sql.gz"
        fi
        
        # Upload media backup
        if [ -f "$BACKUP_DIR/latest_media_backup.tar.gz" ]; then
            aws s3 cp "$BACKUP_DIR/latest_media_backup.tar.gz" \
                "s3://$AWS_S3_BUCKET/backups/media/media_backup_$TIMESTAMP.tar.gz"
        fi
        
        print_success "Backups uploaded to S3"
    elif [ -n "$GOOGLE_CLOUD_BUCKET" ] && command -v gsutil >/dev/null 2>&1; then
        print_step "Uploading backups to Google Cloud Storage..."
        
        gsutil -m cp "$BACKUP_DIR/*_backup_$TIMESTAMP*" \
            "gs://$GOOGLE_CLOUD_BUCKET/backups/"
        
        print_success "Backups uploaded to Google Cloud"
    else
        print_warning "No cloud storage configured - skipping upload"
    fi
}

# Show help
show_help() {
    echo "Usage: ./scripts/backup.sh [TYPE]"
    echo ""
    echo "Backup Types:"
    echo "  full     - Complete backup (database + media + config)"
    echo "  db       - Database only"
    echo "  media    - Media files only"
    echo "  config   - Configuration files only"
    echo ""
    echo "Environment Variables:"
    echo "  RETENTION_DAYS  - Days to keep backups (default: 30)"
    echo "  BACKUP_DIR      - Backup directory (default: ./backups)"
    echo "  AWS_S3_BUCKET   - S3 bucket for cloud backup"
    echo "  GOOGLE_CLOUD_BUCKET - GCS bucket for cloud backup"
    echo ""
    echo "Examples:"
    echo "  ./scripts/backup.sh"
    echo "  ./scripts/backup.sh db"
    echo "  RETENTION_DAYS=7 ./scripts/backup.sh full"
}

# Main backup function
main() {
    case "$BACKUP_TYPE" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
        "db")
            print_header
            setup_backup_dir
            backup_database
            cleanup_old_backups
            generate_manifest
            upload_to_cloud
            ;;
        "media")
            print_header
            setup_backup_dir
            backup_media
            cleanup_old_backups
            generate_manifest
            ;;
        "config")
            print_header
            setup_backup_dir
            backup_config
            cleanup_old_backups
            generate_manifest
            ;;
        "full"|*)
            print_header
            setup_backup_dir
            backup_database
            backup_media
            backup_static
            backup_config
            cleanup_old_backups
            generate_manifest
            upload_to_cloud
            ;;
    esac
    
    # Final summary
    echo -e "${GREEN}"
    echo "========================================"
    echo "🎉 Backup completed successfully!"
    echo "========================================"
    echo -e "${NC}"
    echo "Backup directory: $BACKUP_DIR"
    echo "Timestamp: $TIMESTAMP"
    echo ""
    echo "To restore from backup:"
    echo "  ./scripts/restore.sh $TIMESTAMP"
}

# Run main function
main "$@"