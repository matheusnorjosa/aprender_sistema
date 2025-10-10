include .env
export

help:
	@echo "Targets: build, up, down, logs, ps, makemigrations, migrate, collectstatic, createsuperuser, bootstrap-rbac, preagenda-sync, preagenda-dryrun, dev, prod"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f web

ps:
	docker compose ps

makemigrations:
	docker compose exec -T web python manage.py makemigrations

migrate:
	docker compose exec -T web python manage.py migrate

collectstatic:
	docker compose exec -T web python manage.py collectstatic --noinput

createsuperuser:
	docker compose exec -it web python manage.py createsuperuser

bootstrap-rbac:
	docker compose exec -T web python manage.py bootstrap_rbac --verbose

preagenda-sync:
	docker compose exec -T web python manage.py preagenda_to_gcal

preagenda-dryrun:
	docker compose exec -T web python manage.py preagenda_to_gcal --dry-run

dev:
	RUN_MODE=dev DJANGO_DEBUG=1 docker compose up -d --build

prod:
	RUN_MODE=prod DJANGO_DEBUG=0 docker compose up -d --build
