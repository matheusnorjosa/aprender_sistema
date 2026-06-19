---
title: Observabilidade (v2)
status: active
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/config/settings.py
  - v2/infra/docker-compose.yml
  - v2/infra/Makefile
owner: infra
related:
  - ./LOGGING.md
  - ./SLO_DEFINITIONS.md
  - ../../docs/guides/observability.md
---

# Observabilidade (v2)

Documento-índice da observabilidade do AS v2. Consolida os ponteiros para a stack real de métricas,
logging e alertas. Para o guia narrativo publicado no MkDocs, ver [observability.md](../../docs/guides/observability.md).

> Nota: este arquivo foi criado em 2026-06-19 (Fase 0 do plano SDD) para resolver ponteiros que apontavam
> para um `v2/docs/OBSERVABILITY.md` inexistente (README, INDEX_DOCUMENTACAO, LOGGING). Ver
> [plano SDD](./plans/PLAN_sdd_migration_2026-06-19.md) e [auditoria](./reports/AUDITORIA_DOCUMENTAL_2026-06-19.md).

## Stack real

| Camada | Tecnologia | Onde está |
|---|---|---|
| Erros/tracing | Sentry SDK | bloco `SENTRY` em `config/settings.py` (ativado por `SENTRY_DSN`) |
| Métricas | `django-prometheus` (`/metrics`) | `INSTALLED_APPS`/`MIDDLEWARE` em `config/settings.py` |
| Coleta/painéis | Prometheus + Grafana | `v2/infra/docker-compose.yml` (perfil de observabilidade) |
| Subir local | `make up-obs` | `v2/infra/Makefile` |

> As versões exatas (django-prometheus, sentry-sdk, Prometheus, Grafana) são definidas em
> `v2/backend/requirements.txt` e nas imagens do compose — consultá-las lá para evitar drift de versão.

## Logging

<a id="mp2"></a>

### MP2 — Structured Logging

O logging estruturado (JSON) e as práticas de log (níveis, contexto, dados sensíveis) estão documentados em
[LOGGING.md](./LOGGING.md). Logs de produção são coletados pela stack do container; eventos de erro também
chegam ao Sentry quando `SENTRY_DSN` está configurado.

## SLOs e alertas

Os objetivos de nível de serviço (latência, disponibilidade, taxa de erro) e a política de alertas estão em
[SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md).

## Análise histórica

Para o levantamento de gaps de observabilidade/infra (datado), ver
[analysis/phase-07-infra-observability-backup-dr.md](./analysis/phase-07-infra-observability-backup-dr.md).

## Relacionados

- [LOGGING.md](./LOGGING.md) — logging estruturado
- [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md) — SLOs e alertas
- [observability.md (MkDocs)](../../docs/guides/observability.md) — guia narrativo
- [BACKUP_OPERATIONS.md](./BACKUP_OPERATIONS.md) — operações de backup/DR
