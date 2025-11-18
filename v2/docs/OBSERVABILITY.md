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

## 📚 Referências

- [django-prometheus docs](https://github.com/korfuri/django-prometheus)
- [Prometheus docs](https://prometheus.io/docs/)
- [Grafana docs](https://grafana.com/docs/)
- [postgres_exporter](https://github.com/prometheus-community/postgres_exporter)
- [redis_exporter](https://github.com/oliver006/redis_exporter)

---

**Última atualização**: 2025-11-18
**Responsável**: Claude Code
**Issue**: #165 (MP1 - Prometheus + Grafana)
