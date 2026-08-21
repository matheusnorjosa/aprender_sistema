---
title: Clientes de API (Fetch)
status: canonical
last_verified: 2026-07-24
sources_of_truth:
  - v2/frontend/src/api/config.ts
  - v2/frontend/src/api/auth.ts
  - v2/frontend/src/api/me.ts
  - v2/frontend/src/api/lookup.ts
  - v2/frontend/src/api/ops.ts
  - v2/frontend/src/api/solicitacoes.ts
  - v2/frontend/src/api/availability.ts
  - v2/frontend/src/api/adminDAT.ts
  - v2/frontend/src/api/datModule.ts
  - v2/frontend/src/api/deslocamentos.ts
  - v2/frontend/src/api/gcal.ts
  - v2/frontend/src/constants/timing.ts
  - v2/frontend/package.json
  - v2/frontend/src/api/__tests__/config.test.ts
  - v2/frontend/src/pages/__tests__/NoRawFetchInPages.test.ts
  - docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md
owner: frontend
supersedes:
  - docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md
related:
  - v2/docs/API_REFERENCE.md
  - v2/docs/specs/backend/rbac.spec.md
---

# Clientes de API (Fetch)

## Proposito

A camada `src/api/` concentra todo o acesso HTTP do frontend ao backend DRF. **A migracao axios -> Fetch API nativa esta concluida**: `axios` nao aparece em `v2/frontend/package.json` (nem em `dependencies` nem em `devDependencies`) e o unico residuo no codigo sao dois comentarios de teste legado (`hooks/__tests__/useGoogleIntegration.test.ts:11` e `useSessionMonitor.test.ts:3`, Epic #1039). Todos os clientes consomem um wrapper unico (`config.ts`) construido sobre `fetch()`, eliminando risco de supply chain e ~40KB de bundle (ver ADR-013).

`src/api/` tem hoje **16 arquivos**: o wrapper `config.ts` + **15 clientes tematicos** (auth, me, lookup, solicitacoes, availability, deslocamentos, ops/Controle, adminDAT, datModule, gcal, dashboard, stats, teamMetrics, systemConfig, acoesNotificacao). Eles expoem funcoes tipadas que retornam `Promise<T>` e delegam o transporte, CSRF e tratamento de erro ao `config.ts`. Nenhum componente de `src/pages/` deve chamar `fetch()` diretamente — isso e travado por um teste sentinela (ver "Testes que cobrem"); a regra de ouro e uma funcao de cliente por endpoint.

## Fonte de verdade no codigo

- **Wrapper central**: [`v2/frontend/src/api/config.ts`](../../../frontend/src/api/config.ts) — `API_BASE`, `fetchAPI`, `fetchBlob`, `fetchWithErrorMapping`, `buildUrl` e helpers de CSRF (`getCsrfToken`, `ensureCsrfToken`, `clearCsrfCache`, `initCsrfToken`).
- **Clientes tematicos** (todos importam `./config`): [`auth.ts`](../../../frontend/src/api/auth.ts), [`me.ts`](../../../frontend/src/api/me.ts), [`lookup.ts`](../../../frontend/src/api/lookup.ts), [`solicitacoes.ts`](../../../frontend/src/api/solicitacoes.ts), [`availability.ts`](../../../frontend/src/api/availability.ts), [`deslocamentos.ts`](../../../frontend/src/api/deslocamentos.ts), [`ops.ts`](../../../frontend/src/api/ops.ts), [`adminDAT.ts`](../../../frontend/src/api/adminDAT.ts), [`datModule.ts`](../../../frontend/src/api/datModule.ts), [`gcal.ts`](../../../frontend/src/api/gcal.ts), e ainda `dashboard.ts`, `stats.ts`, `teamMetrics.ts`, `systemConfig.ts`, `acoesNotificacao.ts`.
- **Base URL**: `export const API_BASE = import.meta.env.VITE_API_URL || '/api'` — o default `/api` (same-origin) e o caminho canonico oficial (ver `API_REFERENCE.md`).
- **TTL do cache CSRF**: [`v2/frontend/src/constants/timing.ts`](../../../frontend/src/constants/timing.ts) — `TIMING.CSRF_TOKEN_TTL_MS = 30 min`.

## Contratos e invariantes

- **Base path canonico `/api/`**: clientes passam paths relativos sem o prefixo (ex.: `'/me/events/'`); `fetchAPI`/`fetchBlob` prefixam `API_BASE`. URLs absolutas (`http...`) sao passadas inalteradas. **Proibido** usar o alias deprecated `/api/v1/` em codigo novo (CI bloqueia, #796/#797).
- **Sessao via cookie**: toda chamada usa `credentials: 'include'`. Auth e por sessao Django (nao token Bearer).
- **CSRF obrigatorio em mutacoes**: para `POST/PUT/PATCH/DELETE`, `fetchAPI` injeta header `X-CSRFToken` via `ensureCsrfToken()`. Se nao houver token, lanca `Error('CSRF token ausente...')` antes de enviar.
- **Estrategia de obtencao do CSRF** (`ensureCsrfToken`): (1) le cookie `csrftoken`; (2) usa cache em memoria se valido (TTL 30 min, Issue #258); (3) busca fresco em `GET /api/csrf/` (Issue #135, suporta `CSRF_COOKIE_HTTPONLY=True` retornando o token no body).
- **Retry idempotente de CSRF (1x)**: em `403` cujo body contem `"CSRF"`, limpa o cache e retenta uma unica vez com `forceRefresh` (flag `isRetry` impede loop). Em `401`, invalida o cache CSRF.
- **`401` emite o evento global `auth:expired`** (`config.ts:197-202`, Issue #1376): `fetchAPI` faz `window.dispatchEvent(new Event('auth:expired'))` em **qualquer** `401`. O tratamento e unico e vive em `App.tsx:140-149`, que so age se ja havia sessao (`userRef.current`) — o guard evita loop no load inicial e em rota publica. Telas nao devem tratar `401` isoladamente.
- **Rotacao no login/logout**: `login()` e `logout()` chamam `clearCsrfCache()` porque o Django rotaciona o CSRF token apos login.
- **Forma do erro**: em `!response.ok`, lanca `Error` enriquecido com `.status` e `.response = { status, data }`. A mensagem vem de `error.detail || error.message`. `401/403` sao logados em nivel debug (esperados em load inicial), demais erros em `error`.
- **204 / corpo vazio**: `fetchAPI` retorna `undefined` (nunca chama `response.json()` em `204` ou `content-length: 0`) — contrato esperado por DELETEs.
- **Construcao de query**: `buildUrl(path, params)` omite valores `null`/`undefined`/`''` e escolhe separador `?`/`&` automaticamente.

## API / Interface

Wrapper publico exportado por `config.ts`:

| Funcao | Uso |
|---|---|
| `fetchAPI<T>(url, options?, isRetry?)` | Transporte JSON padrao (GET/POST/...). Retorna `T` ou `undefined` em 204. |
| `fetchBlob(url, options?)` | Downloads binarios (CSV/Excel export). Injeta CSRF em mutacoes; sem parse JSON. |
| `fetchWithErrorMapping<T>(url, options?, errorMap)` | Mapeia status HTTP -> mensagem amigavel por endpoint. |
| `buildUrl(path, params?)` | Monta querystring filtrando valores vazios. |
| `ensureCsrfToken(forceRefresh?)` / `getCsrfToken()` / `clearCsrfCache()` / `initCsrfToken()` | Ciclo de vida do token CSRF. |

`API_BASE` e configuravel por `VITE_API_URL` (default `/api`). Os endpoints concretos consumidos por cada cliente estao em [`v2/docs/API_REFERENCE.md`](../../API_REFERENCE.md). `initCsrfToken()` roda automaticamente no import do modulo, exceto sob Vitest.

## Fluxos principais

1. **GET (leitura, ex. lookup/me)**: cliente monta path com `buildUrl` -> `fetchAPI` prefixa `API_BASE`, envia com `credentials: 'include'` (sem CSRF) -> `response.json()` tipado. Erro 401/403 -> `Error` com `.status`, logado em debug.
2. **Mutacao (POST/PUT/PATCH/DELETE)**: `fetchAPI` chama `ensureCsrfToken()` -> injeta `X-CSRFToken` -> envia. Se backend responder `403 + "CSRF"`: limpa cache, busca token fresco e retenta 1x; se ainda falhar, propaga `Error`.
3. **Login**: `auth.login()` -> `POST /auth/login/` -> sucesso -> `clearCsrfCache()` (Django rotacionou o token) de forma que a proxima mutacao busca token novo.
4. **Bootstrap**: no carregamento do app, `initCsrfToken()` pre-aquece o token para evitar race no primeiro submit.
5. **Download de arquivo**: `fetchBlob('/dat/compras/export/')` retorna `Blob`; o caller cria `URL.createObjectURL`. Falha lanca `Error('Export failed: HTTP <status>')`.

## Decisoes relacionadas (ADRs)

- [ADR-013 — Pin Axios + migracao para Fetch API](../../../../docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md) (axios comprometido em 2026-03-31; CVE-2025-27152; issue #782). **Status: migracao concluida** — esta spec passa a ser o indice vivo do tema.
- Base path `/api/` canonico e corte do `/api/v1/`: `API_REFERENCE.md` (#796/#797).

## Testes que cobrem

- [`v2/frontend/src/api/__tests__/config.test.ts`](../../../frontend/src/api/__tests__/config.test.ts) — `getCsrfToken`, `clearCsrfCache`, `buildUrl`, `fetchAPI` (com MSW). Nota: cookie de teste usa `; Secure` porque jsdom roda em HTTPS (memoria vitest+jsdom Secure cookies).
- [`v2/frontend/src/pages/__tests__/NoRawFetchInPages.test.ts`](../../../frontend/src/pages/__tests__/NoRawFetchInPages.test.ts) — **sentinela #1453**: varre `src/pages/` e falha se alguma pagina chamar `fetch(` cru (mutacao sem `X-CSRFToken` => `403` em producao). Tem um segundo teste que garante que o walk enxerga >20 arquivos, para nao dar falso-verde se a estrutura de pastas mudar. Clientes em `src/api/` estao fora do escopo por serem onde `fetchAPI` e implementado.
- Testes por cliente: `availability.test.ts`, `lookup.test.ts`, `gcal.test.ts`, `adminDAT.test.ts`, `datModule.test.ts`, `systemConfig.test.ts`, `dashboard.test.ts`, `teamMetrics.test.ts`, `ops.normalizeImportResponse.test.ts` (todos em `v2/frontend/src/api/__tests__/`).
- Mocks de rede via MSW (`src/test/mocks/`), sem servidor real.

## Pontos de atencao / dividas conhecidas

- **Sem instancia central legada**: nao existe `src/api.ts` nem `httpClient.ts`; o plano do ADR-013 foi simplificado para um unico `config.ts`. Citar `config.ts` como wrapper, nao `httpClient.ts`.
- **Residuo historico de axios**: somente comentarios em `src/hooks/__tests__/useGoogleIntegration.test.ts` e `useSessionMonitor.test.ts`. Nenhum import real de axios — nao reintroduzir.
- **Retry CSRF detecta por string**: o gatilho do retry e `errorBody.includes('CSRF')`; mudanca na mensagem do Django pode quebrar o retry silenciosamente.
- **`fetchBlob` engole detalhe do erro**: lanca mensagem generica `HTTP <status>` sem parsear o body — pior UX que `fetchAPI` para exports que falham com 400 detalhado.
- **CSRF stale residual**: o TTL de 30 min cobre a maioria dos casos, mas o cookie tem prioridade sobre o cache; se o cookie ficar stale (sem HttpOnly) o retry-1x e a unica rede de seguranca.
- **`deslocamentos.ts` sem teste de cliente**: e o unico cliente com pagina critica (`/solicitacoes/deslocamentos`) e sem arquivo em `src/api/__tests__/`.
