# ================================================================
# AS v2 — Makefile
# ================================================================
# Comandos unificados para operações comuns
# ================================================================

.PHONY: help build build-dev-image build-prod-image up up-obs down down-obs restart logs shell migrate test clean \
	check-env-dev up-dev health-dev down-dev \
	check-env-staging pull-staging up-staging health-staging down-staging \
	check-env-prod pull-prod up-prod health-prod down-prod \
	check-env-prod-like pull-prod-like up-prod-like health-prod-like down-prod-like \
	staging-precheck staging-build staging-up staging-test staging-down staging-full

# Variáveis
COMPOSE_FILE := docker-compose.yml
COMPOSE_OVERRIDE_FILE := docker-compose.override.yml
COMPOSE_PROD_FILE := docker-compose.prod.yml
COMPOSE_OBS_FILE := docker-compose.observability.yml
DOCKERFILE_DEV := Dockerfile.dev
DOCKERFILE_PROD := Dockerfile.prod
SERVICE_WEB := web
SERVICE_DB := db
SERVICE_WORKER := worker
ENV_FILE_DEV := .env.dev
ENV_FILE_STAGING := .env.staging
ENV_FILE_PROD := .env.production
ENV_FILE_PRODLIKE := .env.prodlike.local
DEV_COMPOSE := docker compose --env-file $(ENV_FILE_DEV) -f $(COMPOSE_FILE) -f $(COMPOSE_OVERRIDE_FILE)
STAGING_COMPOSE := docker compose --env-file $(ENV_FILE_STAGING) -f $(COMPOSE_FILE)
PROD_COMPOSE := docker compose --env-file $(ENV_FILE_PROD) -f $(COMPOSE_PROD_FILE)
PRODLIKE_COMPOSE := docker compose --env-file $(ENV_FILE_PRODLIKE) -f $(COMPOSE_PROD_FILE)

# Staging Gate (local pre-merge validation)
STAGING_TAG := staging-local
GIT_SHA := $(shell git rev-parse --short HEAD)
BUILD_DATE := $(shell date -u +%Y-%m-%dT%H:%M:%SZ)
COMPOSE_STAGING_GATE := docker-compose.staging-gate.yml
STAGING_GATE_COMPOSE = IMAGE_TAG=$(STAGING_TAG) docker compose --env-file $(ENV_FILE_STAGING) -f $(COMPOSE_FILE) -f $(COMPOSE_STAGING_GATE)
BACKEND_IMAGE := norjosamatheus/aprender-backend:$(STAGING_TAG)
FRONTEND_IMAGE := norjosamatheus/aprender-frontend:$(STAGING_TAG)

# ================================================================
# Help
# ================================================================

help:  ## Mostrar esta mensagem de ajuda
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║         Aprender Sistema v2 — Comandos Disponíveis        ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ================================================================
# Docker
# ================================================================

build:  ## Construir imagens Docker
	@echo "🔨 Construindo imagens Docker..."
	docker compose -f $(COMPOSE_FILE) build --no-cache

build-dev-image:  ## Construir imagem backend DEV (Dockerfile.dev)
	@echo "🔨 Construindo backend DEV..."
	docker build -f $(DOCKERFILE_DEV) -t aprender-backend:dev-local ..
	@echo "✅ Imagem DEV: aprender-backend:dev-local"

build-prod-image:  ## Construir imagem backend PROD (Dockerfile.prod)
	@echo "🔨 Construindo backend PROD..."
	docker build -f $(DOCKERFILE_PROD) -t aprender-backend:prod-local ..
	@echo "✅ Imagem PROD: aprender-backend:prod-local"

up:  ## Iniciar todos os serviços
	@echo "🚀 Iniciando ambiente DEV..."
	$(DEV_COMPOSE) up -d
	@echo "✅ Serviços iniciados!"
	@echo "🌐 Web: http://localhost:8002"
	@echo "📊 Admin: http://localhost:8002/admin"
	@echo "🔍 API Health: http://localhost:8002/api/health/"

up-obs:  ## Iniciar com stack de observabilidade (Prometheus + Grafana)
	@echo "🚀 Iniciando serviços com observabilidade..."
	docker compose --env-file $(ENV_FILE_DEV) -f $(COMPOSE_FILE) -f $(COMPOSE_OVERRIDE_FILE) -f $(COMPOSE_OBS_FILE) up -d
	@echo "✅ Serviços iniciados!"
	@echo "🌐 Web: http://localhost:8000"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "🔍 Prometheus: http://localhost:9090"

down:  ## Parar todos os serviços
	@echo "⏹️  Parando ambiente DEV..."
	$(DEV_COMPOSE) down

down-obs:  ## Parar serviços + observabilidade
	@echo "⏹️  Parando serviços com observabilidade..."
	docker compose --env-file $(ENV_FILE_DEV) -f $(COMPOSE_FILE) -f $(COMPOSE_OVERRIDE_FILE) -f $(COMPOSE_OBS_FILE) down

restart:  ## Reiniciar todos os serviços
	@echo "🔄 Reiniciando serviços..."
	$(DEV_COMPOSE) restart

logs:  ## Ver logs (use: make logs SERVICE=web)
	@echo "📋 Logs do serviço $(SERVICE_WEB)..."
	$(DEV_COMPOSE) logs -f --tail=100 $(SERVICE_WEB)

ps:  ## Ver status dos containers
	@echo "📊 Status dos containers:"
	$(DEV_COMPOSE) ps

# ================================================================
# Ambientes (issue #753)
# ================================================================

check-env-dev: ## Validar configuração do ambiente DEV
	@echo "🔎 [DEV] validando compose..."
	@echo "    project: COMPOSE_PROJECT_NAME (from $(ENV_FILE_DEV))"
	@echo "    env-file: $(ENV_FILE_DEV)"
	@echo "    compose: $(COMPOSE_FILE) + $(COMPOSE_OVERRIDE_FILE)"
	$(DEV_COMPOSE) config > /dev/null
	@echo "✅ [DEV] configuração válida"

up-dev: ## Subir ambiente DEV (compose + override)
	@echo "🚀 [DEV] subindo ambiente..."
	$(DEV_COMPOSE) up -d
	@echo "✅ [DEV] ambiente iniciado"
	@echo "🌐 [DEV] backend: http://localhost:8002"
	@echo "🌐 [DEV] frontend: http://localhost:5173"

health-dev: ## Verificar health do ambiente DEV
	@echo "❤️  [DEV] verificando /api/readyz..."
	@curl -fsS http://localhost:8002/api/readyz/ > /dev/null && echo "✅ [DEV] readyz ok" || (echo "❌ [DEV] readyz falhou" && exit 1)

down-dev: ## Derrubar ambiente DEV
	@echo "⏹️  [DEV] derrubando ambiente..."
	$(DEV_COMPOSE) down
	@echo "✅ [DEV] ambiente finalizado"

check-env-staging: ## Validar configuração do ambiente STAGING
	@echo "🔎 [STAGING] validando compose..."
	@echo "    project: COMPOSE_PROJECT_NAME (from $(ENV_FILE_STAGING))"
	@echo "    env-file: $(ENV_FILE_STAGING)"
	@echo "    compose: $(COMPOSE_FILE)"
	$(STAGING_COMPOSE) config > /dev/null
	@echo "✅ [STAGING] configuração válida"

pull-staging: ## Pull das imagens do ambiente STAGING (tag obrigatoria)
	@echo "📥 [STAGING] puxando imagens por tag..."
	$(STAGING_COMPOSE) pull
	@echo "✅ [STAGING] pull concluido"

up-staging: ## Subir ambiente STAGING (sem build local)
	@echo "🚀 [STAGING] subindo ambiente..."
	$(STAGING_COMPOSE) up -d --no-build
	@echo "✅ [STAGING] ambiente iniciado"
	@echo "🌐 [STAGING] backend: http://localhost:18002"
	@echo "🌐 [STAGING] frontend: http://localhost:15173"

health-staging: ## Verificar health do ambiente STAGING
	@echo "❤️  [STAGING] verificando /api/readyz..."
	@curl -fsS -H "X-Forwarded-Proto: https" http://localhost:18002/api/readyz/ > /dev/null && echo "✅ [STAGING] readyz ok" || (echo "❌ [STAGING] readyz falhou" && exit 1)

down-staging: ## Derrubar ambiente STAGING
	@echo "⏹️  [STAGING] derrubando ambiente..."
	$(STAGING_COMPOSE) down
	@echo "✅ [STAGING] ambiente finalizado"

check-env-prod: ## Validar configuração do ambiente PRODUÇÃO
	@echo "🔎 [PROD] validando compose..."
	@echo "    project: COMPOSE_PROJECT_NAME (from $(ENV_FILE_PROD))"
	@echo "    env-file: $(ENV_FILE_PROD)"
	@echo "    compose: $(COMPOSE_PROD_FILE)"
	$(PROD_COMPOSE) config > /dev/null
	@echo "✅ [PROD] configuração válida"

pull-prod: ## Pull das imagens do ambiente PRODUÇÃO (tag imutavel promovida)
	@echo "📥 [PROD] puxando imagens publicadas..."
	$(PROD_COMPOSE) pull
	@echo "✅ [PROD] pull concluido"

up-prod: ## Subir ambiente PRODUÇÃO (sem build local)
	@echo "🚀 [PROD] subindo ambiente..."
	$(PROD_COMPOSE) up -d --no-build
	@echo "✅ [PROD] ambiente iniciado"
	@echo "🌐 [PROD] backend: http://localhost:8000"
	@echo "🌐 [PROD] frontend: http://localhost:$${FRONTEND_PORT:-81}"

health-prod: ## Verificar health do ambiente PRODUÇÃO
	@echo "❤️  [PROD] verificando /api/readyz..."
	@curl -fsS -H "X-Forwarded-Proto: https" http://localhost:8000/api/readyz/ > /dev/null && echo "✅ [PROD] readyz ok" || (echo "❌ [PROD] readyz falhou" && exit 1)

down-prod: ## Derrubar ambiente PRODUÇÃO
	@echo "⏹️  [PROD] derrubando ambiente..."
	$(PROD_COMPOSE) down
	@echo "✅ [PROD] ambiente finalizado"

check-env-prod-like: ## Validar configuração do ambiente PROD-LIKE local
	@echo "🔎 [PROD-LIKE] validando compose..."
	@echo "    project: COMPOSE_PROJECT_NAME (from $(ENV_FILE_PRODLIKE))"
	@echo "    env-file: $(ENV_FILE_PRODLIKE)"
	@echo "    compose: $(COMPOSE_PROD_FILE)"
	$(PRODLIKE_COMPOSE) config > /dev/null
	@echo "✅ [PROD-LIKE] configuração válida"

pull-prod-like: ## Pull das imagens do ambiente PROD-LIKE local
	@echo "📥 [PROD-LIKE] puxando imagens..."
	$(PRODLIKE_COMPOSE) pull
	@echo "✅ [PROD-LIKE] pull concluído"

up-prod-like: ## Subir ambiente PROD-LIKE local (sem build)
	@echo "🚀 [PROD-LIKE] subindo ambiente..."
	$(PRODLIKE_COMPOSE) up -d --no-build
	@echo "✅ [PROD-LIKE] ambiente iniciado"
	@echo "🌐 [PROD-LIKE] backend: http://localhost:28000"
	@echo "🌐 [PROD-LIKE] frontend: http://localhost:18081"

health-prod-like: ## Verificar health do ambiente PROD-LIKE local
	@echo "❤️  [PROD-LIKE] verificando /api/readyz..."
	@curl -fsS -H "X-Forwarded-Proto: https" http://localhost:28000/api/readyz/ > /dev/null && echo "✅ [PROD-LIKE] readyz ok" || (echo "❌ [PROD-LIKE] readyz falhou" && exit 1)

down-prod-like: ## Derrubar ambiente PROD-LIKE local
	@echo "⏹️  [PROD-LIKE] derrubando ambiente..."
	$(PRODLIKE_COMPOSE) down
	@echo "✅ [PROD-LIKE] ambiente finalizado"

# ================================================================
# Django
# ================================================================

shell:  ## Abrir Django shell
	@echo "🐚 Abrindo Django shell..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py shell

migrate:  ## Executar migrations
	@echo "🗄️  Executando migrations..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py migrate

makemigrations:  ## Criar migrations
	@echo "📝 Criando migrations..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py makemigrations

superuser:  ## Criar superuser interativamente
	@echo "👤 Criando superuser..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py createsuperuser

collectstatic:  ## Coletar arquivos estáticos
	@echo "📁 Coletando arquivos estáticos..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py collectstatic --noinput

# ================================================================
# Testes
# ================================================================

test:  ## Executar todos os testes
	@echo "🧪 Executando testes..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pytest apps/core/tests apps/dat_ingest/tests apps/dev_tools/tests -v --cov=apps --cov-report=term-missing

test-unit:  ## Executar apenas unit tests
	@echo "🔬 Executando unit tests..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pytest tests/unit/ -v

test-integration:  ## Executar apenas integration tests
	@echo "🔗 Executando integration tests..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pytest tests/integration/ -v

test-e2e:  ## Executar E2E tests (Playwright)
	@echo "🌐 Executando E2E tests..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pytest tests/e2e/ -v

coverage:  ## Gerar relatório de cobertura HTML
	@echo "📊 Gerando relatório de cobertura..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pytest apps/core/tests apps/dat_ingest/tests apps/dev_tools/tests --cov=apps --cov-report=html
	@echo "✅ Relatório gerado em: backend/htmlcov/index.html"

# ================================================================
# ETL & Data
# ================================================================

etl-usuarios:  ## Importar usuários das planilhas
	@echo "📥 Importando usuários..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py etl_usuarios --verbose

etl-agenda:  ## Importar eventos da agenda
	@echo "📅 Importando eventos da agenda..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py etl_agenda --verbose

etl-all:  ## Executar ETL completo
	@echo "🔄 Executando ETL completo..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py etl_completo --verbose

etl-dry-run:  ## Executar ETL em modo simulação
	@echo "🧪 ETL em modo dry-run..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py etl_completo --dry-run --verbose

check-integrity:  ## Verificar integridade dos dados
	@echo "✅ Verificando integridade dos dados..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) python manage.py check_data_integrity

# ================================================================
# Banco de Dados
# ================================================================

db-shell:  ## Abrir PostgreSQL shell
	@echo "🗄️  Abrindo PostgreSQL shell..."
	$(DEV_COMPOSE) exec $(SERVICE_DB) psql -U aprender_user -d aprender_db

db-backup:  ## Fazer backup do banco (output: backups/db_YYYYMMDD.sql)
	@echo "💾 Fazendo backup do banco de dados..."
	mkdir -p ../backups
	$(DEV_COMPOSE) exec -T $(SERVICE_DB) pg_dump -U aprender_user aprender_db > ../backups/db_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup salvo em: backups/db_$(shell date +%Y%m%d_%H%M%S).sql"

db-restore:  ## Restaurar backup do banco (use: make db-restore FILE=backups/db_YYYYMMDD.sql)
	@echo "🔄 Restaurando backup: $(FILE)..."
	$(DEV_COMPOSE) exec -T $(SERVICE_DB) psql -U aprender_user -d aprender_db < $(FILE)
	@echo "✅ Backup restaurado!"

# ================================================================
# Limpeza
# ================================================================

clean:  ## Remover containers, volumes e imagens (⚠️ CUIDADO: Remove dados!)
	@echo "🧹 Limpando ambiente..."
	@echo "⚠️  ATENÇÃO: Isso vai remover todos os containers, volumes e imagens!"
	@read -p "Confirma? (y/N): " confirm && [ $$confirm = y ] || exit 1
	$(DEV_COMPOSE) down -v --rmi all
	@echo "✅ Ambiente limpo!"

prune:  ## Remover volumes órfãos do Docker
	@echo "🗑️  Removendo volumes órfãos..."
	docker volume prune -f

# ================================================================
# Desenvolvimento
# ================================================================

dev:  ## Iniciar ambiente de desenvolvimento (runserver)
	@echo "🚀 Iniciando ambiente de desenvolvimento..."
	$(DEV_COMPOSE) up -d $(SERVICE_DB) redis
	$(DEV_COMPOSE) run --rm --service-ports $(SERVICE_WEB) python manage.py runserver 0.0.0.0:8000

install:  ## Instalar dependências Python no container
	@echo "📦 Instalando dependências..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) pip install -r requirements.txt

lint:  ## Executar linters (Black, Flake8, Bandit)
	@echo "🔍 Executando linters..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) black --check backend/
	$(DEV_COMPOSE) exec $(SERVICE_WEB) flake8 backend/
	$(DEV_COMPOSE) exec $(SERVICE_WEB) bandit -r backend/ -ll

format:  ## Formatar código (Black)
	@echo "✨ Formatando código..."
	$(DEV_COMPOSE) exec $(SERVICE_WEB) black backend/

# ================================================================
# Monitoring
# ================================================================

health:  ## Verificar health dos serviços
	@echo "❤️  Verificando health dos serviços..."
	@echo "Web:"
	@curl -s http://localhost:8002/api/health/ | python -m json.tool || echo "❌ Web não está respondendo"
	@echo ""
	@echo "Database:"
	@$(DEV_COMPOSE) exec $(SERVICE_DB) pg_isready -U aprender_user || echo "❌ DB não está pronto"
	@echo ""
	@echo "Redis:"
	@$(DEV_COMPOSE) exec redis redis-cli ping || echo "❌ Redis não está respondendo"

stats:  ## Ver estatísticas de uso (CPU, memória)
	@echo "📊 Estatísticas dos containers:"
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(shell $(DEV_COMPOSE) ps -q)

# ================================================================
# Staging Gate (Epic #838)
# ================================================================
# Local pre-merge validation: build prod images, run staging stack,
# execute smoke tests. Run via Git Bash on Windows.
# Transitório: usa docker-compose.staging-gate.yml com !reset para
# remover volumes de dev do frontend. Solução estrutural: #857.
# ================================================================

staging-precheck: ## Validar compose com !reset override
	@if ! IMAGE_TAG=$(STAGING_TAG) docker compose --env-file $(ENV_FILE_STAGING) \
	    -f $(COMPOSE_FILE) -f $(COMPOSE_STAGING_GATE) config > /dev/null 2>&1; then \
	  echo "❌ staging-precheck falhou: compose override com !reset não suportado ou inválido."; \
	  echo "   Ação: atualize Docker Compose para versão com suporte a !reset (v2.24.6+)"; \
	  echo "   ou aplique fallback de arquitetura (mover binds dev para docker-compose.override.yml)."; \
	  exit 2; \
	fi
	@echo "✅ staging-precheck ok"

staging-build: ## Build backend+frontend PROD images para staging gate
	@echo "=============================================="
	@echo "   STAGING GATE — Build"
	@echo "=============================================="
	@echo "🔨 [STAGING] building backend ($(BACKEND_IMAGE))..."
	docker build -f $(DOCKERFILE_PROD) \
	  --build-arg GIT_SHA=$(GIT_SHA) \
	  --build-arg BUILD_DATE=$(BUILD_DATE) \
	  --build-arg APP_VERSION=$(STAGING_TAG) \
	  -t $(BACKEND_IMAGE) ..
	@echo "🔨 [STAGING] building frontend ($(FRONTEND_IMAGE))..."
	docker build -f ../frontend/Dockerfile.prod \
	  -t $(FRONTEND_IMAGE) ../frontend
	@echo "✅ [STAGING] build concluído"

staging-up: staging-precheck ## Subir stack staging + migrations
	@echo "🚀 [STAGING] subindo ambiente..."
	@docker image inspect $(BACKEND_IMAGE) > /dev/null 2>&1 || \
	  (echo "❌ Imagem backend não encontrada: $(BACKEND_IMAGE)"; echo "   Execute: make staging-build"; exit 1)
	@docker image inspect $(FRONTEND_IMAGE) > /dev/null 2>&1 || \
	  (echo "❌ Imagem frontend não encontrada: $(FRONTEND_IMAGE)"; echo "   Execute: make staging-build"; exit 1)
	$(STAGING_GATE_COMPOSE) up -d --no-build
	$(STAGING_GATE_COMPOSE) run --rm web python manage.py migrate --noinput
	@echo "✅ [STAGING] ambiente pronto"
	@echo "🌐 [STAGING] backend: http://localhost:18002"
	@echo "🌐 [STAGING] frontend: http://localhost:15173"

staging-test: ## Executar smoke tests no staging
	@echo "=============================================="
	@echo "   STAGING GATE — Smoke Tests"
	@echo "=============================================="
	@bash scripts/smoke_test_staging.sh

staging-down: ## Derrubar stack staging (com volumes)
	@echo "⏹️  [STAGING] derrubando ambiente..."
	-$(STAGING_GATE_COMPOSE) down -v
	@echo "✅ [STAGING] ambiente finalizado"

staging-full: ## Pipeline completo: precheck → build → up → test → teardown
	@echo "=============================================="
	@echo "   STAGING GATE — Full Validation Pipeline"
	@echo "=============================================="
	@bash -lc 'set -euo pipefail; trap "$(MAKE) staging-down || true" EXIT; $(MAKE) staging-precheck && $(MAKE) staging-build && $(MAKE) staging-up && $(MAKE) staging-test'

# ================================================================
# Deploy
# ================================================================

deploy-staging:  ## Deploy em staging
	@echo "🚀 Deploy em staging..."
	@echo "TODO: Implementar pipeline de deploy"

deploy-prod:  ## Deploy em produção
	@echo "🚀 Deploy em produção..."
	@echo "⚠️  ATENÇÃO: Deploy em produção!"
	@read -p "Confirma? (y/N): " confirm && [ $$confirm = y ] || exit 1
	@echo "TODO: Implementar pipeline de deploy"
