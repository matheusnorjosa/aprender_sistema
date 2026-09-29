---
title: Páginas (React)
status: canonical
last_verified: 2026-09-11
verified_at_commit: 0dd1dcb630fdc1cf9b2b488121553e89488dde3c
sources_of_truth:
  - v2/frontend/src/App.tsx
  - v2/frontend/src/components/AppRoutes.tsx
  - v2/frontend/src/components/access/RequirePolicy.tsx
  - v2/frontend/src/components/AppSidebar.tsx
  - v2/frontend/src/hooks/usePermissions.ts
  - v2/frontend/src/hooks/useCanAccess.ts
  - v2/frontend/src/hooks/useCapabilities.ts
  - v2/frontend/src/pages
  - v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx
  - v2/frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx
  - v2/frontend/src/components/access/__tests__/RequirePolicy.test.tsx
  - v2/frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx
  - v2/frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts
  - v2/frontend/e2e/checklist/sem-rolagem-horizontal.desktop.spec.ts
  - v2/frontend/e2e/checklist/sem-rolagem-horizontal.medicao.ts
  - v2/frontend/e2e/checklist/sem-rolagem-horizontal.rotas.ts
  - v2/frontend/src/components/__tests__/AppRoutes.semRolagemHorizontal.test.ts
  - v2/frontend/src/components/__tests__/semRolagemHorizontal.pendentes.test.ts
  - v2/frontend/eslint.tabela-antd-allowlist.js
owner: frontend
supersedes: []
related:
  - ../INDEX_SDD.md
  - ./README.md
  - ./hooks-rbac.spec.md
  - ../../RBAC_NAMING.md
  - ../../rbac_authorization_matrix.md
  - ../../API_REFERENCE.md
  - ../../audits/ACHADOS_REAIS.md
---

# Páginas (React)

## Propósito

O frontend React (Vite 7 + Ant Design 5 + Tailwind) entrega a SPA do AS v2. Toda a árvore de páginas é registrada em [`AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx), montada dentro do shell de layout (sidebar + header) por [`App.tsx`](../../../frontend/src/App.tsx). Cada página é **lazy-loaded** (`React.lazy` + `Suspense`) para code-splitting; desde o #1271 o gate de acesso de **toda** rota guardada é o componente [`<RequirePolicy>`](../../../frontend/src/components/access/RequirePolicy.tsx), em um de dois modos: `policy="<key>" policies={policies}` (policy pública) ou `allow={<expressão booleana>}` (composite sem policy única).

Esta spec é o **índice canônico do inventário de páginas**: domínio, rota e guard de cada página. O detalhe de cada capability (quem pode o quê e por quê) vive na [matriz de autorização RBAC](../../rbac_authorization_matrix.md); a convenção de nomes de permission em [`RBAC_NAMING.md`](../../RBAC_NAMING.md); a camada de hooks que produz as flags em [`hooks-rbac.spec.md`](./hooks-rbac.spec.md). O contrato dos endpoints consumidos pelas páginas está em [`API_REFERENCE.md`](../../API_REFERENCE.md).

## Fonte de verdade no código

- [`v2/frontend/src/App.tsx`](../../../frontend/src/App.tsx) — shell: carrega `getMe()` + `getMyPolicies()`, decide login vs app, monta sidebar/header/`<AppRoutes>`. `LoginPage` é a única página lazy fora de `AppRoutes` (`App.tsx`, const `LoginPage`); sem `user`, o app renderiza só a `LoginPage` (`App.tsx`, `AppContent` → ramo `if (!user)`) — é daí que vem o guard "autenticado" das rotas sem gate próprio.
- [`v2/frontend/src/components/AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx) — **registro único de rotas**. **42 páginas lazy** (`AppRoutes.tsx`) e **53 `<Route>`**, dos quais **6 são redirects** de URLs legadas (`<Navigate replace>`).
- [`v2/frontend/src/components/access/RequirePolicy.tsx`](../../../frontend/src/components/access/RequirePolicy.tsx) — guard único. Decisão no componente `RequirePolicy` (local `granted`): `allow` (boolean explícito) tem precedência; senão `policies.includes(policy)`; **sem `policy` nem `allow` → fail-secure** (`granted = false`). Fallback padrão é `DefaultForbidden`.
- [`v2/frontend/src/hooks/usePermissions.ts`](../../../frontend/src/hooks/usePermissions.ts) — flags legacy (`canControle`/`canDAT`/`canDisponibilidade`/…) derivadas de `setores`+`funcoes`+`is_superuser`. **Marcado `@deprecated` (#1269)** no próprio arquivo; ainda é o que alimenta os guards `allow=` dos composites.
- [`v2/frontend/src/hooks/useCanAccess.ts`](../../../frontend/src/hooks/useCanAccess.ts) — em `AppRoutes` sobrou **só** para os composites de disponibilidade/bloqueios: é instanciado com uma única flag legacy, `canBloqueios` (`AppRoutes.tsx`, chamada `useCanAccess`).
- [`v2/frontend/src/components/AppSidebar.tsx`](../../../frontend/src/components/AppSidebar.tsx) — menu lateral; desde o #1270 deriva os itens de [`useCapabilities(policies)`](../../../frontend/src/hooks/useCapabilities.ts) (`AppSidebar.tsx`), ou seja, **policy pura** — não usa mais as mesmas flags legacy das rotas. É UX, não é o gate autoritativo.
- Diretório [`v2/frontend/src/pages/`](../../../frontend/src/pages) — **15 diretórios de domínio** (AdminDAT, Aprovacoes, Auth, Controle, DAT, DATModule, Dashboards, Deslocamentos, Disponibilidade, Home, MapaBrasil, MeusEventos, Perfil, PreAgenda, Solicitacoes) + `__tests__`.

> **Contagem real:** **43 páginas lazy-loaded** (42 em `AppRoutes` + `LoginPage` em `App.tsx`), não "45+".
>
> **Correção de mito (o inverso do que esta spec dizia até 2026-07-20):** `pages/Disponibilidade/` (diretório) **não tem `index`**; quem está roteado em `/solicitacoes/bloqueios` é o arquivo solto [`pages/Disponibilidade.tsx`](../../../frontend/src/pages/Disponibilidade.tsx) (`AppRoutes.tsx`, const `DisponibilidadeBlocks` → `import('../pages/Disponibilidade')` resolve o arquivo antes do diretório). Do diretório homônimo, só `MonthlyPage` é roteada (`AppRoutes.tsx`, const `MonthlyPage`).

## Contratos e invariantes

- **Gate de rota é autoritativo, menu é só UX.** Esconder o item no `AppSidebar` não basta: a rota em `AppRoutes` **deve** renderizar o fallback de `<RequirePolicy>` quando o guard é falso. Deep-link/bookmark/redirect 3rd-party não pode abrir página proibida (provado pelo teste de acesso por perfil).
- **O fallback não vaza recurso (OWASP).** `DefaultForbidden` usa `status="info"`, título fixo "Recurso indisponível" e subtítulo genérico (`RequirePolicy.tsx`, `DefaultForbidden`); nunca revela a policy/capability exigida nem a existência do recurso.
- **Fail-secure por construção.** `<RequirePolicy>` sem `policy` e sem `allow` nega (`RequirePolicy.tsx`, `RequirePolicy` → `granted`) — esquecer o gate não abre a página.
- **Frontend não é a fronteira de segurança.** O guard de rota é defesa de UX; a autorização real é do backend (`permission_classes=[HasPerm("codename")]`). Este invariante é sobre **não abrir** o que o backend negaria; ele **não** garante o inverso — há telas que oferecem fluxos que o backend rejeita (ver "Divergências conhecidas" abaixo).
- **RBAC idiomático.** Decisões de acesso derivam de `policies` (policy pública) ou de flags computadas de `setores`+`funcoes`+`is_superuser`; nunca de checagem direta de nome de grupo (banido por `scripts/rbac_lint.py` no backend; o equivalente no FE é não hardcodar nomes de grupo nas páginas).
- **`is_superuser` é escape hatch.** As flags `canControle`/`canDAT`/`canDashboard*` já embutem `is_superuser` e o backend devolve todas as `PUBLIC_POLICY_KEYS` ao superuser; superuser passa em tudo. Páginas não devem ramificar por `is_superuser` para regra de negócio — só para widgets admin/debug.
- **Aprovações = policy exclusiva.** `/solicitacoes/aprovacoes` depende **somente** da policy pública `access_solicitation_approvals` (`AppRoutes.tsx`). O legacy `can_approve_super` foi removido do contrato do FE (PR 10 hardening RBAC). A página carrega `getMe()` em paralelo com as policies para a segregação (PA-02, PR B1): a linha da **própria** solicitação (não-superuser) sai sem checkbox e sem Aprovar/Reprovar, com a Tag "Sua solicitação" e o Tooltip "Outra pessoa aprovadora precisa decidir" — o backend recusa com 403 `self_approval_forbidden` de qualquer forma.
- **Redirects preservam deep-links.** As 6 URLs legadas (`/aprovacoes`, `/disponibilidade`, `/bloqueios`, `/deslocamentos`, `/meus-eventos`, `/dat/importacao`) redirecionam com `<Navigate replace>` para a rota canônica sob `/solicitacoes/*` ou `/dat/importacoes`.

## Padrão responsivo

**A regra (dono, 29/09/2026):** nenhuma tela rola na horizontal, nem a página nem dentro de tabela, grade ou card, e nenhum conteúdo fica cortado sem reticências, em **360, 768, 1024 e 1280 px**. A largura de 1024 é a de um notebook de 1366 px com escala de 125% no Windows. Reflow sem rolagem também é critério da WCAG 2.1 (1.4.10). Esta seção é a SSOT do padrão.

- **Como se mede.** Três critérios: a página não rola (`documentElement.scrollWidth - clientWidth ≤ 0`); nenhum elemento com `overflow-x` auto ou scroll tem `scrollWidth - clientWidth > 1` (só o primeiro critério não enxerga a tabela do AntD, que rola dentro de `.ant-table-content`); e nenhum elemento com `overflow-x` hidden ou clip corta conteúdo sem `text-overflow: ellipsis`. No corte ficam de fora campos de formulário, caixas invisíveis ou sem largura, `aria-hidden` e uma lista curta de internos do AntD e do Leaflet que escondem conteúdo de propósito (`CORTE_PERMITIDO`).
- **Barra de rolagem.** A 360 e 768 px a barra é sobreposta, como no celular. A 1024 e 1280 px ela ocupa 15 px, como no Chrome do Windows: o Chromium headless esconde a barra (`--hide-scrollbars`), e o spec de desktop tira esse flag.
- **Trava 1, Playwright.** [`sem-rolagem-horizontal.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts) (360 e 768) e [`sem-rolagem-horizontal.desktop.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.desktop.spec.ts) (1024 e 1280) abrem cada rota de `AppRoutes` com um perfil que a acessa, mais a tela de login e as vistas alternativas declaradas (Coordenadores "Lista" e "Por área", Mapa "Lista"). A medição e as pré-condições ficam em [`sem-rolagem-horizontal.medicao.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.medicao.ts).
- **Pré-condições: a tela, não só a casca.** Antes de medir, a rota tem de mostrar o seu título em `main`, a casca autenticada (header com "Sair"; a tela de login também tem `main`), nenhum Result/Alert de erro, "Algo deu errado" ou "Recurso indisponível", a linha de tabela com o texto do seed e nenhuma requisição da mesma origem com falha (4xx, 5xx ou `requestfailed`). Controles provam que cada uma reprova o seu caso (chunk da página abortado, sessão perdida, API com 403, erro da própria página). Sem isso, uma tela quebrada passaria por "sem rolagem" ou, estando em `PENDENTES`, mandaria tirar a combinação da lista.
- **Dados.** Vêm de `seed_frontend_contract_data`, com textos de 80+ caracteres em todo campo de tabela, porque tabela vazia nunca estoura. Rotas, títulos, textos do seed, vistas alternativas e aliases ficam em [`sem-rolagem-horizontal.rotas.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.rotas.ts). [`AppRoutes.semRolagemHorizontal.test.ts`](../../../frontend/src/components/__tests__/AppRoutes.semRolagemHorizontal.test.ts) lê o `AppRoutes` pela árvore do TypeScript e reprova rota nova sem entrada lá; ele também confere que cada texto procurado existe no seed do backend. O que não é medido fica em `NAO_MEDIDOS`, com o motivo (Home com outros perfis, modo Google da Pré-agenda, passos do wizard, ImportUploader depois da validação, modais).
- **Trava 2, lint.** `Table` do AntD só entra por `components/ResponsiveTable`, que o C1 cria e que é isento para sempre. A regra cobre os barris (`antd`, `antd/es`, `antd/lib`, com `/index` ou `.js`, e o bundle de `antd/dist`), os caminhos profundos de `antd/*/table` (menos a `interface`, só tipos), o `rc-table`, e `import()`/`require` de antd. Os 27 arquivos que já importavam `Table` estão em [`eslint.tabela-antd-allowlist.js`](../../../frontend/eslint.tabela-antd-allowlist.js), cada um com o PR do Programa C que o tira. [`tabelaAntdRestrita.test.ts`](../../../frontend/src/test/lint/tabelaAntdRestrita.test.ts) tem um controle por forma de contorno e compara identidade: o conjunto de arquivos de `src/` que importam `Table`, medido com os comentários `eslint-disable` desligados, tem de ser exatamente a allowlist.
- **Dívida medida (`PENDENTES`).** Em 29/09/2026, 126 combinações rota × largura rolavam ou cortavam, em 34 chaves (31 das 42 rotas medidas, mais 3 vistas alternativas); 26 chaves falham até a 1280 px. Cada combinação roda com `test.fail`: quando a tela é consertada, o teste passa a falhar e a combinação tem de sair da lista. [`semRolagemHorizontal.pendentes.test.ts`](../../../frontend/src/components/__tests__/semRolagemHorizontal.pendentes.test.ts) trava a lista: toda combinação tem de estar na linha de base medida, e o tamanho é exatamente um teto que só desce. A lista e a allowlist só encolhem, e o Programa C (C1 a C7) zera as duas.
- **Tela nova ou alterada.** Nada de `scroll={{ x }}` nem de largura fixa maior que a tela. Colunas secundárias somem por breakpoint (`responsive`), texto longo usa `ellipsis`, ações vão para um menu, e o que some aparece na linha expandida.

## API / Interface

Inventário por domínio (rota → componente → guard **como o código aplica hoje**). `policy=X` significa `<RequirePolicy policy="X" policies={policies}>`; `allow=` significa expressão booleana. Detalhe da capability na [matriz RBAC](../../rbac_authorization_matrix.md).

### Home

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/`, `/home` | `Home/HomePage` | sem `<RequirePolicy>` — autenticado por construção |

### Auth

| Rota | Página | Guard |
|---|---|---|
| (sem rota — render condicional em `App.tsx`, `AppContent` → ramo `if (!user)`) | `Auth/LoginPage` | anônimo |

### Perfil

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/perfil` | `Perfil/PerfilPage` | `allow={!!user}` |

### Solicitações (agrupadas sob `/solicitacoes/*`)

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/minhas` | `Solicitacoes/MySolicitacoesPage` | policy `create_solicitation` |
| `/solicitacoes/nova` | `Solicitacoes/NewSolicitacaoWizard` | policy `create_solicitation` |
| `/solicitacoes/publicacao` | `Solicitacoes/PublicacaoSetorPage` | policy `publish_setor_solicitacao` (#1656) — Apoio de Coordenação publica no Google Agenda os aprovados do próprio setor; `use_gcal` **não** abre esta rota |
| `/solicitacoes/:id/editar` | `Solicitacoes/EditSolicitacaoPage` | `allow={canCoordenador \|\| canApproveSuper}` (#1169) — **não** é "autenticado" |
| `/solicitacoes/meus-eventos` | `MeusEventos/MeusEventosPage` | `allow={!!user}` |

### Aprovações

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/aprovacoes` | `Aprovacoes/ApprovalsPage` | policy `access_solicitation_approvals` |

### Disponibilidade

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/disponibilidade` | `Disponibilidade/MonthlyPage` | `allow={can('view_all_availability') \|\| canDisponibilidade}` |
| `/solicitacoes/bloqueios` | `pages/Disponibilidade.tsx` (arquivo raiz) | `allow={access.canAccessBlocks}` — inclui Formador, escopo próprio |
| `/solicitacoes/deslocamentos` | `Deslocamentos/DeslocamentosPage` | `allow={can('view_all_availability') \|\| canControle \|\| canCoordenador \|\| canDAT \|\| isGestorPorVinculo}` |

> **PR A (2026-09-29):** `canDisponibilidade`, `canBloqueios` (→ `canAccessBlocks`) e o gate de Deslocamentos também aceitam `isGestorPorVinculo` — vínculo GERENTE/COORDENADOR/APOIO em `/api/me/.gerencias`, mesmo sem grupo de FUNÇÃO (o backend já escopa por vínculo). O menu (`AppSidebar`) e o gate local da `DeslocamentosPage` seguem as mesmas flags. Na Grade, a `FiltersBar` escolhe a gerência pela policy `view_all_availability` + `me.gerencias` (ver [`hooks-rbac.spec.md`](./hooks-rbac.spec.md)); a opção sem gerência se chama "Participantes de projetos SUPER". Na PreAgenda, o filtro de gerência é um Select das gerências ativas que manda `gerencia_id` para a lista e para o resumo (KPIs); o resumo não recebe mais o `status` da lista (lá `status` é o `gcal_status`, e `approved` zerava os KPIs). Nas telas de admin, setor = `rotulo` da gerência: coluna Setor de Usuários pela lotação vigente (sem vínculo — Controle, DAT, Diretoria —, os grupos de setor, como no Perfil), o Select de lotação inclui a gerência atual mesmo inativa, 1ª coluna de Gerências, e em Projetos a tag da gerência com o setor do catálogo embaixo quando difere (sem coluna nova).

### Controle

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/controle` | `Controle/ControlePage` | policy `access_controle_section` |
| `/controle/acoes` | `DATModule/AcoesPage` | policy `access_controle_section` |
| `/controle/compras`, `/compras-materiais` | `DATModule/ComprasPage` | `allow={canControle \|\| canDAT}` |
| `/controle/coordenadores` | `DATModule/CoordenadoresPage` | policy `access_controle_section` |
| `/controle/plano-formacoes` | `DATModule/PlanoFormacoesPage` | policy `access_controle_section` |
| `/controle/pre-agenda`, `/pre-agenda` | `PreAgenda/PreAgendaPage` | policy `access_controle_section` |
| `/acoes-notificacao`, `/acoes-notificacao/timeline`, `/notificacoes-internas` | `Controle/AcoesNotificacaoPage` / `AcoesTimelinePage` / `NotificacoesInternasPage` | policy `manage_internal_actions` |

> `/controle/formacoes` (lia `DATFormacao`, tabela vazia — não existe formação avulsa: toda formação é encontro de plano) foi **removida** em #1978. As formações reais vivem em `/controle/plano-formacoes` (children de `PlanoFormacoes`, matriz F1..F15). O model/endpoint `DATFormacao` foi **deletado do backend** em 2026-09-14 (dead-code; a stat `total_formacoes` do coordenador saiu junto).

> **#1976 (níveis de catálogo Projeto):** o catálogo tem 2 níveis — **família** (`A COR DA GENTE`) ← evento/**plano** apontam aqui; **variante-por-série** (`A COR DA GENTE 1..9`) ← DAT/compra. O dropdown de projeto do **plano de formação** passou a listar **só famílias** (`getProjetosOptions({ excludeKits: true })` → `/options/projetos/?exclude_kits=true`, mesma heurística do `ProjetoLookup` que a NOVA solicitação já usa). Compras/DAT seguem com todas as variantes (default `exclude_kits=false`).

> **#1984 (`/controle` = hub):** `ControlePage` deixou de ser a lista de compras legada (`core.Compra`, redundante com `/controle/compras`) e virou o **Painel de Controle** — KPIs de contagem reais (Ações/Compras/Planos/Coordenadores via os `/stats/`, sem valor financeiro) + atalhos pras sub-páginas.

### DAT / AdminDAT

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/dat/admin` + `/dat/admin/{usuarios,municipios,projetos,grupos,setores,funcoes,gerencias,produtos,configuracoes,colecoes,equipe-gerencia}` | `AdminDAT/*` | policy `manage_admin_registries` |
| `/dat/cadastros` | `DATModule/CadastrosPage` | policy `manage_admin_registries` |
| `/dat/importacoes` | `DAT/ImportacoesPage` | policy `manage_admin_registries` |
| `/dat/registros` | `DATModule/DATRegistrosPage` | policy `manage_admin_registries` |
| `/dat/compras-materiais` | `DATModule/ComprasPage` | `allow={canControle \|\| canDAT}` |
| `/dat/coordenadores` | `DATModule/CoordenadoresPage` | policy `access_controle_section` |

### Dashboards

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/dashboards` | `Dashboards/DashboardsPage` | policy `view_overview_dashboard` |
| `/dashboards/compras` | `Dashboards/ComprasDashboardPage` | policy `view_compras_dashboard` |
| `/dashboards/equipe` | `Dashboards/EquipeDashboardPage` | policy `view_team_dashboard` |
| `/dashboards/gcal` | `Dashboards/GCalDashboardPage` | policy `view_gcal_dashboard` |
| `/mapa-brasil` | `MapaBrasil/MapaBrasilPage` | policy `view_map_metrics` |

> As flags legacy `canDashboardOverview`/`canDashboardEquipe`/`canDashboardGcal`/`canMapaBrasil` de `usePermissions` **não gateiam mais** essas rotas desde o #1271; continuam existindo no hook e são usadas por outros consumidores (ex.: menu antigo, widgets).

## Fluxos principais

1. **Boot / autenticação** — `App.tsx` chama `getMe()`; se anônimo (`isAuthError`), renderiza `LoginPage`. Autenticado: busca `getMyPolicies()` (sequencial, evita 403 espúrio pré-login), monta sidebar/header/rotas. Loading → `FullscreenLoader`.
2. **Navegação para página guardada** — `AppRoutes` recebe `permissions` (`usePermissions`) + `policies` e resolve `access` (`useCanAccess`, só para os composites de disponibilidade). Cada rota delega a decisão a `<RequirePolicy>`: se concedido, monta a página lazy (fallback `PageLoader` durante o chunk); se não, monta `DefaultForbidden`.
3. **URL legada** — `<Navigate replace>` redireciona para a rota canônica antes de qualquer render de página, preservando histórico/bookmark.
4. **Erro de runtime na página** — `ErrorBoundary` (raiz, `App.tsx`) captura; falhas de auth em chamadas de API são tratadas por `isAuthError` e degradam para estado anônimo/`[]`. Um `401` em qualquer chamada dispara o evento global `auth:expired`, tratado uma única vez em `App.tsx` (`handleAuthExpired`: limpa sessão → volta à `LoginPage`).

## Decisões relacionadas (ADRs)

- [Matriz de autorização RBAC](../../rbac_authorization_matrix.md) — §3 dashboards, decisões D7/D8/D9 (acesso a dashboards e Grade Mensal), composite Setor×Função das aprovações.
- [`RBAC_NAMING.md`](../../RBAC_NAMING.md) — convenção de codenames/policies públicas.
- Issue #927 — decomposição de `App.tsx` (extração de hooks/`AppRoutes`/`AppSidebar`).
- Epic 3 (#1227/#1228) — agrupamento sob `/solicitacoes/*` + camada `useCanAccess`. PR-C DAT Imports (2026-04-29) — unificação de imports em `/dat/importacoes`.
- #1169 — gate próprio de `/solicitacoes/:id/editar` (antes era só "autenticado").
- #1270 / #1271 — menu por `useCapabilities` e rotas por `<RequirePolicy>`; fim do `Forbidden` inline.

## Testes que cobrem

- [`v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx) — matriz **10 atores canônicos × 12 rotas críticas**; prova que deep-link proibido renderiza o fallback genérico. Inclui os gates de `/solicitacoes/:id/editar` e de `/solicitacoes/publicacao` (#1656).
- [`v2/frontend/src/components/access/__tests__/RequirePolicy.test.tsx`](../../../frontend/src/components/access/__tests__/RequirePolicy.test.tsx) — comportamento do guard (concede/nega, `loading` não pisca 403).
- [`v2/frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx) — gate e redirect das rotas DAT (`/dat/importacao` → `/dat/importacoes`).
- [`v2/frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx`](../../../frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx) — remoção das rotas/imports legados de DAT.
- [`v2/frontend/src/components/__tests__/AppSidebar.menu.test.tsx`](../../../frontend/src/components/__tests__/AppSidebar.menu.test.tsx) — itens de menu por ator (paridade com os gates de rota).
- [`sem-rolagem-horizontal.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts), [`sem-rolagem-horizontal.desktop.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.desktop.spec.ts), [`AppRoutes.semRolagemHorizontal.test.ts`](../../../frontend/src/components/__tests__/AppRoutes.semRolagemHorizontal.test.ts) e [`semRolagemHorizontal.pendentes.test.ts`](../../../frontend/src/components/__tests__/semRolagemHorizontal.pendentes.test.ts) — padrão responsivo (seção acima).
- Testes de página individuais: `NewSolicitacaoWizard.test.tsx`, `MeusEventosPage.test.tsx`, `ImportacoesPage.test.tsx`, `UsuariosPage.cpf.test.tsx`, `GruposPage.readonly.test.tsx`, `PreAgendaPage.gcal.test.tsx`, `PerfilPage.test.tsx`, `PublicacaoSetorPage.test.tsx`.

## Divergências conhecidas entre página e backend

Reconfirmadas por execução na auditoria modular M00–M28 e rastreadas no documento vivo
[`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md). **Algumas já foram RESOLVIDAS** (marcador por
linha na coluna à direita); as demais seguem **vivas em produção** — esta seção descreve o que as
páginas fazem, não o que deveriam fazer.

| Achado | Página | O que o código faz hoje |
|---|---|---|
| `M05-07` (#1655) | `Home/HomePage` | Os cards "Enviar Solicitação"/"Minhas Solicitações" são gateados por `perms.canCoordenador` (`HomePage.tsx`, `isCoordenador`), isto é, por setor/função — **não** pela policy `create_solicitation` que gateia as rotas de destino (`AppRoutes.tsx`, rotas `/solicitacoes/{minhas,nova}`). Quem tem a policy sem ser Coordenador/DAT não vê o atalho; quem é DAT vê um atalho para uma rota que a policy pode negar. |
| `M09-05` (#1621) | `Deslocamentos/DeslocamentosPage` | O campo "Formador" do modal é `required` (`Form.Item name="usuario"`) e só oferece terceiros; o POST sempre manda `usuario` (`handleModalSubmit`). O backend exige delegação (`views_deslocamento.py`, `DeslocamentoViewSet.perform_create`) satisfeita apenas por `operate_preagenda`/`view_all_availability` (`rbac/policies.py`, `user_can_delegate_deslocamento`) — capabilities que Coordenador não tem. Resultado: Coordenador acessa a página e falha em 100% dos creates. |
| `M09-06` (#1622) | `Deslocamentos/DeslocamentosPage` | **RESOLVIDO (#1622)** (PRs #1731/#1737/#1753). Era: filtros Origem/Destino como `<Input>` não-controlados, sem debounce, e o early-return `if (loading) return …` desmontava a árvore inteira a cada tecla (o input perdia foco e o caractere). Hoje: inputs **controlados** (`value={filters.origem ?? ''}`), **debounce de 350 ms**, `pageLoading`/`tableLoading` separados (o early-return cobre só a carga inicial) e `seqRef` (latest-wins) + `AbortController` descartando respostas obsoletas. |
| `M12-19` (#1629) | `PreAgenda/PreAgendaPage` | **RESOLVIDO (#1629)** (#1750). Era: a tabela anunciava `total = superCount + naoCount` mas só carregava a primeira página de cada lista e paginava no cliente sem handler — as páginas além do buscado ficavam vazias, e o polling pressionava o throttle `user: 1000/hour`. Hoje: carrega as duas listas de uma vez, `total = loadedRows.length` (contador honesto), guarda latest-wins e **backoff após 429** no polling. |
| `M15-10` (#1637) | `DATModule/ComprasPage` | **Fase A resolvida (#1714/#1716); resta Fase B (#1637 OPEN)** — o achado NÃO fechou por inteiro. Fase A: `buildCompraPayload` faz strip **explícito** dos campos extras (não é mais spread cru) e o save reporta erro por-campo; `codigo_produto` **existe** no serializer como mirror read-only (`source="produto.codigo"`); `valor_unitario` e `ano_uso` viraram **obrigatórios** no modal (o `valor_total` R$0 sumiu — card removido em #1983). Fase B (aberta): persistir `fornecedor`, `numero_nota_fiscal` e `data_entrega` no lado do Controle — hoje `buildCompraPayload` ainda os remove por não terem destino no serializer. |
| `M16-08` (#1639) | `DATModule/DATRegistrosPage` | **RESOLVIDO (#1712).** Era: um único `STATUS_OPTIONS` de 3 valores reusado para dois conjuntos de choices diferentes do backend (`DATRegistro.STATUS_CHOICES`/`TURMA_STATUS_CHOICES`), tornando `em_andamento`/`concluido` inválidos em `turma_formar_status` → 400. Hoje partido em `TURMA_STATUS_OPTIONS` (3, casa `TURMA_STATUS_CHOICES`) e `ETAPA_STATUS_OPTIONS` (5, casa `STATUS_CHOICES`) em `DATRegistros/constants.tsx`; `turma_formar_status` usa `TURMA_STATUS_OPTIONS`; contrato travado por `statusOptionsContract.test.ts`. |
| `M18-06` (#1653) | telas DAT com `useTableFilters` | **RESOLVIDO (#1653)** (commit `062df0ec`). Era: o FE enviava `page_size` mas o DRF usava `PageNumberPagination` de estoque como `DEFAULT_PAGINATION_CLASS`, com `page_size_query_param` = `None` — o parâmetro era ignorado e a API devolvia 100 linhas. Hoje o default é `StandardPagination(PageNumberPagination)` com `page_size_query_param="page_size"` e `max_page_size=500`, honrando `?page_size` (coberto por teste). |

## Pontos de atenção / dívidas conhecidas

- **Guard duplicado FE/BE.** Os guards `allow=` ainda são reimplementação client-side da matriz RBAC do backend; divergência silenciosa é possível. A matriz viva no backend é o SSOT — qualquer página nova deve casar com a policy/permission do endpoint que consome. Os composites que sobraram sem policy pública são: `/solicitacoes/:id/editar`, `/solicitacoes/disponibilidade`, `/solicitacoes/bloqueios`, `/solicitacoes/deslocamentos`, `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais`.
- **`usePermissions` é `@deprecated` mas ainda gateia rotas.** O hook declara remoção na onda 4.5 (#1269), e sete rotas dependem dele via `allow=`. Migrar exige criar as policies públicas correspondentes primeiro.
- **`pages/Solicitacoes.tsx` removido (#1728).** O arquivo raiz (~15 KB) era dead code — **não importado por nenhum módulo**, nenhuma rota o alcançava — e foi removido nesta limpeza. `pages/Disponibilidade.tsx` (também na raiz) **está** roteado; os dois não devem ser tratados como o mesmo caso.
- **Logout via `window.location.reload()`.** Tech-debt assumido (#927, `App.tsx`, `handleLogout`) — sem auth store centralizado, logout força reload em vez de limpeza de estado.
- **Sidebar e rotas usam camadas diferentes.** O menu decide por `useCapabilities` (policy pura) e as rotas compostas por flags legacy; onde as duas discordam, o item aparece e a rota nega (ou o contrário). `AppSidebar.menu.test.tsx` cobre a paridade nos atores canônicos, não em todas as rotas.
