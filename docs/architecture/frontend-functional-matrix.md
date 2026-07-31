# Frontend Functional Matrix (Critical)

Matriz funcional crítica versionada para regressão frontend↔backend.

Fonte executável:
- `v2/frontend/e2e/checklist/functional-contract.matrix.ts`

Gate automatizado:
- `v2/frontend/e2e/checklist/functional-contract.spec.ts`
- Workflow: `frontend-ci` job `[required] checklist tests (meta, a11y, security)`

## Casos críticos atuais

Espelho de `FUNCTIONAL_CRITICAL_MATRIX` (`functional-contract.matrix.ts:29-76`). Em caso de
divergência, o arquivo `.ts` é a fonte — este documento é o resumo legível.

| ID | Rota | Endpoint(s) | Texto crítico asserido |
|---|---|---|---|
| `controle-compras-core-compra` | `/controle/compras` | `/api/dat/compras-materiais/` (`:34`) | `Produto` e `Total da Página` na `table` (`:37-47`) |
| `dashboard-compras-pendencias` | `/dashboards/compras` | `/api/dat/compras-materiais/dashboard/`, `/api/dat/compras-materiais/pendencias/` (`:54`) | `Municípios pendentes de agendamento`, `Matrizopolis`, `KIT MATRIX CONTRACT` (`:56-73`) |

> **Atenção ao nome do primeiro caso.** O id diz `core-compra`, mas o endpoint exercitado é o
> de `core_dat_compra` — a rota `/controle/compras` renderiza `DATModule/ComprasPage`
> (`v2/frontend/src/components/AppRoutes.tsx:119`), o mesmo componente de
> `/dat/compras-materiais`. Quem consome `/api/controle/compras/` (`core_compra`) é a rota
> `/controle` via `listCompras` (`v2/frontend/src/api/ops.ts:369-373`, usado em
> `pages/Controle/ControlePage.tsx:11`). Nenhum caso da matriz cobre esse endpoint hoje.

## Estratégia

- Backend real em Docker para checklist funcional.
- Seed determinístico antes dos testes (`seed_frontend_contract_data`).
- Falha com rastreabilidade: rota + campo + endpoint.

## Evolução

Adicionar novos casos por rota crítica com a mesma estrutura:
1. endpoint real usado pela tela
2. campo renderizado observado pelo usuário
3. dado seedado determinístico para assertiva estável
