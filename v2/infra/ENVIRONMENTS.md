# Matriz de Ambientes (dev/staging/producao)

Fonte operacional oficial para evitar confusao de contexto no fluxo solo.

## 1) Regras Gerais

1. Sempre explicitar ambiente alvo antes de executar comandos.
2. `dev`, `staging` e `producao` usam env-file, projeto compose e comando diferentes.
3. Em staging/producao, operar com imagem publicada e identificada por tag.
4. Este documento complementa: `.codex/docs/plans/2026-03-04_ambientes-dev-staging-producao.md`.

## 2) Matriz Rapida

| Ambiente | Objetivo | Compose | Env file | COMPOSE_PROJECT_NAME | Backend | Frontend | DB | Redis |
|---|---|---|---|---|---|---|---|---|
| dev | Desenvolvimento local | `docker-compose.yml + docker-compose.override.yml` | `.env.dev` | `aprender_dev` | `8002` | `5173` | `5434` | `6380` |
| staging | Homologacao local | `docker-compose.yml` | `.env.staging` | `aprender_staging` | `18002` | `15173` | `15434` | `16380` |
| prod-like | Validacao local fiel ao compose de producao | `docker-compose.prod.yml` | `.env.prodlike.local` | `aprender_prod_like` | `28000` | `18081` | externo | interno |
| producao | Runtime final (VM01) | `docker-compose.prod.yml` | `stack.env`/`.env.production` | `aprender_prod` | `8000` | `81` | VM02 | VM03 |

## 3) Comandos Oficiais

Usar os alvos do `v2/infra/Makefile`:

```bash
cd v2/infra

# DEV
make check-env-dev
make up-dev
make health-dev
make down-dev

# STAGING
make check-env-staging
make pull-staging
make up-staging
make health-staging
make down-staging

# PROD-LIKE (LOCAL)
make check-env-prod-like
make pull-prod-like
make up-prod-like
make health-prod-like
make down-prod-like

# PRODUCAO (validacao local controlada)
make check-env-prod
make pull-prod
make up-prod
make health-prod
make down-prod
```

Build explicito do backend por perfil:

```bash
cd v2/infra
make build-dev-image
make build-prod-image
```

## 4) Boas Praticas Operacionais

1. Antes de subir ambiente, rode `check-env-*`.
2. Depois de subir, valide com `health-*`.
3. Nunca assumir ambiente pelo terminal; validar pelo comando executado.
4. Para deploy real em VM, registrar `IMAGE_TAG` usada como evidencia.
5. Arquivos `.env.*` deste diretorio sao templates e nao devem conter segredos reais.
6. `staging/producao` devem usar imagem publicada gerada com `Dockerfile.prod`.
7. `staging` exige `IMAGE_TAG` explicita da release; em `producao` a stack opera com `IMAGE_TAG=latest` e promocao controlada por `promotion_tag` no workflow.
8. Em `staging/producao`, `docker-compose.override.yml` nao e aplicado.
9. Em producao Golden Cloud (3-VMs), `docker-compose.prod.yml` usa DB/Redis externos (VM02/VM03); a stack da VM01 sobe `web/worker/beat/frontend`.
10. O `docker-compose.yml` base e prod-like: binds de codigo do frontend (`src/public`) ficam apenas no `docker-compose.override.yml` (dev-only).

## 5) Staging Gate — Validacao Local Pre-Merge

Pipeline local que builda imagens prod, sobe stack staging, roda smoke tests e reporta PASS/FAIL.
Objetivo: validar Dockerfile.prod + integracao de servicos antes do merge.

### Quick start

```bash
cd v2/infra
make staging-full    # build → up → smoke test → teardown (trap EXIT)
```

### O que valida (8 checks)

| # | Check | Endpoint/Comando | Criterio |
| --- | ----- | ---------------- | -------- |
| 1 | Backend readyz | `GET /api/readyz/` | HTTP 200 + `"healthy"` |
| 2 | Backend version | `GET /api/version/` | HTTP 200 + version != "unknown" |
| 3 | CSRF endpoint | `GET /api/csrf/` | HTTP 200 + `csrfToken` presente |
| 4 | Auth pipeline | `POST /api/auth/login/` | HTTP 4xx (Django processa, nao 301) |
| 5 | Celery worker | `celery inspect ping` | resposta `pong` (retry 12x) |
| 6 | Celery beat | `compose ps` + `compose top` | container running + processo ativo |
| 7 | Frontend HTTP | `GET /` (frontend) | HTTP 200 + `<div id="root"` |
| 8 | Frontend health | `GET /health` (nginx) | HTTP 200 |

### Portas (dev vs staging)

| Servico | Dev | Staging |
| ------- | --- | ------- |
| Backend | 8002 | 18002 |
| Frontend | 5173 | 15173 |
| DB | 5434 | 15434 |
| Redis | 6380 | 16380 |

### Targets individuais

```bash
make staging-precheck   # valida suporte a !reset no compose
make staging-build      # build imagens prod (backend + frontend)
make staging-up         # sobe stack + migrations
make staging-test       # roda smoke tests (pode rodar com stack ja up)
make staging-down       # derruba stack + remove volumes
```

### Nota: X-Forwarded-Proto

Staging roda com `DEBUG=0` e `SECURE_SSL_REDIRECT=1`. Todos os curls para o backend
incluem `-H X-Forwarded-Proto:https` para evitar redirect 301.

### Pre-requisitos

- Docker Compose v2.24.6+ (suporte a `!reset`)
- Git Bash (Windows) para execucao dos targets `staging-*`
- Imagens devem ser buildadas localmente antes de `staging-up`

## 6) Evidencias Minimas por Mudanca

1. Comando executado e ambiente alvo.
2. Resultado de `check-env-*`.
3. Resultado de `health-*`.
4. Tag/digest da imagem (staging/producao).
