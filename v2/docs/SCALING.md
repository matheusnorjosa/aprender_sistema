# Horizontal Scaling Guide

**Data**: 2026-07-24 (revisão contra o código)
**Status**: Ativo — **documento de projeto/capacidade, não de operação corrente**
**Referência**: PLAN_maturity_gaps.md (Gap 7)

> ⚠️ **Nada aqui está em uso em produção hoje.** A produção roda **uma instância de cada
> serviço** numa stack Docker Compose sob Portainer na VM01
> (`v2/infra/docker-compose.prod.yml`): `migrate` (one-shot), `web`, `redis`, `worker`,
> `beat`, `frontend`. **Não há `replicas`, não há Kubernetes, não há load balancer interno**
> — o edge é um Nginx Proxy Manager externo ao repositório. Este documento descreve o que a
> arquitetura *permite*, para quando houver necessidade. Antes de citar qualquer trecho como
> "é assim que roda", confira o compose.

---

## 1. Visão Geral

O AS v2 foi projetado para scaling horizontal desde o início. Este documento descreve
a arquitetura stateless e como escalar a aplicação **quando for preciso**.

---

## 2. Arquitetura Stateless

### 2.1 Componentes

| Componente | State | Storage | Estado real |
|------------|-------|---------|---|
| Django App | Stateless | - | ✅ |
| Sessions | Redis | `SESSION_ENGINE=cache` (`settings.py:328-329`) | ✅ em uso |
| Cache | Redis | `django_redis.cache.RedisCache` | ✅ em uso |
| Media Files | S3 (opcional) | `django-storages` **só se `AWS_STORAGE_BUCKET_NAME` estiver setado** (`settings.py:385-386`) | ⚠️ **não configurado**; cai em `MEDIA_ROOT = BASE_DIR/"media"` (disco local, `settings.py:379`). Hoje nenhum model usa `FileField`/`ImageField`, então isso não bloqueia réplicas — **passaria a bloquear** no primeiro upload persistente |
| Task Queue | Redis | Celery broker | ✅ em uso |
| Database | PostgreSQL | Externo (VM02) | ✅ |

### 2.2 Verificação de Statelessness

```bash
cd v2/backend
grep -nE "SESSION_ENGINE|SESSION_CACHE_ALIAS|AWS_STORAGE_BUCKET_NAME" config/settings.py

# Esperado:
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# SESSION_CACHE_ALIAS = "default"
```

> `DEFAULT_FILE_STORAGE` **não existe** neste projeto (Django 5.2 usa `STORAGES`); procurar
> por ele não retorna nada e não prova nada.

---

## 3. Deploy com Múltiplas Instâncias

> **Exemplos ilustrativos.** Nenhum dos blocos desta seção reflete o compose real. O
> compose de produção não declara `deploy.replicas`, não tem serviço `db` (Postgres é
> externo) e trata migrations com um serviço one-shot `migrate` +
> `depends_on: service_completed_successfully` (`docker-compose.prod.yml:47-51`) — não com
> `RUN_MIGRATIONS`.

### 3.1 Docker Compose (exemplo)

```yaml
# EXEMPLO — não é o docker-compose.yml deste repositório
services:
  web:
    build: .
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    environment:
      - RUN_MIGRATIONS=0  # Migrations em apenas 1 instância
    depends_on:
      - db
      - redis

  web-migrate:
    build: .
    command: python manage.py migrate --noinput
    deploy:
      replicas: 1  # Apenas 1 instância para migrations
    depends_on:
      - db

  celery:
    build: .
    command: celery -A config worker -l info --concurrency=4
    deploy:
      replicas: 2
```

### 3.2 Nginx Load Balancer (exemplo — não existe hoje)

> Em produção o roteamento é feito pelo **Nginx Proxy Manager**, que é **externo ao
> repositório**: o compose apenas se conecta à rede `shared_proxy`, declarada
> `external: true` (`docker-compose.prod.yml:322-323,341-342`). A configuração do NPM
> (rotas, TLS, headers, tratamento de `X-Forwarded-For`) **não está versionada aqui** e
> precisa ser inspecionada no próprio NPM. O `nginx.conf` versionado é o do container
> `frontend` (SPA + proxy `/api/`), não um balanceador.

```nginx
# EXEMPLO ilustrativo — não é nenhum arquivo deste repositório
upstream django {
    least_conn;  # Distribuir para conexão com menos requests
    server web1:8000 weight=1;
    server web2:8000 weight=1;
    server web3:8000 weight=1;

    keepalive 32;
}

server {
    listen 80;

    location / {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /healthz/ {
        proxy_pass http://django;
        proxy_connect_timeout 5s;
        proxy_read_timeout 5s;
    }
}
```

### 3.3 Kubernetes — ❌ NÃO USADO

> **Não existe Kubernetes neste projeto.** Não há diretório `k8s/`, nem manifesto, nem
> cluster. Produção é Docker Compose sob Portainer (ADR-001, ADR-018). O bloco abaixo é
> material de referência caso um dia se migre — **não** um artefato deste repositório.

```yaml
# EXEMPLO — arquivo inexistente (não há k8s/ neste repositório)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: as-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: as-web
  template:
    metadata:
      labels:
        app: as-web
    spec:
      containers:
        - name: web
          image: as-backend:latest
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "1"
          ports:
            - containerPort: 8000
          readinessProbe:
            httpGet:
              path: /healthz/
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /healthz/
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
          env:
            - name: RUN_MIGRATIONS
              value: "0"
---
apiVersion: v1
kind: Service
metadata:
  name: as-web
spec:
  selector:
    app: as-web
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
```

---

## 4. Considerações

### 4.1 Migrations

**Problema**: Múltiplas instâncias não podem rodar migrations simultaneamente.

**Como o projeto já resolve isso (produção, hoje)**: um serviço **one-shot `migrate`**
(`docker-compose.prod.yml:47-51`) espera o Postgres da VM02 responder, roda
`manage.py migrate --noinput` e sai. `web`, `worker` e `beat` só sobem depois que ele
termina com **êxito** (`depends_on: condition: service_completed_successfully`, #1456).
Uma migration quebrada **bloqueia o deploy** em vez de servir um schema meio-migrado.

> A `Dockerfile.prod` não tem `ENTRYPOINT`, então o `entrypoint.sh` (que migraria sob
> `RUN_MIGRATIONS=1`) **nunca roda em produção**. Não conte com `RUN_MIGRATIONS` em prod.

Alternativas equivalentes em outros orquestradores (não usados aqui):
1. **Job separado** antes do rollout
2. **Init Container (K8s)** — ver a ressalva da seção 3.3

### 4.2 Celery Workers

- Workers escalam independentemente do web
- Usar `--concurrency` para controlar threads por worker
- Recomendação: `concurrency = 2 * CPU cores`

```bash
# Produção: 4 workers com 4 threads cada = 16 tarefas paralelas
celery -A config worker -l info --concurrency=4
```

### 4.3 Database Pool

Configuração real, em `v2/backend/config/settings.py:247-276`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        # ...
        "CONN_MAX_AGE": 60,          # Reutiliza conexões por 60s
        "CONN_HEALTH_CHECKS": True,  # Valida conexões antes de reutilizar
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",  # só em produção
            "sslmode": "require",                     # fail-closed em produção (SEC-016)
        },
    }
}
```

> ⚠️ **`MAX_CONNS` não existe** no backend PostgreSQL do Django — versões anteriores deste
> documento sugeriam colocá-lo em `OPTIONS`, onde ele seria repassado ao driver e causaria
> erro de conexão. O Django não faz pooling próprio: cada processo gunicorn/celery mantém
> **uma** conexão persistente por `CONN_MAX_AGE`. Para pooling real, use PgBouncer.

**Cálculo de conexões** (sem pooling externo; o Django abre **1 conexão por thread**):
```
max_connections (PostgreSQL) >= (web_replicas * gunicorn_workers * gunicorn_threads)
                              + (celery_replicas * concurrency)
                              + beat + migrate + operadores (psql/admin)
                              + buffer
```

O gunicorn roda `worker_class = "gthread"` com `workers = GUNICORN_WORKERS` (default =
nº de CPUs) e `threads = GUNICORN_THREADS` (default 2) — `v2/infra/gunicorn.conf.py:16-18`.
São esses dois, e não um "pool", que multiplicam as conexões. Confira o limite real do
servidor antes de escalar:

```sql
SHOW max_connections;
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```

### 4.4 Redis

- Sessions e cache compartilham mesma instância Redis
- Para alta disponibilidade: Redis Sentinel ou Redis Cluster
- Monitorar uso de memória (sessions podem crescer)

---

## 5. Health Checks

### 5.1 Endpoints

| Endpoint | Propósito | Checks | Acesso |
|----------|-----------|--------|--------|
| `/healthz/` | Liveness | Básico (app running) | aberto |
| `/api/readyz/` | Readiness | DB + Redis — é o que o healthcheck do container `web` usa (`docker-compose.prod.yml:109`) e o que o applier confirma no deploy | aberto |
| `/healthz/detailed/` | Monitoring | DB + Redis + circuit breaker do GCal | ⚠️ **gated**: superuser **ou** IP interno (`config/urls.py:46-54`); de fora responde **403** |
| `/api/version/` | Identificar a release aplicada | SHA/tag em execução | aberto |

### 5.2 Implementação

A implementação real é `healthz_detailed` em **`v2/backend/config/urls.py:40-95`** (não em
`apps/core/views.py`). Ela devolve `{"status": ..., "checks": {"database", "redis",
"gcal_circuit"}}`, e o `status` global considera apenas `database` e `redis` como *core
checks* — um `gcal_circuit` aberto **não** derruba o health.

---

## 6. Load Testing

### 6.1 Ferramenta: Locust

```bash
pip install locust
cd v2/tests/load
locust -f locustfile.py --host=http://localhost:8000
```

### 6.2 Cenários de Teste

| Cenário | Users | Spawn Rate | Duração |
|---------|-------|------------|---------|
| Smoke | 10 | 1/s | 1 min |
| Load | 50 | 5/s | 5 min |
| Stress | 100 | 10/s | 10 min |
| Spike | 200 | 50/s | 2 min |

### 6.3 Métricas de Sucesso

| Métrica | Target |
|---------|--------|
| p95 Latency | < 500ms |
| p99 Latency | < 1000ms |
| Error Rate | < 0.1% |
| Throughput | > 50 req/s |

---

## 7. Troubleshooting

### 7.1 Conexões de Banco Esgotadas

```sql
-- Verificar conexões ativas
SELECT count(*) FROM pg_stat_activity;

-- Identificar queries lentas
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';
```

### 7.2 Redis Memory Pressure

```bash
# Verificar uso de memória
redis-cli INFO memory | grep used_memory_human

# Limpar cache se necessário (NÃO sessions!)
redis-cli FLUSHDB  # Cuidado: limpa tudo
```

### 7.3 Load Balancer Não Distribui Bem

- Verificar se health checks estão passando em todas as instâncias
- Usar `least_conn` no Nginx ao invés de `round_robin`
- Verificar se `Connection: keep-alive` está habilitado

---

## 8. Referências

- [Django Database Pooling](https://docs.djangoproject.com/en/5.0/ref/databases/#persistent-database-connections)
- [Gunicorn Deployment](https://docs.gunicorn.org/en/stable/deploy.html)
- [Celery Workers Guide](https://docs.celeryq.dev/en/stable/userguide/workers.html)
- [PLAN_infrastructure_scaling.md](./_archive/plans/PLAN_infrastructure_scaling.md)
