# ======================================
# 🛠️ MAKEFILE - SISTEMA APRENDER
# Comandos Padronizados para Desenvolvimento
# ======================================

# Variables
PYTHON := python
MANAGE := $(PYTHON) manage.py
DOCKER_COMPOSE_DEV := docker-compose -f docker-compose.dev.yml
DOCKER_COMPOSE_PROD := docker-compose -f docker-compose.prod.yml

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Help message
.PHONY: help
help: ## 📋 Show this help message
	@echo "$(BLUE)🎓 Sistema Aprender - Available Commands$(RESET)"
	@echo "======================================"
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*?##/ { printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ==========================================
# 🏠 LOCAL DEVELOPMENT
# ==========================================

.PHONY: install
install: ## 📦 Install all dependencies
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "$(GREEN)✅ Dependencies installed!$(RESET)"

.PHONY: run
run: ## 🚀 Run development server locally
	@echo "$(BLUE)Starting Django development server...$(RESET)"
	$(MANAGE) runserver

.PHONY: migrate
migrate: ## 🗄️ Apply database migrations
	@echo "$(BLUE)Applying database migrations...$(RESET)"
	$(MANAGE) makemigrations
	$(MANAGE) migrate
	@echo "$(GREEN)✅ Migrations applied!$(RESET)"

.PHONY: superuser
superuser: ## 👤 Create superuser
	@echo "$(BLUE)Creating superuser...$(RESET)"
	$(MANAGE) createsuperuser

.PHONY: shell
shell: ## 🐍 Open Django shell
	$(MANAGE) shell_plus --ipython

.PHONY: dbshell
dbshell: ## 💾 Open database shell
	$(MANAGE) dbshell

# ==========================================
# 🧪 TESTING
# ==========================================

.PHONY: test
test: ## 🧪 Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	$(MANAGE) test --verbosity=2

.PHONY: test-coverage
test-coverage: ## 📊 Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	coverage run --source='.' manage.py test --verbosity=2
	coverage report --show-missing
	coverage html
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/$(RESET)"

.PHONY: test-unit
test-unit: ## 🎯 Run unit tests only
	$(MANAGE) test core.tests.test_models core.tests.test_views --verbosity=2

.PHONY: test-integration
test-integration: ## 🔗 Run integration tests
	$(MANAGE) test core.tests.test_integration --verbosity=2

.PHONY: test-e2e
test-e2e: ## 🌐 Run end-to-end tests
	$(MANAGE) test core.tests.test_e2e --verbosity=2

# ==========================================
# 🔍 CODE QUALITY
# ==========================================

.PHONY: lint
lint: ## 🔍 Run all linting and formatting
	@echo "$(BLUE)Running code quality checks...$(RESET)"
	@echo "$(YELLOW)🎯 Formatting with Black...$(RESET)"
	black . --diff --color
	@echo "$(YELLOW)📐 Sorting imports with isort...$(RESET)"
	isort . --diff --color
	@echo "$(YELLOW)🕵️ Linting with flake8...$(RESET)"
	flake8 .
	@echo "$(YELLOW)🔒 Security check with bandit...$(RESET)"
	bandit -r . -x "/venv/,/tests/,/migrations/" -ll
	@echo "$(GREEN)✅ All checks passed!$(RESET)"

.PHONY: format
format: ## ✨ Auto-format code (Black + isort)
	@echo "$(BLUE)Auto-formatting code...$(RESET)"
	black .
	isort .
	@echo "$(GREEN)✅ Code formatted!$(RESET)"

.PHONY: type-check
type-check: ## 🔎 Run type checking with mypy
	mypy . --ignore-missing-imports

.PHONY: security
security: ## 🔒 Run security checks
	@echo "$(BLUE)Running security checks...$(RESET)"
	bandit -r . -x "/venv/,/tests/,/migrations/" -f json -o bandit-report.json
	safety check --json --output safety-report.json
	@echo "$(GREEN)✅ Security check completed!$(RESET)"

.PHONY: pre-commit
pre-commit: ## 🔄 Run pre-commit hooks on all files
	pre-commit run --all-files

# ==========================================
# 🐳 DOCKER DEVELOPMENT
# ==========================================

.PHONY: docker-build
docker-build: ## 🏗️ Build Docker development images
	@echo "$(BLUE)Building Docker development images...$(RESET)"
	$(DOCKER_COMPOSE_DEV) build --no-cache

.PHONY: docker-up
docker-up: ## ⬆️ Start Docker development environment
	@echo "$(BLUE)Starting Docker development environment...$(RESET)"
	$(DOCKER_COMPOSE_DEV) up -d
	@echo "$(GREEN)✅ Docker environment started!$(RESET)"
	@echo "$(YELLOW)🌐 Application: http://localhost:8000$(RESET)"
	@echo "$(YELLOW)💾 Adminer: http://localhost:8080$(RESET)"
	@echo "$(YELLOW)📧 MailHog: http://localhost:8025$(RESET)"

.PHONY: docker-down
docker-down: ## ⬇️ Stop Docker development environment
	@echo "$(BLUE)Stopping Docker development environment...$(RESET)"
	$(DOCKER_COMPOSE_DEV) down

.PHONY: docker-logs
docker-logs: ## 📜 Show Docker logs
	$(DOCKER_COMPOSE_DEV) logs -f

.PHONY: docker-shell
docker-shell: ## 🐚 Open shell in web container
	$(DOCKER_COMPOSE_DEV) exec web /bin/bash

.PHONY: docker-clean
docker-clean: ## 🧹 Clean Docker resources
	@echo "$(BLUE)Cleaning Docker resources...$(RESET)"
	$(DOCKER_COMPOSE_DEV) down --volumes --remove-orphans
	docker system prune -f
	@echo "$(GREEN)✅ Docker resources cleaned!$(RESET)"

# ==========================================
# 🚀 PRODUCTION DEPLOYMENT
# ==========================================

.PHONY: prod-build
prod-build: ## 🏗️ Build production Docker images
	@echo "$(BLUE)Building production images...$(RESET)"
	$(DOCKER_COMPOSE_PROD) build --no-cache

.PHONY: prod-deploy
prod-deploy: ## 🚀 Deploy to production
	@echo "$(BLUE)Deploying to production...$(RESET)"
	@echo "$(RED)⚠️  Make sure all environment variables are set!$(RESET)"
	$(DOCKER_COMPOSE_PROD) up -d
	@echo "$(GREEN)✅ Production deployment completed!$(RESET)"

.PHONY: prod-logs
prod-logs: ## 📜 Show production logs
	$(DOCKER_COMPOSE_PROD) logs -f

.PHONY: prod-status
prod-status: ## 📊 Check production status
	$(DOCKER_COMPOSE_PROD) ps

# ==========================================
# 📊 DATABASE MANAGEMENT
# ==========================================

.PHONY: backup
backup: ## 💾 Create database backup
	@echo "$(BLUE)Creating database backup...$(RESET)"
	./scripts/backup.sh
	@echo "$(GREEN)✅ Database backup created!$(RESET)"

.PHONY: restore
restore: ## 📥 Restore database from backup
	@echo "$(BLUE)Restoring database...$(RESET)"
	@read -p "Enter backup filename: " backup; \
	./scripts/restore.sh $$backup

.PHONY: reset-db
reset-db: ## 🔄 Reset database (DANGER: destroys all data)
	@echo "$(RED)⚠️  This will destroy all data! Are you sure? [y/N]$(RESET)" && read ans && [ $${ans:-N} = y ]
	$(MANAGE) flush --noinput
	$(MANAGE) migrate
	@echo "$(GREEN)✅ Database reset completed!$(RESET)"

# ==========================================
# 🧹 MAINTENANCE
# ==========================================

.PHONY: clean
clean: ## 🧹 Clean temporary files
	@echo "$(BLUE)Cleaning temporary files...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	rm -rf .coverage htmlcov/ .pytest_cache/
	@echo "$(GREEN)✅ Temporary files cleaned!$(RESET)"

.PHONY: update-deps
update-deps: ## 📦 Update dependencies
	@echo "$(BLUE)Updating dependencies...$(RESET)"
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements-dev.in
	pip install -r requirements-dev.txt
	@echo "$(GREEN)✅ Dependencies updated!$(RESET)"

.PHONY: collectstatic
collectstatic: ## 📁 Collect static files
	@echo "$(BLUE)Collecting static files...$(RESET)"
	$(MANAGE) collectstatic --noinput --clear
	@echo "$(GREEN)✅ Static files collected!$(RESET)"

# ==========================================
# 📈 MONITORING & HEALTH
# ==========================================

.PHONY: health
health: ## 🩺 Check application health
	@echo "$(BLUE)Checking application health...$(RESET)"
	curl -f http://localhost:8000/health/ || echo "$(RED)❌ Health check failed$(RESET)"

.PHONY: check
check: ## ✅ Run Django system checks
	$(MANAGE) check --deploy

.PHONY: load-data
load-data: ## 📥 Load initial data fixtures
	@echo "$(BLUE)Loading initial data...$(RESET)"
	$(MANAGE) loaddata fixtures/initial_data.json
	@echo "$(GREEN)✅ Initial data loaded!$(RESET)"

# ==========================================
# 🔧 UTILITIES
# ==========================================

.PHONY: requirements
requirements: ## 📋 Generate requirements.txt from .in files
	pip-compile requirements.in
	pip-compile requirements-dev.in

.PHONY: serve-docs
serve-docs: ## 📚 Serve documentation locally
	@echo "$(BLUE)Serving documentation...$(RESET)"
	@echo "$(YELLOW)📖 Documentation: http://localhost:8080$(RESET)"
	cd docs && python -m http.server 8080

.PHONY: translations
translations: ## 🌐 Update translation files
	$(MANAGE) makemessages -l pt_BR
	$(MANAGE) compilemessages

# ==========================================
# 🎯 SHORTCUTS
# ==========================================

.PHONY: dev
dev: install migrate run ## 🚀 Full development setup

.PHONY: ci
ci: lint test-coverage ## 🔄 Run CI pipeline locally

.PHONY: quick
quick: format lint test ## ⚡ Quick development cycle

# Default target
.DEFAULT_GOAL := help