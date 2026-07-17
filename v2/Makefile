# PROJECT nomeia o stack Docker. Default = aprender_dev (comportamento de sempre).
# Para rodar múltiplos worktrees em paralelo, cada um exporta um PROJECT distinto
# + portas próprias (DB_HOST_PORT/REDIS_HOST_PORT/BACKEND_HOST_PORT/FRONTEND_HOST_PORT,
# lidas direto pelo compose). Use `source infra/scripts/worktree-env.sh <slot>` para
# derivar tudo de um número. `?=` respeita env/CLI, então quem não exporta nada não muda.
PROJECT ?= aprender_dev
DC = COMPOSE_PROJECT_NAME=$(PROJECT) IMAGE_TAG=latest docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml
WEB = $(DC) exec -T web

.PHONY: up down build logs shell migrate collect seed seed-demo seed-rbac \
        import-compras-dry import-acoes-dry import-cadastros-dry \
        solic-pend-super solic-approve solic-reject \
        readyz healthz preview-json apply-json flags-fake flags-google preview-on preview-off \
        ban-v1 up-worker up-beat logs-worker logs-beat logs-worker-last logs-beat-last \
        seed-e2e test-e2e test-e2e-ui test-e2e-headed help

up:
	$(DC) up -d --build

build:
	$(DC) build --no-cache

down:
	$(DC) down --remove-orphans

logs:
	$(DC) logs -f web

shell:
	$(WEB) bash

migrate:
	$(WEB) python manage.py migrate
	$(WEB) python manage.py collectstatic --noinput

collect:
	$(WEB) python manage.py collectstatic --noinput

seed:
	$(WEB) python manage.py seed_rbac --verbose

seed-demo:
	$(WEB) python manage.py seed_e2e_users

seed-rbac:
	$(WEB) python manage.py seed_rbac

# ════════════════════════════════════════════════════════════════════════════
# API HTTP Imports (via curl - requer autenticação)
# ════════════════════════════════════════════════════════════════════════════

import-compras-dry:
	@echo "⚙️  Uso: make import-compras-dry FILE=/path/to/compras.csv"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Variável FILE não definida"; \
		echo "   Exemplo: make import-compras-dry FILE=./data/compras.csv"; \
		exit 1; \
	fi
	@echo "📤 POST /api/controle/import-compras/?dry_run=true"
	curl -X POST "http://localhost:8002/api/controle/import-compras/?dry_run=true" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(FILE)" \
		-b cookies.txt -c cookies.txt || true

import-acoes-dry:
	@echo "⚙️  Uso: make import-acoes-dry FILE=/path/to/acoes.csv"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Variável FILE não definida"; \
		echo "   Exemplo: make import-acoes-dry FILE=./data/acoes_controle.csv"; \
		exit 1; \
	fi
	@echo "📤 POST /api/controle/import-acoes/?dry_run=true"
	curl -X POST "http://localhost:8002/api/controle/import-acoes/?dry_run=true" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(FILE)" \
		-b cookies.txt -c cookies.txt || true

import-cadastros-dry:
	@echo "⚙️  Uso: make import-cadastros-dry FILE=/path/to/cadastros.csv"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Variável FILE não definida"; \
		echo "   Exemplo: make import-cadastros-dry FILE=./data/dat_cadastros.csv"; \
		exit 1; \
	fi
	@echo "📤 POST /api/dat/import-cadastros/?dry_run=true"
	curl -X POST "http://localhost:8002/api/dat/import-cadastros/?dry_run=true" \
		-H "Content-Type: multipart/form-data" \
		-F "file=@$(FILE)" \
		-b cookies.txt -c cookies.txt || true

# ════════════════════════════════════════════════════════════════════════════
# PR15: Solicitações (Fluxo Coordenador → Superintendência → Controle)
# ════════════════════════════════════════════════════════════════════════════

solic-pend-super:
	@echo "📋 GET /api/solicitacoes/?status=pending&flow=SUPER"
	curl -s -b cookies.txt "http://localhost:8002/api/solicitacoes/?status=pending&flow=SUPER" | jq .

solic-approve:
	@echo "⚙️  Uso: make solic-approve ID=123"
	@if [ -z "$(ID)" ]; then \
		echo "❌ Erro: Variável ID não definida"; \
		echo "   Exemplo: make solic-approve ID=42"; \
		exit 1; \
	fi
	@echo "✅ PATCH /api/solicitacoes/$(ID)/approve/"
	curl -s -X PATCH -b cookies.txt -H "Content-Type: application/json" \
		"http://localhost:8002/api/solicitacoes/$(ID)/approve/" | jq .

solic-reject:
	@echo "⚙️  Uso: make solic-reject ID=123 REASON='conflito de agenda'"
	@if [ -z "$(ID)" ] || [ -z "$(REASON)" ]; then \
		echo "❌ Erro: Variáveis ID e REASON obrigatórias"; \
		echo "   Exemplo: make solic-reject ID=42 REASON='Conflito com evento existente'"; \
		exit 1; \
	fi
	@echo "❌ PATCH /api/solicitacoes/$(ID)/reject/"
	curl -s -X PATCH -b cookies.txt -H "Content-Type: application/json" \
		-d '{"reason":"$(REASON)"}' \
		"http://localhost:8002/api/solicitacoes/$(ID)/reject/" | jq .

readyz:
	curl -fsS http://localhost:8002/api/readyz/ || true

healthz:
	curl -fsS http://localhost:8002/healthz/ || true

preview-json:
	$(WEB) sh -c 'python manage.py preagenda_to_gcal --dry-run --json > /tmp/preagenda.json 2>&1 || true'
	$(WEB) sh -c 'echo "--- /tmp/preagenda.json (head) ---"; head -c 400 /tmp/preagenda.json 2>/dev/null || echo "Arquivo não gerado ou vazio"'

apply-json:
	$(WEB) python manage.py preagenda_to_gcal --json
	@echo "✅ Apply executado. Verifique AuditLog e retornos."

flags-fake:
	@echo "⚙️  Configure GCAL_MODE=fake e PREVIEW_ONLY=true no .env e rode '$(DC) up -d web'"

flags-google:
	@echo "⚙️  Configure GCAL_MODE=google e rode '$(DC) up -d web'"

preview-on:
	@echo "⚙️  PREVIEW_ONLY=true (sem apply). Reinicie web"

preview-off:
	@echo "⚙️  PREVIEW_ONLY=false (aplica no calendário). Reinicie web"

ban-v1:
	./scripts/ban_v1.sh

# ════════════════════════════════════════════════════════════════════════════
# Celery Worker & Beat
# ════════════════════════════════════════════════════════════════════════════

up-worker:
	$(DC) up -d worker

up-beat:
	$(DC) up -d beat

logs-worker:
	$(DC) logs -f worker

logs-beat:
	$(DC) logs -f beat

logs-worker-last:
	$(DC) logs --tail=200 worker

logs-beat-last:
	$(DC) logs --tail=200 beat

# ════════════════════════════════════════════════════════════════════════════
# E2E Tests (Playwright) — Fase 2
# ════════════════════════════════════════════════════════════════════════════

seed-e2e:
	@echo "🌱 Criando seeds para testes E2E (Playwright)..."
	$(WEB) python manage.py seed_e2e_users
	@echo "✅ Seeds E2E criados com sucesso"

test-e2e:
	@echo "🎭 Executando testes E2E (Playwright headless)..."
	@cd tests/playwright && npm run test

test-e2e-ui:
	@echo "🎭 Executando testes E2E com UI interativa (Playwright)..."
	@cd tests/playwright && npm run test:ui

test-e2e-headed:
	@echo "🎭 Executando testes E2E (headed mode - ver browser)..."
	@cd tests/playwright && npm run test:headed

# ════════════════════════════════════════════════════════════════════════════
# Help
# ════════════════════════════════════════════════════════════════════════════

help:
	@echo "════════════════════════════════════════════════════════════════════════════"
	@echo "  Aprender Sistema v2 — Makefile Targets"
	@echo "════════════════════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Stack Management:"
	@echo "  make up                    Start all services (with rebuild)"
	@echo "  make down                  Stop and remove all services"
	@echo "  make build                 Rebuild images (no cache)"
	@echo "  make logs                  Follow web logs"
	@echo ""
	@echo "Django:"
	@echo "  make shell                 Open bash in web container"
	@echo "  make migrate               Run migrations + collectstatic"
	@echo "  make collect               Collect static files"
	@echo "  make seed                  Seed RBAC data"
	@echo "  make seed-demo             Seed demo users"
	@echo "  make seed-rbac             Seed RBAC groups/permissions (idempotent)"
	@echo ""
	@echo "Import via API HTTP (porta 8002, trailing slashes):"
	@echo "  make import-compras-dry    POST /api/controle/import-compras/ (use FILE=...)"
	@echo "  make import-acoes-dry      POST /api/controle/import-acoes/ (use FILE=...)"
	@echo "  make import-cadastros-dry  POST /api/dat/import-cadastros/ (use FILE=...)"
	@echo "  Nota: Relatórios salvos em out_etl/"
	@echo ""
	@echo "PR15 - Solicitações (via API HTTP):"
	@echo "  make solic-pend-super      GET /api/solicitacoes/?status=pending&flow=SUPER"
	@echo "  make solic-approve         PATCH /api/solicitacoes/{ID}/approve/ (use ID=...)"
	@echo "  make solic-reject          PATCH /api/solicitacoes/{ID}/reject/ (use ID=... REASON=...)"
	@echo ""
	@echo "Celery (Worker & Beat):"
	@echo "  make up-worker             Start worker"
	@echo "  make up-beat               Start beat"
	@echo "  make logs-worker           Follow worker logs (Ctrl+C to exit)"
	@echo "  make logs-beat             Follow beat logs (Ctrl+C to exit)"
	@echo "  make logs-worker-last      Show last 200 lines of worker logs"
	@echo "  make logs-beat-last        Show last 200 lines of beat logs"
	@echo ""
	@echo "E2E Tests (Playwright) — Fase 2:"
	@echo "  make seed-e2e              Create seeds for E2E tests (coord, super, controle, formador)"
	@echo "  make test-e2e              Run E2E tests (headless)"
	@echo "  make test-e2e-ui           Run E2E tests with interactive UI"
	@echo "  make test-e2e-headed       Run E2E tests (headed mode - visible browser)"
	@echo "  Nota: Requer npm install em tests/playwright/"
	@echo ""
	@echo "Health Checks:"
	@echo "  make readyz                Check /api/readyz/ (db + redis)"
	@echo "  make healthz               Check /healthz/ (app health)"
	@echo ""
	@echo "Preview & Apply (Google Calendar):"
	@echo "  make preview-json          Preview events (dry-run, JSON output)"
	@echo "  make apply-json            Apply events to Google Calendar"
	@echo "  make flags-fake            Instructions for fake client"
	@echo "  make flags-google          Instructions for Google client"
	@echo "  make preview-on            Enable preview mode"
	@echo "  make preview-off           Disable preview mode"
	@echo ""
	@echo "Security:"
	@echo "  make ban-v1                Run v1 ban script"
	@echo ""
	@echo "════════════════════════════════════════════════════════════════════════════"
