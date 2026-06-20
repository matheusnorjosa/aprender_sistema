---
title: Observabilidade (v2)
status: active
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/config/settings.py
  - v2/backend/config/urls.py
  - v2/infra/docker-compose.yml
  - v2/infra/Makefile
owner: infra
related:
  - ./LOGGING.md
  - ./SLO_DEFINITIONS.md
  - ../../docs/guides/observability.md
---

# Observabilidade (v2)

> **Dev × Produção (importante):** a stack de **coleta e painéis (Prometheus + Grafana) é local/opcional e NÃO
> roda em produção.** Em prod, o app apenas **expõe `/metrics`** (instrumentação `django-prometheus`) para
> scraping por um serviço externo do provedor, e envia erros ao **Sentry somente se `SENTRY_DSN` estiver
> configurado**. Fonte autoritativa: comentário em `v2/infra/docker-compose.yml` — a stack foi movida para
> `docker-compose.observability.yml` (Issue #234): *"Em produção, use o serviço de observabilidade do provedor.
> O endpoint /metrics do Django permanece disponível para scraping."*

Documento-índice criado em 2026-06-19 (Fase 0 do plano SDD) para resolver ponteiros que apontavam para um
`v2/docs/OBSERVABILITY.md` inexistente (README, INDEX_DOCUMENTACAO, LOGGING). Ver
[plano SDD](./plans/PLAN_sdd_migration_2026-06-19.md) e [auditoria](./reports/AUDITORIA_DOCUMENTAL_2026-06-19.md).

## O que existe em cada ambiente

| Componente | Dev/local | Produção |
|---|---|---|
| Instrumentação `django-prometheus` (middleware) | ✅ | ✅ (sempre ativa; em `INSTALLED_APPS`/`MIDDLEWARE`) |
| Endpoint `/metrics` | ✅ | ✅ **gated** — só staff / IP interno (`config/urls.py`, SEC-RECON-02) |
| Prometheus + Grafana (coleta + painéis) | ✅ opcional via `make up-obs` | ❌ **não roda em prod** — design é scraping externo do `/metrics` pelo provedor |
| Sentry (erros/tracing) | se `SENTRY_DSN` setado | se `SENTRY_DSN` setado (secret do Portainer — **status não verificado**) |

> Os arquivos da stack local (`docker-compose.observability.yml`, `prometheus.yml`, `grafana/`) são **locais e
> não versionados** (gitignored). `docker-compose.prod.yml` não contém nenhum serviço de Prometheus/Grafana.

## Stack local (opcional)

```bash
make up-obs     # docker-compose.yml + docker-compose.observability.yml (Prometheus + Grafana)
make down-obs
```

## Logging

<a id="mp2"></a>

### MP2 — Structured Logging

O logging estruturado (JSON) e as práticas de log (níveis, contexto, dados sensíveis) estão documentados em
[LOGGING.md](./LOGGING.md). Em produção, os erros chegam ao Sentry apenas quando `SENTRY_DSN` está configurado.

## SLOs e alertas

Os objetivos de nível de serviço (latência, disponibilidade, taxa de erro) estão em
[SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md).

## Análise histórica

Para o levantamento de gaps de observabilidade/infra (datado), ver
[_archive/analysis/phase-07-infra-observability-backup-dr.md](./_archive/analysis/phase-07-infra-observability-backup-dr.md).

## Relacionados

- [LOGGING.md](./LOGGING.md) — logging estruturado
- [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md) — SLOs e alertas
- [observability.md (MkDocs)](../../docs/guides/observability.md) — guia narrativo
- [BACKUP_OPERATIONS.md](./BACKUP_OPERATIONS.md) — operações de backup/DR
