---
title: Hooks de RBAC e Guards (Frontend)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/frontend/src/hooks/usePermissions.ts
  - v2/frontend/src/hooks/useCanAccess.ts
  - v2/frontend/src/hooks/useGoogleGuard.tsx
  - v2/frontend/src/hooks/useGoogleIntegration.ts
  - v2/frontend/src/api/me.ts
  - v2/frontend/src/api/auth.ts
  - v2/frontend/src/types/usuario.ts
  - v2/frontend/src/App.tsx
  - v2/frontend/src/components/AppRoutes.tsx
  - v2/frontend/src/hooks/__tests__/usePermissions.test.js
  - v2/frontend/src/hooks/__tests__/useCanAccess.test.ts
  - v2/frontend/src/hooks/__tests__/rbac_matrix.test.ts
  - v2/backend/apps/core/views/me.py
  - v2/backend/apps/core/rbac/policies.py
owner: frontend
supersedes: []
related:
  - v2/docs/RBAC_NAMING.md
  - v2/docs/rbac_authorization_matrix.md
  - v2/docs/API_REFERENCE.md
---

# Hooks de RBAC e Guards (Frontend)

## Proposito

Esta camada decide **o que o usuario ve e pode acionar** na SPA React, sem nunca virar fonte de autoridade: a decisao final continua no backend (`permission_classes=[HasPerm("codename")]`). O frontend le o estado de identidade/autorizacao do usuario autenticado a partir de `GET /api/me/` (perfil + setores/funcoes) e `GET /api/me/policies/` (capabilities publicas), traduz isso em flags semanticas e usa essas flags para esconder/exibir menu, guardar rotas e desativar acoes. O objetivo e UX honesta (nao oferecer o que sera negado), nao seguranca: qualquer flag pode ser burlada no cliente e o backend revalida.

Ha tambem um guard transversal de integracao Google (OAuth): antes de operacoes que tocam o Google Calendar, o frontend confere se a conta corporativa esta conectada e, se nao, conduz o usuario ao fluxo OAuth em vez de deixar a chamada falhar com `403 google_not_connected`.

## Fonte de verdade no codigo

- **Identidade e capabilities legacy**: [`v2/frontend/src/hooks/usePermissions.ts`](../../../frontend/src/hooks/usePermissions.ts) — funcao pura `computePermissions(user)` + hook memoizado `usePermissions(user)`. Computa flags de role (`isCoordenador`, `isFormador`, `isGerente`), setor (`inSuperintendencia`, `inDAT`, `inControle`, `inDiretoria`, `inGerencia`) e capability derivada (`canControle`, `canDAT`, `canDisponibilidade`, `canDashboard*`, `canSeeAllSectors`, etc.) a partir de `user.setores` / `user.funcoes` / `user.is_superuser`.
- **Capability Policy Layer**: [`v2/frontend/src/hooks/useCanAccess.ts`](../../../frontend/src/hooks/useCanAccess.ts) — funcao pura `computeAccess(policies, legacy)` + hook `useCanAccess`. Traduz as `PUBLIC_POLICY_KEYS` recebidas em `policies` (mais flags legacy de fallback) nas **derived flags** que os componentes consomem: `canAccessApprovals`, `canAccessBlocks`, `canCreateSolicitation`, `canViewComprasDashboard`, e o predicado generico `can(key)`.
- **Guard Google OAuth**: [`v2/frontend/src/hooks/useGoogleGuard.tsx`](../../../frontend/src/hooks/useGoogleGuard.tsx) — `requireGoogleConnection(action)`, `handleGoogleError(error)`, `isConnected`.
- **Status da integracao Google**: [`v2/frontend/src/hooks/useGoogleIntegration.ts`](../../../frontend/src/hooks/useGoogleIntegration.ts) — `fetchStatus()` le `GET /api/integrations/google/status/`; expoe `status.connected` consumido pelo guard.
- **Clientes HTTP**: [`v2/frontend/src/api/auth.ts`](../../../frontend/src/api/auth.ts) (`checkAuth()` le `/api/me/`) e [`v2/frontend/src/api/me.ts`](../../../frontend/src/api/me.ts) (`getMyPolicies()` le `/api/me/policies/`).
- **Contrato de tipo + runtime guard**: [`v2/frontend/src/types/usuario.ts`](../../../frontend/src/types/usuario.ts) — interface `CurrentUser` e `assertCurrentUserPayload()` (lanca `Invalid /api/me payload shape` se o payload divergir).
- **Wiring / composicao**: [`v2/frontend/src/App.tsx`](../../../frontend/src/App.tsx) carrega `user` e `policies` e injeta em [`v2/frontend/src/components/AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx), que aplica os guards por rota.
- **Backend (contraparte autoritativa)**: [`v2/backend/apps/core/views/me.py`](../../../backend/apps/core/views/me.py) (`/api/me/policies/`) e [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) (`PUBLIC_POLICY_KEYS`, `resolve_public_policies`).

## Contratos e invariantes

- **O frontend NUNCA e autoridade.** Toda flag e cosmetica; o backend revalida via `HasPerm`/Policy. Esconder um botao nao substitui o gate de endpoint.
- **SSOT de capability esta no backend.** O frontend reflete `PUBLIC_POLICY_KEYS` recebidas em `/api/me/policies/`; nunca infere policy a partir de nome de grupo/setor para decisao de acesso de capability. Flags de setor/funcao em `usePermissions` sao legacy/fallback e estao sendo migradas para policies (ver `useCanAccess`).
- **Estabilidade do contrato de policy keys.** As keys de `PUBLIC_POLICY_KEYS` sao imutaveis apos release: renomear = breaking change; adicionar = compativel. Remover exige periodo de depreciacao de 2 releases (ver `v2/docs/RBAC_NAMING.md` §9). Os fixtures de `rbac_matrix.test.ts` e o snapshot do backend (`PUBLIC_POLICY_KEYS`) precisam permanecer simetricos.
- **Anonymous nao chama `/me/policies/`.** `App.tsx` so busca policies **depois** de `getMe()` retornar com sucesso, evitando `403`/`401` espurio pre-login. Falha em policies degrada para `[]` (fail-closed: nenhuma capability publica).
- **`policies = []` e ambiguo por design**: significa "ainda carregando" OU "anonymous". A distincao e feita pela flag `loading` em `App.tsx`, nao pelo array vazio.
- **Superuser recebe todas as `PUBLIC_POLICY_KEYS`** via `/me/policies/`; `isAdmin` (de `user.is_superuser`) e escape hatch admin-only — usar so para widgets de debug/bypass, nunca para regra de negocio normal.
- **Semantica das policies e OR.** Usuario obtem a policy se qualquer capability que a satisfaz estiver presente. O conjunto de capabilities que satisfaz uma policy pode mudar sem breaking.
- **Formador owns own**: `canAccessBlocks` inclui Formador via flag legacy (`canBloqueios`) porque o escopo do proprio bloqueio (RD-02/RD-03) e garantido pelo queryset do backend, nao por policy publica.
- **Guard Google (PA-06, controle explicito)**: nenhuma operacao GCal e disparada com conta desconectada. `requireGoogleConnection` retorna `false` e abre modal apenas quando `googleStatus` esta carregado E `connected === false`; com `googleStatus === null` (status ainda desconhecido) ele **permite prosseguir** e delega a deteccao ao backend via `handleGoogleError` (que trata `403` com `code === 'google_not_connected'`). O redirect OAuth sempre carrega `return_to` para voltar a pagina de origem.

## API / Interface

Endpoints backend consumidos (contrato detalhado em `v2/docs/API_REFERENCE.md` e `v2/docs/RBAC_NAMING.md`):

- `GET /api/me/` — perfil do usuario autenticado (`CurrentUser`: `setores[]`, `funcoes[]`, `is_superuser`, `is_superintendencia`, `can_approve_super`, `permissions[]`, ...). `401` se anonimo.
- `GET /api/me/policies/` — array ordenado de strings (subset de `PUBLIC_POLICY_KEYS`); `401` se anonimo; superuser recebe todas. Nunca expoe codenames brutos de capability.
- `GET /api/integrations/google/status/` — `{ connected, googleEmail, tokenExpiry, expiresInDays, isExpired }`.
- `GET /api/oauth/google/start/?return_to=<path>` — inicia o fluxo OAuth (redirect do browser, nao XHR).

Interface publica dos hooks:

- `usePermissions(user: CurrentUser | null): Permissions` — todas as flags `false` quando `user === null`.
- `useCanAccess(policies: readonly string[], legacy?: LegacyAccessFlags): AccessState` — expoe `can(key)` + derived flags.
- `useGoogleGuard({ googleStatus, returnTo }): { requireGoogleConnection, handleGoogleError, isConnected }`.
- `useGoogleIntegration(): { status, loading, error, fetchStatus, disconnect }`.

## Fluxos principais

**Bootstrap de autorizacao (1x por mount, sem polling de RBAC):**

1. `App.tsx` chama `getMe()` (= `/api/me/`); o payload passa por `assertCurrentUserPayload` (em `api/availability.ts`/`auth.ts`). Sucesso => `setUser`.
2. So entao chama `getMyPolicies()` (= `/api/me/policies/`); sucesso => `setPolicies`. Erro nao-auth => log `warn` + degrada para `[]`.
3. `usePermissions(user)` computa flags legacy; `AppRoutes` chama `useCanAccess(policies, { canBloqueios, canCoordenador, canDashboardCompras })` para derivar flags.
4. Menu/rotas renderizam condicionalmente. Rota negada renderiza `<Forbidden />` (mensagem generica, OWASP — nao revela recurso/permissao necessaria).

**Atualizacao de RBAC**: nao ha polling das capabilities. Mudancas de permissao so refletem apos reload/relogin (logout faz `window.location.reload()`). Os pollings existentes em `App.tsx` (`useGCalAlertsPolling`, `useUnreadNotificationsPolling`) sao de dados operacionais, gated pelas flags de `usePermissions`, e nao re-buscam policies.

**Guard Google (caminho feliz + erro):**

1. Pagina (ex: PreAgenda) obtem `googleStatus` via `useGoogleIntegration` e instancia `useGoogleGuard({ googleStatus, returnTo })`.
2. Antes da acao: `if (!requireGoogleConnection('publicar eventos')) return;` — se desconectado, abre `Modal.confirm` e (no `onOk`) redireciona para `/api/oauth/google/start/?return_to=...`.
3. No `catch` da chamada: `if (handleGoogleError(error)) return;` — trata `403 google_not_connected` reabrindo o modal; demais erros seguem o fluxo normal de mensagem.

## Decisoes relacionadas (ADRs)

- `v2/docs/RBAC_NAMING.md` §9 — Policy Resolution Rules, vocabulario canonico, `PUBLIC_POLICY_KEYS`, stability rules e contrato de `GET /api/me/policies/` (Epics 4.1–4.4).
- `v2/docs/rbac_authorization_matrix.md` — matriz canonica modulo×papel/capability×grupo (decisoes D7–D9 referenciadas inline em `usePermissions.ts`; D10–D17 §6 Admin-driven Group×Cap).
- Epic 3 / Issue #1228 — Capability Policy Layer no frontend (`useCanAccess`).
- PR 3 / PR 10 hardening RBAC (2026-04-29/30) — `access_solicitation_approvals` como fonte exclusiva de `canAccessApprovals` (fallback `can_approve_super` removido do contrato do hook).

## Testes que cobrem

- [`v2/frontend/src/hooks/__tests__/usePermissions.test.js`](../../../frontend/src/hooks/__tests__/usePermissions.test.js) — `computePermissions` por ator (null, superuser, Coordenador/Apoio, DAT, Controle, Gerente, visibilidade de dashboards, `canDisponibilidade`).
- [`v2/frontend/src/hooks/__tests__/useCanAccess.test.ts`](../../../frontend/src/hooks/__tests__/useCanAccess.test.ts) — `computeAccess` (match exato de policy, fallback legacy, derived flags).
- [`v2/frontend/src/hooks/__tests__/rbac_matrix.test.ts`](../../../frontend/src/hooks/__tests__/rbac_matrix.test.ts) — **matriz viva** parametrizada por ator: garante simetria entre policies do backend e derived flags do frontend; falha em drift.
- [`v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx) — guards de rota por perfil.
- Contraparte backend: `v2/backend/apps/core/tests/test_me_policies.py` e `test_rbac_policies_contract.py` provam o contrato de `/api/me/policies/`.

## Pontos de atencao / dividas conhecidas

- **`useGoogleGuard.tsx` sem teste unitario** — nao ha `useGoogleGuard.test.*` (apenas `useGoogleIntegration.test.js`). O contrato critico de "permitir prosseguir quando `googleStatus === null`" + tratamento de `403 google_not_connected` nao tem cobertura direta. GAP a fechar.
- **TOCTOU benigno no guard Google**: o status pode estar stale entre `fetchStatus` e a acao; o `handleGoogleError` no `catch` e a rede de seguranca (backend e a autoridade). Por design, mas significa que a UX pode mostrar o modal so apos a tentativa.
- **Sem invalidacao de RBAC em runtime**: mudanca de setor/funcao/grupo de um usuario logado so reflete apos reload/relogin (nao ha refetch de `/me/policies/`). Aceitavel para o tenant atual; revisitar se surgir admin que altere permissoes em tempo real.
- **Camada legacy ainda em migracao**: varias derived flags de `useCanAccess` dependem de flags legacy de `usePermissions` (setor/funcao) porque ainda nao ha policy publica equivalente (`canCreateSolicitation`, parte de `canAccessBlocks`). Cada migracao = trocar 1 `OR` em `useCanAccess` + atualizar a matriz viva e o seed do backend em sincronia.
- **`policies = []` ambiguo**: consumidores fora de `App.tsx` que recebam `policies` precisam tratar `loading` separadamente para nao confundir "carregando" com "sem acesso".
