# 📘 Aprender Sistema v2 — Runbook Operacional

**Versão:** 1.0
**Projeto Docker:** `aprender_v2`
**Última atualização:** 2026-02-24

---

## 📋 Índice

1. [Recarregar Variáveis de Ambiente (.env)](#recarregar-variáveis-de-ambiente-env)
2. [Operações Celery (Worker/Beat)](#operações-celery-workerbeat)
3. [Health Checks e Validações](#health-checks-e-validações)
4. [ETL: Importação de Ações (Controle e DAT)](#etl-importação-de-ações-controle-e-dat)
5. [APIs REST: Ações (Controle e DAT)](#apis-rest-ações-controle-e-dat)
6. [Troubleshooting Comum](#troubleshooting-comum)
7. [Deploy Workflow (Canônico)](#deploy-workflow-canônico)

---

## 🚀 Deploy Workflow (Canônico)

Workflow oficial:
- `.github/workflows/deploy.yaml`

Comportamento:
- `push` na `main` -> deploy automático em `staging`.
- `workflow_dispatch`:
  - `target_environment=staging` (build e deploy de staging),
  - `target_environment=production` + `promotion_tag`,
  - `target_environment=production` + `rollback_tag`.

### Variáveis obrigatórias por ambiente

Portainer:
- `STAGING_PORTAINER_URL` / `PRODUCTION_PORTAINER_URL` ou `PORTAINER_URL`
- `STAGING_PORTAINER_STACK_ID` / `PRODUCTION_PORTAINER_STACK_ID` ou `PORTAINER_STACK_ID`
- `STAGING_PORTAINER_ENDPOINT_ID` / `PRODUCTION_PORTAINER_ENDPOINT_ID` ou `PORTAINER_ENDPOINT_ID`
- `STAGING_PORTAINER_ACCESS_TOKEN` / `PRODUCTION_PORTAINER_ACCESS_TOKEN` ou `PORTAINER_ACCESS_TOKEN`

Verificação:
- `STAGING_HEALTHCHECK_URL` / `PRODUCTION_HEALTHCHECK_URL`
- `STAGING_VERSIONCHECK_URL` / `PRODUCTION_VERSIONCHECK_URL`

### Evidências geradas

Artifacts relevantes:
- `deploy-evidence.txt`
- `post-deploy-health-response.txt`
- `post-deploy-version-response.txt`
- `post-deploy-debug.txt`
- `portainer-stack-update-attempts.txt` (quando houver retries/falhas no update da stack)

### Troubleshooting do post-deploy

Quando falhar a verificação de versão/health no `deploy.yaml`, usar:

1. `deploy-evidence.txt` para contexto do run.
2. `post-deploy-debug.txt` para causa classificada (`failure_cause`):
   - `network_unavailable`
   - `endpoint_not_ready`
   - `version_mismatch`
3. `post-deploy-*.txt` para última resposta dos endpoints.

### Comandos canônicos

```bash
# Staging manual
gh workflow run deploy.yaml -f target_environment=staging

# Produção (promoção)
gh workflow run deploy.yaml -f target_environment=production -f promotion_tag=vYYYY.MM.DD-<sha>

# Produção (rollback)
gh workflow run deploy.yaml -f target_environment=production -f rollback_tag=vYYYY.MM.DD-<sha-anterior>
```

### Deprecação aplicada

Workflows removidos:
- `.github/workflows/release.yaml`
- `.github/workflows/dockerhub-rebuild.yml`

Variáveis obsoletas:
- `STAGING_DEPLOY_COMMAND`
- `PRODUCTION_DEPLOY_COMMAND`

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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat
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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat

# 3. Verificar logs
docker compose -p aprender_v2 -f infra/docker-compose.yml logs -f web worker beat

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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d worker
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d beat
```

### **Parar Worker e Beat**

```bash
cd v2

# Parar (sem remover)
docker compose -p aprender_v2 -f infra/docker-compose.yml stop worker beat

# Remover containers (dados em volumes são mantidos)
docker compose -p aprender_v2 -f infra/docker-compose.yml down worker beat
```

### **Ver Logs em Tempo Real**

```bash
cd v2

# Usando Makefile (recomendado)
make logs-worker     # Worker (tempo real)
make logs-beat       # Beat (tempo real)

# OU diretamente
docker compose -p aprender_v2 -f infra/docker-compose.yml logs -f worker
docker compose -p aprender_v2 -f infra/docker-compose.yml logs -f beat
```

### **Ver Últimas 200 Linhas de Logs**

```bash
cd v2

# Usando Makefile (recomendado)
make logs-worker-last
make logs-beat-last

# OU diretamente
docker compose -p aprender_v2 -f infra/docker-compose.yml logs --tail=200 worker
docker compose -p aprender_v2 -f infra/docker-compose.yml logs --tail=200 beat
```

### **Reiniciar Worker/Beat (após mudanças de código)**

```bash
cd v2

# ⚠️ Para recarregar .env: use up -d (não restart!)
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d worker beat

# ✅ Para apenas reiniciar (sem recarregar .env): use restart
docker compose -p aprender_v2 -f infra/docker-compose.yml restart worker beat
```

### **Verificar Status**

```bash
cd v2

# Status de todos os serviços
docker compose -p aprender_v2 -f infra/docker-compose.yml ps

# Status apenas de worker/beat
docker compose -p aprender_v2 -f infra/docker-compose.yml ps worker beat
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
- Em produção/systemd, usar scheduler padrão do Celery para respeitar `app.conf.beat_schedule` definido em `config/celery.py`.
- Só usar `django_celery_beat.schedulers:DatabaseScheduler` se as `PeriodicTask` estiverem cadastradas no banco.

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

docker compose -p aprender_v2 -f infra/docker-compose.yml exec -T web python -c "
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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat
```

---

### **Problema 2: Mudanças no .env não têm efeito**

**Causa:**
- Usou `docker compose restart` (não recarrega variáveis)

**Solução:**
```bash
# Usar up -d para recriar
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d <serviço>
```

---

### **Problema 3: Worker mostra "ConnectionRefusedError"**

**Verificar:**
1. Redis está rodando?
   ```bash
   docker compose -p aprender_v2 ps redis
   ```

2. REDIS_PORT correto no .env?
   ```bash
   docker compose exec -T worker printenv | grep REDIS
   # Deve mostrar: REDIS_PORT=6379 (não 6380!)
   ```

3. Worker foi recriado (não apenas reiniciado)?
   ```bash
   docker compose -p aprender_v2 up -d worker
   ```

---

### **Problema 4: Beat não agenda tarefas**

**Verificar:**
1. Beat está rodando?
   ```bash
   docker compose -p aprender_v2 ps beat
   make logs-beat-last
   ```

2. Tarefas estão cadastradas no Django Admin?
   - http://localhost:8002/admin/
   - Django Celery Beat → Periodic Tasks

3. Schedule está configurado corretamente?
   ```bash
   docker compose exec -T beat celery -A config inspect scheduled
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
COMPOSE_PROJECT_NAME=aprender_v2

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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d

# ════════════════════════════════════════════════════════════
# Recarregar .env (após edição)
# ════════════════════════════════════════════════════════════
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat

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
docker compose -p aprender_v2 -f infra/docker-compose.yml down

# ════════════════════════════════════════════════════════════
# Migrations
# ════════════════════════════════════════════════════════════
docker compose -p aprender_v2 exec -T web python manage.py makemigrations
docker compose -p aprender_v2 exec -T web python manage.py migrate

# ════════════════════════════════════════════════════════════
# Django Shell
# ════════════════════════════════════════════════════════════
docker compose -p aprender_v2 exec web python manage.py shell
```

---

## 📚 Referências

- **Docker Compose:** https://docs.docker.com/compose/
- **Celery:** https://docs.celeryq.dev/
- **Django:** https://docs.djangoproject.com/

---

**Autor:** Equipe Aprender Sistema
**Projeto:** `aprender_v2`
**Stack:** Django 5.1.2 + PostgreSQL 15 + Redis 7 + Celery 5.4.0

---

## 📦 ETL e Seeds

### Seeds RBAC

Cria grupos e permissões mínimas (idempotente):

```bash
# Via Makefile
make seed-rbac

# Via Docker diretamente
docker compose -p aprender_v2 exec -T web python manage.py seed_rbac
```

**Grupos criados:**
- Superintendência
- Coordenador
- Formador
- Controle
- DAT
- Gerência

**Permissões atribuídas:** view/add/change para Solicitacao conforme grupo.

### ETL Acompanhamento

Importa eventos e participantes de CSVs normalizados.

**Preparação:**
1. Colocar arquivos em `v2/data/csv-import/`:
   - `etl_eventos_normalizados.csv`
   - `etl_participantes_normalizados.csv`

2. Preview (dry-run):
```bash
make etl-acomp-dry
```

3. Aplicar:
```bash
make etl-acomp-apply
```

**Bind mount:** `../data/csv-import:/app/data/csv-import:ro` (read-only).

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
docker compose -p aprender_v2 exec -T web python manage.py shell -c "
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
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat

# Verificar logs
docker compose -p aprender_v2 -f infra/docker-compose.yml logs -f web | grep -i google
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
docker compose -p aprender_v2 exec -T web python manage.py shell -c "
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
docker compose -p aprender_v2 exec -T web printenv | grep GOOGLE

# Recriar container se necessário
docker compose -p aprender_v2 -f infra/docker-compose.yml up -d web worker beat
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

## 📊 ETL: Importação de Ações (Controle e DAT)

### **Visão Geral**

O sistema oferece importação idempotente de **Ações de Controle** e **Cadastros DAT** via CSV/XLSX.

**Características:**
- ✅ **Idempotência via `external_hash`** (SHA1): rodar 2x não duplica
- ✅ **Resolução automática de FKs**: Município, Projeto, Coordenador/Responsável
- ✅ **Parsing flexível de datas**: ISO (yyyy-mm-dd), BR (dd/mm/yyyy), Excel serial
- ✅ **Headers flexíveis**: case-insensitive, múltiplos aliases
- ✅ **Relatórios JSON** em `out_etl/`

**Permissões:**
- `IsControleOrSuper` para importação de **Ações de Controle**
- `IsDATOrSuper` para importação de **Cadastros DAT**

---

### **ETL 1: Ações de Controle**

**Modelo:** `AcaoControle`
**Campos:**
- `municipio` (obrigatório)
- `projeto` (obrigatório)
- `coordenador` (opcional, resolvido por email ou nome)
- `data_entrega`, `data_carta`, `contato_inicial`, `data_reuniao` (datas opcionais)
- `observacao` (opcional)

**Hash de idempotência:**
```
SHA1(municipio_id|projeto_id|data_entrega|data_reuniao)
```

#### **Preparar CSV/XLSX**

Headers aceitos (case-insensitive):
- `municipio` ou `município`
- `projeto`
- `coordenador`, `email`, `responsavel`, `responsável`
- `data_entrega` ou `data entrega`
- `data_carta` ou `data carta`
- `contato_inicial` ou `contato inicial`
- `data_reuniao`, `data_reunião` ou `data reunião`
- `observacao`, `observação` ou `obs`

**Exemplo CSV:**
```csv
Município,Projeto,Coordenador,Data Entrega,Data Reunião,Observação
Fortaleza,ACerta,coord@example.com,2025-01-15,2025-02-01,Entrega confirmada
Maracanaú,ACerta,maria.silva@example.com,15/01/2025,,Aguardando reunião
```

#### **Comandos de Importação**

**Preview (dry-run):**
```bash
cd v2

# Via Makefile (recomendado)
make etl-acoes-dry FILE=/app/data/acoes_controle.csv

# OU diretamente via Docker
docker compose exec -T web python manage.py etl_import_acoes_controle \
  /app/data/acoes_controle.csv --dry-run
```

**Aplicar (persistir no banco):**
```bash
# Via Makefile
make etl-acoes-apply FILE=/app/data/acoes_controle.xlsx

# OU diretamente
docker compose exec -T web python manage.py etl_import_acoes_controle \
  /app/data/acoes_controle.xlsx
```

#### **Relatório de Importação**

Arquivo salvo em: `out_etl/import_acoes_controle_report.json`

**Estrutura:**
```json
{
  "stats": {
    "created": 10,
    "updated": 2,
    "unchanged": 5,
    "skipped": {
      "municipio": 1,
      "projeto": 0,
      "coordenador": 3,
      "dates": 0,
      "other": 0
    }
  },
  "pendencias": {
    "municipios": [{"linha": 15, "nome": "Município Inexistente"}],
    "projetos": [],
    "coordenadores": [{"linha": 20, "valor": "email@invalido.com"}],
    "outros": []
  },
  "dry_run": false,
  "file": "/app/data/acoes_controle.csv"
}
```

#### **Validar Resultado**

```bash
# Entrar no shell Django
make shell

# Contar registros importados
python -c "from apps.core.models import AcaoControle; print(AcaoControle.objects.count())"

# Ver últimos 5 registros
python manage.py shell -c "
from apps.core.models import AcaoControle
for a in AcaoControle.objects.all()[:5]:
    print(f'{a.municipio.nome} | {a.projeto.nome} | {a.data_reuniao}')
"
```

---

### **ETL 2: Cadastros DAT**

**Modelo:** `AcaoDAT`
**Campos:**
- `municipio` (obrigatório)
- `projeto` (obrigatório)
- `tipo_acao` (obrigatório, texto livre)
- `responsavel` (opcional, resolvido por email ou nome)
- `data_registro` (opcional)
- `observacao` (opcional)

**Hash de idempotência:**
```
SHA1(municipio_id|projeto_id|tipo_acao|data_registro)
```

#### **Preparar CSV/XLSX**

Headers aceitos (case-insensitive):
- `municipio` ou `município`
- `projeto`
- `tipo_acao`, `tipo acao`, `tipo de acao`, `tipo`, etc.
- `responsavel`, `responsável`, `email`
- `data_registro`, `data registro`, `data`
- `observacao`, `observação`, `obs`

**Exemplo CSV:**
```csv
Município,Projeto,Tipo de Ação,Responsável,Data Registro,Observação
Fortaleza,ACerta,Cadastro INEP,resp@example.com,2025-01-20,Concluído
Maracanaú,ACerta,Cadastro SIGPEC,joao.silva@example.com,25/01/2025,Pendente validação
```

#### **Comandos de Importação**

**Preview (dry-run):**
```bash
cd v2

# Via Makefile
make etl-dat-dry FILE=/app/data/dat_cadastros.csv

# OU diretamente
docker compose exec -T web python manage.py etl_import_dat_cadastros \
  /app/data/dat_cadastros.csv --dry-run
```

**Aplicar:**
```bash
# Via Makefile
make etl-dat-apply FILE=/app/data/dat_cadastros.xlsx

# OU diretamente
docker compose exec -T web python manage.py etl_import_dat_cadastros \
  /app/data/dat_cadastros.xlsx
```

#### **Relatório de Importação**

Arquivo salvo em: `out_etl/import_dat_cadastros_report.json`

**Estrutura:**
```json
{
  "stats": {
    "created": 8,
    "updated": 1,
    "unchanged": 3,
    "skipped": {
      "municipio": 0,
      "projeto": 0,
      "tipo_acao": 2,
      "responsavel": 1,
      "other": 0
    }
  },
  "pendencias": {
    "municipios": [],
    "projetos": [],
    "tipo_acao": [{"linha": 10, "valor": null}],
    "responsaveis": [{"linha": 15, "valor": "usuario@invalido.com"}],
    "outros": []
  },
  "dry_run": false,
  "file": "/app/data/dat_cadastros.csv"
}
```

---

## 🔌 APIs REST: Ações (Controle e DAT)

### **Visão Geral**

Endpoints RESTful para consulta e criação de ações com **RBAC** (Role-Based Access Control).

**Base URL:** `http://localhost:8002/api/`

**Autenticação:** Session-based (Django Auth)

---

### **API 1: Ações de Controle**

**Endpoint:** `GET /api/controle/acoes/`

**Permissão:** `IsControleOrSuper` (grupos: Controle ou Superintendência)

**Descrição:** Lista ações do setor Controle com filtros opcionais de data.

#### **Query Parameters**

| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `data_inicio` | `YYYY-MM-DD` | Filtra por qualquer data >= data_inicio | `2025-01-01` |
| `data_fim` | `YYYY-MM-DD` | Filtra por qualquer data <= data_fim | `2025-12-31` |

**Comportamento do filtro:**
- Considera **todas as datas** do modelo: `data_entrega`, `data_carta`, `contato_inicial`, `data_reuniao`
- Retorna ação se **pelo menos uma** das datas estiver no intervalo
- Usa `Q()` do Django para OR lógico

#### **Exemplo de Requisição**

```bash
# Listar todas as ações
curl -X GET http://localhost:8002/api/controle/acoes/ \
  -H "Cookie: sessionid=<seu-session-id>"

# Filtrar por intervalo de datas
curl -X GET "http://localhost:8002/api/controle/acoes/?data_inicio=2025-01-01&data_fim=2025-03-31" \
  -H "Cookie: sessionid=<seu-session-id>"
```

#### **Resposta (200 OK)**

```json
[
  {
    "id": 1,
    "municipio": "Fortaleza",
    "projeto": "ACerta",
    "coordenador": "Maria Silva",
    "data_entrega": "2025-01-15",
    "data_carta": "2025-01-10",
    "contato_inicial": "2025-01-20",
    "data_reuniao": "2025-02-01",
    "observacao": "Entrega confirmada",
    "external_hash": "a1b2c3d4e5f6...",
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-01T10:00:00Z"
  }
]
```

**Notas:**
- FKs retornados como **strings** via `StringRelatedField` (ex: "Fortaleza", não ID)
- Ordenação padrão: `-data_reuniao`, `-data_entrega`

---

### **API 2: Cadastros DAT (Leitura)**

**Endpoint:** `GET /api/dat/acoes/`

**Permissão:** `IsDATOrSuper` (grupos: DAT ou Superintendência/superuser)

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
[
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
```

---

### **API 3: Cadastros DAT (Criação)**

**Endpoint:** `POST /api/dat/acoes/`

**Permissão:** `IsDATOrSuper`

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

**Causa:** Usuário sem permissão (grupo incorreto).

**Solução:**
```bash
# Verificar grupos do usuário
make shell
python manage.py shell -c "
from django.contrib.auth import get_user_model
u = get_user_model().objects.get(username='seu_usuario')
print(u.groups.values_list('name', flat=True))
"

# Adicionar ao grupo correto
python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
u = get_user_model().objects.get(username='seu_usuario')
g = Group.objects.get(name='Controle')  # ou 'DAT'
u.groups.add(g)
"
```

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

## 📦 ETL: Acompanhamento com hash v2 e Quality Gates (PR21)

### **Visão Geral**

O ETL de Acompanhamento foi aprimorado com:
- **hash v2**: Usa 17 campos normalizados para detecção de duplicatas (vs. 8 campos do hash v1)
- **Quality Gates**: Valida qualidade dos dados antes de permitir apply

---

### **1. Backfill external_hash v2**

Atualiza hashes existentes de v1 para v2 em solicitações já criadas.

**Comando:**
```bash
# Dry-run (mostra o que seria feito, sem alterar DB)
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \
  python manage.py backfill_external_hash_v2

# Apply (persiste novos hashes)
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \
  python manage.py backfill_external_hash_v2 --apply

# Limitar a N solicitações (para testes)
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \
  python manage.py backfill_external_hash_v2 --limit 100
```

**Output:**
```
================================================================================
BACKFILL EXTERNAL_HASH V2 (PR21)
================================================================================
Modo: DRY-RUN
Limit: Todas as solicitações

📊 Total de solicitações: 1523

--------------------------------------------------------------------------------
📊 SUMÁRIO:
   Total processadas: 1523
   Would update: 1523
   Unchanged: 0
   Errors: 0
   Colisões detectadas: 2
--------------------------------------------------------------------------------

⚠️  2 colisões detectadas!
   Veja: v2/.agents/outbox/external_hash_v2_collisions.json

⚠️  DRY-RUN: Use --apply para atualizar

✅ Backfill concluído!
```

**Relatórios gerados:**
- `v2/.agents/outbox/external_hash_v2_collisions.json` (somente se houver colisões)

---

### **2. ETL Acompanhamento com Quality Gates**

Processa eventos normalizados com validação de qualidade obrigatória.

**Comandos:**
```bash
# Dry-run (sempre permitido, mesmo com violações)
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \
  python manage.py etl_upsert_acompanhamento

# Apply (valida quality gates, aborta se violar)
docker compose -p aprender_v2 -f v2/infra/docker-compose.yml exec -T web \
  python manage.py etl_upsert_acompanhamento --apply
```

**Flags de Controle (config/settings.py):**
| Flag | Default | Descrição |
|------|---------|-----------|
| `USE_EXTERNAL_HASH_V2` | `True` | Usa hash v2 (17 campos) ao invés de v1 (8 campos) |
| `ETL_MAX_DUPLICATES_PCT` | `1.0` | % máxima de duplicatas permitida |
| `ETL_MAX_UNKNOWN_USERS` | `100` | Máximo de pessoas sem cadastro permitidas |
| `ETL_REQUIRE_ZERO_INVALID_INTERVALS` | `True` | Aborta se houver intervalos inválidos (fim ≤ início) |
| `ETL_REQUIRE_ZERO_INVALID_DATES` | `True` | Aborta se houver datas/horas inválidas |

**Output (Dry-run):**
```
🚀 ETL Acompanhamento (dry_run=True, apply=False)
   TZ: America/Fortaleza
   Today: 2025-10-24
   Events CSV: /app/data/csv-import/etl_eventos_normalizados.csv
   Participants CSV: /app/data/csv-import/etl_participantes_normalizados.csv

📂 Carregando CSVs...
   1250 eventos carregados
   1250 grupos de participantes

📊 Calculando métricas de qualidade...
   Total eventos: 1250
   Duplicatas: 8 (0.64%)
   Usuários desconhecidos: 45
   Intervalos inválidos: 0
   Datas inválidas: 0
   📄 Métricas salvas em: v2/.agents/outbox/etl_metrics.json

⚙️  Processando eventos...
   [DRY-RUN] Rollback transaction

✅ ETL concluído!
```

**Output (Apply com violação):**
```
📊 Calculando métricas de qualidade...
   Total eventos: 1250
   Duplicatas: 25 (2.0%)
   Usuários desconhecidos: 150
   Intervalos inválidos: 3
   Datas inválidas: 0

❌ Quality gates violated (3 gate(s)). Apply aborted.
  - ETL_MAX_DUPLICATES_PCT: Duplicates threshold violated: 2.0% > 1.0%
  - ETL_MAX_UNKNOWN_USERS: Unknown users threshold violated: 150 > 100
  - ETL_REQUIRE_ZERO_INVALID_INTERVALS: Invalid intervals detected: 3 (ETL_REQUIRE_ZERO_INVALID_INTERVALS=True)
   📄 Violações salvas em: v2/.agents/outbox/etl_violations.csv

Error: ❌ Quality gates violated (3 gate(s)). Apply aborted.
```

**Relatórios gerados:**
- `v2/.agents/outbox/etl_metrics.json` (sempre)
- `v2/.agents/outbox/etl_violations.csv` (somente se houver violações)

---

### **3. Arquivos de Output**

Todos os relatórios são salvos em `v2/.agents/outbox/`:

| Arquivo | Quando gerado | Conteúdo |
|---------|---------------|----------|
| `external_hash_v2_collisions.json` | Backfill com colisões | Lista de hashes duplicados com IDs das solicitações |
| `etl_metrics.json` | Sempre (dry-run ou apply) | Métricas de qualidade: duplicatas%, unknown_users, etc. |
| `etl_violations.csv` | Apply com violações de gates | Detalhes das violações (gate, mensagem, valor, threshold) |

**Exemplo de etl_metrics.json:**
```json
{
  "total_events": 1250,
  "duplicates_count": 8,
  "duplicates_pct": 0.64,
  "unknown_users_count": 45,
  "invalid_intervals_count": 0,
  "invalid_dates_count": 0
}
```

**Exemplo de etl_violations.csv:**
```csv
gate,message,metric_value,threshold
ETL_MAX_DUPLICATES_PCT,Duplicates threshold violated: 2.0% > 1.0%,2.0,1.0
ETL_MAX_UNKNOWN_USERS,Unknown users threshold violated: 150 > 100,150,100
```

---

### **4. Workflow Recomendado**

**Passo 1: Validar dados (dry-run)**
```bash
docker compose exec -T web python manage.py etl_upsert_acompanhamento
# Verifica métricas em v2/.agents/outbox/etl_metrics.json
```

**Passo 2: Corrigir violações se necessário**
- Duplicatas > threshold → revisar CSVs de entrada
- Unknown users > threshold → cadastrar usuários faltantes (usar gen_top50_usuarios + import_usuarios_from_csv)
- Invalid intervals → corrigir datas/horas nos CSVs
- Invalid dates → validar formato das datas

**Passo 3: Aplicar (apply)**
```bash
docker compose exec -T web python manage.py etl_upsert_acompanhamento --apply
```

**Passo 4: Backfill hash v2 (opcional)**
```bash
# Somente se quiser atualizar solicitações antigas de v1 para v2
docker compose exec -T web python manage.py backfill_external_hash_v2 --apply
```

---

### **5. Troubleshooting**

#### **Erro: "Quality gates violated"**
**Causa:** Dados de entrada violam thresholds configurados.

**Solução:**
1. Verifique `v2/.agents/outbox/etl_violations.csv` para detalhes
2. Ajuste dados de entrada ou aumente thresholds temporariamente (se justificável)
3. Para testes, você pode desabilitar gates via .env:
   ```bash
   ETL_REQUIRE_ZERO_INVALID_INTERVALS=False
   ETL_REQUIRE_ZERO_INVALID_DATES=False
   ```
4. Recarregue variáveis: `docker compose up -d web`

#### **Erro: "Collisions detected" no backfill**
**Causa:** Duas ou mais solicitações geram o mesmo hash v2 (duplicata real).

**Solução:**
1. Verifique `v2/.agents/outbox/external_hash_v2_collisions.json`
2. Identifique se são duplicatas legítimas (mesmo evento cadastrado 2x)
3. Se sim, delete manualmente as duplicatas no banco
4. Execute backfill novamente

#### **Dry-run sempre permitido**
**Observação:** Dry-run **nunca** é bloqueado por quality gates. Use para diagnóstico sem risco.

---
