---
title: Ambientes (dev / staging / prod-like)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/Makefile
  - v2/infra/Makefile
  - v2/infra/docker-compose.yml
  - v2/infra/docker-compose.override.yml
  - v2/infra/docker-compose.staging-gate.yml
  - v2/infra/docker-compose.prod.yml
  - v2/infra/.env.prodlike.example
  - v2/infra/scripts/smoke_test_staging.sh
owner: infra
supersedes: []
related:
  - ./deploy.spec.md
  - ../INDEX_SDD.md
  - ../../OBSERVABILITY.md
  - ../../DEPLOY_CHECKLIST.md
---

# Ambientes (dev / staging / prod-like)

> **Verificado em 2026-06-19** contra os Makefiles, os `docker-compose*.yml` e os `.env.*` do repositório.
> Esta spec descreve **quais** ambientes existem, **como cada um sobe** e **o que muda** entre eles.
> Para o que **de fato roda em produção** (mecanismo de deploy, hardening, gaps de go-live), ver a
> [deploy.spec](./deploy.spec.md) — esta spec não duplica esse conteúdo.

## Propósito

O sistema tem **quatro perfis de ambiente** montados sobre o mesmo conjunto de imagens Docker, diferenciados
por arquivo de compose, `.env` e portas publicadas. O objetivo é permitir iterar em **dev** com hot-reload,
validar fidelidade prod localmente (**staging-gate** e **prod-like**) e rodar **produção** com a stack
endurecida — sem que os perfis colidam entre si (cada um usa `COMPOSE_PROJECT_NAME` e portas de host distintas).

A separação de Makefiles é deliberada: **dev** é dirigido por [`v2/Makefile`](../../../Makefile) (que opera de
dentro de `v2/`, prefixando `infra/...` nos compose); **staging / prod / prod-like / staging-gate** são
dirigidos por [`v2/infra/Makefile`](../../../infra/Makefile). Vale a Cláusula Pétrea **CP-01**: v2 roda
**apenas em Docker**.

## Fonte de verdade no código

| Perfil | Makefile (target) | Compose | `.env` | Imagem |
|---|---|---|---|---|
| **dev** | [`v2/Makefile`](../../../Makefile) `up` / `down` / `logs` | [`docker-compose.yml`](../../../infra/docker-compose.yml) + [`docker-compose.override.yml`](../../../infra/docker-compose.override.yml) | `.env.dev` (local) | build local ([`Dockerfile.dev`](../../../infra/Dockerfile.dev)), `IMAGE_TAG=latest` |
| **staging** | [`v2/infra/Makefile`](../../../infra/Makefile) `up-staging` / `health-staging` / `down-staging` | `docker-compose.yml` **sozinho** | `.env.staging` (local) | pull por tag publicada (`--no-build`), `IMAGE_TAG` **obrigatório** |
| **staging-gate** | `v2/infra/Makefile` `staging-full` (precheck→build→up→test→down) | `docker-compose.yml` + [`docker-compose.staging-gate.yml`](../../../infra/docker-compose.staging-gate.yml) | `.env.staging` | build local PROD ([`Dockerfile.prod`](../../../infra/Dockerfile.prod)), tag `staging-local` |
| **prod-like** | `v2/infra/Makefile` `up-prod-like` / `health-prod-like` | [`docker-compose.prod.yml`](../../../infra/docker-compose.prod.yml) **standalone** | `.env.prodlike.local` (cópia de [`.env.prodlike.example`](../../../infra/.env.prodlike.example)) | pull por tag (`--no-build`) |
| **prod** | `v2/infra/Makefile` `up-prod` (→ ver [deploy.spec](./deploy.spec.md)) | `docker-compose.prod.yml` **standalone** | `stack.env` no Portainer (`APP_ENV_FILE`) | tag imutável promovida |

Definições das variáveis de composição estão no topo de [`v2/infra/Makefile`](../../../infra/Makefile)
(`DEV_COMPOSE`, `STAGING_COMPOSE`, `PROD_COMPOSE`, `PRODLIKE_COMPOSE`, `STAGING_GATE_COMPOSE`).

## Contratos e invariantes

- **CP-01** — todo ambiente é Docker. Não há modo "roda na máquina sem container".
- **Override é dev-only.** [`docker-compose.override.yml`](../../../infra/docker-compose.override.yml) monta o
  código como volume (`../backend:/app`, `../frontend/src` ro) para hot-reload e **NÃO pode** ser aplicado em
  staging/prod (declarado no cabeçalho do próprio arquivo). Staging usa `docker-compose.yml` sozinho; prod usa
  `docker-compose.prod.yml` standalone (**não** mergeia a base).
- **`IMAGE_TAG` é obrigatório fora de dev.** A base [`docker-compose.yml`](../../../infra/docker-compose.yml)
  usa `${IMAGE_TAG:?IMAGE_TAG is required}` em todos os serviços de app. Só dev define `IMAGE_TAG=latest`;
  staging/prod-like/prod **devem** passar tag explícita (`vYYYY.MM.DD-<sha>`).
- **Isolamento por projeto + portas.** Cada perfil tem `COMPOSE_PROJECT_NAME` próprio
  (`aprender_dev` / `aprender_staging` / `aprender_prod_like` / `aprender_prod`) e portas de host distintas
  (dev 8002/5173/5434/6380; staging 18002/15173/15434/16380; prod-like 28000/18081). Subir dois perfis em
  paralelo não colide.
- **Topologia de produção (VM01 vs VM02).** Em prod, **Redis é container local na stack da VM01**
  (`docker-compose.prod.yml`, serviço `redis` com `--requirepass` + AOF); **PostgreSQL é externo na VM02**
  (`DB_HOST` aponta para o IP da VM02). Em dev/staging/prod-like o `db` é um container local da própria stack.
- **`DEBUG` e `ENVIRONMENT`.** Apenas dev tem `DEBUG=1` / `ENVIRONMENT=development`. Staging =
  `ENVIRONMENT=staging` (`DEBUG=0`); prod/prod-like = `ENVIRONMENT=production`. O `settings.py` deriva
  comportamento disso (cookies `Secure`, `statement_timeout=30000ms`, JSON logging em staging/prod, Silk
  profiler só em staging).
- **`.env.*` versionados são templates.** `SECRET_KEY=CHANGE_ME_*` e senhas placeholder. Segredos reais de
  produção vivem no `stack.env` do Portainer, **não** no repo.
- **Observabilidade é DEV-only.** Prometheus+Grafana sobem só via `make up-obs` (compose de observabilidade é
  **gitignored**, fora desta árvore). Em produção não há Prometheus/Grafana na stack: o endpoint `/metrics`
  fica **gated** (`_metrics_gate` → staff ou IP interno, em `config/urls.py`) e Sentry só liga se `SENTRY_DSN`
  estiver setado (atualmente OFF). Detalhe em [OBSERVABILITY.md](../../OBSERVABILITY.md).

## API / Interface

Comandos de operação (todos exigem Docker; CP-01):

```bash
# DEV (de dentro de v2/) — v2/Makefile
make up          # docker-compose.yml + override, build local, sobe tudo
make down
make logs
make health      # checa /api/readyz/, pg_isready, redis-cli ping

# STAGING / PROD-LIKE / PROD (de dentro de v2/infra/) — v2/infra/Makefile
make check-env-staging      # valida `docker compose config` sem subir
make up-staging             # pull por tag + up --no-build  (IMAGE_TAG=... obrigatório)
make health-staging         # /api/readyz/ com X-Forwarded-Proto: https
make down-staging
make up-prod-like           # docker-compose.prod.yml standalone, --no-build
make health-prod-like
make up-prod                 # idem prod (ver deploy.spec)

# STAGING GATE (validação pré-merge prod-like local)
make staging-full           # precheck → build PROD → up → smoke → teardown
```

Endpoints de health expostos por todos os perfis: `GET /api/readyz/` (db + redis) e `GET /healthz/` (app).

## Fluxos principais

**Subir dev (caminho feliz):** de `v2/`, `make up` → `DEV_COMPOSE` (`--env-file .env.dev -f infra/docker-compose.yml -f infra/docker-compose.override.yml`) faz build local e sobe `db`, `redis`, `web`, `frontend` (worker/beat sob demanda). Backend em `http://localhost:8002`, frontend em `:5173`. Hot-reload ativo pelos volumes do override.

**Validar pré-merge (staging-gate):** de `v2/infra/`, `make staging-full` roda o pipeline
[`smoke_test_staging.sh`](../../../infra/scripts/smoke_test_staging.sh): `staging-precheck` (valida o override
`!reset`, exige Compose v2.24.6+) → `staging-build` (imagens PROD com `GIT_SHA`/`BUILD_DATE`) → `staging-up`
(sobe + `migrate --noinput`, portas 18002/15173) → `staging-test` (smoke) → `staging-down -v` (teardown via
`trap EXIT`, remove volumes).

**Reproduzir prod localmente (prod-like):** `cp .env.prodlike.example .env.prodlike.local` (ajustar secrets) →
`make up-prod-like`. Usa `docker-compose.prod.yml` standalone com `DB_HOST=host.docker.internal` para simular o
PostgreSQL externo da VM02; Redis é local na stack. Backend em `:28000`, frontend em `:18081`.

**Erros comuns:**

- `IMAGE_TAG is required` ao subir staging/prod sem tag → exportar `IMAGE_TAG=vYYYY.MM.DD-<sha>`.
- `staging-precheck falhou: !reset não suportado` → atualizar Docker Compose (v2.24.6+).
- Colisão de porta → confirmar que não há outro perfil usando a mesma faixa (cada perfil tem portas próprias).

## Decisões relacionadas (ADRs)

- Separação de perfis e portas — issue **#753** (seção "Ambientes" do [`v2/infra/Makefile`](../../../infra/Makefile)).
- Staging Gate (validação prod-like pré-merge) — Epic **#838**; override `!reset` transitório, solução
  estrutural rastreada em **#857**.
- Observabilidade movida para compose dedicado (dev-only) — issue **#234**.
- Hardening de runtime / segmentação de rede em prod (SEC-006/013/014/015) — ver [deploy.spec](./deploy.spec.md).

## Testes que cobrem

- **Smoke do staging-gate:** [`v2/infra/scripts/smoke_test_staging.sh`](../../../infra/scripts/smoke_test_staging.sh)
  (invocado por `make staging-test` / `staging-full`) — valida que a stack prod-like sobe e responde.
- **Health gates por perfil:** targets `health-dev` / `health-staging` / `health-prod-like` em
  [`v2/infra/Makefile`](../../../infra/Makefile) batem em `/api/readyz/`.
- **Config validation:** `check-env-dev` / `check-env-staging` / `check-env-prod` / `check-env-prod-like`
  rodam `docker compose config` para falhar cedo em compose inválido.
- A validação combinada `make staging-full` (8/8 PASS) é o gate de merge documentado no body de PR
  (ver [DEPLOY_CHECKLIST.md](../../DEPLOY_CHECKLIST.md) e [deploy.spec](./deploy.spec.md)).

## Pontos de atenção / dívidas conhecidas

- **Override `!reset` é transitório.** O `staging-gate` existe porque a base `docker-compose.yml` monta volumes
  de dev no `frontend`; a solução estrutural (mover esses binds para o `override.yml` dev-only) está em **#857**.
  Até lá, o gate depende de Docker Compose **v2.24.6+**.
- **`v2/Makefile` desatualizado em alguns targets:** o target `test` ainda referencia `apps/dat_ingest/tests`,
  app **removido** do projeto — usar os targets de teste de `apps/core`/`apps/dev_tools` (ver
  [django-patterns]) e ignorar `dat_ingest` nesses alvos. Os targets `etl_*`/`etl_completo` do `v2/Makefile`
  são do **ETL legado morto**; o import real hoje é `import_export_contract` + endpoints DRF.
- **Não existe doc canônico `v2/docs/ENVIRONMENTS.md`** (esperado pelo contexto, mas ausente no repo) — esta
  spec passa a ser a SSOT do tópico; quando o doc longo existir, deve ser linkado aqui (não duplicado).
- **`make health-*` usa health externo via curl,** que em algumas redes (Kaspersky/Golden) retorna HTTP 000
  para `:443` mesmo com containers `healthy` — não confundir falha de rede com falha de app (ver deploy.spec).
- **Prod sem staging remoto:** não há ambiente de staging em VM; merge na `main` = deploy direto pra prod
  (ver [deploy.spec](./deploy.spec.md)). O `staging-gate`/`prod-like` **locais** são a única barreira prod-like
  antes do merge.
