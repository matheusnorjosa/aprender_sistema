---
title: Páginas (React)
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/frontend/src/App.tsx
  - v2/frontend/src/components/AppRoutes.tsx
  - v2/frontend/src/components/AppSidebar.tsx
  - v2/frontend/src/hooks/usePermissions.ts
  - v2/frontend/src/hooks/useCanAccess.ts
  - v2/frontend/src/pages
  - v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx
  - v2/frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx
  - v2/frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx
owner: frontend
supersedes: []
related:
  - ../INDEX_SDD.md
  - ./README.md
  - ../../RBAC_NAMING.md
  - ../../rbac_authorization_matrix.md
  - ../../API_REFERENCE.md
---

# Páginas (React)

## Propósito

O frontend React (Vite 7 + Ant Design 5 + Tailwind) entrega a SPA do AS v2. Toda a árvore de páginas é registrada em [`AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx), montada dentro do shell de layout (sidebar + header) por [`App.tsx`](../../../frontend/src/App.tsx). Cada página é **lazy-loaded** (`React.lazy` + `Suspense`) para code-splitting; o gate de acesso é resolvido inline na rota a partir de flags derivadas das permissões do usuário.

Esta spec é o **índice canônico do inventário de páginas**: domínio, rota e guard (capability) de cada página. O detalhe de cada capability (quem pode o quê e por quê) vive na [matriz de autorização RBAC](../../rbac_authorization_matrix.md); a convenção de nomes de permission em [`RBAC_NAMING.md`](../../RBAC_NAMING.md). O contrato dos endpoints consumidos pelas páginas está em [`API_REFERENCE.md`](../../API_REFERENCE.md).

## Fonte de verdade no código

- [`v2/frontend/src/App.tsx`](../../../frontend/src/App.tsx) — shell: carrega `getMe()` + `getMyPolicies()`, decide login vs app, monta sidebar/header/`<AppRoutes>`. `LoginPage` é a única página lazy fora de `AppRoutes`.
- [`v2/frontend/src/components/AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx) — **registro único de rotas**. 39 páginas lazy + 50 `<Route>` (inclui 7 redirects de URLs legadas). Cada rota guardada usa o padrão `element={guard ? <Page /> : <Forbidden />}`.
- [`v2/frontend/src/hooks/usePermissions.ts`](../../../frontend/src/hooks/usePermissions.ts) — deriva flags `canControle`/`canDAT`/`canDashboard*`/`canDisponibilidade`/… de `setores`+`funcoes`+`is_superuser` do payload de `/api/me/`.
- [`v2/frontend/src/hooks/useCanAccess.ts`](../../../frontend/src/hooks/useCanAccess.ts) — camada de tradução semântica: converte `policies` públicas (de `GET /api/me/policies/`) em flags como `canAccessApprovals`, `canCreateSolicitation`, `canViewComprasDashboard`.
- [`v2/frontend/src/components/AppSidebar.tsx`](../../../frontend/src/components/AppSidebar.tsx) — menu lateral; usa as mesmas flags para esconder itens (UX, não é o gate autoritativo).
- Diretório [`v2/frontend/src/pages/`](../../../frontend/src/pages) — **14 diretórios de domínio** (AdminDAT, Aprovacoes, Auth, Controle, DAT, DATModule, Dashboards, Deslocamentos, Disponibilidade, Home, MapaBrasil, MeusEventos, PreAgenda, Solicitacoes) + `__tests__`.

> **Correção de mito:** o número real é **40 páginas lazy-loaded** (39 em `AppRoutes` + `LoginPage` em `App.tsx`), não "45+". `Solicitacoes.tsx` e `Disponibilidade.tsx` na raiz de `pages/` ainda existem; `pages/Disponibilidade` (dir) é o que está roteado em `/solicitacoes/bloqueios`.

## Contratos e invariantes

- **Gate de rota é autoritativo, menu é só UX.** Esconder o item no `AppSidebar` não basta: a rota em `AppRoutes` **deve** renderizar `<Forbidden />` quando o guard é falso. Deep-link/bookmark/redirect 3rd-party não pode abrir página proibida (provado pelo teste de acesso por perfil).
- **`<Forbidden />` não vaza recurso (OWASP).** Mensagem genérica fixa ("Recurso indisponível"); nunca revelar a policy/capability exigida nem a existência do recurso.
- **Frontend não é a fronteira de segurança.** O guard de rota é defesa de UX; a autorização real é do backend (`permission_classes=[HasPerm("codename")]`). Toda página guardada tem endpoint correspondente protegido — o frontend nunca "abre" dado que o backend negaria.
- **RBAC idiomático.** Decisões de acesso derivam de `policies`/flags computadas de `setores`+`funcoes`+`is_superuser`; nunca de checagem direta de nome de grupo (banido por `scripts/rbac_lint.py` no backend; o equivalente no FE é não hardcodar nomes de grupo nas páginas).
- **`is_superuser` é escape hatch.** As flags `canControle`/`canDAT`/`canDashboard*` já embutem `is_superuser`; superuser passa em tudo. Páginas não devem ramificar por `is_superuser` para regra de negócio — só para widgets admin/debug.
- **Aprovações = policy exclusiva.** `/solicitacoes/aprovacoes` depende **somente** da policy pública `access_solicitation_approvals` (composite Gerente∩Superintendência OU Assistente Administrativo∩Controle). O legacy `can_approve_super` foi removido do contrato do FE (PR 10 hardening RBAC).
- **Redirects preservam deep-links.** URLs legadas (`/aprovacoes`, `/disponibilidade`, `/bloqueios`, `/deslocamentos`, `/meus-eventos`, `/dat/importacao`) redirecionam com `<Navigate replace>` para a rota canônica sob `/solicitacoes/*` ou `/dat/importacoes`.

## API / Interface

Inventário por domínio (rota → componente → guard). Detalhe da capability na [matriz RBAC](../../rbac_authorization_matrix.md).

### Home

| Rota | Página | Guard |
|---|---|---|
| `/`, `/home` | `Home/HomePage` | autenticado |

### Auth

| Rota | Página | Guard |
|---|---|---|
| (sem rota — render condicional em `App.tsx`) | `Auth/LoginPage` | anônimo |

### Solicitações (agrupadas sob `/solicitacoes/*`)

| Rota | Página | Guard |
|---|---|---|
| `/solicitacoes/minhas` | `Solicitacoes/MySolicitacoesPage` | `access.canCreateSolicitation` |
| `/solicitacoes/nova` | `Solicitacoes/NewSolicitacaoWizard` | `access.canCreateSolicitation` |
| `/solicitacoes/:id/editar` | `Solicitacoes/EditSolicitacaoPage` | autenticado |
| `/solicitacoes/meus-eventos` | `MeusEventos/MeusEventosPage` | autenticado |

### Aprovações

| Rota | Página | Guard |
|---|---|---|
| `/solicitacoes/aprovacoes` | `Aprovacoes/ApprovalsPage` | policy `access_solicitation_approvals` |

### Disponibilidade

| Rota | Página | Guard |
|---|---|---|
| `/solicitacoes/disponibilidade` | `Disponibilidade/MonthlyPage` | policy `view_all_availability` OU `canDisponibilidade` |
| `/solicitacoes/bloqueios` | `Disponibilidade` (blocks) | `access.canAccessBlocks` (inclui Formador, escopo próprio) |
| `/solicitacoes/deslocamentos` | `Deslocamentos/DeslocamentosPage` | `view_all_availability` OU `canControle`/`canCoordenador`/`canDAT` |

### Controle

| Rota | Página | Guard |
|---|---|---|
| `/controle` | `Controle/ControlePage` | `canControle` |
| `/controle/acoes` | `DATModule/AcoesPage` | `canControle` |
| `/controle/compras`, `/compras-materiais` | `DATModule/ComprasPage` | `canControle` OU `canDAT` |
| `/controle/coordenadores` | `DATModule/CoordenadoresPage` | `canControle` |
| `/controle/formacoes` | `DATModule/FormacoesPage` | `canControle` |
| `/controle/plano-formacoes` | `DATModule/PlanoFormacoesPage` | `canControle` |
| `/controle/pre-agenda`, `/pre-agenda` | `PreAgenda/PreAgendaPage` | `canControle` |
| `/acoes-notificacao`, `/acoes-notificacao/timeline`, `/notificacoes-internas` | `Controle/AcoesNotificacaoPage` / `AcoesTimelinePage` / `NotificacoesInternasPage` | `canAcoesInternas` |

### DAT / AdminDAT

| Rota | Página | Guard |
|---|---|---|
| `/dat/admin` (+ `/usuarios`, `/municipios`, `/projetos`, `/grupos`, `/setores`, `/funcoes`, `/gerencias`, `/produtos`, `/configuracoes`, `/colecoes`, `/equipe-gerencia`) | `AdminDAT/*` | `canDAT` |
| `/dat/cadastros` | `DATModule/CadastrosPage` | `canDAT` |
| `/dat/importacoes` | `DAT/ImportacoesPage` | `canDAT` |
| `/dat/registros` | `DATModule/DATRegistrosPage` | `canDAT` |
| `/dat/compras-materiais` | `DATModule/ComprasPage` | `canControle` OU `canDAT` |
| `/dat/coordenadores` | `DATModule/CoordenadoresPage` | `canControle` |

### Dashboards

| Rota | Página | Guard |
|---|---|---|
| `/dashboards` | `Dashboards/DashboardsPage` | `canDashboardOverview` (Diretoria/superuser) |
| `/dashboards/compras` | `Dashboards/ComprasDashboardPage` | `access.canViewComprasDashboard` (policy `view_compras_dashboard`) |
| `/dashboards/equipe` | `Dashboards/EquipeDashboardPage` | `canDashboardEquipe` (Diretoria/DAT/superuser) |
| `/dashboards/gcal` | `Dashboards/GCalDashboardPage` | `canDashboardGcal` (Diretoria/DAT/Controle/superuser) |
| `/mapa-brasil` | `MapaBrasil/MapaBrasilPage` | `canMapaBrasil` (Diretoria/DAT/superuser) |

## Fluxos principais

1. **Boot / autenticação** — `App.tsx` chama `getMe()`; se anônimo (`isAuthError`), renderiza `LoginPage`. Autenticado: busca `getMyPolicies()` (sequencial, evita 403 espúrio pré-login), monta sidebar/header/rotas. Loading → `FullscreenLoader`.
2. **Navegação para página guardada** — `AppRoutes` resolve `permissions` (`usePermissions`) + `access` (`useCanAccess`); se o guard é true, monta a página lazy (fallback `PageLoader` durante o chunk); se false, monta `<Forbidden />`.
3. **URL legada** — `<Navigate replace>` redireciona para a rota canônica antes de qualquer render de página, preservando histórico/bookmark.
4. **Erro de runtime na página** — `ErrorBoundary` (raiz, `App.tsx`) captura; falhas de auth em chamadas de API são tratadas por `isAuthError` e degradam para estado anônimo/`[]`.

## Decisões relacionadas (ADRs)

- [Matriz de autorização RBAC](../../rbac_authorization_matrix.md) — §3 dashboards, decisões D7/D8/D9 (acesso a dashboards e Grade Mensal), composite Setor×Função das aprovações.
- [`RBAC_NAMING.md`](../../RBAC_NAMING.md) — convenção de codenames/policies públicas.
- Issue #927 — decomposição de `App.tsx` (extração de hooks/`AppRoutes`/`AppSidebar`).
- Epic 3 (#1227/#1228) — agrupamento sob `/solicitacoes/*` + camada `useCanAccess`. PR-C DAT Imports (#1227-relacionado, 2026-04-29) — unificação de imports em `/dat/importacoes`.

## Testes que cobrem

- [`v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx) — matriz 10 atores canônicos × 12 rotas críticas; prova que deep-link proibido renderiza `<Forbidden />` com mensagem genérica.
- [`v2/frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx) — gate e redirect das rotas DAT (`/dat/importacao` → `/dat/importacoes`).
- [`v2/frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx`](../../../frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx) — remoção das rotas/imports legados de DAT.
- Testes de página individuais: `NewSolicitacaoWizard.test.tsx`, `MeusEventosPage.test.tsx`, `ImportacoesPage.test.tsx`, `UsuariosPage.cpf.test.tsx`.

## Pontos de atenção / dívidas conhecidas

- **Guard duplicado FE/BE.** As flags de guard são reimplementação client-side da matriz RBAC do backend; divergência silenciosa é possível. A matriz viva no backend é o SSOT — qualquer página nova deve casar com a policy/permission do endpoint que consome.
- **`Forbidden` inline vs `RequirePolicy`.** Há dois mecanismos de negação (o `Forbidden` inline em `AppRoutes` e o `<RequirePolicy>`); a unificação está pendente (comentário no próprio `AppRoutes`).
- **`DATPage` (`pages/DAT/DATPage.tsx`) órfã.** Não está mais roteada (substituída por `ImportacoesPage`); remoção definitiva ficou para "PR-D" (ver comentário no `AppRoutes`).
- **Páginas raiz legadas.** `pages/Solicitacoes.tsx` e `pages/Disponibilidade.tsx` (arquivos soltos na raiz de `pages/`) coexistem com os diretórios homônimos roteados — risco de confusão; conferir o import do `AppRoutes` antes de editar.
- **Logout via `window.location.reload()`.** Tech-debt assumido (#927) — sem auth store centralizado, logout força reload em vez de limpeza de estado.
- **README de specs frontend desatualizado.** [`./README.md`](./README.md) ainda diz "6/14 documentadas" e "45+ pages"; esta spec corrige a contagem para 14 dirs / 40 páginas lazy.
