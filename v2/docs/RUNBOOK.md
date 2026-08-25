# 📘 Aprender Sistema v2 — Runbook Operacional

**Versão:** 1.2
**Projeto Docker:** `aprender_dev` (SSOT: `v2/Makefile:6`, `PROJECT ?= aprender_dev`)
**Última atualização:** 2026-08-25

> ⚠️ **Escopo: este runbook é majoritariamente DEV/LOCAL.** Portas `8002`/`5434`/`6380`,
> serviço `db`, `GCAL_CLIENT=fake`, credenciais de admin e `make` targets são do ambiente
> local (`infra/docker-compose.yml` + `infra/docker-compose.override.yml`, projeto
> `aprender_dev`).
>
> **Em produção nada disso vale:** a stack roda sob Portainer na VM01 com
> `infra/docker-compose.prod.yml` (serviços `migrate`, `web`, `redis`, `worker`, `beat`,
> `frontend` — **não existe serviço `db`**; o PostgreSQL é externo, na VM02), o GCal usa o
> cliente real via OAuth, e o único procedimento válido de mudança é o **pull-based**
> descrito abaixo. Para incidentes de dados/DR, vá direto para
> [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) e [GUIDE_DR.md](./GUIDE_DR.md).

---

## 📋 Índice

0. [Como invocar o compose](#como-invocar-o-compose)
1. [Recarregar Variáveis de Ambiente (.env)](#recarregar-variáveis-de-ambiente-env)
2. [Operações Celery (Worker/Beat)](#operações-celery-workerbeat)
3. [Health Checks e Validações](#health-checks-e-validações)
4. [Importação de Ações (Controle e DAT)](#importação-de-ações-controle-e-dat)
5. [APIs REST: Ações (Controle e DAT)](#apis-rest-ações-controle-e-dat)
6. [Troubleshooting Comum](#troubleshooting-comum)
7. [Deploy Workflow (Canônico)](#deploy-workflow-canônico)

---

## 🧭 Como invocar o compose

> [!warning] Até 2026-08-25 este runbook mandava rodar
> `docker compose -p aprender_v2 -f infra/docker-compose.yml …`.
> Nenhuma dessas ~20 invocações funcionava. Três motivos, todos verificáveis:
>
> | Problema | Realidade | Onde |
> |---|---|---|
> | Projeto errado | O stack chama-se **`aprender_dev`**, não `aprender_v2`. `-p aprender_v2` cria/consulta um projeto vazio e o comando não acha container nenhum | `v2/Makefile:6` |
> | `IMAGE_TAG` faltando | O compose declara `image: …:${IMAGE_TAG:?IMAGE_TAG is required}`; sem a variável o docker aborta antes de subir qualquer coisa | `infra/docker-compose.yml:54, 98, 122, 146` |
> | `override.yml` omitido | É o override que traz `build:` e o **bind-mount do fonte** (`../backend:/app`). Sem ele você roda a imagem publicada, não o seu código | `infra/docker-compose.override.yml:15-51` |

**Prefira os alvos do Makefile.** Eles já carregam projeto, `IMAGE_TAG` e os dois arquivos
de compose (`Makefile:11`, a variável `DC`):

```bash
cd v2
make up            # sobe a stack (up -d --build)
make down          # derruba (--remove-orphans)
make logs          # logs -f web
make shell         # bash no web
make migrate       # migrate + collectstatic
make healthz       # curl /healthz/
make readyz        # curl /api/readyz/
make help          # lista todos os alvos
```

**Quando precisar do compose cru** (não há alvo para `ps`, `exec`, `restart`), exporte a
mesma invocação que o Makefile usa e reaproveite:

```bash
cd v2
export COMPOSE_PROJECT_NAME=aprender_dev
export IMAGE_TAG=latest
DC="docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml"

$DC ps
$DC exec -T web python manage.py shell
```

Todos os `$DC` deste runbook assumem esse bloco. Rodando vários worktrees em paralelo,
`source infra/scripts/worktree-env.sh <slot>` deriva `PROJECT` e as portas
(`Makefile:1-6`).

---

## 🚀 Deploy Workflow (Canônico)

> **Modelo atual: pull-based (ADR-018).** Decisão:
> [ADR-018 — Pull-based deploy](../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md)
> (supersede o ADR-010).
> SSOT do mecanismo: [`specs/infra/deploy.spec.md`](specs/infra/deploy.spec.md).
> O modelo antigo (o CI fazia `PUT` no Portainer `:9443` **público**) foi desligado no cutover (#1515) e o job
> `deploy` foi **removido** na Fase 4 (#1516) — conferido em `.github/workflows/deploy.yaml`, cujos únicos
> jobs hoje são `prepare`, `build_and_push`, `sign` e `tag_and_release`.

Workflows oficiais:
- `.github/workflows/deploy.yaml` (hoje **"Build, sign and release (main)"**)
- `.github/workflows/promote.yml` (promoção/rollback, gated)

### Merge na `main` NÃO deploya

`push`/merge na `main` dispara apenas `deploy.yaml`, que faz **build → scan (Trivy) → push no Docker Hub →
assina** as imagens (cosign keyless + provenance SLSA) → cria a **tag imutável** `vYYYY.MM.DD-<sha7>` + GitHub
Release. Nenhum ambiente é atualizado nesse passo.

### Produção muda em dois passos deliberados

1. **Promoção (`promote.yml`)** — `workflow_dispatch` atrás do GitHub Environment `production` (*required
   reviewer*, 1 aprovação). Resolve tag→digest, exige imagens assinadas, monta e **assina** o ponteiro de
   release (`cosign sign-blob`, identidade OIDC do workflow) e publica no branch protegido **`deploy-pointer`**.

   ```bash
   gh workflow run promote.yml -f release=vYYYY.MM.DD-<sha7>
   ```

2. **Aplicação (agente `aprender-deployer` na VM01)** — systemd na própria VM lê o ponteiro assinado,
   verifica com **cosign** contra um trusted-root pinado offline, verifica as imagens **por digest**, checa
   anti-rollback (selo monotônico) + drift do compose + backup de DB fresco, faz o `PUT` em
   **`127.0.0.1:9443`** com o compose pinado que ele mesmo detém e confirma de dentro da VM
   (`/api/readyz/` + `/api/version/`). Por confirmar em `localhost`, é imune ao *false-red* do `:9443` público.

### Regras de produção

- Só tag imutável `vYYYY.MM.DD-<sha7>`; `latest` é bloqueada para promoção. O pipeline não faz retag `latest`.
- **Rollback = promover a tag anterior** pelo mesmo caminho gated: `gh workflow run promote.yml -f release=<tag-anterior>`.
- Alterar o compose exige edição **manual** no Editor do Portainer + re-captura do pinado (senão o agente recusa por `compose_drift`).

### Depreciado / removido

- Job `deploy` (PUT ao Portainer `:9443` público) e `validate_existing_tag` — **removidos** (#1516).
- `workflow_dispatch` do `deploy.yaml` **não** tem mais os inputs `target_environment` / `promotion_tag` / `rollback_tag`.
- Secrets/vars `PORTAINER_*`, `STAGING_*`, `PRODUCTION_*` e `*_DEPLOY_COMMAND` — **removidos do GitHub** (não configurar mais).
- Workflows `release.yaml` e `dockerhub-rebuild.yml` — removidos (issue #814).

## 🔄 Recarregar Variáveis de Ambiente (.env)

### ⚠️ **IMPORTANTE: `restart` NÃO recarrega variáveis!**

Quando você altera o arquivo `.env`, **NÃO** use `docker compose restart`!
O comando `restart` apenas para e reinicia os containers **sem recriar**, mantendo as variáveis antigas.

### ✅ **Método Correto:**

```bash
# Recriar containers para recarregar .env
docker compose up -d <serviço>

# Exemplo: Recarregar variáveis no web, worker e beat
cd v2
$DC up -d web worker beat
```

**Por quê funciona?**
- `up -d` **recria** os containers com as novas variáveis do `.env`
- As variáveis são injetadas no momento da criação do container

### 📌 **Serviços Afetados por Mudanças no .env:**

| Serviço | Variáveis Críticas | Comando para Recarregar |
|---------|-------------------|-------------------------|
| **web** | `REDIS_PORT`, `DB_PORT`, `SECRET_KEY`, `GCAL_CLIENT` | `up -d web` |
| **worker** | `REDIS_PORT`, `DB_PORT`, `CELERY_BROKER_URL` | `up -d worker` |
| **beat** | `REDIS_PORT`, `DB_PORT`, `CELERY_BROKER_URL` | `up -d beat` |
| **db** | `POSTGRES_*` | Raramente necessário |
| **redis** | (nenhuma) | Não usa .env |

### 🛠️ **Workflow Completo:**

```bash
# 1. Editar .env
cd v2/infra
nano .env  # ou editor de sua preferência

# 2. Recriar serviços afetados
cd ..
$DC up -d web worker beat

# 3. Verificar logs
$DC logs -f web worker beat

# 4. Validar health
make healthz && make readyz
```

---

## 🔧 Operações Celery (Worker/Beat)

### **Subir Worker e Beat**

```bash
cd v2

# Usando Makefile (recomendado)
make up-worker
make up-beat

# OU diretamente com docker compose
$DC up -d worker
$DC up -d beat
```

### **Parar Worker e Beat**

```bash
cd v2

# Parar (sem remover)
$DC stop worker beat

# Remover containers (dados em volumes são mantidos)
$DC down worker beat
```

### **Ver Logs em Tempo Real**

```bash
cd v2

# Usando Makefile (recomendado)
make logs-worker     # Worker (tempo real)
make logs-beat       # Beat (tempo real)

# OU diretamente
$DC logs -f worker
$DC logs -f beat
```

### **Ver Últimas 200 Linhas de Logs**

```bash
cd v2

# Usando Makefile (recomendado)
make logs-worker-last
make logs-beat-last

# OU diretamente
$DC logs --tail=200 worker
$DC logs --tail=200 beat
```

### **Reiniciar Worker/Beat (após mudanças de código)**

```bash
cd v2

# ⚠️ Para recarregar .env: use up -d (não restart!)
$DC up -d worker beat

# ✅ Para apenas reiniciar (sem recarregar .env): use restart
$DC restart worker beat
```

### **Verificar Status**

```bash
cd v2

# Status de todos os serviços
$DC ps

# Status apenas de worker/beat
$DC ps worker beat
```

### **Critérios de Sucesso (Worker)**

```
✅ Logs contêm:
   - "Connected to redis://redis:6379/1"
   - "celery@<hostname> ready."
   - [tasks] listando as tasks disponíveis
```

### **Critérios de Sucesso (Beat)**

```
✅ Logs contêm:
   - "celery beat v5.4.0 (opalescent) is starting."
   - "broker -> redis://redis:6379/1"
   - "beat: Starting..."
```

Notas operacionais:
- Em **produção** (Docker/Portainer na VM01, **não** systemd) o beat roda com o **scheduler padrão** do
  Celery: `celery -A config beat -l info --schedule /tmp/celerybeat-schedule`
  (`v2/infra/docker-compose.prod.yml:243`; o `--schedule` aponta para tmpfs porque o root FS é `read_only`).
  É esse scheduler que respeita o schedule definido em código, em `config/celery.py:35-56`.
- Só usar `django_celery_beat.schedulers:DatabaseScheduler` se as `PeriodicTask` estiverem cadastradas no banco.
- **O beat só agenda; quem executa é o `worker`.** Ao investigar um job que não rodou (ex.: o backup diário
  das 02:00), olhe os **dois**: `logs beat` para o disparo, `logs worker` para a execução. Só o `worker` tem o
  bind-mount `/backups` (`docker-compose.prod.yml:235`) — ver [BACKUP_OPERATIONS.md](./BACKUP_OPERATIONS.md).

---

## 🏥 Health Checks e Validações

### **Endpoints de Saúde**

```bash
# Health geral
curl http://localhost:8002/healthz/
# Esperado: {"status": "ok", "environment": "development", ...}

# Readiness (DB + Redis)
curl http://localhost:8002/api/readyz/
# Esperado: {"db": "ok", "redis": "ok"}

# Features e flags
curl http://localhost:8002/api/features/
# Esperado: {"GCAL_CLIENT": "fake", "apply_blocked": true, ...}
```

### **Usando Makefile**

```bash
cd v2

# Health check
make healthz

# Readiness check
make readyz
```

### **Verificar Configuração Celery**

```bash
cd v2

$DC exec -T web python -c "
from django.conf import settings
print('BROKER:', settings.CELERY_BROKER_URL)
print('RESULT_BACKEND:', settings.CELERY_RESULT_BACKEND)
"
```

**Esperado:**
```
BROKER: redis://redis:6379/1
RESULT_BACKEND: django-db
```

---

## 🐛 Troubleshooting Comum

### **Problema 1: Worker/Beat não conectam ao Redis**

**Sintoma:**
```
Could not connect to Redis at redis:6380: Connection refused
```

**Causa:**
- `.env` tem `REDIS_PORT=6380` (porta do HOST)
- Containers devem usar `REDIS_PORT=6379` (porta interna)

**Solução:**
```bash
# 1. Editar .env
cd v2/infra
# Alterar: REDIS_PORT=6380 → REDIS_PORT=6379

# 2. Recriar containers (NÃO usar restart!)
cd ..
$DC up -d web worker beat
```

---

### **Problema 2: Mudanças no .env não têm efeito**

**Causa:**
- Usou `docker compose restart` (não recarrega variáveis)

**Solução:**
```bash
# Usar up -d para recriar
$DC up -d <serviço>
```

---

### **Problema 3: Worker mostra "ConnectionRefusedError"**

**Verificar:**
1. Redis está rodando?
   ```bash
   $DC ps redis
   ```

2. REDIS_PORT correto no .env?
   ```bash
   $DC exec -T worker printenv | grep REDIS
   # Deve mostrar: REDIS_PORT=6379 (não 6380!)
   ```

3. Worker foi recriado (não apenas reiniciado)?
   ```bash
   $DC up -d worker
   ```

---

### **Problema 4: Beat não agenda tarefas**

**Verificar:**
1. Beat está rodando?
   ```bash
   $DC ps beat
   make logs-beat-last
   ```

2. Tarefas estão cadastradas no Django Admin?
   - http://localhost:8002/admin/
   - Django Celery Beat → Periodic Tasks

3. Schedule está configurado corretamente?
   ```bash
   $DC exec -T beat celery -A config inspect scheduled
   ```

---

## 📊 Portas e Mapeamentos

### **HOST (seu computador) vs. CONTAINER (rede Docker)**

| Serviço | Porta HOST | Porta CONTAINER | Acesso HOST | Acesso CONTAINER |
|---------|-----------|-----------------|-------------|------------------|
| **Web** | 8002 | 8000 | `localhost:8002` | `web:8000` |
| **PostgreSQL** | 5434 | 5432 | `localhost:5434` | `db:5432` |
| **Redis** | 6380 | 6379 | `localhost:6380` | `redis:6379` |

### **Quando usar cada porta?**

- **Aplicações no HOST** (seu computador):
  - Use `localhost:8002`, `localhost:5434`, `localhost:6380`

- **Containers Docker** (web, worker, beat):
  - Use `db:5432`, `redis:6379`
  - **NUNCA** use as portas do HOST (5434, 6380) no `.env`!

---

## 🔐 Variáveis de Ambiente Críticas

### **.env (Local, NÃO commitar)**

```bash
# ⚠️ Portas INTERNAS dos containers (não as do HOST!)
DB_HOST=db
DB_PORT=5432  # ← Não usar 5434!

REDIS_HOST=redis
REDIS_PORT=6379  # ← Não usar 6380!

# Docker
REQUIRE_DOCKER=1
COMPOSE_PROJECT_NAME=aprender_dev   # mesmo default do Makefile (PROJECT ?= aprender_dev)
IMAGE_TAG=latest                    # exigido pelo compose (${IMAGE_TAG:?…})

# Google Calendar
GCAL_CLIENT=fake  # Valores: "fake" ou "google"
```

### **.env.example (Template, commitar)**

Veja `v2/infra/.env.example` para o template completo com comentários.

---

## 🚀 Comandos Rápidos (Cheat Sheet)

```bash
# ════════════════════════════════════════════════════════════
# Iniciar Stack
# ════════════════════════════════════════════════════════════
cd v2
$DC up -d

# ════════════════════════════════════════════════════════════
# Recarregar .env (após edição)
# ════════════════════════════════════════════════════════════
$DC up -d web worker beat

# ════════════════════════════════════════════════════════════
# Celery - Subir Worker/Beat
# ════════════════════════════════════════════════════════════
make up-worker
make up-beat

# ════════════════════════════════════════════════════════════
# Celery - Ver Logs
# ════════════════════════════════════════════════════════════
make logs-worker          # Tempo real
make logs-worker-last     # Últimas 200 linhas

# ════════════════════════════════════════════════════════════
# Health Checks
# ════════════════════════════════════════════════════════════
make healthz
make readyz
curl http://localhost:8002/api/features/

# ════════════════════════════════════════════════════════════
# Django Admin
# ════════════════════════════════════════════════════════════
# URL: http://localhost:8002/admin/
# User: admin
# Pass: Admin@123

# ════════════════════════════════════════════════════════════
# Parar Stack (sem perder dados)
# ════════════════════════════════════════════════════════════
$DC down

# ════════════════════════════════════════════════════════════
# Migrations — DEV/LOCAL apenas (ver nota abaixo)
# ════════════════════════════════════════════════════════════
$DC exec -T web python manage.py makemigrations
make migrate      # migrate + collectstatic

# ════════════════════════════════════════════════════════════
# Django Shell
# ════════════════════════════════════════════════════════════
make shell                                   # bash no web
$DC exec web python manage.py shell          # shell do Django
```

> ⛔ **Não rode `migrate` a mão em produção.** As migrations são aplicadas por um
> serviço **one-shot `migrate`**, automático e bloqueante: `web`/`worker`/`beat` só
> sobem depois que ele termina (#1456). Rodar `migrate` manualmente em produção foi
> **revogado** junto com o cutover pull-based — ver
> [ADR-018](../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md) e
> [Deploy Workflow](#deploy-workflow-canônico).

---

## 📚 Referências

- **Docker Compose:** https://docs.docker.com/compose/
- **Celery:** https://docs.celeryq.dev/
- **Django:** https://docs.djangoproject.com/

---

**Autor:** Equipe Aprender Sistema
**Projeto:** `aprender_dev`
**Stack:** Django 5.2.1 LTS + PostgreSQL 15 + Redis 7 + Celery 5.5.3

---

## 🌱 Seeds (RBAC)

### Seeds RBAC

> ⛔ **DEV/STAGING APENAS — o comando não existe em produção.** `seed_rbac` vive em
> `apps/dev_tools` (`v2/backend/apps/dev_tools/management/commands/seed_rbac.py`), e
> `config/settings.py:137-143` **força `INCLUDE_DEV_TOOLS=False` quando
> `ENVIRONMENT == "production"`**, independentemente da env var (CP-08 / #1466). O app não
> entra em `INSTALLED_APPS`, então `manage.py seed_rbac` responde *Unknown command* em prod.
> `docker-compose.prod.yml` ainda fixa `INCLUDE_DEV_TOOLS: "false"` como defesa em
> profundidade. **Não** tente "seedar RBAC" em produção por aqui.

Cria grupos e permissões mínimas (idempotente):

```bash
# Via Makefile
make seed-rbac

# Via Docker diretamente
$DC exec -T web python manage.py seed_rbac
```

**Grupos criados:** a união de `SETOR_GROUPS` (13) + `FUNCAO_GROUPS` (5), definidos em
`v2/backend/apps/core/constants.py:16-45` — essa é a SSOT, não esta lista.

- **Setores (13):** Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT,
  Controle, Diretoria, Comercial, Relacionamento, Logística Viagens, Logística Galpão
- **Funções (5):** Formador, Coordenador, Apoio de Coordenação, Gerente,
  Assistente Administrativo

> O grupo **"Gerência"** foi **descontinuado** em favor da função **"Gerente"** (#1222). Ele
> ainda aparece em `PERMS_BY_GROUP` do seed por compatibilidade com testes legados
> (`seed_rbac.py:89,124-126`), mas **não** está em `ALLOWED_USER_GROUPS` — não atribua
> usuários a ele.

**Permissões atribuídas:** ver `PERMS_BY_GROUP` em `seed_rbac.py:32-92`. A matriz de
autorização real (capabilities/policies) está em
[rbac_authorization_matrix.md](./rbac_authorization_matrix.md) — as Django permissions do
seed são só o piso.

---

## 🔒 AuditLog

**Ações logadas:**
- `APPROVE`: Aprovação de solicitação
- `REJECT`: Rejeição de solicitação
- `PREVIEW_GCAL`: Preview de publicação GCal
- `PUBLISH_GCAL_REQUESTED`: Publicação solicitada (via Celery)
- `PUBLISH_GCAL`: Publicação executada

**Campos registrados:**
- `usuario`: Usuário que executou a ação (ou NULL para tasks assíncronas)
- `action`: Tipo de ação
- `model_name`: Modelo relacionado (ex: "Solicitacao")
- `details`: JSON com contexto (solicitation_id, prev_status, new_status, ip_address, etc)
- `created_at`: Timestamp da ação

**Consultar logs:**
```bash
$DC exec -T web python manage.py shell -c "
from apps.core.models import AuditLog
logs = AuditLog.objects.order_by('-created_at')[:10]
for log in logs:
    print(f'{log.created_at} - {log.action} - {log.usuario or \"Sistema\"}')" 
```

---

## 🎛️ Features Flags

Consultar configurações ativas:

```bash
curl http://localhost:8002/api/features/
```

**Resposta:**
```json
{
  "GCAL_CLIENT": "fake",
  "apply_blocked": true,
  "ENVIRONMENT": "staging"
}
```

**apply_blocked:**
- `true`: Operações de publish bloqueadas (GCAL_CLIENT != "google")
- `false`: Publicações permitidas (GCAL_CLIENT == "google")

**Uso em workflows:**
- `/api/availability/monthly` (PR #3): Grade mensal de disponibilidade
- `POST /api/solicitacoes/{id}/preview-gcal/` (PR #4): Preview sem publicar
- `POST /api/solicitacoes/{id}/publish/` (PR #4): Publicação via Celery (respeit apply_blocked)

---

## 📅 Google Calendar — Service Account (cliente real)

### **Visão Geral**

O sistema suporta dois modos de cliente do Google Calendar:
- **fake** (padrão): Cliente in-memory, safe, sem side effects. Usado para desenvolvimento e testes.
- **google**: Cliente real conectado à Google Calendar API via Service Account.

### **Pré-requisitos**

1. **Projeto no Google Cloud Console**
   - Criar projeto (ou usar existente)
   - Habilitar **Google Calendar API**
   - Criar Service Account com credenciais JSON

2. **Compartilhar Calendário com Service Account**
   - Abrir Google Calendar
   - Ir em Settings → Calendários → [Seu calendário]
   - "Share with specific people"
   - Adicionar o email da Service Account (ex: `aprender-sa@project.iam.gserviceaccount.com`)
   - Permissão: **"Make changes to events"** (Fazer alterações em eventos)

3. **Obter Credenciais JSON**
   - No Google Cloud Console → IAM & Admin → Service Accounts
   - Selecionar a Service Account
   - Keys → Add Key → Create new key → JSON
   - Baixar arquivo (ex: `sa-aprender.json`)

### **Configuração no Sistema**

#### **Opção 1: Arquivo de Credenciais (recomendado)**

```bash
# 1. Copiar arquivo JSON para secrets/
cd v2/infra
mkdir -p secrets
cp /path/to/sa-aprender.json secrets/sa.json

# 2. Editar .env
nano .env

# Adicionar/alterar:
GCAL_CLIENT=google
GCAL_CALENDAR_ID=primary  # ou ID específico do calendário (ex: abc123@group.calendar.google.com)
GOOGLE_SERVICE_ACCOUNT_FILE=/run/secrets/sa.json
```

#### **Opção 2: JSON Inline (não recomendado para produção)**

```bash
# Editar .env
nano .env

# Adicionar/alterar:
GCAL_CLIENT=google
GCAL_CALENDAR_ID=primary
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"...","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"aprender-sa@project.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}'
```

**⚠️ Importante:** Ao usar JSON inline, escape aspas duplas se necessário e mantenha em uma linha.

### **Recarregar Configuração**

```bash
cd v2

# Recriar containers para carregar novas variáveis .env
$DC up -d web worker beat

# Verificar logs
$DC logs -f web | grep -i google
```

**Logs esperados:**
```
GoogleCalendarClient initialized with Service Account
```

### **Verificação**

#### **1. Verificar Features**

```bash
curl http://localhost:8002/api/features/
```

**Resposta esperada:**
```json
{
  "GCAL_CLIENT": "google",
  "apply_blocked": false,
  "ENVIRONMENT": "staging"
}
```

- `GCAL_CLIENT: "google"` → Cliente real ativo
- `apply_blocked: false` → Publicações permitidas

#### **2. Testar Preview (sem publicar)**

```bash
# Obter ID de uma solicitação aprovada
curl http://localhost:8002/admin/  # Login e verificar Admin

# Preview
curl -X POST http://localhost:8002/api/solicitacoes/1/preview-gcal/ \
  -H "Content-Type: application/json"
```

**Resposta esperada:**
```json
{
  "id": "aprender-sol-1-...",
  "summary": "Evento Teste",
  "start": {"dateTime": "2025-10-21T10:00:00-03:00"},
  "end": {"dateTime": "2025-10-21T12:00:00-03:00"},
  ...
}
```

#### **3. Testar Publicação (com calendário real)**

```bash
# Publicar (assíncrono via Celery)
curl -X POST http://localhost:8002/api/solicitacoes/1/publish/ \
  -H "Content-Type: application/json"
```

**Resposta esperada:**
```json
{
  "message": "publish_to_gcal enqueued",
  "task_id": "abc123-...",
  "solicitation_id": 1
}
```

**Verificar no Google Calendar:**
- Abrir o calendário compartilhado
- Verificar se evento foi criado
- Evento deve ter link do Google Meet gerado automaticamente

#### **4. Logs de Auditoria**

```bash
$DC exec -T web python manage.py shell -c "
from apps.core.models import AuditLog
logs = AuditLog.objects.filter(action__in=['PREVIEW_GCAL', 'PUBLISH_GCAL']).order_by('-created_at')[:5]
for log in logs:
    print(f'{log.created_at} - {log.action} - {log.usuario or \"Sistema\"} - {log.details}')"
```

### **Troubleshooting**

#### **Erro 403: Forbidden**

**Causa:** Service Account não tem permissão no calendário.

**Solução:**
1. Verificar se calendário foi compartilhado com o email da Service Account
2. Permissão deve ser **"Make changes to events"**
3. Aguardar alguns minutos para propagação (pode demorar até 5min)

#### **Erro 404: Calendar not found**

**Causa:** `GCAL_CALENDAR_ID` incorreto.

**Solução:**
1. Verificar ID do calendário no Google Calendar Settings
2. Se usar calendário principal da Service Account, use `primary`
3. Para calendários compartilhados, use o ID completo (ex: `abc123@group.calendar.google.com`)

#### **Erro: Service Account credentials not found**

**Causa:** Variáveis `GOOGLE_SERVICE_ACCOUNT_FILE` ou `GOOGLE_SERVICE_ACCOUNT_JSON` não configuradas.

**Solução:**
```bash
# Verificar variáveis no container
$DC exec -T web printenv | grep GOOGLE

# Recriar container se necessário
$DC up -d web worker beat
```

#### **Erro: Rate limit exceeded (429)**

**Causa:** Muitas requisições simultâneas à Google Calendar API.

**Comportamento esperado:**
- Cliente implementa retry com exponential backoff (1s, 2s, 4s)
- Até 3 tentativas automáticas
- Se continuar falhando, revisar batch_size em comandos de sync

### **Comandos de Sync com Cliente Real**

#### **Preview (dry-run) sem publicar**

```bash
cd v2
make shell

# Dentro do shell Django
python manage.py preagenda_to_gcal --client=google --dry-run --verbose
```

#### **Publicar intervalo específico**

```bash
python manage.py preagenda_to_gcal \
  --client=google \
  --since 2025-10-01T00:00:00 \
  --until 2025-10-31T23:59:59 \
  --verbose
```

#### **IDs específicos**

```bash
python manage.py preagenda_to_gcal \
  --client=google \
  --ids 1,2,3 \
  --verbose
```

### **Segurança**

- **NUNCA** commitar arquivo `.env` ou credenciais JSON
- Arquivo `secrets/sa.json` está no `.gitignore`
- Em produção, usar **Google Secret Manager** ou **Docker Secrets**
- Rotacionar chaves periodicamente

### **Referências**

- **Google Calendar API:** https://developers.google.com/calendar/api/quickstart/python
- **Service Accounts:** https://cloud.google.com/iam/docs/service-accounts
- **OAuth 2.0:** https://developers.google.com/identity/protocols/oauth2

---

## 📥 Importação de Ações (Controle e DAT)

O ETL legado (`etl_import_acoes_controle`, `etl_import_dat_cadastros`) foi **removido** (#967/#971). Use os endpoints DRF descritos na seção seguinte ([APIs REST: Ações](#apis-rest-ações-controle-e-dat)), ou os make targets `import-acoes-dry` / `import-cadastros-dry` e o command `import_export_contract` (dry-run por padrão). Ver a spec viva [`imports.spec.md`](specs/backend/imports.spec.md).

---

## 🔌 APIs REST: Ações (Controle e DAT)

### **Visão Geral**

Endpoints RESTful para consulta e criação de ações com **RBAC** (Role-Based Access Control).

**Base URL:** `http://localhost:8002/api/`

**Autenticação:** Session-based (Django Auth)

> [!note] As classes `IsControleOrSuper` / `IsDATOrSuper` não existem mais.
> Este runbook citava as duas como permissão destes endpoints. O `rbac_lint`
> **bane** qualquer `class Is<Word>(...)` fora da whitelist
> (`IsGerenteSuperintendencia`, `IsOwnerOrPrivileged`) — regra **V002**,
> `v2/backend/scripts/rbac_lint.py:37-43`, com job obrigatório no CI
> (`[required] backend rbac-lint`). O idioma canônico é
> `HasPerm("<codename>")` ou uma classe `Can*` do Capability Policy Layer; o
> mapeamento das classes legadas está em `scripts/rbac_codemod.py:36-37`
> (`IsControleOrSuper → import_spreadsheet`,
> `IsDATOrSuper → manage_admin_registries`). Convenção completa:
> [RBAC_NAMING.md](./RBAC_NAMING.md).

---

### ~~API 1: Ações de Controle~~ — **rota removida**

> [!warning] `GET /api/controle/acoes/` não existe mais.
> Este runbook documentou o endpoint até 2026-08-25. A rota foi retirada na **Onda 1 do
> programa de imports órfãos**, junto com o modelo `AcaoControle` que a alimentava — hoje
> o import de ações grava em `DATAcao`. Não há `path("controle/acoes/", …)` em
> `v2/backend/apps/core/urls.py`. As rotas `controle/…` que restaram são
> `controle/import-acoes/` (`urls.py:211-214`), que é **upload de planilha**, e
> `controle/compras/` (`urls.py:215-219`) — nenhuma delas lista ações. Registro:
> `v2/docs/plans/PLANO_IMPORTS_ORFAOS.md` e o cabeçalho de
> `apps/core/tests/test_controle_dat_api.py:14-16`.

Para onde ir:

| Se você queria | Use |
|---|---|
| Listar ações do ciclo DAT | `GET /api/dat/acoes-ciclo/` (`DATAcaoViewSet`, `urls.py:147`) |
| Importar ações de planilha | `POST /api/controle/import-acoes/` — `HasPerm("import_spreadsheet")`, `dry_run=true` por padrão (`views_imports.py:48-58`) |
| Listar cadastros DAT legados | [API 2](#api-2-cadastros-dat-leitura), abaixo |

---

### **API 2: Cadastros DAT (Leitura)**

**Endpoint:** `GET /api/dat/acoes/`

**Permissão:** `HasPerm("manage_admin_registries")` (`views_controle_dat.py:56`)

**Descrição:** Lista cadastros do setor DAT com filtros opcionais.

#### **Query Parameters**

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `projeto` | `int` | ID do projeto | `1` |
| `municipio` | `int` | ID do município | `5` |
| `tipo_acao` | `string` | Filtro parcial (icontains) no tipo de ação | `INEP` |
| `data_inicio` | `YYYY-MM-DD` | Filtra data_registro >= data_inicio | `2025-01-01` |
| `data_fim` | `YYYY-MM-DD` | Filtra data_registro <= data_fim | `2025-12-31` |

#### **Exemplo de Requisição**

```bash
# Listar todos os cadastros
curl -X GET http://localhost:8002/api/dat/acoes/ \
  -H "Cookie: sessionid=<seu-session-id>"

# Filtrar por tipo de ação
curl -X GET "http://localhost:8002/api/dat/acoes/?tipo_acao=Cadastro%20INEP" \
  -H "Cookie: sessionid=<seu-session-id>"

# Filtrar por projeto e intervalo de datas
curl -X GET "http://localhost:8002/api/dat/acoes/?projeto=1&data_inicio=2025-01-01&data_fim=2025-03-31" \
  -H "Cookie: sessionid=<seu-session-id>"
```

#### **Resposta (200 OK)**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "municipio": "Fortaleza",
      "projeto": "ACerta",
      "tipo_acao": "Cadastro INEP",
      "responsavel": "João Silva",
      "observacao": "Cadastro concluído",
      "data_registro": "2025-01-20",
      "external_hash": "x1y2z3a4b5c6...",
      "created_at": "2025-01-01T12:00:00Z",
      "updated_at": "2025-01-01T12:00:00Z"
    }
  ]
}
```

> A resposta é **paginada**: `StandardPagination` é o
> `DEFAULT_PAGINATION_CLASS` (`config/settings.py:508-509`), com `page_size=100` e
> `max_page_size=500`, e honra `?page_size=` (`apps/core/pagination.py:21-23`).
> Ordenação padrão: `-data_registro`, `municipio_id` (`views_controle_dat.py:57-59`).

---

### **API 3: Cadastros DAT (Criação)**

**Endpoint:** `POST /api/dat/acoes/`

**Permissão:** `HasPerm("manage_admin_registries")` (mesma view)

**Descrição:** Cria nova ação DAT.

#### **Body (JSON)**

```json
{
  "municipio": 1,
  "projeto": 1,
  "tipo_acao": "Novo Cadastro",
  "responsavel": 5,
  "data_registro": "2025-03-01",
  "observacao": "Observação opcional"
}
```

**Campos obrigatórios:**
- `municipio` (ID)
- `projeto` (ID)
- `tipo_acao` (string)

**Campos opcionais:**
- `responsavel` (ID do usuário)
- `data_registro` (YYYY-MM-DD)
- `observacao` (texto)

#### **Exemplo de Requisição**

```bash
curl -X POST http://localhost:8002/api/dat/acoes/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=<seu-session-id>" \
  -d '{
    "municipio": 1,
    "projeto": 1,
    "tipo_acao": "Cadastro SIGPEC",
    "responsavel": 3,
    "data_registro": "2025-03-15"
  }'
```

#### **Resposta (201 Created)**

```json
{
  "id": 10,
  "municipio": "Fortaleza",
  "projeto": "ACerta",
  "tipo_acao": "Cadastro SIGPEC",
  "responsavel": "Maria Silva",
  "observacao": null,
  "data_registro": "2025-03-15",
  "external_hash": "g7h8i9j0k1l2...",
  "created_at": "2025-03-01T14:30:00Z",
  "updated_at": "2025-03-01T14:30:00Z"
}
```

**Nota:** Response usa serializer de **leitura** (StringRelatedField), enquanto request aceita IDs.

---

### **Erros Comuns**

#### **403 Forbidden**

**Causa:** Usuário sem a **capability** exigida pela view.

**Solução:** diagnostique pela capability, não pelo nome do grupo — é a permissão que
a view checa (`HasPerm("manage_admin_registries")`), e o grupo é só um dos caminhos
para chegar nela.

```bash
make shell
python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.core.rbac import user_has_any_perm
u = get_user_model().objects.get(username='seu_usuario')
print('grupos:', list(u.groups.values_list('name', flat=True)))
print('tem a capability:', user_has_any_perm(u, 'manage_admin_registries'))
"
```

Se faltar, atribua o usuário ao grupo que carrega a permissão pelo **Django Admin**
(`/admin/auth/user/`) ou reaplique o seed em dev (`make seed-rbac`). O mapeamento
grupo → permissões é `PERMS_BY_GROUP` em
`apps/dev_tools/management/commands/seed_rbac.py`; a matriz de autorização real está em
[rbac_authorization_matrix.md](./rbac_authorization_matrix.md).

#### **400 Bad Request (campo obrigatório faltando)**

**Exemplo:**
```json
{
  "municipio": ["This field is required."],
  "tipo_acao": ["This field is required."]
}
```

**Solução:** Incluir todos os campos obrigatórios no body da requisição.

---

## 📥 Importação de Acompanhamento

O ETL legado (`etl_upsert_acompanhamento`, `external_hash` v2, quality gates) foi **removido** (#967/#971). A importação atual usa o command `import_export_contract` (dry-run por padrão). Ver a spec viva [`imports.spec.md`](specs/backend/imports.spec.md).

---

## Municípios IBGE — Operação Contínua

### Objetivo
Manter a base de referência nacional (`core_municipio_referencia`) atualizada e preencher `ibge_code` faltante no cadastro principal (`core_municipio`) com segurança.

### Comandos

1. **Sincronizar referência IBGE** (API oficial -> `core_municipio_referencia`)

```bash
cd v2/backend
python manage.py sync_municipios_ibge
python manage.py sync_municipios_ibge --apply
```

2. **Backfill de IBGE no cadastro principal** (`core_municipio`)

```bash
cd v2/backend
python manage.py backfill_municipios_ibge --fonte=ibge
python manage.py backfill_municipios_ibge --fonte=ibge --apply --verbose
```

### Ordem recomendada (produção)

1. Rodar `sync_municipios_ibge --apply`
2. Rodar `backfill_municipios_ibge --fonte=ibge --apply`

### Frequência sugerida

- Mensal (ex.: 1º dia útil, madrugada)
- Sempre executar primeiro em `dry-run` após mudança de versão/ambiente

### Segurança operacional

- `sync_municipios_ibge` e `backfill_municipios_ibge` são idempotentes
- O backfill só atualiza municípios sem `ibge_code`
- Matches ambíguos/conflitantes são reportados e não são aplicados automaticamente
