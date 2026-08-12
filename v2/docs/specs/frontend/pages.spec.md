---
title: Páginas (React)
status: canonical
last_verified: 2026-07-24
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

- [`v2/frontend/src/App.tsx`](../../../frontend/src/App.tsx) — shell: carrega `getMe()` + `getMyPolicies()`, decide login vs app, monta sidebar/header/`<AppRoutes>`. `LoginPage` é a única página lazy fora de `AppRoutes` (`App.tsx:40`); sem `user`, o app renderiza só a `LoginPage` (`App.tsx:176-184`) — é daí que vem o guard "autenticado" das rotas sem gate próprio.
- [`v2/frontend/src/components/AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx) — **registro único de rotas**. **40 páginas lazy** (`AppRoutes.tsx:10-49`) e **51 `<Route>`**, dos quais **6 são redirects** de URLs legadas (`:109-113` e `:151`).
- [`v2/frontend/src/components/access/RequirePolicy.tsx`](../../../frontend/src/components/access/RequirePolicy.tsx) — guard único. Decisão em `:76-91`: `allow` (boolean explícito) tem precedência; senão `policies.includes(policy)`; **sem `policy` nem `allow` → fail-secure** (`granted = false`). Fallback padrão é `DefaultForbidden` (`:48-61`).
- [`v2/frontend/src/hooks/usePermissions.ts`](../../../frontend/src/hooks/usePermissions.ts) — flags legacy (`canControle`/`canDAT`/`canDisponibilidade`/…) derivadas de `setores`+`funcoes`+`is_superuser`. **Marcado `@deprecated` (#1269)** no próprio arquivo (`:5-9`); ainda é o que alimenta os guards `allow=` dos composites.
- [`v2/frontend/src/hooks/useCanAccess.ts`](../../../frontend/src/hooks/useCanAccess.ts) — em `AppRoutes` sobrou **só** para os composites de disponibilidade/bloqueios: é instanciado com uma única flag legacy, `canBloqueios` (`AppRoutes.tsx:73-75`).
- [`v2/frontend/src/components/AppSidebar.tsx`](../../../frontend/src/components/AppSidebar.tsx) — menu lateral; desde o #1270 deriva os itens de [`useCapabilities(policies)`](../../../frontend/src/hooks/useCapabilities.ts) (`AppSidebar.tsx:16,206`), ou seja, **policy pura** — não usa mais as mesmas flags legacy das rotas. É UX, não é o gate autoritativo.
- Diretório [`v2/frontend/src/pages/`](../../../frontend/src/pages) — **15 diretórios de domínio** (AdminDAT, Aprovacoes, Auth, Controle, DAT, DATModule, Dashboards, Deslocamentos, Disponibilidade, Home, MapaBrasil, MeusEventos, Perfil, PreAgenda, Solicitacoes) + `__tests__`.

> **Contagem real:** **41 páginas lazy-loaded** (40 em `AppRoutes` + `LoginPage` em `App.tsx`), não "45+".
>
> **Correção de mito (o inverso do que esta spec dizia até 2026-07-20):** `pages/Disponibilidade/` (diretório) **não tem `index`**; quem está roteado em `/solicitacoes/bloqueios` é o arquivo solto [`pages/Disponibilidade.tsx`](../../../frontend/src/pages/Disponibilidade.tsx) (`AppRoutes.tsx:10`, `import('../pages/Disponibilidade')` resolve o arquivo antes do diretório). Do diretório homônimo, só `MonthlyPage` é roteada (`AppRoutes.tsx:11`).

## Contratos e invariantes

- **Gate de rota é autoritativo, menu é só UX.** Esconder o item no `AppSidebar` não basta: a rota em `AppRoutes` **deve** renderizar o fallback de `<RequirePolicy>` quando o guard é falso. Deep-link/bookmark/redirect 3rd-party não pode abrir página proibida (provado pelo teste de acesso por perfil).
- **O fallback não vaza recurso (OWASP).** `DefaultForbidden` usa `status="info"`, título fixo "Recurso indisponível" e subtítulo genérico (`RequirePolicy.tsx:48-61`); nunca revela a policy/capability exigida nem a existência do recurso.
- **Fail-secure por construção.** `<RequirePolicy>` sem `policy` e sem `allow` nega (`RequirePolicy.tsx:82-85`) — esquecer o gate não abre a página.
- **Frontend não é a fronteira de segurança.** O guard de rota é defesa de UX; a autorização real é do backend (`permission_classes=[HasPerm("codename")]`). Este invariante é sobre **não abrir** o que o backend negaria; ele **não** garante o inverso — há telas que oferecem fluxos que o backend rejeita (ver "Divergências conhecidas" abaixo).
- **RBAC idiomático.** Decisões de acesso derivam de `policies` (policy pública) ou de flags computadas de `setores`+`funcoes`+`is_superuser`; nunca de checagem direta de nome de grupo (banido por `scripts/rbac_lint.py` no backend; o equivalente no FE é não hardcodar nomes de grupo nas páginas).
- **`is_superuser` é escape hatch.** As flags `canControle`/`canDAT`/`canDashboard*` já embutem `is_superuser` e o backend devolve todas as `PUBLIC_POLICY_KEYS` ao superuser; superuser passa em tudo. Páginas não devem ramificar por `is_superuser` para regra de negócio — só para widgets admin/debug.
- **Aprovações = policy exclusiva.** `/solicitacoes/aprovacoes` depende **somente** da policy pública `access_solicitation_approvals` (`AppRoutes.tsx:99`). O legacy `can_approve_super` foi removido do contrato do FE (PR 10 hardening RBAC).
- **Redirects preservam deep-links.** As 6 URLs legadas (`/aprovacoes`, `/disponibilidade`, `/bloqueios`, `/deslocamentos`, `/meus-eventos`, `/dat/importacao`) redirecionam com `<Navigate replace>` para a rota canônica sob `/solicitacoes/*` ou `/dat/importacoes`.

## API / Interface

Inventário por domínio (rota → componente → guard **como o código aplica hoje**). `policy=X` significa `<RequirePolicy policy="X" policies={policies}>`; `allow=` significa expressão booleana. Detalhe da capability na [matriz RBAC](../../rbac_authorization_matrix.md).

### Home

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/`, `/home` | `Home/HomePage` | sem `<RequirePolicy>` — autenticado por construção (`:80-81`) |

### Auth

| Rota | Página | Guard |
|---|---|---|
| (sem rota — render condicional em `App.tsx:176-184`) | `Auth/LoginPage` | anônimo |

### Perfil

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/perfil` | `Perfil/PerfilPage` | `allow={!!user}` (`:106`) |

### Solicitações (agrupadas sob `/solicitacoes/*`)

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/minhas` | `Solicitacoes/MySolicitacoesPage` | policy `create_solicitation` (`:93`) |
| `/solicitacoes/nova` | `Solicitacoes/NewSolicitacaoWizard` | policy `create_solicitation` (`:94`) |
| `/solicitacoes/:id/editar` | `Solicitacoes/EditSolicitacaoPage` | `allow={canCoordenador \|\| canApproveSuper}` (`:96`, #1169) — **não** é "autenticado" |
| `/solicitacoes/meus-eventos` | `MeusEventos/MeusEventosPage` | `allow={!!user}` (`:105`) |

### Aprovações

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/aprovacoes` | `Aprovacoes/ApprovalsPage` | policy `access_solicitation_approvals` (`:99`) |

### Disponibilidade

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/solicitacoes/disponibilidade` | `Disponibilidade/MonthlyPage` | `allow={can('view_all_availability') \|\| canDisponibilidade}` (`:102`) |
| `/solicitacoes/bloqueios` | `pages/Disponibilidade.tsx` (arquivo raiz) | `allow={access.canAccessBlocks}` (`:103`) — inclui Formador, escopo próprio |
| `/solicitacoes/deslocamentos` | `Deslocamentos/DeslocamentosPage` | `allow={can('view_all_availability') \|\| canControle \|\| canCoordenador \|\| canDAT}` (`:104`) |

### Controle

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/controle` | `Controle/ControlePage` | policy `access_controle_section` (`:117`) |
| `/controle/acoes` | `DATModule/AcoesPage` | policy `access_controle_section` (`:118`) |
| `/controle/compras`, `/compras-materiais` | `DATModule/ComprasPage` | `allow={canControle \|\| canDAT}` (`:119`, `:121`) |
| `/controle/coordenadores` | `DATModule/CoordenadoresPage` | policy `access_controle_section` (`:120`) |
| `/controle/formacoes` | `DATModule/FormacoesPage` | policy `access_controle_section` (`:123`) |
| `/controle/plano-formacoes` | `DATModule/PlanoFormacoesPage` | policy `access_controle_section` (`:124`) |
| `/controle/pre-agenda`, `/pre-agenda` | `PreAgenda/PreAgendaPage` | policy `access_controle_section` (`:125-126`) |
| `/acoes-notificacao`, `/acoes-notificacao/timeline`, `/notificacoes-internas` | `Controle/AcoesNotificacaoPage` / `AcoesTimelinePage` / `NotificacoesInternasPage` | policy `manage_internal_actions` (`:129-131`) |

### DAT / AdminDAT

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/dat/admin` + `/dat/admin/{usuarios,municipios,projetos,grupos,setores,funcoes,gerencias,produtos,configuracoes,colecoes,equipe-gerencia}` | `AdminDAT/*` | policy `manage_admin_registries` (`:133-144`) |
| `/dat/cadastros` | `DATModule/CadastrosPage` | policy `manage_admin_registries` (`:145`) |
| `/dat/importacoes` | `DAT/ImportacoesPage` | policy `manage_admin_registries` (`:152`) |
| `/dat/registros` | `DATModule/DATRegistrosPage` | policy `manage_admin_registries` (`:153`) |
| `/dat/compras-materiais` | `DATModule/ComprasPage` | `allow={canControle \|\| canDAT}` (`:146`) |
| `/dat/coordenadores` | `DATModule/CoordenadoresPage` | policy `access_controle_section` (`:147`) |

### Dashboards

| Rota | Página | Guard (`AppRoutes.tsx`) |
|---|---|---|
| `/dashboards` | `Dashboards/DashboardsPage` | policy `view_overview_dashboard` (`:85`) |
| `/dashboards/compras` | `Dashboards/ComprasDashboardPage` | policy `view_compras_dashboard` (`:86`) |
| `/dashboards/equipe` | `Dashboards/EquipeDashboardPage` | policy `view_team_dashboard` (`:87`) |
| `/dashboards/gcal` | `Dashboards/GCalDashboardPage` | policy `view_gcal_dashboard` (`:88`) |
| `/mapa-brasil` | `MapaBrasil/MapaBrasilPage` | policy `view_map_metrics` (`:89`) |

> As flags legacy `canDashboardOverview`/`canDashboardEquipe`/`canDashboardGcal`/`canMapaBrasil` de `usePermissions` **não gateiam mais** essas rotas desde o #1271; continuam existindo no hook e são usadas por outros consumidores (ex.: menu antigo, widgets).

## Fluxos principais

1. **Boot / autenticação** — `App.tsx` chama `getMe()`; se anônimo (`isAuthError`), renderiza `LoginPage`. Autenticado: busca `getMyPolicies()` (sequencial, evita 403 espúrio pré-login), monta sidebar/header/rotas. Loading → `FullscreenLoader`.
2. **Navegação para página guardada** — `AppRoutes` recebe `permissions` (`usePermissions`) + `policies` e resolve `access` (`useCanAccess`, só para os composites de disponibilidade). Cada rota delega a decisão a `<RequirePolicy>`: se concedido, monta a página lazy (fallback `PageLoader` durante o chunk); se não, monta `DefaultForbidden`.
3. **URL legada** — `<Navigate replace>` redireciona para a rota canônica antes de qualquer render de página, preservando histórico/bookmark.
4. **Erro de runtime na página** — `ErrorBoundary` (raiz, `App.tsx`) captura; falhas de auth em chamadas de API são tratadas por `isAuthError` e degradam para estado anônimo/`[]`. Um `401` em qualquer chamada dispara o evento global `auth:expired`, tratado uma única vez em `App.tsx:140-149` (limpa sessão → volta à `LoginPage`).

## Decisões relacionadas (ADRs)

- [Matriz de autorização RBAC](../../rbac_authorization_matrix.md) — §3 dashboards, decisões D7/D8/D9 (acesso a dashboards e Grade Mensal), composite Setor×Função das aprovações.
- [`RBAC_NAMING.md`](../../RBAC_NAMING.md) — convenção de codenames/policies públicas.
- Issue #927 — decomposição de `App.tsx` (extração de hooks/`AppRoutes`/`AppSidebar`).
- Epic 3 (#1227/#1228) — agrupamento sob `/solicitacoes/*` + camada `useCanAccess`. PR-C DAT Imports (2026-04-29) — unificação de imports em `/dat/importacoes`.
- #1169 — gate próprio de `/solicitacoes/:id/editar` (antes era só "autenticado").
- #1270 / #1271 — menu por `useCapabilities` e rotas por `<RequirePolicy>`; fim do `Forbidden` inline.

## Testes que cobrem

- [`v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx) — matriz **10 atores canônicos × 12 rotas críticas** (`:145-158`, `:175`, `:625`); prova que deep-link proibido renderiza o fallback genérico. Inclui o gate de `/solicitacoes/:id/editar` (`:650-667`).
- [`v2/frontend/src/components/access/__tests__/RequirePolicy.test.tsx`](../../../frontend/src/components/access/__tests__/RequirePolicy.test.tsx) — comportamento do guard (concede/nega, `loading` não pisca 403).
- [`v2/frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.dat-imports.test.tsx) — gate e redirect das rotas DAT (`/dat/importacao` → `/dat/importacoes`).
- [`v2/frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx`](../../../frontend/src/pages/__tests__/DatImportsLegacyRemoval.test.tsx) — remoção das rotas/imports legados de DAT.
- [`v2/frontend/src/components/__tests__/AppSidebar.menu.test.tsx`](../../../frontend/src/components/__tests__/AppSidebar.menu.test.tsx) — itens de menu por ator (paridade com os gates de rota).
- Testes de página individuais: `NewSolicitacaoWizard.test.tsx`, `MeusEventosPage.test.tsx`, `ImportacoesPage.test.tsx`, `UsuariosPage.cpf.test.tsx`, `GruposPage.readonly.test.tsx`, `PreAgendaPage.gcal.test.tsx`, `PerfilPage.test.tsx`.

## Divergências conhecidas entre página e backend

Reconfirmadas por execução na auditoria modular M00–M28 e rastreadas no documento vivo
[`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md). **Estão vivas em produção** — esta seção
existe para que a spec descreva o que as páginas fazem, não o que deveriam fazer.

| Achado | Página | O que o código faz hoje |
|---|---|---|
| `M05-07` (#1655) | `Home/HomePage` | Os cards "Enviar Solicitação"/"Minhas Solicitações" são gateados por `perms.canCoordenador` (`HomePage.tsx:152`, `:245`), isto é, por setor/função — **não** pela policy `create_solicitation` que gateia as rotas de destino (`AppRoutes.tsx:93-94`). Quem tem a policy sem ser Coordenador/DAT não vê o atalho; quem é DAT vê um atalho para uma rota que a policy pode negar. |
| `M09-05` (#1621) | `Deslocamentos/DeslocamentosPage` | O campo "Formador" do modal é `required` (`:431-447`) e só oferece terceiros; o POST sempre manda `usuario` (`:209-219`). O backend exige delegação (`views_deslocamento.py:212-220`) satisfeita apenas por `operate_preagenda`/`view_all_availability` (`rbac/policies.py:449-468`) — capabilities que Coordenador não tem. Resultado: Coordenador acessa a página e falha em 100% dos creates. |
| `M09-06` (#1622) | `Deslocamentos/DeslocamentosPage` | Filtros Origem/Destino são `<Input>` não-controlados sem debounce (`:388-399`); cada tecla muda `filters` (`:160-162`), refaz o `useEffect` (`:147-152`) e liga `loading`, e o early-return `if (loading) return …` (`:324-326`) desmonta a árvore inteira — o input perde foco e o caractere digitado. |
| `M12-19` (#1629) | `PreAgenda/PreAgendaPage` | `usePolling` a cada 5 s (`:219-223` + `constants/timing.ts:29`) dispara 3 requisições por ciclo (`:191-195`) contra o throttle `user: 1000/hour` (`config/settings.py:490-497`). A tabela anuncia `total = superCount + naoCount` (`:197-203`) mas só carrega a primeira página de cada lista, e pagina no cliente sem handler (`:785-789`) — as páginas além do que foi buscado ficam vazias. |
| `M15-10` (#1637) | `DATModule/ComprasPage` | O payload é um spread cru do form (`:227-232`); `codigo_produto`, `uf`, `data_entrega`, `numero_nota_fiscal` e `fornecedor` não existem no serializer (`serializers/dat_module/dat_compra.py:35-67`) e são descartados em silêncio. Não há campo de preço no modal, então `valor_unitario` fica no default `0.00` (`models/dat_compra.py:78-80`) e o `valor_total` do dashboard sai zerado. |
| `M16-08` (#1639) | `DATModule/DATRegistrosPage` | Um único `STATUS_OPTIONS` de 3 valores (`DATRegistros/constants.tsx:43-47`) é reusado para dois conjuntos de choices diferentes do backend (`models/dat_registro.py:47-59`). Para `turma_formar_status`, `em_andamento` e `concluido` são inválidos → 400 no save. |
| `M18-06` (#1653) | telas DAT com `useTableFilters` | O FE envia `page_size` (`hooks/useTableFilters.ts:126`, default 15 em `:92`), mas o DRF usa a `PageNumberPagination` de estoque (`config/settings.py:485-486`), cujo `page_size_query_param` é `None` — o parâmetro é ignorado e a API devolve 100 linhas. A `<Table>` do antd exibe 15 delas, escondendo o resto. |

## Pontos de atenção / dívidas conhecidas

- **Guard duplicado FE/BE.** Os guards `allow=` ainda são reimplementação client-side da matriz RBAC do backend; divergência silenciosa é possível. A matriz viva no backend é o SSOT — qualquer página nova deve casar com a policy/permission do endpoint que consome. Os composites que sobraram sem policy pública são: `/solicitacoes/:id/editar`, `/solicitacoes/disponibilidade`, `/solicitacoes/bloqueios`, `/solicitacoes/deslocamentos`, `/controle/compras`, `/compras-materiais`, `/dat/compras-materiais`.
- **`usePermissions` é `@deprecated` mas ainda gateia rotas.** O hook declara remoção na onda 4.5 (#1269), e sete rotas dependem dele via `allow=`. Migrar exige criar as policies públicas correspondentes primeiro.
- **`pages/Solicitacoes.tsx` removido (#1728).** O arquivo raiz (~15 KB) era dead code — **não importado por nenhum módulo**, nenhuma rota o alcançava — e foi removido nesta limpeza. `pages/Disponibilidade.tsx` (também na raiz) **está** roteado; os dois não devem ser tratados como o mesmo caso.
- **Logout via `window.location.reload()`.** Tech-debt assumido (#927, `App.tsx:152-169`) — sem auth store centralizado, logout força reload em vez de limpeza de estado.
- **Sidebar e rotas usam camadas diferentes.** O menu decide por `useCapabilities` (policy pura) e as rotas compostas por flags legacy; onde as duas discordam, o item aparece e a rota nega (ou o contrário). `AppSidebar.menu.test.tsx` cobre a paridade nos atores canônicos, não em todas as rotas.
