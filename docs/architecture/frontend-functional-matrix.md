# Frontend Functional Matrix (Critical)

Matriz funcional crítica versionada para regressão frontend↔backend.

Fonte executável:
- `v2/frontend/e2e/checklist/functional-contract.matrix.ts`

Gate automatizado:
- `v2/frontend/e2e/checklist/functional-contract.spec.ts`
- Workflow: `frontend-ci` job `[required] checklist tests (meta, a11y, security)`

## Casos críticos atuais

| ID | Rota | Endpoint(s) | Campo crítico validado |
|---|---|---|---|
| `controle-compras-core-compra` | `/controle/compras` | `/api/controle/compras/` | tabela exibe código e município seedados |
| `dashboard-compras-pendencias` | `/dashboards/compras` | `/api/dat/compras-materiais/dashboard/`, `/api/dat/compras-materiais/pendencias/` | seção de pendências e item de produto pendente |

## Estratégia

- Backend real em Docker para checklist funcional.
- Seed determinístico antes dos testes (`seed_frontend_contract_data`).
- Falha com rastreabilidade: rota + campo + endpoint.

## Evolução

Adicionar novos casos por rota crítica com a mesma estrutura:
1. endpoint real usado pela tela
2. campo renderizado observado pelo usuário
3. dado seedado determinístico para assertiva estável
