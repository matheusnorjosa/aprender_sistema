# Commands Cheatsheet — Aprender Sistema v2

Quick reference for development commands.

---

## Docker (CP-01)

```bash
# Subir ambiente completo
cd v2 && make up

# Parar containers
cd v2 && make down

# Rebuild completo
cd v2 && make rebuild

# Logs
docker compose logs -f web
docker compose logs -f celery
docker compose logs -f db

# Shell no container
docker compose exec web bash
docker compose exec db psql -U postgres aprender_db
```

---

## Django

```bash
# Sempre via docker compose exec web

# Migrations
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Shell
docker compose exec web python manage.py shell_plus

# Criar superuser
docker compose exec web python manage.py createsuperuser

# Collect static
docker compose exec web python manage.py collectstatic --noinput
```

---

## Testes

```bash
# Todos os testes
docker compose exec web python manage.py test

# Pytest (recomendado)
docker compose exec web pytest

# Testes específicos
docker compose exec web pytest apps/core/tests/test_availability_service.py -v
docker compose exec web pytest apps/core/tests/test_approval_policy_PA.py -v
docker compose exec web pytest apps/core/tests/test_gcal*.py -v

# Com coverage
docker compose exec web pytest --cov=apps --cov-report=term-missing

# Verbose com output
docker compose exec web pytest -v -s
```

---

## Type Checking

```bash
# Pyright (Pyright strict mode)
cd v2/backend && pyright apps/core
cd v2/backend && pyright apps/dev_tools
cd v2/backend && pyright apps/dat_ingest

# Pyright completo
cd v2/backend && pyright
```

---

## ETL Commands

```bash
# Dry-run (preview sem aplicar)
docker compose exec web python manage.py etl_upsert_acompanhamento
docker compose exec web python manage.py etl_upsert_deslocamento
docker compose exec web python manage.py etl_import_compras

# Apply (aplicar mudanças)
docker compose exec web python manage.py etl_upsert_acompanhamento --apply
docker compose exec web python manage.py etl_upsert_deslocamento --apply
docker compose exec web python manage.py etl_import_compras --apply

# Com arquivo específico
docker compose exec web python manage.py etl_import_compras --file=/data/compras.xlsx --apply
```

---

## Dev Tools (INCLUDE_DEV_TOOLS=true)

```bash
# Seeds
docker compose exec web python manage.py seed_usuarios
docker compose exec web python manage.py seed_projetos
docker compose exec web python manage.py seed_rbac

# Backfills
docker compose exec web python manage.py backfill_<nome>

# Fixes únicos
docker compose exec web python manage.py fix_<nome>

# Limpeza E2E
docker compose exec web python manage.py cleanup_e2e_data
```

---

## Core Commands (sempre disponíveis)

```bash
# Google Calendar sync
docker compose exec web python manage.py preagenda_to_gcal

# Rotação de chave GCal
docker compose exec web python manage.py rotate_gcal_encryption_key
```

---

## Git (CP-05, CP-07)

```bash
# Branch pattern
git checkout -b feat/<nome>
git checkout -b fix/<nome>
git checkout -b chore/<nome>

# Commit pattern
git commit -m "feat(scope): message"
git commit -m "fix(scope): message"
git commit -m "chore(scope): message"

# Push e PR
git push -u origin <branch>
gh pr create --title "type(scope): message" --body "## Summary\n..."

# Merge (squash)
gh pr merge <number> --squash --delete-branch
```

---

## Linting / Formatting

```bash
# Backend
docker compose exec web ruff check apps/
docker compose exec web ruff format apps/

# Frontend
cd v2/frontend && npm run lint
cd v2/frontend && npm run format
```

---

## Database

```bash
# Acesso direto PostgreSQL
docker compose exec db psql -U postgres aprender_db

# Dump
docker compose exec db pg_dump -U postgres aprender_db > backup.sql

# Restore
docker compose exec -T db psql -U postgres aprender_db < backup.sql
```

---

## Redis

```bash
# CLI Redis
docker compose exec redis redis-cli

# Limpar cache
docker compose exec redis redis-cli FLUSHALL
```

---

## Celery

```bash
# Verificar tasks
docker compose exec celery celery -A config inspect active

# Purge queue
docker compose exec celery celery -A config purge
```

---

## Frontend

```bash
# Dev server
cd v2/frontend && npm run dev

# Build
cd v2/frontend && npm run build

# Preview build
cd v2/frontend && npm run preview

# Testes
cd v2/frontend && npm test

# E2E (Playwright)
cd v2/frontend && npx playwright test
```

---

## Aliases Úteis (adicionar ao .bashrc)

```bash
alias dc="docker compose"
alias dcw="docker compose exec web"
alias dct="docker compose exec web pytest"
alias dcm="docker compose exec web python manage.py"
```
