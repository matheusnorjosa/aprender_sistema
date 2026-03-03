# OpenAPI Contract Gate (Dashboard/GCal)

Esta política define o conjunto mínimo de endpoints críticos cujo contrato OpenAPI é bloqueante no CI.

## Objetivo

Evitar regressão silenciosa de schema (`No response body` ou respostas genéricas) nos endpoints usados pelo frontend em páginas de dashboard e GCal.

## Endpoints no gate mínimo

- `GET /api/dashboard/overview/`
- `GET /api/gcal/status-summary/`
- `GET /api/gcal/dashboard/metrics/`
- `GET /api/gcal/dashboard/events/`
- `GET /api/gcal/dashboard/insights/success-rate/`
- `GET /api/gcal/dashboard/insights/top/`
- `GET /api/gcal/dashboard/events/{id}/detail/`
- `POST /api/gcal/dashboard/batch/reapply/`
- `POST /api/gcal/dashboard/batch/resync/`

## Como o gate é aplicado

- Validação automatizada em `v2/backend/apps/core/tests/test_openapi.py`.
- Os testes verificam:
  - existência de schema 2xx tipado;
  - presença de campos críticos no response;
  - presença de request schema para ações batch.

## Integração com CI

- O gate roda dentro da suíte backend (`apps/core/tests`) no workflow principal de CI.
- Qualquer regressão nesses contratos falha o check obrigatório de backend e bloqueia merge.

## Expansão futura

- Novos endpoints críticos devem entrar neste documento e no `test_openapi.py`.
- A expansão deve ser incremental para evitar gate excessivamente estrito em áreas fora do escopo.
