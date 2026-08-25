# Service Level Objectives (SLOs)

**Data**: 2026-07-24 (revisão contra o código)
**Status**: Ativo — **metas declaradas; não medidas em produção**
**Referência**: PLAN_maturity_gaps.md (Gap 3)

---

## 1. Visão Geral

Este documento define os Service Level Objectives (SLOs) para o Aprender Sistema v2.
SLOs são metas internas de qualidade de serviço que guiam decisões de arquitetura e operações.

> ⚠️ **Nenhum destes SLOs é medido hoje.** Prometheus e Grafana **não rodam em produção**
> (são stack local opcional, `make up-obs`, com arquivos gitignored — ver
> [OBSERVABILITY.md](./OBSERVABILITY.md)). Em prod existe só o `/metrics` do
> `django-prometheus`, **gated** por staff/IP interno, dependente de um scraper externo que
> não está documentado como configurado. **Não existe nenhuma regra de alerta versionada**
> neste repositório. Consequência prática: os números abaixo são **alvos de projeto**, e
> "estamos dentro do SLO" **não é uma afirmação verificável hoje** — não a use em
> post-mortem sem antes apontar a fonte de medição.

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

| Dado | RPO (alvo) | RTO (alvo) | Backup |
|------|-----|-----|--------|
| Banco de Dados | 5 min | 1 hora | WAL + dump diário cifrado — ver SSOT [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md) |
| Redis (cache **e sessões**) | N/A | 5 min | Não persistido — reiniciar o Redis **desloga todos os usuários** (`SESSION_ENGINE=cache`) |
| Google Calendar | 0 | 24 horas | Resync automático |

> ⚠️ **Estes são alvos, não capacidade demonstrada.** Hoje: o WAL archiving da VM02 **não
> foi verificado** (sem ele o RPO efetivo é ~24h, o intervalo do dump diário) e **nenhum
> ensaio de restore foi registrado**
> ([#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646), aberta).
> A ferramenta oficial de restore **voltou a funcionar** com o formato de produção
> `.age` — #1611 corrigido em `8f392636`, #1645 em `3bca74f3` —, mas ferramenta correta
> não é RTO medido. Antes de comprometer RPO/RTO com terceiros, leia
> [BACKUP_OPERATIONS.md → Estado real do restore](./BACKUP_OPERATIONS.md#estado-real-do-restore).

### 6.2 Consistência

| Operação | Garantia |
|----------|----------|
| Criar Solicitação | Eventual (2s) para grade mensal |
| Aprovar Solicitação | Strong (imediato) |
| GCal Sync | Eventual (5 min) |

---

## 7. Monitoramento

### 7.1 Métricas Prometheus

> ⚠️ **As séries `http_request_duration_seconds_bucket`, `http_responses_total` e
> `http_requests_total` não são exportadas por este sistema.** A instrumentação é o
> `django-prometheus` (2.5.0), que publica métricas com prefixo **`django_http_*`** —
> nomes diferentes dos usados abaixo. Copiar estas queries para um painel resulta em
> gráfico vazio.
>
> **Antes de escrever qualquer query**, leia os nomes reais na própria instância:
> ```bash
> # de dentro da VM (o /metrics é gated: staff ou IP interno)
> curl -s http://127.0.0.1:8000/metrics | grep -E '^# (HELP|TYPE) django_http' | head -40
> ```
> A única métrica customizada do projeto é `as_db_transaction_retries_total`
> (`apps/core/services/db_retry.py:64`) — ver
> [RUNBOOK_concurrency.md](./RUNBOOK_concurrency.md).

Forma das queries (substituindo pelos nomes reais lidos acima):

```promql
# Latência p95
histogram_quantile(0.95, sum(rate(<histograma_de_latencia>_bucket[5m])) by (le, view))

# Error rate 5xx
sum(rate(<contador_de_respostas>{status=~"5.."}[5m]))
  / sum(rate(<contador_de_respostas>[5m]))

# Throughput
sum(rate(<contador_de_requests>[5m]))
```

### 7.2 Alertas — ❌ nenhum implementado

Não existe arquivo de regra de alerta versionado no repositório (busca por `expr:` em
`*.yml`/`*.yaml` não retorna nenhuma regra Prometheus), e o Grafana não roda em produção.
A tabela abaixo é o **backlog** de alertas desejados, não o que está ativo:

| Alerta | Condição | Severidade | Status |
|--------|----------|------------|--------|
| HighLatencyP95 | p95 > 500ms por 5min | Warning | ❌ não implementado |
| HighLatencyP99 | p99 > 1s por 5min | Critical | ❌ não implementado |
| HighErrorRate | 5xx > 1% por 5min | Critical | ❌ não implementado |
| LowAvailability | Uptime < 99% em 1h | Critical | ❌ não implementado |

O único mecanismo automático de detecção hoje é o **Sentry**, e ele só está ativo se
`SENTRY_DSN` estiver configurado — ausente em produção na última verificação
([OBSERVABILITY.md](./OBSERVABILITY.md)).

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
| 1.1 | 2026-07-24 | Marcado como **não medido em produção**; corrigidos os nomes de métrica PromQL (não são as séries do `django-prometheus`); alertas reclassificados de "recomendados" para **não implementados**; ressalva de RPO/RTO ligada a #1611 |
| 1.2 | 2026-08-25 | Ressalva de RPO/RTO **religada a #1646** (ensaio de DR, aberta): #1611 e #1645 foram corrigidos (`8f392636`, `3bca74f3`) e a ferramenta de restore deixou de ser o gargalo |

---

## 9. Referências

- [Google SRE Book - SLOs](https://sre.google/sre-book/service-level-objectives/)
- [PLAN_maturity_gaps.md](./_archive/plans/PLAN_maturity_gaps.md)
- [OBSERVABILITY.md](./OBSERVABILITY.md) — o que existe de fato em cada ambiente
- **Prometheus Alerting Rules: não existem.** Nem versionadas no repositório, nem em
  Grafana de produção (o Grafana é dev-only).
