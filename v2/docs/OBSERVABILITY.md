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

## 📚 Referências

- [django-prometheus docs](https://github.com/korfuri/django-prometheus)
- [Prometheus docs](https://prometheus.io/docs/)
- [Grafana docs](https://grafana.com/docs/)
- [postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
- [redis_exporter](https://github.com/oliver006/redis_exporter)
- [python-json-logger docs](https://github.com/madzak/python-json-logger)
- [Grafana Loki docs](https://grafana.com/docs/loki/)

---

**Última atualização**: 2025-11-18
**Responsável**: Claude Code
**Issues**: #165 (MP1 - Prometheus + Grafana), #166 (MP2 - Structured Logging)
