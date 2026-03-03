# OpenAPI Contract Gate (Frontend Critical Endpoints)

Esta política define o conjunto mínimo de endpoints críticos cujo contrato OpenAPI é bloqueante no CI.

## Objetivo

Evitar regressão silenciosa de schema (`No response body` ou respostas genéricas) nos endpoints críticos usados pelo frontend.

## Endpoints no gate mínimo

- Dashboard/GCal:
  - `GET /api/dashboard/overview/`
  - `GET /api/gcal/status-summary/`
  - `GET /api/gcal/dashboard/metrics/`
  - `GET /api/gcal/dashboard/events/`
  - `GET /api/gcal/dashboard/insights/success-rate/`
  - `GET /api/gcal/dashboard/insights/top/`
  - `GET /api/gcal/dashboard/events/{id}/detail/`
  - `POST /api/gcal/dashboard/batch/reapply/`
  - `POST /api/gcal/dashboard/batch/resync/`
- Home/Disponibilidade:
  - `GET /api/stats/home/`
  - `GET /api/availability/monthly/`
- Options (`/api/options/*`):
  - `GET /api/options/municipios/`
  - `GET /api/options/projetos/`
  - `GET /api/options/tipos-evento/`
  - `GET /api/options/usuarios/`
  - `GET /api/options/produtos/`
  - `GET /api/options/coordenadores/`
  - `GET /api/options/areas/`
  - `GET /api/options/formadores-do-setor/`
- Import operations (frontend):
  - `POST /api/controle/import-compras/`
  - `POST /api/controle/import-acoes/`
  - `POST /api/dat/import-cadastros/`
  - `POST /api/disponibilidade/import-bloqueios/`
  - `POST /api/deslocamentos/import/`
  - `POST /api/solicitacoes/import/`
  - `POST /api/usuarios/import/`
  - `POST /api/municipios/import/`
  - `POST /api/colecoes/import/`
  - `POST /api/equipe-gerencia/import/`
  - `POST /api/produtos/import/`

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
