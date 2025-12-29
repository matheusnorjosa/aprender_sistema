# Observabilidade

Stack completa de monitoramento e logging.

## Stack

| Componente | Versão | Função |
|------------|--------|--------|
| Prometheus | 2.54.0 | Coleta de métricas |
| Grafana | 11.2.0 | Visualização |
| django-prometheus | 2.3.1 | Instrumentação Django |
| postgres_exporter | 0.15.0 | Métricas PostgreSQL |
| redis_exporter | 1.62.0 | Métricas Redis |
| Sentry | - | APM e Error Tracking |

## Quick Start

### Stack Principal

```bash
cd v2/infra
make up
```

### Stack com Observabilidade

```bash
cd v2/infra
make up-obs
```

## Portas

| Serviço | Porta | URL |
|---------|-------|-----|
| Django Metrics | 8002 | http://localhost:8002/metrics |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |

## Métricas Django

```promql
# Requests por segundo
rate(django_http_requests_total_by_view_transport_method_total[1m])

# Latência P99
histogram_quantile(0.99, rate(django_http_requests_latency_seconds_by_view_method_bucket[5m]))

# Taxa de erro
sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))
```

## Structured Logging

### Formato JSON (Produção)

```json
{
  "asctime": "2025-11-18T18:30:00.123456Z",
  "levelname": "INFO",
  "name": "apps.core.services",
  "message": "check_conflicts called",
  "request_id": "abc123-def456",
  "environment": "staging",
  "service": "web"
}
```

### Correlation ID

Cada requisição recebe `request_id` único:

```bash
# Ver header na response
curl -i http://localhost:8002/api/solicitacoes/ | grep X-Request-ID

# Filtrar logs por request_id
docker compose logs web | jq 'select(.request_id == "abc123")'
```

## Sentry APM

### Configuração

```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Features

- Error tracking com stack traces
- Performance monitoring
- N+1 query detection
- Release tracking
- User context

## Dashboard Grafana

**"AS v2 - System Overview"** inclui:

1. Requests/Second por endpoint
2. Request Latency (P50/P95/P99)
3. Error Rate (4xx/5xx)
4. Redis Cache Hit Rate
5. PostgreSQL Operations Rate
6. PostgreSQL Active Connections

### Acesso

1. Abrir http://localhost:3000
2. Login: `admin` / `admin`
3. Dashboards → Aprender Sistema → AS v2 - System Overview
