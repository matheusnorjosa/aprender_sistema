#!/bin/bash
# ======================================
# 🚀 SETUP SCRIPT - SISTEMA APRENDER
# Automated Development Environment Setup
# ======================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "🎓 Sistema Aprender - Setup Script"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
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

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    if command_exists python3; then
        PYTHON_CMD="python3"
    elif command_exists python; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed or not in PATH"
        exit 1
    fi

    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || [ "$PYTHON_MAJOR" -eq 3 -a "$PYTHON_MINOR" -lt 11 ]; then
        print_error "Python 3.11+ is required. Found: $PYTHON_VERSION"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION detected"
}

# Create virtual environment
setup_virtualenv() {
    print_step "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi

    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        print_success "Virtual environment activated (Linux/Mac)"
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
        print_success "Virtual environment activated (Windows)"
    else
        print_error "Could not find virtual environment activation script"
        exit 1
    fi
}

# Install Python dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install development dependencies
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    else
        print_warning "requirements-dev.txt not found, installing base requirements"
        pip install -r requirements.txt
    fi
}

# Setup environment variables
setup_environment() {
    print_step "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Environment file created from .env.example"
            print_warning "Please edit .env file with your configuration"
        else
            print_warning ".env.example not found, creating basic .env"
            cat > .env << EOL
# Basic environment configuration
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
EOL
        fi
    else
        print_warning ".env file already exists"
    fi
}

# Setup database
setup_database() {
    print_step "Setting up database..."
    
    # Run migrations
    python manage.py makemigrations
    python manage.py migrate
    
    print_success "Database migrations applied"
    
    # Create superuser if needed
    echo -e "${YELLOW}Do you want to create a superuser? (y/N):${NC}"
    read -r create_superuser
    
    if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
        python manage.py createsuperuser
    fi
}

# Load initial data
load_initial_data() {
    print_step "Loading initial data..."
    
    if [ -d "fixtures" ] && [ "$(ls -A fixtures)" ]; then
        python manage.py loaddata fixtures/*.json
        print_success "Initial data loaded"
    else
        print_warning "No fixtures found to load"
    fi
}

# Setup pre-commit hooks
setup_precommit() {
    print_step "Setting up pre-commit hooks..."
    
    if command_exists pre-commit; then
        pre-commit install
        print_success "Pre-commit hooks installed"
    else
        print_warning "Pre-commit not available, installing..."
        pip install pre-commit
        pre-commit install
        print_success "Pre-commit installed and configured"
    fi
}

# Setup Docker (if available)
setup_docker() {
    if command_exists docker && command_exists docker-compose; then
        print_step "Docker detected - setting up Docker environment..."
        
        echo -e "${YELLOW}Do you want to set up Docker environment? (y/N):${NC}"
        read -r setup_docker_env
        
        if [ "$setup_docker_env" = "y" ] || [ "$setup_docker_env" = "Y" ]; then
            # Build and start development environment
            docker-compose -f docker-compose.dev.yml build
            docker-compose -f docker-compose.dev.yml up -d
            
            print_success "Docker development environment started"
            print_success "Application: http://localhost:8000"
            print_success "Adminer: http://localhost:8080"
            print_success "MailHog: http://localhost:8025"
        fi
    else
        print_warning "Docker not available - skipping Docker setup"
    fi
}

# Run tests
run_tests() {
    print_step "Running tests to verify setup..."
    
    if python manage.py test --verbosity=0 >/dev/null 2>&1; then
        print_success "All tests passed"
    else
        print_warning "Some tests failed - setup may need attention"
    fi
}

# Create necessary directories
create_directories() {
    print_step "Creating necessary directories..."
    
    directories=("logs" "media" "staticfiles" "backups")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        fi
    done
}

# Main setup function
main() {
    print_header
    
    print_step "Starting Sistema Aprender setup..."
    
    # Check prerequisites
    check_python
    
    # Setup steps
    setup_virtualenv
    install_dependencies
    setup_environment
    create_directories
    setup_database
    load_initial_data
    setup_precommit
    
    # Optional Docker setup
    setup_docker
    
    # Verify setup
    run_tests
    
    # Final message
    echo -e "${GREEN}"
    echo "========================================"
    echo "🎉 Setup completed successfully!"
    echo "========================================"
    echo -e "${NC}"
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Edit .env file with your configuration"
    echo "2. Run: ${BLUE}python manage.py runserver${NC}"
    echo "3. Open: ${BLUE}http://localhost:8000${NC}"
    echo ""
    echo -e "${YELLOW}Useful commands:${NC}"
    echo "- ${BLUE}make help${NC} - Show all available commands"
    echo "- ${BLUE}make dev${NC} - Start development environment"
    echo "- ${BLUE}make test${NC} - Run tests"
    echo "- ${BLUE}make lint${NC} - Run code quality checks"
    echo ""
    echo -e "${GREEN}Happy coding! 🚀${NC}"
}

# Run main function
main "$@"