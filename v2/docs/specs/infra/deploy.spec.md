---
title: Deploy & Produção (spec)
status: canonical
last_verified: 2026-07-10
sources_of_truth:
  - v2/infra/docker-compose.prod.yml
  - v2/infra/Dockerfile.prod
  - v2/frontend/Dockerfile.prod
  - .github/workflows/deploy.yaml
  - v2/infra/Makefile
owner: infra
related:
  - ../INDEX_SDD.md
  - ../../OBSERVABILITY.md
  - ../../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md
---

# Deploy & Produção

> **Verificado em 2026-06-19** contra a stack viva no Portainer (aba Editor + Environment variables) e contra o
> repositório. **Drift funcional: zero** — o compose vivo é idêntico ao `v2/infra/docker-compose.prod.yml` (só
> diferem 2-3 linhas de comentário). Esta spec descreve o que **de fato** roda em produção.
>
> **Pré-go-live:** em 2026-06-19 produção está **sem dados e sem usuários** — isso reduz a urgência dos gaps
> abaixo (não são emergência), mas todos devem ser fechados **antes do go-live**.

## Qual arquivo vai para produção

| Artefato | Produção | Observação |
|---|---|---|
| Compose | **`v2/infra/docker-compose.prod.yml`** (standalone) | Usado **sozinho** (`-f docker-compose.prod.yml`), **não** mergeia o `docker-compose.yml` base — ver `Makefile` `PROD_COMPOSE`. |
| Imagem backend | **`v2/infra/Dockerfile.prod`** → `norjosamatheus/aprender-backend:${IMAGE_TAG}` | `deploy.yaml` |
| Imagem frontend | **`v2/frontend/Dockerfile.prod`** → `norjosamatheus/aprender-frontend:${IMAGE_TAG}` | `deploy.yaml` |
| Env | `stack.env` no Portainer (`APP_ENV_FILE`) | **não** é o `.env.production` do repo (que é template) |

**NÃO vão para produção:** `docker-compose.yml` (base; dev+staging), `docker-compose.override.yml` (dev,
auto-load), `docker-compose.staging-gate.yml` (gate), `docker-compose.observability.yml` (local, gitignored),
`Dockerfile.dev`, `v2/frontend/Dockerfile`.

## Mecanismo de deploy — PULL-BASED (ADR-018)

> **Mudou em 2026-07-09/10.** O modelo antigo (o CI fazia `PUT` no `:9443` **público**) foi desligado no
> cutover (#1515) e o job `deploy` foi **deletado** na Fase 4 (#1516). O texto abaixo é o fluxo atual.

**Merge na `main` NÃO deploya.** Ele dispara `deploy.yaml` (hoje *"Build, sign and release"*), que faz
build → scan → push no Docker Hub → **assina** as imagens (cosign keyless + provenance SLSA) → cria a tag
imutável `vYYYY.MM.DD-<sha7>` e o GitHub Release. Fim.

Produção muda em **dois passos deliberados**:

1. **`promote.yml`** (`workflow_dispatch`, gated no GitHub Environment `production` com *required reviewer*):
   resolve tag→digest, **exige** que as imagens estejam assinadas, monta o `production.json` (release, digests,
   `sequence` monotônica, `expires_at`) e o **assina** (`cosign sign-blob`, identidade OIDC do próprio workflow).
   Publica no branch protegido **`deploy-pointer`**.
2. **Agente `aprender-deployer` na VM01** (systemd, ~60s): lê o ponteiro *tokenless* por `raw.githubusercontent.com`,
   verifica a assinatura contra um trusted-root **pinado offline**, verifica as duas imagens **por digest**
   (`cosign verify`), e entrega ao `aprender-applier` (o único que detém o token do Portainer). O applier
   re-verifica tudo dos bytes, confere anti-rollback (**selo** monotônico), confere **drift do compose**, exige
   **backup de DB fresco**, faz o `PUT` em **`127.0.0.1:9443`** com o compose que ele mesmo detém, confirma em
   `localhost` (`/api/readyz/` + `/api/version/`) e só então **sela** a sequence. Cada degrau é **fail-closed**.

Consequências que mudam o modelo mental antigo:

- **O corpo do compose É enviado** no PUT do applier — mas é o `trust/compose.pinned.yml`, imutável na VM, nunca
  um texto vindo da rede. Alterar o compose continua exigindo edição **manual** no Editor do Portainer, seguida de
  re-captura do pinado (senão o `compose_check_drift` recusa o deploy).
- As imagens são fixadas **por digest** (`repo:${IMAGE_TAG}@${DIGEST:?}`), não por tag.
- A confirmação é feita **de dentro da VM**, o que a torna imune ao *false-red* do `:9443` (o `PUT` chega, prod
  atualiza, mas a resposta não volta pelo firewall).

> **Risco de drift:** `docker-compose.prod.yml` no repo é a *intenção*; a verdade é o Editor do Portainer — e o
> `trust/compose.pinned.yml` na VM é o que o agente reenvia. Divergência entre o pinado e o vivo **bloqueia** o
> deploy (`REFUSE compose_drift`), o que é o comportamento desejado.

**Depreciado (issue #814):** os workflows `.github/workflows/release.yaml` e
`.github/workflows/dockerhub-rebuild.yml` foram **removidos** — o `deploy.yaml` é o único pipeline de deploy.
As variáveis `STAGING_DEPLOY_COMMAND` e `PRODUCTION_DEPLOY_COMMAND` ficaram **obsoletas** e não são mais usadas
pelo pipeline canônico (ver `DEPLOY_CHECKLIST.md` §7).

## Produção vs Local (estado verificado 2026-06-19)

| Componente | Produção | Local/dev |
|---|---|---|
| Stack | 5 serviços: web, redis, worker, beat, frontend | idem + override de dev |
| Observabilidade (Prometheus/Grafana) | **NÃO roda** | opcional via `make up-obs` (compose gitignored) |
| `/metrics` (django-prometheus) | exposto, **gated** (staff/IP interno, SEC-RECON-02) | exposto |
| Sentry | **DESLIGADO** — `SENTRY_DSN` ausente no stack.env | off (salvo se setar DSN) |
| Backup Celery | **morto e silencioso** — ver abaixo | grava em `backup_data:/backups` (base) |
| Redis auth | **ATIVO** — `REDIS_PASSWORD` preenchido; isolado em `backend-internal` sem porta no host | conforme `.env` |
| Migrations | **manuais** — nenhum serviço roda `migrate` (web=gunicorn, worker/beat=celery) | idem |
| Guards de prod | **OK** — `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, `SECURE_SSL_REDIRECT`, `DB_SSLMODE` setados | guards não se aplicam |
| GCal | **configurado** (`GCAL_*` completos) | conforme `.env` |
| dev_tools (CP-08) | **off** — `INCLUDE_DEV_TOOLS` ausente → default `false` | on em dev |

### Backup: por que está "morto e silencioso"

- `worker` e `beat` são `read_only: true`; `tmpfs` só em `/tmp,/run,/home/appuser,/app/out_etl`; **nenhum volume
  `/backups`** (único volume nomeado é `redis_data`). O default `BACKUP_DIR=/backups` cai em filesystem read-only
  → **EROFS** → a task Celery falha e não gera nenhum arquivo.
- `BACKUP_AGE_RECIPIENT` **está setado** (backup encriptado *pretendido*), mas como nada é escrito, a encriptação
  nunca acontece.
- Com **Sentry off**, a falha não gera alerta → silenciosa. A única proteção de dados possível é o cron na **VM02**
  (#376, WAL archiving) — **fora desta stack**, não verificável pelo Portainer/repo (exige SSH na VM02).
- Rastreado em **#1455** (mount `/backups`) e **#1457**/**#1456** (Redis guard / migrations).

## Topologia do Redis: container na VM01 (decisão 2026-06-19)

**Realidade:** o Redis roda como **container na VM01** (serviço `redis` no `docker-compose.prod.yml`, rede
`backend-internal`), **não** numa VM03 dedicada. O app conecta via `REDIS_HOST` (default `redis` → o container);
cache (`/0`), Celery broker (`/1`) e sessões (`SESSION_ENGINE=cache`) usam esse Redis.

**Decisão: manter na VM01.** Latência localhost (<1ms — sessão bate no Redis a cada request autenticado), seguro
(senha + `backend-internal` sem porta no host), cabe nos recursos (2g de 16g). O downside (restart da VM01 =
re-login + perda de tasks Celery em voo) é irrelevante pré-go-live e aceitável no volume previsto.
**Rejeitado:** Redis grátis externo (latência por-request + rate-limit de free tier para sessão/cache/broker).
VM03 dedicada só se **HA** virar requisito.

**Docs a reconciliar (Fase 2 — hoje afirmam VM03, divergindo do compose):** `v2/infra/ENVIRONMENTS.md:19/74`
("Redis externo VM03"), `v2/infra/README.md:170` (tabela "VM03_Redis"), `.claude/CLAUDE.md` (tabela prod).
Vestigiais (não montados pelo container, que usa `--requirepass` inline): `v2/infra/configs/vm03/redis.conf`,
`v2/infra/redis/redis.conf`. **VM03 provavelmente está ociosa** (nota de inventário/custo).

## Variáveis de ambiente em produção (stack.env)

Presentes (valores no Portainer; secrets marcados `[s]`): `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`[s],
`DB_PORT`, `DB_SSLMODE`, `DATABASE_URL`[s], `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`[s], `REDIS_URL`[s],
`SECRET_KEY`[s], `DEBUG`, `ALLOWED_HOSTS`, `ENVIRONMENT`, `CSRF_TRUSTED_ORIGINS`, `SECURE_SSL_REDIRECT`,
`VITE_API_URL`, `FRONTEND_URL`, `DOCKER_HUB_TOKEN`[s], `GCAL_CLIENT`, `GCAL_AUTH_MODE`, `GCAL_CALENDAR_ID`,
`GCAL_OAUTH_CLIENT_ID`, `GCAL_OAUTH_CLIENT_SECRET`[s], `GCAL_OAUTH_REDIRECT_URI`, `GCAL_ENCRYPTION_KEY`[s],
`GCAL_ALLOWED_DOMAIN`, `BACKUP_AGE_RECIPIENT`, `IMAGE_TAG`.

**Ausentes (significativo):** `SENTRY_DSN` (→ Sentry off), `BACKUP_DIR` (→ default `/backups`, EROFS),
`INCLUDE_DEV_TOOLS`/`INCLUDE_ETL` (→ defaults off, correto).

> **Redundância a revisar (não-bug):** coexistem `DATABASE_URL` e `DB_*`, e `REDIS_URL` e `REDIS_*`. Conferir qual
> o `config/settings.py` realmente consome para não haver duas fontes divergentes.

## Como re-verificar (read-only)

1. Portainer → Stacks → stack de prod → **Editor** (compose vivo) e **Environment variables** (valores reais).
2. (Opcional) VM01 via SSH: `docker ps`, `docker inspect <svc>` (mounts/read_only/env). **Nunca** reiniciar
   Docker/containers (Kaspersky/KESL derruba o site).

## Gaps abertos relacionados

- **#1455** — backup Celery sem `/backups` gravável em prod (agravado: Sentry off → silencioso).
- **#1456** — deploy não aplica migrations + CI sem `makemigrations --check`.
- **#1457** — guard de `REDIS_PASSWORD` obrigatório (em prod está setado; falta o fail-fast preventivo).
