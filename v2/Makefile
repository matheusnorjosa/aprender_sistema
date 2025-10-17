DC = COMPOSE_PROJECT_NAME=as_v2 docker compose -f infra/docker-compose.yml
WEB = $(DC) exec -T web

.PHONY: up down build logs shell migrate collect seed seed-demo readyz healthz \
        preview-json apply-json flags-fake flags-google preview-on preview-off \
        ban-v1

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
