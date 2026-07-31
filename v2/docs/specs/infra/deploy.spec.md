---
title: Deploy & Produção (spec)
status: canonical
last_verified: 2026-07-24
sources_of_truth:
  - v2/infra/docker-compose.prod.yml
  - v2/infra/Dockerfile.prod
  - v2/frontend/Dockerfile.prod
  - .github/workflows/deploy.yaml
  - .github/workflows/promote.yml
  - v2/infra/deployer/README.md
  - v2/infra/scripts/restore_db.sh
  - v2/infra/Makefile
owner: infra
related:
  - ../INDEX_SDD.md
  - ../../OBSERVABILITY.md
  - ../../reports/AUDITORIA_DOCUMENTAL_2026-06-19.md
---

# Deploy & Produção

> **Comparação com a stack viva do Portainer: 2026-06-19.** Naquela data o compose vivo era idêntico ao
> `v2/infra/docker-compose.prod.yml` (só diferiam 2-3 linhas de comentário). **Essa comparação não foi refeita
> desde então** — o que esta spec afirma sobre *o repositório* foi reverificado em 2026-07-24, mas o que ela
> afirma sobre *o Portainer* (em especial a lista de variáveis da `stack.env`) segue sendo o snapshot de junho.
>
> **⚠️ O go-live já aconteceu (2026-07-03).** Produção roda `v2026.07.18-94f2765` e tem **148 usuários ativos**
> (94 Formador, 42 Coordenador, 9 Gerente, 3 DAT, 1 Controle, 1 Superintendência, 1 Assistente Administrativo;
> Diretoria e Apoio de Coordenação sem membros ativos) e **apenas 1 superuser**. Qualquer texto abaixo que trate
> os gaps como "pré-go-live, sem urgência" está obsoleto: eles alcançam dados e pessoas reais. O bus factor de
> **1 superuser** é agravado pelo #1567, que tornou a administração de Grupo×Capability superuser-only.

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

## Mecanismo de deploy — PULL-BASED ([ADR-018](../../../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md))

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

## Produção vs Local

> Coluna "Produção": o que vem do **repositório** (compose, workflows) foi reverificado em **2026-07-24**; o que
> vem do **Portainer** (valores de `stack.env`) é o snapshot de **2026-06-19** e está marcado como tal.

| Componente | Produção | Local/dev |
|---|---|---|
| Stack | **6 serviços**: `migrate` (one-shot), `web`, `redis`, `worker`, `beat`, `frontend` (docker-compose.prod.yml:47,84,135,171,240,289) | idem + override de dev |
| Observabilidade (Prometheus/Grafana) | **NÃO roda** | opcional via `make up-obs` (compose gitignored) |
| `/metrics` (django-prometheus) | exposto, **gated** (staff/IP interno, SEC-RECON-02) | exposto |
| Sentry | **DESLIGADO** — `SENTRY_DSN` ausente no stack.env | off (salvo se setar DSN) |
| Backup Celery | mount `/backups` **corrigido no compose** (#1455); **execução real em prod NÃO verificada** — ver abaixo | grava em `backup_data:/backups` (base) |
| Redis auth | **ATIVO** — `REDIS_PASSWORD` preenchido; isolado em `backend-internal` sem porta no host | conforme `.env` |
| Migrations | **automáticas no deploy** — serviço one-shot `migrate` roda `python manage.py migrate --noinput`; web/worker/beat aguardam via `depends_on: service_completed_successfully` (docker-compose.prod.yml:47-50,106-107,202-203,261-262; add. #1495 2026-07-02; corrigido nesta spec 2026-07-17) | via `make up` |
| Guards de prod | **OK** — `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, `SECURE_SSL_REDIRECT`, `DB_SSLMODE` setados | guards não se aplicam |
| GCal | **configurado** (`GCAL_*` completos) | conforme `.env` |
| dev_tools (CP-08) | **off** — `INCLUDE_DEV_TOOLS` ausente → default `false` | on em dev |

### Backup: o que foi corrigido e o que continua em aberto

**Corrigido no compose (#1455).** O serviço `worker` tem hoje o bind-mount gravável
`- /var/backups/aprender:/backups` (docker-compose.prod.yml:234-235), apesar do
`read_only: true` do root FS. A task Celery `backup.perform_database_backup` roda **no
`worker`** (não no `beat`, que só a agenda) e chama `backup_db.sh`, que grava
`backup_full_*.sql.gz.age` em `/backups`. `BACKUP_AGE_RECIPIENT` está fixado no
`environment:` do worker (docker-compose.prod.yml:197), e não na `stack.env`, para sobreviver
à recriação da stack. O `beat` **não** tem volume algum (docker-compose.prod.yml:279-287) —
correto, pois não escreve dumps.

**Não verificado — exige olhar produção.** Que o mount exista no compose **não prova** que o
backup rode. Continuam sem confirmação: (a) o `beat` está de fato agendando a task; (b)
existe artefato recente em `/var/backups/aprender` na VM01; (c) o diretório do host foi
criado com dono/permissão corretos (0755, UID do `appuser`), pré-requisito documentado no
próprio compose. Precedente: **#1537**, backup que nunca rodou. Para confirmar seria preciso
SSH na VM01 e `ls -la /var/backups/aprender` + `journalctl`/logs do worker.

**Aberto e grave — o restore não funciona (P0, #1611).** `v2/infra/scripts/restore_db.sh:91`
executa `gzip -t "$BACKUP_FILE"` **incondicionalmente**, antes do branch que trata artefatos
`age` (linhas 113-119). Como produção grava **exclusivamente** `.age` (fail-closed em
`backup_db.sh:44-52` + recipient no compose), a ferramenta oficial de restore rejeita todo
backup de produção com a mensagem falsa `ERROR: Backup file is corrupted!` — nos três
caminhos de entrada (arquivo explícito, `--latest`, interativo). É **fail-closed** (para
antes do `DROP DATABASE` da linha 107), então não há destruição de dados; o dano é RTO
estourado. Achados `M26-01` (#1611), `M26-02` (#1645, sucesso falso com exit 0) e `M26-03`
(#1646, `test_dr.sh` nunca exercita o round-trip cifrado), agrupados no épico **#1662**.

**Complementar, fora desta stack:** o cron na **VM02** (#376, WAL archiving) — não
verificável pelo Portainer/repo (exige SSH na VM02).

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

**Ausentes (significativo):** `SENTRY_DSN` (→ Sentry off), `BACKUP_DIR` (→ default `/backups`, que hoje **é**
gravável no `worker` graças ao bind-mount do #1455), `INCLUDE_DEV_TOOLS`/`INCLUDE_ETL` (→ defaults off, correto).

> **Snapshot datado (2026-06-19), não reverificado.** Esta lista veio de uma leitura das *Environment variables*
> no Portainer em 2026-06-19 e **não** foi reconferida desde então. A auditoria M00–M28 tem 18 achados cuja
> severidade depende do conteúdo real dos envs hoje (fato **F5**, o único ainda capaz de promover algo a P0 — ex.:
> `DEBUG=True`). Trate como histórico até um novo export read-only. Um item específico a revisar:
> `DOCKER_HUB_TOKEN` aparece nesta lista e, via `env_file`, alcançaria o ambiente de processo dos quatro serviços
> de backend; seu consumidor legítimo (o job `deploy` do `deploy.yaml`) **foi removido** na Fase 4 do ADR-018, e o
> token já existe como *secret do repositório* no GitHub, que é o lugar correto. Achado `M27-15`, **não
> verificado** — exige acesso ao Portainer.

> **Redundância a revisar (não-bug):** coexistem `DATABASE_URL` e `DB_*`, e `REDIS_URL` e `REDIS_*`. Conferir qual
> o `config/settings.py` realmente consome para não haver duas fontes divergentes.

## Como re-verificar (read-only)

1. Portainer → Stacks → stack de prod → **Editor** (compose vivo) e **Environment variables** (valores reais).
2. (Opcional) VM01 via SSH: `docker ps`, `docker inspect <svc>` (mounts/read_only/env). **Nunca** reiniciar
   Docker/containers (Kaspersky/KESL derruba o site).

## Gaps abertos relacionados

- **#1455** — *mount `/backups` fechado no compose* (worker, linhas 234-235). Resta confirmar em produção que o
  backup realmente roda e gera artefato (fato **F7**, não verificado; precedente #1537).
- **#1456** — *serviço `migrate` entregue* (aplica migrations no deploy) e `makemigrations --check` existe na CI.
  Resta o **gating**: o job `backend-migrate-integrity` é `[info]` e não entra no `needs` do `[required] tests`,
  então model-drift é detectado mas **não bloqueia merge**. Ver [`ci.spec.md`](./ci.spec.md).
- **#1457** — guard de `REDIS_PASSWORD` obrigatório (em prod está setado; falta o fail-fast preventivo).
- **#1611 / épico #1662 (P0)** — `restore_db.sh` rejeita todo backup `.age` de produção. Ver a seção de backup acima.
- **#1660 (P2)** — `docker-compose.prod.yml:100-101` publica a porta do backend em `0.0.0.0` sem bind em
  `127.0.0.1`. O dono confirmou por teste externo (4G) que a porta **não responde** da internet: há allowlist de
  firewall externo (Golden). Não é exposição pública — mas o firewall externo é a **única** camada protegendo um
  canal em texto claro que serve a API e o `/admin`, fora do TLS e do `limit_req`. Correção que preserva o
  consumidor legítimo (`deployer/apply.sh:73-80` usa `confirm_localhost`): `127.0.0.1:${BACKEND_HOST_PORT}:8000`.
