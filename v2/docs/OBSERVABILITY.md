# Guia de Observabilidade - AS v2 (MP1)

**Data**: 2025-11-18
**Status**: ✅ Implementado
**Issue**: #165

---

## 📊 Stack de Observabilidade

### Componentes

1. **Prometheus** (v2.54.0) - Coleta e armazenamento de métricas
2. **Grafana** (v11.2.0) - Visualização e dashboards
3. **django-prometheus** (v2.3.1) - Instrumentação Django
4. **postgres_exporter** (v0.15.0) - Métricas PostgreSQL
5. **redis_exporter** (v1.62.0) - Métricas Redis

### Portas

| Serviço | Porta | URL |
|---------|-------|-----|
| Prometheus UI | 9090 | http://localhost:9090 |
| Grafana UI | 3000 | http://localhost:3000 |
| Metrics endpoint | 8002 | http://localhost:8002/metrics |
| PostgreSQL exporter | 9187 | http://localhost:9187/metrics |
| Redis exporter | 9121 | http://localhost:9121/metrics |

---

## 🚀 Quick Start

### Iniciar Stack Completa

```bash
cd v2/infra
docker compose up -d
```

### Acessar Dashboards

**Prometheus**:
- URL: http://localhost:9090
- Targets: http://localhost:9090/targets
- Query: `rate(django_http_requests_total[1m])`

**Grafana**:
- URL: http://localhost:3000
- Login: `admin` / `admin`
- Dashboard: "AS v2 - System Overview"

---

## 📈 Métricas Disponíveis

### Django (via django-prometheus)

**HTTP Requests**:
- `django_http_requests_total_by_view_transport_method_total` - Total de requests por endpoint
- `django_http_requests_latency_seconds_by_view_method` - Latência por endpoint
- `django_http_responses_total_by_status_total` - Responses por status code

**Database**:
- `django_db_execute_total` - Total de queries SQL
- `django_db_execute_created` - Queries em execução
- `django_db_new_connections_total` - Conexões criadas

**Models**:
- `django_model_inserts_total` - Inserts por model
- `django_model_updates_total` - Updates por model
- `django_model_deletes_total` - Deletes por model

**Cache**:
- `django_cache_get_total` - Cache gets
- `django_cache_hits_total` - Cache hits
- `django_cache_misses_total` - Cache misses

### PostgreSQL (via postgres_exporter)

- `pg_database_size_bytes` - Tamanho do banco
- `pg_stat_database_tup_fetched` - Tuplas lidas
- `pg_stat_database_tup_inserted` - Tuplas inseridas
- `pg_stat_activity_count` - Conexões ativas

### Redis (via redis_exporter)

- `redis_keyspace_hits_total` - Cache hits
- `redis_keyspace_misses_total` - Cache misses
- `redis_memory_used_bytes` - Memória utilizada
- `redis_connected_clients` - Clientes conectados

---

## 📋 Dashboard "AS v2 - System Overview"

### Painéis Incluídos

1. **Requests/Second** (by endpoint) - Tráfego HTTP por rota
2. **Request Latency** (P50/P95/P99) - Latência de responses
3. **Error Rate** (4xx/5xx) - Taxa de erros HTTP
4. **Redis Cache Hit Rate** - Eficiência do cache
5. **PostgreSQL Operations Rate** - Operações no banco
6. **PostgreSQL Active Connections** - Conexões ativas (gauge)

### Acessar Dashboard

1. Abrir Grafana: http://localhost:3000
2. Login: `admin` / `admin`
3. Navegar: Dashboards → Aprender Sistema → AS v2 - System Overview

---

## 🔧 Configuração

### Prometheus (`v2/infra/prometheus.yml`)

**Scrape Configs**:
- Django web: `web:8000/metrics` (15s interval)
- PostgreSQL: `postgres_exporter:9187/metrics` (15s interval)
- Redis: `redis_exporter:9121/metrics` (15s interval)
- Prometheus: `localhost:9090/metrics` (30s interval)

**Retention**: 30 dias

### Grafana (`v2/infra/grafana/`)

**Provisioning**:
- Datasource: Prometheus (auto-configurado)
- Dashboards: Auto-carregados de `grafana/dashboards/`

**Credenciais**:
- Usuário: `admin`
- Senha: `admin` (alterar em produção via `GRAFANA_ADMIN_PASSWORD`)

---

## 🎯 Queries Úteis

### Top 5 endpoints mais lentos (P99)

```promql
topk(5, histogram_quantile(0.99,
  rate(django_http_requests_latency_seconds_by_view_method_bucket[5m])
))
```

### Taxa de erro (últimos 5 min)

```promql
sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))
```

### Cache hit rate (Redis)

```promql
(rate(redis_keyspace_hits_total[5m]) /
 (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m]))) * 100
```

### Queries SQL/segundo

```promql
rate(django_db_execute_total[1m])
```

---

## 🐛 Troubleshooting

### Metrics endpoint retorna 404

**Problema**: `/metrics` não acessível
**Solução**: Verificar se django_prometheus está em INSTALLED_APPS e URLs configuradas

```bash
# Verificar instalação
docker compose exec web python -c "import django_prometheus; print(django_prometheus.__version__)"

# Verificar endpoint
curl http://localhost:8002/metrics | head -20
```

### Prometheus não coleta métricas do Django

**Problema**: Target `django_web` aparece como DOWN no Prometheus
**Causa**: ALLOWED_HOSTS não inclui hostname interno 'web'
**Solução**: Adicionar 'web' ao ALLOWED_HOSTS em settings.py

### Grafana não mostra dados

**Problema**: Painéis vazios ou "No Data"
**Solução**:
1. Verificar se datasource Prometheus está configurado
2. Verificar se Prometheus está coletando métricas (`/targets`)
3. Gerar tráfego HTTP para popular métricas

---

## 📝 Structured Logging (MP2)

**Status**: ✅ Implementado
**Issue**: #166

### Formato JSON

Logs em produção/staging são estruturados em JSON para agregação e análise:

```json
{
  "asctime": "2025-11-18T18:30:00.123456Z",
  "levelname": "INFO",
  "name": "apps.core.services.availability_service",
  "message": "check_conflicts called",
  "request_id": "abc123-def456-ghi789",
  "environment": "staging",
  "service": "web"
}
```

### Campos Disponíveis

- `asctime`: Timestamp ISO 8601 (UTC)
- `levelname`: DEBUG/INFO/WARNING/ERROR/CRITICAL
- `name`: Logger name (módulo)
- `message`: Mensagem do log
- `request_id`: Correlation ID único por requisição HTTP
- `environment`: development/staging/production
- `service`: web/worker/beat

### Visualizar Logs

**Docker Compose**:
```bash
# Logs de todos os serviços (JSON)
docker compose logs -f

# Logs apenas do web (formatados)
docker compose logs -f web | jq

# Filtrar por request_id
docker compose logs web | jq 'select(.request_id == "abc123")'

# Filtrar por nível ERROR
docker compose logs web | jq 'select(.levelname == "ERROR")'
```

**Logs locais (development)**:
```bash
# Em development, logs são human-readable (verbose format)
[INFO] 2025-11-18 15:30:00,123 availability_service 1234 5678 check_conflicts called
```

### Correlation ID (request_id)

Cada requisição HTTP recebe um `request_id` único (UUID4) que:
- Está presente em todos os logs da requisição
- É retornado no header `X-Request-ID` da response
- Permite rastrear toda a jornada de uma requisição (view → service → database → cache)

**Exemplo**:
```bash
curl -i http://localhost:8002/api/solicitacoes/ | grep X-Request-ID
# X-Request-ID: abc123-def456-ghi789

docker compose logs web | jq 'select(.request_id == "abc123-def456-ghi789")'
```

### Serviços Identificados

| Serviço | SERVICE_NAME | Logs |
|---------|--------------|------|
| Django Web | `web` | Requests HTTP, views, services |
| Celery Worker | `worker` | Tasks assíncronas, ETL |
| Celery Beat | `beat` | Agendamento de tasks |

### Agregação de Logs (Futuro)

Para agregação centralizada, considere:
- **Loki** (Grafana): Integra com Grafana existente
- **ELK Stack**: Elasticsearch + Logstash + Kibana
- **CloudWatch** / **Datadog** / **New Relic**: SaaS

**Integração com Loki** (exemplo):
```yaml
# promtail.yml (agent de coleta)
clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        target_label: 'container'
```

---

## 🔍 Sentry APM (MP3)

**Status**: ✅ Implementado
**Issue**: #167

### O que é Sentry?

Sentry é uma plataforma de **Application Performance Monitoring (APM)** e **Error Tracking** que fornece:
- **Error Tracking**: Captura exceções com stack traces completos
- **Performance Monitoring**: Detecta queries lentas, N+1 queries, endpoints lentos
- **Distributed Tracing**: Rastreia requests across services (Django → Celery → DB)
- **Release Tracking**: Correlaciona erros com deploys específicos (commit SHA)
- **User Context**: Identifica quais usuários foram afetados por erros

### Configuração

**1. Criar projeto no Sentry.io**

1. Acessar [sentry.io](https://sentry.io) e criar conta/projeto
2. Selecionar platform: **Django**
3. Copiar o **DSN** (Data Source Name)

**2. Configurar variáveis de ambiente** (`.env`):

```bash
# Sentry DSN (obrigatório para habilitar Sentry)
SENTRY_DSN=https://your-key@sentry.io/your-project-id

# Performance tracing (% de transactions)
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% (ajustar conforme tráfego)

# Profiling (experimental, desabilitado por padrão)
SENTRY_PROFILES_SAMPLE_RATE=0.0

# Release tracking (opcional, set automaticamente no CI/CD)
GIT_COMMIT_SHA=abc123def456
```

**3. Restart dos serviços**:

```bash
cd v2/infra
docker compose restart web worker beat
```

### Features Habilitadas

#### ✅ Django Integration

- **Error tracking**: Todas as exceções não tratadas são capturadas
- **SQL queries**: Detecta N+1 queries e slow queries
- **Middleware tracking**: Monitora execução de cada middleware
- **Signals tracking**: Monitora Django signals (pre_save, post_save, etc.)

#### ✅ Celery Integration

- **Task monitoring**: Rastreia todas as tasks assíncronas (worker)
- **Beat monitoring**: Monitora agendamento de tasks (beat scheduler)
- **Distributed tracing**: Correlaciona requests HTTP → tasks Celery

#### ✅ Privacy & Compliance (LGPD/GDPR)

- **send_default_pii = False**: Não envia PII (Personally Identifiable Information)
- **User context**: Pode ser habilitado manualmente com `set_user()` quando necessário
- **Data residency**: Escolher region do servidor Sentry (EU/US) no projeto

### Como Usar

#### Ver Erros no Dashboard

1. Acessar [sentry.io](https://sentry.io) → Seu Projeto
2. Navegue para **Issues** → Ver erros capturados
3. Filtrar por:
   - **Environment** (`development`/`staging`/`production`)
   - **Release** (commit SHA)
   - **User** (se context habilitado)

#### Performance Monitoring

1. Navegar para **Performance** → **Transactions**
2. Ordenar por:
   - **P95 Latency** (endpoints mais lentos)
   - **Throughput** (endpoints com mais tráfego)
   - **Failure Rate** (endpoints com mais erros)
3. Clicar em transaction para ver:
   - **Span waterfall** (breakdown de tempo: DB, cache, external APIs)
   - **Slow queries** (SQL queries > 100ms)
   - **N+1 queries** detectadas automaticamente

#### Release Tracking

1. Configurar `GIT_COMMIT_SHA` no CI/CD pipeline:
   ```yaml
   # .github/workflows/deploy.yml
   - name: Deploy to production
     env:
       GIT_COMMIT_SHA: ${{ github.sha }}
   ```

2. Ver deploys em **Releases** → Correlacionar erros com deploys

### Validação Manual

**1. Disparar erro intencional**:

```python
# Em qualquer view Django:
def test_sentry(request):
    division_by_zero = 1 / 0  # Dispara exceção
    return HttpResponse("OK")
```

**2. Verificar no dashboard Sentry**:

- Acessar **Issues** → Novo erro aparece em ~5-10 segundos
- Ver stack trace completo
- Ver request context (URL, método HTTP, headers)

**3. Verificar performance tracing**:

```python
# Em view com query N+1:
solicitacoes = Solicitacao.objects.all()
for sol in solicitacoes:
    print(sol.municipio.nome)  # N+1 query!
```

- Acessar **Performance** → Ver transaction lenta
- Span waterfall mostra N queries ao banco

### Sample Rates Recomendados

| Environment | Errors | Traces | Profiles | Justificativa |
|-------------|--------|--------|----------|---------------|
| **Development** | 100% | 100% | 0% | Debug completo, baixo tráfego |
| **Staging** | 100% | 50% | 0% | Validação pré-produção |
| **Production** | 100% | 10% | 0% | Custos controlados, amostra representativa |

**Ajustar conforme tráfego**:
- Tráfego baixo (<1k req/dia) → Traces 100%
- Tráfego médio (1k-10k req/dia) → Traces 10-50%
- Tráfego alto (>10k req/dia) → Traces 1-10%

### Troubleshooting

#### Sentry não captura erros

**Problema**: Erros não aparecem no dashboard
**Soluções**:
1. Verificar `SENTRY_DSN` está configurado e não vazio
2. Verificar logs do container: `docker compose logs web | grep sentry`
3. Testar DSN manualmente:
   ```python
   import sentry_sdk
   sentry_sdk.init(dsn="your-dsn")
   sentry_sdk.capture_message("Test from Django")
   ```

#### Performance overhead

**Problema**: Sentry está deixando aplicação lenta
**Soluções**:
1. Reduzir `SENTRY_TRACES_SAMPLE_RATE` (ex: 0.1 → 0.01)
2. Desabilitar profiling: `SENTRY_PROFILES_SAMPLE_RATE=0.0`
3. Filtrar transactions desnecessárias com `traces_sampler`:
   ```python
   def traces_sampler(sampling_context):
       if sampling_context["parent_sampled"] is not None:
           return sampling_context["parent_sampled"]
       if "health" in sampling_context["wsgi_environ"]["PATH_INFO"]:
           return 0  # Nunca trace healthchecks
       return 0.1  # 10% de outros endpoints

   sentry_sdk.init(dsn=..., traces_sampler=traces_sampler)
   ```

---

## 📚 Referências

- [django-prometheus docs](https://github.com/korfuri/django-prometheus)
- [Prometheus docs](https://prometheus.io/docs/)
- [Grafana docs](https://grafana.com/docs/)
- [postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
- [redis_exporter](https://github.com/oliver006/redis_exporter)
- [python-json-logger docs](https://github.com/madzak/python-json-logger)
- [Grafana Loki docs](https://grafana.com/docs/loki/)
- [Sentry docs](https://docs.sentry.io/)
- [Sentry Django Integration](https://docs.sentry.io/platforms/python/integrations/django/)
- [Sentry Celery Integration](https://docs.sentry.io/platforms/python/integrations/celery/)

---

**Última atualização**: 2025-11-18
**Responsável**: Claude Code
**Issues**: #165 (MP1 - Prometheus + Grafana), #166 (MP2 - Structured Logging), #167 (MP3 - Sentry APM)
