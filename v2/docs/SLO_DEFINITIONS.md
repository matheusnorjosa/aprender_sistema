# Service Level Objectives (SLOs)

**Data**: 2026-01-12
**Status**: Ativo
**Referência**: PLAN_maturity_gaps.md (Gap 3)

---

## 1. Visão Geral

Este documento define os Service Level Objectives (SLOs) para o Aprender Sistema v2.
SLOs são metas internas de qualidade de serviço que guiam decisões de arquitetura e operações.

---

## 2. Latência (Response Time)

### 2.1 Endpoints de Leitura (GET)

| Endpoint | p50 | p95 | p99 | Notas |
|----------|-----|-----|-----|-------|
| `GET /api/solicitacoes/` | 100ms | 300ms | 500ms | Lista paginada (100 itens) |
| `GET /api/solicitacoes/{id}/` | 50ms | 150ms | 300ms | Detalhe único |
| `GET /api/availability/monthly/` | 150ms | 400ms | 800ms | Grade com cache Redis |
| `GET /api/availability-blocks/` | 100ms | 250ms | 400ms | Lista de bloqueios |
| `GET /api/options/*` | 50ms | 100ms | 200ms | Dropdowns (cached) |
| `GET /api/me/` | 30ms | 80ms | 150ms | Usuário atual |
| `GET /healthz/` | 10ms | 30ms | 50ms | Health check |

### 2.2 Endpoints de Escrita (POST/PUT/PATCH)

| Endpoint | p50 | p95 | p99 | Notas |
|----------|-----|-----|-----|-------|
| `POST /api/solicitacoes/` | 200ms | 500ms | 1000ms | Criação com validações |
| `PATCH /api/solicitacoes/{id}/` | 150ms | 400ms | 800ms | Atualização parcial |
| `POST /api/solicitacoes/{id}/aprovar/` | 200ms | 500ms | 1000ms | Aprovação + audit log |
| `POST /api/availability-blocks/` | 100ms | 300ms | 500ms | Criar bloqueio |

### 2.3 Endpoints de Integração (GCal)

| Endpoint | p50 | p95 | p99 | Notas |
|----------|-----|-----|-----|-------|
| `POST /api/gcal/publish-batch/` | 500ms | 2000ms | 5000ms | Batch de eventos (async) |
| `GET /api/gcal/status-summary/` | 200ms | 500ms | 1000ms | Status agregado |
| `GET /api/gcal/dashboard/events/` | 300ms | 800ms | 1500ms | Lista com filtros |

---

## 3. Disponibilidade (Availability)

### 3.1 Targets

| Serviço | Target | Error Budget Mensal | Notas |
|---------|--------|---------------------|-------|
| API (web) | 99.5% | 3.6 horas | Downtime planejado excluído |
| Background Jobs (Celery) | 99.0% | 7.2 horas | Tasks podem ser retriadas |
| Google Calendar Sync | 95.0% | 36 horas | Dependência externa |

### 3.2 Cálculo de Disponibilidade

```
Availability = (Total Time - Downtime) / Total Time × 100

Error Budget (horas/mês) = (100 - SLO%) × 720 / 100
- 99.5% SLO = 3.6 horas de error budget
- 99.0% SLO = 7.2 horas de error budget
```

---

## 4. Throughput

### 4.1 Capacidade Normal

| Métrica | Valor | Condições |
|---------|-------|-----------|
| Requests/segundo (sustained) | 50 req/s | p95 latency dentro dos SLOs |
| Requests/segundo (peak) | 100 req/s | Burst de até 5 minutos |
| Usuários simultâneos | 500 | Sessions ativas |

### 4.2 Limites de Rate Limiting

| Tipo | Limite | Período |
|------|--------|---------|
| Anônimo | 100 | por hora |
| Autenticado | 1000 | por hora |
| Availability Check | 60 | por minuto |

---

## 5. Error Rate

### 5.1 Targets por Tipo de Erro

| Código HTTP | Target Máximo | Notas |
|-------------|---------------|-------|
| 5xx (Server Error) | < 0.1% | Erros internos |
| 4xx (Client Error) | < 5% | Esperado (validação) |
| Timeout (504) | < 0.01% | Gateway timeout |

### 5.2 Exceções

- Erros 401/403 não contam para error rate (autenticação/autorização)
- Erros 429 (rate limit) são esperados e não contam

---

## 6. Dados e Consistência

### 6.1 Durabilidade

| Dado | RPO | RTO | Backup |
|------|-----|-----|--------|
| Banco de Dados | 5 min | 1 hora | WAL + Daily dump — ver SSOT [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md) |
| Redis (cache) | N/A | 5 min | Não persistido |
| Google Calendar | 0 | 24 horas | Resync automático |

> Para detalhes de backup (frequência, retenção, criptografia opcional, S3,
> health checks) consultar o SSOT [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md).

### 6.2 Consistência

| Operação | Garantia |
|----------|----------|
| Criar Solicitação | Eventual (2s) para grade mensal |
| Aprovar Solicitação | Strong (imediato) |
| GCal Sync | Eventual (5 min) |

---

## 7. Monitoramento

### 7.1 Métricas Prometheus

```promql
# Latência p95 (histograma)
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path))

# Error rate 5xx
sum(rate(http_responses_total{status=~"5.."}[5m])) / sum(rate(http_responses_total[5m]))

# Throughput
sum(rate(http_requests_total[5m]))
```

### 7.2 Alertas Recomendados

| Alerta | Condição | Severidade |
|--------|----------|------------|
| HighLatencyP95 | p95 > 500ms por 5min | Warning |
| HighLatencyP99 | p99 > 1s por 5min | Critical |
| HighErrorRate | 5xx > 1% por 5min | Critical |
| LowAvailability | Uptime < 99% em 1h | Critical |

---

## 8. Revisão e Evolução

### 8.1 Ciclo de Revisão

- **Mensal**: Revisar métricas vs SLOs
- **Trimestral**: Ajustar SLOs baseado em dados
- **Anual**: Revisão completa com stakeholders

### 8.2 Versionamento

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0 | 2026-01-12 | Versão inicial |

---

## 9. Referências

- [Google SRE Book - SLOs](https://sre.google/sre-book/service-level-objectives/)
- [PLAN_maturity_gaps.md](./_archive/plans/PLAN_maturity_gaps.md)
- Prometheus Alerting Rules: configuradas via Grafana dashboard (não versionadas em arquivo yml)
