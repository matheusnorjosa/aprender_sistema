# 🚀 Developer Setup Guide - Sistema Aprender

Welcome to the Sistema Aprender development team! This guide will help you set up your development environment quickly and efficiently.

## 📋 Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, macOS 10.15+, or Ubuntu 20.04+
- **Python**: 3.11+ (recommended: 3.13)
- **Node.js**: 16+ (for frontend tools, optional)
- **Git**: Latest version
- **Docker**: 24.0+ (optional but recommended)
- **Code Editor**: VS Code (recommended) with Python extension

### Knowledge Prerequisites
- Basic Python and Django experience
- Understanding of Git workflows
- Familiarity with PostgreSQL
- Basic Docker knowledge (if using containerized development)

---

## 🛠️ Quick Setup (Automated)

### Option 1: One-Command Setup
```bash
# Clone repository and run automated setup
git clone https://github.com/your-org/aprender_sistema.git
cd aprender_sistema
./scripts/setup.sh
```

The automated setup script will:
- Check Python version compatibility
- Create and activate virtual environment
- Install all dependencies
- Set up environment variables
- Initialize database
- Run initial migrations
- Create development superuser
- Start development server

### Option 2: Docker Development Environment
```bash
# Clone and start with Docker
git clone https://github.com/your-org/aprender_sistema.git
cd aprender_sistema
make docker-dev-setup
```

---

## 🔧 Manual Setup (Step by Step)

### 1. Repository Setup
```bash
# Clone the repository
git clone https://github.com/your-org/aprender_sistema.git
cd aprender_sistema

# Set up Git configuration (first time only)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Install pre-commit hooks
make setup-git-hooks
```

### 2. Python Environment
```bash
# Check Python version (must be 3.11+)
python --version

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env.development

# Edit development environment variables
# Use your preferred editor (VS Code, nano, vim, etc.)
code .env.development
```

#### Development Environment Variables
```bash
# .env.development
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (SQLite for development)
DATABASE_URL=sqlite:///db.sqlite3

# Optional: PostgreSQL for development
# DATABASE_URL=postgresql://postgres:password@localhost:5432/aprender_dev

# Google APIs (optional for basic development)
GOOGLE_CLIENT_ID=your-dev-client-id
GOOGLE_CLIENT_SECRET=your-dev-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Email (console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Cache (in-memory for development)
CACHE_BACKEND=django.core.cache.backends.locmem.LocMemCache

# Time zone
TIME_ZONE=America/Fortaleza
```

### 4. Database Setup
```bash
# Run database migrations
python manage.py migrate

# Create development superuser
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com  
# Password: admin123 (for development only)

# Load initial data (optional)
python manage.py loaddata initial_data.json
```

### 5. Verify Installation
```bash
# Run development server
python manage.py runserver

# Open browser to http://localhost:8000
# You should see the Sistema Aprender homepage

# Access admin panel at http://localhost:8000/admin
# Login with superuser credentials
```

---

## 🐳 Docker Development Setup

### Development with Docker Compose
```bash
# Start all development services
make docker-dev-up

# View logs
make docker-dev-logs

# Access application shell
make docker-dev-shell

# Run Django commands
make docker-dev-manage makemigrations
make docker-dev-manage migrate
make docker-dev-manage createsuperuser

# Stop all services
make docker-dev-down
```

### Docker Services Overview
```yaml
services:
  web:          # Django application (port 8000)
  db:           # PostgreSQL 15 (port 5432)
  redis:        # Redis cache (port 6379)
  mailhog:      # Email testing (port 8025)
  adminer:      # Database admin (port 8080)
```

### Docker Development URLs
- **Application**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin
- **Database Admin**: http://localhost:8080 (adminer)
- **Email Testing**: http://localhost:8025 (mailhog)

---

## 🧪 Development Tools Setup

### 1. Code Quality Tools
```bash
# Install and configure pre-commit hooks
pre-commit install

# Run code formatting
make format

# Run linting
make lint

# Run security checks
make security-check

# Run all quality checks
make quality-check
```

### 2. Testing Setup
```bash
# Run all tests
make test

# Run tests with coverage
make test-coverage

# Run specific test module
python manage.py test core.tests.test_models

# Run integration tests
make test-integration

# Generate test report
make test-report
```

### 3. Database Tools
```bash
# Access database shell
python manage.py dbshell

# Create database backup
make backup-dev-db

# Reset database (WARNING: Deletes all data)
make reset-dev-db

# Import sample data
make import-sample-data
```

---

## 🔧 IDE Configuration

### VS Code Setup
```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.formatting.provider": "black",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": false,
    "python.testing.unittestEnabled": true,
    "python.testing.unittestArgs": [
        "-v",
        "-s",
        ".",
        "-p",
        "test*.py"
    ],
    "files.associations": {
        "*.html": "django-html"
    }
}
```

### Recommended VS Code Extensions
```json
// .vscode/extensions.json
{
    "recommendations": [
        "ms-python.python",
        "ms-python.black-formatter",
        "ms-python.flake8",
        "batisteo.vscode-django",
        "bradlc.vscode-tailwindcss",
        "ms-vscode.vscode-json",
        "redhat.vscode-yaml",
        "ms-vscode.vscode-markdown",
        "streetsidesoftware.code-spell-checker"
    ]
}
```

### PyCharm Setup
```python
# Settings → Project → Python Interpreter
# Select: <project>/venv/bin/python

# Code Style → Python
# Scheme: Black (install Black plugin first)

# Build, Execution, Deployment → Console → Django Console
# Django project root: /path/to/aprender_sistema
# Settings module: aprender_sistema.settings
```

---

## 📚 Development Workflow

### 1. Daily Development Process
```bash
# Start development session
make dev-start

# Pull latest changes
git pull origin develop

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes...

# Run quality checks
make pre-commit-check

# Commit changes
git add .
git commit -m "feat: add your feature description"

# Push changes
git push origin feature/your-feature-name

# Create pull request via GitHub
```

### 2. Branch Strategy
```
main                    # Production branch
├── develop            # Integration branch  
├── feature/feature-x  # Feature branches
├── fix/bug-name       # Bug fix branches
└── hotfix/critical    # Emergency fixes
```

### 3. Commit Message Convention
```bash
# Format: type(scope): description

# Examples:
feat(auth): add Google OAuth integration
fix(calendar): resolve timezone handling issue
docs(setup): update development guide
test(models): add user model tests
refactor(views): simplify approval logic
style(templates): improve responsive design
```

---

## 🧪 Testing & Quality Assurance

### Running Tests
```bash
# Full test suite
make test

# Unit tests only
make test-unit

# Integration tests only
make test-integration

# Specific app tests
python manage.py test core

# Test with coverage reporting
make test-coverage

# Performance tests
make test-performance
```

### Code Quality Checks
```bash
# Format code with Black
make format

# Check code style with flake8
make lint

# Security analysis with Bandit
make security-check

# Type checking with mypy
make type-check

# Import sorting with isort
make sort-imports

# All quality checks
make quality
```

### Pre-commit Hooks
```bash
# Install hooks (done automatically in setup)
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Skip hooks (only if necessary)
git commit --no-verify
```

---

## 🌐 Local Development URLs

### Application URLs
- **Homepage**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/
- **Health Check**: http://localhost:8000/health/

### Development Tools
- **Database Admin**: http://localhost:8080/ (adminer)
- **Email Testing**: http://localhost:8025/ (mailhog)
- **Redis Commander**: http://localhost:8081/ (if enabled)

---

## 🔍 Debugging & Troubleshooting

### Common Issues

#### Virtual Environment Issues
```bash
# Deactivate and recreate virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

#### Database Issues
```bash
# Reset migrations (CAREFUL: Deletes data)
rm -rf */migrations/0*.py
python manage.py makemigrations
python manage.py migrate

# Check migration status
python manage.py showmigrations

# Fake migrations (if needed)
python manage.py migrate --fake
```

#### Port Already in Use
```bash
# Find process using port 8000
lsof -i :8000          # macOS/Linux
netstat -ano | find "8000"  # Windows

# Kill process
kill -9 <PID>          # macOS/Linux
taskkill /PID <PID> /F # Windows

# Use different port
python manage.py runserver 8001
```

#### Import/Module Errors
```bash
# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check Django settings
python manage.py check

# Verify dependencies
pip check

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Debugging Tools

#### Django Debug Toolbar (Development)
```python
# Already configured in development settings
# Access at http://localhost:8000 (panel on right side)
```

#### Python Debugger
```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint() (Python 3.7+)
breakpoint()

# In VS Code, use F5 to start debugging
```

#### Django Shell Plus
```bash
# Enhanced Django shell with auto-imports
python manage.py shell_plus

# Interactive SQL queries
python manage.py shell_plus --print-sql
```

---

## 📊 Performance Optimization

### Development Performance Tips
```bash
# Use database query optimization
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)  # View SQL queries

# Enable query debugging
DEBUG_QUERIES = True  # in development settings

# Profile view performance
python manage.py runprofileserver

# Analyze memory usage
python -m memory_profiler your_script.py
```

### Database Optimization
```sql
-- Create indexes for frequently queried fields
CREATE INDEX idx_solicitacao_status ON core_solicitacao(status);
CREATE INDEX idx_formador_disponibilidade ON core_formador(ativo);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM core_solicitacao WHERE status = 'PENDENTE';
```

---

## 🚀 Deployment Testing

### Local Production Testing
```bash
# Build production Docker image
make docker-prod-build

# Test production configuration
ENVIRONMENT=production python manage.py check --deploy

# Run security checks
python manage.py check --tag security

# Test static files collection
ENVIRONMENT=production python manage.py collectstatic --dry-run
```

### Staging Environment
```bash
# Deploy to staging
make deploy-staging

# Run integration tests against staging
make test-staging

# Performance testing
make performance-test-staging
```

---

## 📝 Development Checklist

### New Developer Onboarding
- [ ] Repository cloned and setup script run successfully
- [ ] Virtual environment created and activated
- [ ] Dependencies installed without errors
- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Development server starts successfully
- [ ] Admin panel accessible with superuser account
- [ ] Pre-commit hooks installed and working
- [ ] IDE configured with recommended extensions
- [ ] Git configuration set up (name, email)
- [ ] Test suite runs successfully
- [ ] Code quality tools working (lint, format, security check)
- [ ] Docker development environment tested (if applicable)
- [ ] Access to project documentation and resources
- [ ] Team communication channels joined

### Before Each Development Session
- [ ] Pull latest changes from develop branch
- [ ] Activate virtual environment
- [ ] Check for new dependencies (`pip install -r requirements.txt`)
- [ ] Apply any new database migrations (`python manage.py migrate`)
- [ ] Run quick health check (`python manage.py check`)

### Before Creating Pull Request
- [ ] All tests pass (`make test`)
- [ ] Code quality checks pass (`make quality`)
- [ ] No security issues (`make security-check`)
- [ ] Documentation updated if needed
- [ ] Commit messages follow convention
- [ ] Branch is up to date with develop
- [ ] Feature works in development environment
- [ ] No unnecessary files committed

---

## 📚 Learning Resources

### Django Resources
- [Django Official Documentation](https://docs.djangoproject.com/)
- [Django Best Practices](https://django-best-practices.readthedocs.io/)
- [Two Scoops of Django](https://www.feldroy.com/books/two-scoops-of-django-3-x)

### Python Resources
- [Python Official Documentation](https://docs.python.org/3/)
- [Real Python](https://realpython.com/)
- [Python Type Checking](https://mypy.readthedocs.io/)

### Project-Specific Resources
- [Sistema Aprender Wiki](https://github.com/your-org/aprender_sistema/wiki)
- [API Documentation](http://localhost:8000/api/docs/)
- [Code Style Guide](docs/CONTRIBUTING.md#code-style)
- [Testing Guide](docs/dev/testing.md)

---

## 💬 Getting Help

### Internal Resources
- **Team Lead**: dev-lead@yourdomain.com
- **Senior Developer**: senior-dev@yourdomain.com
- **DevOps Support**: devops@yourdomain.com

### Communication Channels
- **Slack**: #aprender-sistema-dev
- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and discussions
- **Wiki**: For detailed documentation and guides

### Common Questions
1. **Q: How do I reset my development database?**
   A: Run `make reset-dev-db` (WARNING: This deletes all data)

2. **Q: My tests are failing after pulling latest changes**
   A: Run `python manage.py migrate` and `pip install -r requirements.txt`

3. **Q: How do I add a new dependency?**
   A: Add to requirements.txt and run `pip install -r requirements.txt`

4. **Q: Pre-commit hooks are failing**
   A: Run `make format` and `make lint` to fix common issues

5. **Q: Docker containers won't start**
   A: Try `make docker-clean` followed by `make docker-dev-up`

---

## 🎉 Welcome to the Team!

You're now ready to contribute to the Sistema Aprender project. Remember:

- **Ask questions** - The team is here to help
- **Follow the conventions** - Consistency makes everyone's life easier
- **Test your changes** - Quality is everyone's responsibility  
- **Document your work** - Future you (and others) will thank you
- **Have fun coding!** - We're building something great together

---

*Developer setup guide created during repository cleanup - Phase 4*  
*Date: 2025-09-11*  
*Version: 1.0*