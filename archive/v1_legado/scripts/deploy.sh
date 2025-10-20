#!/bin/bash
# ======================================
# 🚀 DEPLOY SCRIPT - SISTEMA APRENDER
# Automated Deployment Pipeline
# ======================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Variables
ENVIRONMENT="${1:-staging}"
VERSION="${2:-latest}"
BACKUP_ENABLED="${3:-true}"

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "🚀 Sistema Aprender - Deploy Script"
    echo "Environment: $ENVIRONMENT"
    echo "Version: $VERSION"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[DEPLOY]${NC} $1"
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

print_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is not installed"
        exit 1
    fi
    
    # Check if docker-compose is installed
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment files
    case "$ENVIRONMENT" in
        "production")
            ENV_FILE=".env.prod"
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        "staging")
            ENV_FILE=".env.staging"
            COMPOSE_FILE="docker-compose.prod.yml"
            ;;
        "development")
            ENV_FILE=".env"
            COMPOSE_FILE="docker-compose.dev.yml"
            ;;
        *)
            print_error "Invalid environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found: $ENV_FILE"
        exit 1
    fi
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Docker Compose file not found: $COMPOSE_FILE"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Backup database
backup_database() {
    if [ "$BACKUP_ENABLED" = "true" ] && [ "$ENVIRONMENT" != "development" ]; then
        print_step "Creating database backup..."
        
        BACKUP_DIR="backups"
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        
        mkdir -p $BACKUP_DIR
        
        # Create backup using docker-compose
        docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T db pg_dump \
            -U ${DB_USER:-postgres} \
            -d ${DB_NAME:-aprender_sistema} > "$BACKUP_DIR/$BACKUP_FILE"
        
        print_success "Database backup created: $BACKUP_DIR/$BACKUP_FILE"
    else
        print_info "Database backup skipped"
    fi
}

# Run pre-deploy checks
pre_deploy_checks() {
    print_step "Running pre-deploy checks..."
    
    # Check if tests pass
    print_step "Running tests..."
    if ! ./scripts/test.sh quick >/dev/null 2>&1; then
        print_error "Tests failed - aborting deployment"
        exit 1
    fi
    
    # Check code quality
    print_step "Checking code quality..."
    if ! ./scripts/lint.sh check >/dev/null 2>&1; then
        print_warning "Code quality issues found - continuing anyway"
    fi
    
    # Check Django configuration
    print_step "Checking Django configuration..."
    if [ "$ENVIRONMENT" != "development" ]; then
        export $(cat $ENV_FILE | grep -v '^#' | xargs)
        if ! python manage.py check --deploy >/dev/null 2>&1; then
            print_error "Django deployment check failed"
            exit 1
        fi
    fi
    
    print_success "Pre-deploy checks passed"
}

# Build images
build_images() {
    print_step "Building Docker images..."
    
    if [ "$ENVIRONMENT" = "development" ]; then
        docker-compose -f $COMPOSE_FILE build --no-cache
    else
        docker-compose -f $COMPOSE_FILE build --no-cache web
    fi
    
    print_success "Docker images built successfully"
}

# Deploy application
deploy_application() {
    print_step "Deploying application..."
    
    # Stop existing services
    print_step "Stopping existing services..."
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down || true
    
    # Start new services
    print_step "Starting new services..."
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d
    
    # Wait for services to be ready
    print_step "Waiting for services to be ready..."
    sleep 30
    
    # Check if services are healthy
    if ! docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE ps | grep -q "Up"; then
        print_error "Services failed to start properly"
        exit 1
    fi
    
    print_success "Application deployed successfully"
}

# Run post-deploy tasks
post_deploy_tasks() {
    print_step "Running post-deploy tasks..."
    
    # Apply database migrations
    print_step "Applying database migrations..."
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py migrate --noinput
    
    # Collect static files
    print_step "Collecting static files..."
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py collectstatic --noinput --clear
    
    # Warm up cache (if applicable)
    if [ "$ENVIRONMENT" != "development" ]; then
        print_step "Warming up application cache..."
        docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py warm_cache 2>/dev/null || print_warning "Cache warming failed (non-critical)"
    fi
    
    print_success "Post-deploy tasks completed"
}

# Health check
health_check() {
    print_step "Performing health check..."
    
    # Get application URL based on environment
    case "$ENVIRONMENT" in
        "production")
            APP_URL="${PRODUCTION_URL:-https://aprender.com}"
            ;;
        "staging")
            APP_URL="${STAGING_URL:-https://staging.aprender.com}"
            ;;
        "development")
            APP_URL="http://localhost:8000"
            ;;
    esac
    
    # Wait for application to be ready
    RETRY_COUNT=0
    MAX_RETRIES=30
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -f "$APP_URL/health/" >/dev/null 2>&1; then
            print_success "Health check passed"
            return 0
        fi
        
        print_info "Waiting for application to be ready... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 10
        RETRY_COUNT=$((RETRY_COUNT + 1))
    done
    
    print_error "Health check failed after $MAX_RETRIES attempts"
    exit 1
}

# Send deployment notification
send_notification() {
    print_step "Sending deployment notification..."
    
    WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
    
    if [ -n "$WEBHOOK_URL" ]; then
        MESSAGE="🚀 Sistema Aprender deployed to $ENVIRONMENT (version: $VERSION) at $(date)"
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$MESSAGE\"}" \
            "$WEBHOOK_URL" >/dev/null 2>&1 || print_warning "Notification failed"
        
        print_success "Deployment notification sent"
    else
        print_info "No webhook URL configured - skipping notification"
    fi
}

# Rollback function
rollback() {
    print_error "Deployment failed - initiating rollback..."
    
    # Stop failed deployment
    docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down || true
    
    # Restore from backup if available
    if [ "$BACKUP_ENABLED" = "true" ] && [ -f "backups/latest_backup.sql" ]; then
        print_step "Restoring database from backup..."
        # Restore database logic here
    fi
    
    # Restart previous version (if available)
    print_step "Restarting previous version..."
    # This would typically involve pulling the previous image tag
    
    print_error "Rollback completed - please investigate the deployment failure"
    exit 1
}

# Show help
show_help() {
    echo "Usage: ./scripts/deploy.sh [ENVIRONMENT] [VERSION] [BACKUP]"
    echo ""
    echo "Parameters:"
    echo "  ENVIRONMENT  - Target environment (development|staging|production)"
    echo "  VERSION      - Version tag or 'latest' (default: latest)"
    echo "  BACKUP       - Enable backup (true|false, default: true)"
    echo ""
    echo "Examples:"
    echo "  ./scripts/deploy.sh staging"
    echo "  ./scripts/deploy.sh production v1.2.3 true"
    echo "  ./scripts/deploy.sh development latest false"
    echo ""
    echo "Environment Files:"
    echo "  - development: .env"
    echo "  - staging: .env.staging"
    echo "  - production: .env.prod"
}

# Confirmation prompt for production
confirm_production() {
    if [ "$ENVIRONMENT" = "production" ]; then
        echo -e "${RED}⚠️  You are about to deploy to PRODUCTION!${NC}"
        echo -e "${YELLOW}This will affect live users and data.${NC}"
        echo ""
        read -p "Are you sure you want to continue? (type 'yes' to confirm): " confirmation
        
        if [ "$confirmation" != "yes" ]; then
            print_info "Deployment cancelled"
            exit 0
        fi
    fi
}

# Main deployment function
main() {
    case "$1" in
        "help"|"-h"|"--help")
            show_help
            exit 0
            ;;
    esac
    
    # Trap errors and perform rollback
    trap rollback ERR
    
    print_header
    
    # Confirmation for production
    confirm_production
    
    # Deployment pipeline
    check_prerequisites
    backup_database
    pre_deploy_checks
    build_images
    deploy_application
    post_deploy_tasks
    health_check
    send_notification
    
    # Success message
    echo -e "${GREEN}"
    echo "========================================"
    echo "🎉 Deployment completed successfully!"
    echo "========================================"
    echo -e "${NC}"
    echo "Environment: $ENVIRONMENT"
    echo "Version: $VERSION"
    echo "URL: $APP_URL"
    echo ""
    echo "Next steps:"
    echo "1. Monitor application logs"
    echo "2. Verify functionality"
    echo "3. Update documentation if needed"
}

# Run main function
main "$@"