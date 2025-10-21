DC = COMPOSE_PROJECT_NAME=aprender_v2 docker compose -f infra/docker-compose.yml
WEB = $(DC) exec -T web

.PHONY: up down build logs shell migrate collect seed seed-demo seed-rbac \
        etl-acomp-dry etl-acomp-apply etl-desloc-dry etl-desloc-apply readyz healthz \
        preview-json apply-json flags-fake flags-google preview-on preview-off \
        ban-v1 up-worker up-beat logs-worker logs-beat logs-worker-last logs-beat-last help

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
	$(WEB) python manage.py seed_demo_users --verbose

seed-rbac:
	$(WEB) python manage.py seed_rbac

etl-acomp-dry:
	$(WEB) python manage.py etl_upsert_acompanhamento \
		--events-csv /app/data/csv-import/etl_eventos_normalizados.csv \
		--participants-csv /app/data/csv-import/etl_participantes_normalizados.csv \
		--dry-run

etl-acomp-apply:
	$(WEB) python manage.py etl_upsert_acompanhamento \
		--events-csv /app/data/csv-import/etl_eventos_normalizados.csv \
		--participants-csv /app/data/csv-import/etl_participantes_normalizados.csv

etl-desloc-dry:
	@echo "⚙️  Uso: make etl-desloc-dry FILE=/app/data/deslocamentos.csv"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Variável FILE não definida"; \
		echo "   Exemplo: make etl-desloc-dry FILE=/app/data/deslocamentos.xlsx"; \
		exit 1; \
	fi
	$(WEB) python manage.py etl_upsert_deslocamento --file "$(FILE)" --dry-run

etl-desloc-apply:
	@echo "⚙️  Uso: make etl-desloc-apply FILE=/app/data/deslocamentos.csv"
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Erro: Variável FILE não definida"; \
		echo "   Exemplo: make etl-desloc-apply FILE=/app/data/deslocamentos.xlsx"; \
		exit 1; \
	fi
	$(WEB) python manage.py etl_upsert_deslocamento --file "$(FILE)"

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
	@echo "ETL:"
	@echo "  make etl-acomp-dry         Preview ETL acompanhamento (dry-run)"
	@echo "  make etl-acomp-apply       Apply ETL acompanhamento"
	@echo "  make etl-desloc-dry FILE=...   Preview ETL deslocamentos (dry-run)"
	@echo "  make etl-desloc-apply FILE=... Apply ETL deslocamentos"
	@echo ""
	@echo "Celery (Worker & Beat):"
	@echo "  make up-worker             Start worker"
	@echo "  make up-beat               Start beat"
	@echo "  make logs-worker           Follow worker logs (Ctrl+C to exit)"
	@echo "  make logs-beat             Follow beat logs (Ctrl+C to exit)"
	@echo "  make logs-worker-last      Show last 200 lines of worker logs"
	@echo "  make logs-beat-last        Show last 200 lines of beat logs"
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
