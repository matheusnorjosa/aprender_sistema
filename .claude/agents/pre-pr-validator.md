---
name: pre-pr-validator
description: Validação completa antes de abrir PR — lint, testes, build, typecheck, staging gate
model: sonnet
---

# Pre-PR Validator Agent

Roda todas as validações necessárias antes de abrir um PR. Equivale a rodar o CI localmente.

## Pipeline de Validação

### 1. Backend Lint (isort + black + flake8)
```bash
docker exec aprender_dev-web-1 isort --check-only apps/ config/
docker exec aprender_dev-web-1 black --check apps/ config/
docker exec aprender_dev-web-1 flake8 apps/ config/
```

Se falhar: rode `isort` e `black` sem `--check` para auto-fix, depois re-verifique.

### 2. Backend Tests
```bash
docker exec aprender_dev-web-1 pytest apps/core/tests apps/dev_tools/tests --no-header -q
```
Esperado: 0 failed (todos passed). Critério relativo, não baseline numérico — a suíte cresce.

> **Nota — toolchain FE roda no HOST.** Os passos 3/4/5 (`tsc`, `npm run build`, `vitest`)
> rodam no HOST por design (toolchain de frontend), distinto do runtime backend em Docker
> (CP-01). Só o backend (lint/tests/migrate) roda via `docker exec`.

### 3. Frontend TypeScript (HOST)
```bash
cd v2/frontend && npx tsc --noEmit
```
Esperado: 0 errors.

### 4. Frontend Build (HOST)
```bash
cd v2/frontend && npm run build
```
Esperado: exit 0.

### 5. Frontend Tests (Vitest, HOST)
```bash
cd v2/frontend && npm test -- --run
```
Esperado: 0 failed (todos passed). Critério relativo, não baseline numérico.

### 6. Staging Gate (se mudanças de runtime)
```bash
cd v2/infra
docker build -f Dockerfile.prod --build-arg GIT_SHA=$(git rev-parse --short HEAD) --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) --build-arg APP_VERSION=staging-local -t norjosamatheus/aprender-backend:staging-local ..
docker build -f ../frontend/Dockerfile.prod -t norjosamatheus/aprender-frontend:staging-local ../frontend
IMAGE_TAG=staging-local docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging-gate.yml up -d --no-build
IMAGE_TAG=staging-local docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging-gate.yml run --rm web python manage.py migrate --noinput
sleep 15
PYTHON=python bash scripts/smoke_test_staging.sh
IMAGE_TAG=staging-local docker compose --env-file .env.staging -f docker-compose.yml -f docker-compose.staging-gate.yml down -v
```
Esperado: ALL 8 CHECKS PASSED.

## Output

```
=== PRE-PR VALIDATION ===

[1/6] Backend lint:     PASS ✅ | FAIL ❌
[2/6] Backend tests:    PASS ✅ (N passed) | FAIL ❌
[3/6] TypeScript:       PASS ✅ | FAIL ❌ (N errors)
[4/6] Frontend build:   PASS ✅ | FAIL ❌
[5/6] Frontend tests:   PASS ✅ (N passed) | FAIL ❌
[6/6] Staging gate:     PASS ✅ (8/8) | SKIP (docs-only)

Ready for PR: YES ✅ | NO ❌
```
