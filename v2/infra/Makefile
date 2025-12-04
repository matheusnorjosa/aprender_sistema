# ================================================================
# AS v2 — Makefile
# ================================================================
# Comandos unificados para operações comuns
# ================================================================

.PHONY: help build up up-obs down down-obs restart logs shell migrate test clean

# Variáveis
COMPOSE_FILE := docker-compose.yml
COMPOSE_OBS_FILE := docker-compose.observability.yml
SERVICE_WEB := web
SERVICE_DB := db
SERVICE_WORKER := worker

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

up:  ## Iniciar todos os serviços
	@echo "🚀 Iniciando serviços..."
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "✅ Serviços iniciados!"
	@echo "🌐 Web: http://localhost:8000"
	@echo "📊 Admin: http://localhost:8000/admin"
	@echo "🔍 API Health: http://localhost:8000/api/health/"

up-obs:  ## Iniciar com stack de observabilidade (Prometheus + Grafana)
	@echo "🚀 Iniciando serviços com observabilidade..."
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_OBS_FILE) up -d
	@echo "✅ Serviços iniciados!"
	@echo "🌐 Web: http://localhost:8000"
	@echo "📊 Grafana: http://localhost:3000 (admin/admin)"
	@echo "🔍 Prometheus: http://localhost:9090"

down:  ## Parar todos os serviços
	@echo "⏹️  Parando serviços..."
	docker compose -f $(COMPOSE_FILE) down

down-obs:  ## Parar serviços + observabilidade
	@echo "⏹️  Parando serviços com observabilidade..."
	docker compose -f $(COMPOSE_FILE) -f $(COMPOSE_OBS_FILE) down

restart:  ## Reiniciar todos os serviços
	@echo "🔄 Reiniciando serviços..."
	docker compose -f $(COMPOSE_FILE) restart

logs:  ## Ver logs (use: make logs SERVICE=web)
	@echo "📋 Logs do serviço $(SERVICE_WEB)..."
	docker compose -f $(COMPOSE_FILE) logs -f --tail=100 $(SERVICE_WEB)

ps:  ## Ver status dos containers
	@echo "📊 Status dos containers:"
	docker compose -f $(COMPOSE_FILE) ps

# ================================================================
# Django
# ================================================================

shell:  ## Abrir Django shell
	@echo "🐚 Abrindo Django shell..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py shell

migrate:  ## Executar migrations
	@echo "🗄️  Executando migrations..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py migrate

makemigrations:  ## Criar migrations
	@echo "📝 Criando migrations..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py makemigrations

superuser:  ## Criar superuser interativamente
	@echo "👤 Criando superuser..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py createsuperuser

collectstatic:  ## Coletar arquivos estáticos
	@echo "📁 Coletando arquivos estáticos..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py collectstatic --noinput

# ================================================================
# Testes
# ================================================================

test:  ## Executar todos os testes
	@echo "🧪 Executando testes..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pytest tests/ -v --cov=core --cov=dat_ingest --cov-report=term-missing

test-unit:  ## Executar apenas unit tests
	@echo "🔬 Executando unit tests..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pytest tests/unit/ -v

test-integration:  ## Executar apenas integration tests
	@echo "🔗 Executando integration tests..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pytest tests/integration/ -v

test-e2e:  ## Executar E2E tests (Playwright)
	@echo "🌐 Executando E2E tests..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pytest tests/e2e/ -v

coverage:  ## Gerar relatório de cobertura HTML
	@echo "📊 Gerando relatório de cobertura..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pytest tests/ --cov=core --cov=dat_ingest --cov-report=html
	@echo "✅ Relatório gerado em: backend/htmlcov/index.html"

# ================================================================
# ETL & Data
# ================================================================

etl-usuarios:  ## Importar usuários das planilhas
	@echo "📥 Importando usuários..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py etl_usuarios --verbose

etl-agenda:  ## Importar eventos da agenda
	@echo "📅 Importando eventos da agenda..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py etl_agenda --verbose

etl-all:  ## Executar ETL completo
	@echo "🔄 Executando ETL completo..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py etl_completo --verbose

etl-dry-run:  ## Executar ETL em modo simulação
	@echo "🧪 ETL em modo dry-run..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py etl_completo --dry-run --verbose

check-integrity:  ## Verificar integridade dos dados
	@echo "✅ Verificando integridade dos dados..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) python manage.py check_data_integrity

# ================================================================
# Banco de Dados
# ================================================================

db-shell:  ## Abrir PostgreSQL shell
	@echo "🗄️  Abrindo PostgreSQL shell..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_DB) psql -U aprender_user -d aprender_db

db-backup:  ## Fazer backup do banco (output: backups/db_YYYYMMDD.sql)
	@echo "💾 Fazendo backup do banco de dados..."
	mkdir -p ../backups
	docker compose -f $(COMPOSE_FILE) exec -T $(SERVICE_DB) pg_dump -U aprender_user aprender_db > ../backups/db_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup salvo em: backups/db_$(shell date +%Y%m%d_%H%M%S).sql"

db-restore:  ## Restaurar backup do banco (use: make db-restore FILE=backups/db_YYYYMMDD.sql)
	@echo "🔄 Restaurando backup: $(FILE)..."
	docker compose -f $(COMPOSE_FILE) exec -T $(SERVICE_DB) psql -U aprender_user -d aprender_db < $(FILE)
	@echo "✅ Backup restaurado!"

# ================================================================
# Limpeza
# ================================================================

clean:  ## Remover containers, volumes e imagens (⚠️ CUIDADO: Remove dados!)
	@echo "🧹 Limpando ambiente..."
	@echo "⚠️  ATENÇÃO: Isso vai remover todos os containers, volumes e imagens!"
	@read -p "Confirma? (y/N): " confirm && [ $$confirm = y ] || exit 1
	docker compose -f $(COMPOSE_FILE) down -v --rmi all
	@echo "✅ Ambiente limpo!"

prune:  ## Remover volumes órfãos do Docker
	@echo "🗑️  Removendo volumes órfãos..."
	docker volume prune -f

# ================================================================
# Desenvolvimento
# ================================================================

dev:  ## Iniciar ambiente de desenvolvimento (runserver)
	@echo "🚀 Iniciando ambiente de desenvolvimento..."
	docker compose -f $(COMPOSE_FILE) up -d $(SERVICE_DB) redis
	docker compose -f $(COMPOSE_FILE) run --rm --service-ports $(SERVICE_WEB) python manage.py runserver 0.0.0.0:8000

install:  ## Instalar dependências Python no container
	@echo "📦 Instalando dependências..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) pip install -r requirements.txt

lint:  ## Executar linters (Black, Flake8, Bandit)
	@echo "🔍 Executando linters..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) black --check backend/
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) flake8 backend/
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) bandit -r backend/ -ll

format:  ## Formatar código (Black)
	@echo "✨ Formatando código..."
	docker compose -f $(COMPOSE_FILE) exec $(SERVICE_WEB) black backend/

# ================================================================
# Monitoring
# ================================================================

health:  ## Verificar health dos serviços
	@echo "❤️  Verificando health dos serviços..."
	@echo "Web:"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool || echo "❌ Web não está respondendo"
	@echo ""
	@echo "Database:"
	@docker compose -f $(COMPOSE_FILE) exec $(SERVICE_DB) pg_isready -U aprender_user || echo "❌ DB não está pronto"
	@echo ""
	@echo "Redis:"
	@docker compose -f $(COMPOSE_FILE) exec redis redis-cli ping || echo "❌ Redis não está respondendo"

stats:  ## Ver estatísticas de uso (CPU, memória)
	@echo "📊 Estatísticas dos containers:"
	docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(shell docker compose -f $(COMPOSE_FILE) ps -q)

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
