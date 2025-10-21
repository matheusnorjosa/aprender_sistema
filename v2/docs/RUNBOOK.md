# 📘 Aprender Sistema v2 — Runbook Operacional

**Versão:** 1.0
**Projeto Docker:** `aprender_v2`
**Última atualização:** 2025-10-20

---

## 📋 Índice

1. [Recarregar Variáveis de Ambiente (.env)](#recarregar-variáveis-de-ambiente-env)
2. [Operações Celery (Worker/Beat)](#operações-celery-workerbeat)
3. [Health Checks e Validações](#health-checks-e-validações)
4. [Troubleshooting Comum](#troubleshooting-comum)

---

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

