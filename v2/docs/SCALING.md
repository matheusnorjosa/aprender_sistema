# Horizontal Scaling Guide

**Data**: 2026-01-12
**Status**: Ativo
**Referência**: PLAN_maturity_gaps.md (Gap 7)

---

## 1. Visão Geral

O AS v2 foi projetado para scaling horizontal desde o início. Este documento descreve
a arquitetura stateless e como escalar a aplicação.

---

## 2. Arquitetura Stateless

### 2.1 Componentes

| Componente | State | Storage |
|------------|-------|---------|
| Django App | Stateless | - |
| Sessions | Redis | `django-redis` |
| Cache | Redis | `django-redis` |
| Media Files | S3/MinIO | `django-storages` |
| Task Queue | Redis | Celery broker |
| Database | PostgreSQL | Persistente |

### 2.2 Verificação de Statelessness

```bash
# Verificar settings.py
grep -E "SESSION_ENGINE|CACHES|DEFAULT_FILE_STORAGE" config/settings.py

# Esperado:
# SESSION_ENGINE = "django.contrib.sessions.backends.cache"
# CACHES = { "default": { "BACKEND": "django_redis.cache.RedisCache" } }
```

---

## 3. Deploy com Múltiplas Instâncias

### 3.1 Docker Compose (Desenvolvimento/Staging)

```yaml
# docker-compose.yml
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

### 3.2 Nginx Load Balancer

```nginx
# nginx.conf
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

### 3.3 Kubernetes (Produção)

```yaml
# k8s/deployment.yaml
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

**Solução**:
1. **Job separado**: Rodar migrations em job/container separado antes do deploy
2. **Variável RUN_MIGRATIONS**: Usar `RUN_MIGRATIONS=1` apenas em 1 instância
3. **Init Container (K8s)**: Container que roda migrations antes do pod principal

```yaml
# Kubernetes init container
initContainers:
  - name: migrations
    image: as-backend:latest
    command: ["python", "manage.py", "migrate", "--noinput"]
```

### 4.2 Celery Workers

- Workers escalam independentemente do web
- Usar `--concurrency` para controlar threads por worker
- Recomendação: `concurrency = 2 * CPU cores`

```bash
# Produção: 4 workers com 4 threads cada = 16 tarefas paralelas
celery -A config worker -l info --concurrency=4
```

### 4.3 Database Pool

```python
# settings.py
DATABASES = {
    "default": {
        # ...
        "CONN_MAX_AGE": 60,  # Reutilizar conexões por 60s
        "CONN_HEALTH_CHECKS": True,  # Django 4.1+
        "OPTIONS": {
            "MAX_CONNS": 20,  # Pool máximo por processo
        },
    }
}
```

**Cálculo de conexões**:
```
max_connections (PostgreSQL) = (web_replicas * pool_per_worker) + (celery_workers * concurrency) + buffer

Exemplo:
- 3 web replicas * 20 pool = 60
- 2 celery workers * 4 concurrency = 8
- buffer = 32
- Total: 100 conexões
```

### 4.4 Redis

- Sessions e cache compartilham mesma instância Redis
- Para alta disponibilidade: Redis Sentinel ou Redis Cluster
- Monitorar uso de memória (sessions podem crescer)

---

## 5. Health Checks

### 5.1 Endpoints

| Endpoint | Propósito | Checks |
|----------|-----------|--------|
| `/healthz/` | Load balancer | Básico (app running) |
| `/healthz/detailed/` | Monitoring | DB + Redis + GCal |

### 5.2 Implementação

```python
# apps/core/views.py
def health_detailed(request):
    """Detailed health check for monitoring."""
    checks = {}

    # Database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Redis
    try:
        cache.set("health_check", "ok", 1)
        checks["redis"] = "ok" if cache.get("health_check") == "ok" else "fail"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # GCal Circuit Breaker
    try:
        from apps.core.services.gcal.circuit_breaker import get_circuit_state
        checks["gcal_circuit"] = get_circuit_state()
    except Exception:
        checks["gcal_circuit"] = "unknown"

    status = "ok" if all(v == "ok" for v in checks.values() if v != "unknown") else "degraded"
    return JsonResponse({"status": status, "checks": checks})
```

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
- [PLAN_infrastructure_scaling.md](./PLAN_infrastructure_scaling.md)
