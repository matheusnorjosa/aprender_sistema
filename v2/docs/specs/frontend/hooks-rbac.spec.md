---
title: Hooks de RBAC e Guards (Frontend)
status: canonical
last_verified: 2026-10-19
sources_of_truth:
  - v2/frontend/src/contexts/AcessoContext.ts
  - v2/frontend/src/test/lint/acessoSoPorPolicy.test.ts
  - v2/frontend/src/hooks/useCapabilities.ts
  - v2/frontend/src/hooks/useIdentity.ts
  - v2/frontend/src/hooks/useGoogleGuard.tsx
  - v2/frontend/src/hooks/useGoogleIntegration.ts
  - v2/frontend/src/components/access/RequirePolicy.tsx
  - v2/frontend/src/api/me.ts
  - v2/frontend/src/api/auth.ts
  - v2/frontend/src/types/usuario.ts
  - v2/frontend/src/App.tsx
  - v2/frontend/src/components/AppRoutes.tsx
  - v2/frontend/src/components/AppSidebar.tsx
  - v2/frontend/src/pages/Disponibilidade/FiltersBar.tsx
  - v2/frontend/src/test/atoresRbac.ts
  - v2/frontend/src/pages/Home/__tests__/HomePage.acesso.test.tsx
  - v2/frontend/src/hooks/__tests__/useCapabilities.test.ts
  - v2/frontend/src/hooks/__tests__/useIdentity.test.ts
  - v2/frontend/src/hooks/__tests__/rbac_matrix.test.ts
  - v2/backend/apps/core/views/me.py
  - v2/backend/apps/core/rbac/policies.py
  - v2/backend/apps/core/tests/test_rbac_politicas_de_tela.py
owner: frontend
supersedes: []
related:
  - ./pages.spec.md
  - v2/docs/RBAC_NAMING.md
  - v2/docs/rbac_authorization_matrix.md
  - v2/docs/API_REFERENCE.md
  - v2/docs/audits/ACHADOS_REAIS.md
---

# Hooks de RBAC e Guards (Frontend)

## Proposito

Esta camada decide **o que o usuario ve e pode acionar** na SPA React, sem nunca virar fonte de autoridade: a decisao final continua no backend (`permission_classes=[HasPerm("codename")]`). Desde o PR 7 das permissoes (15/10/2026) ha **uma fonte so** para acesso: `GET /api/me/policies/` (policies publicas, calculadas no servidor pela lotacao (pacote do perfil da gerencia e papel vigente, ADR-020); o grupo so soma com `RBAC_FONTE=uniao`, a volta de emergencia do PR 12 — SSOT `rbac.spec.md`, item "O corte"). `GET /api/me/` (perfil, setores, funcoes, vinculos) e exibicao; o unico campo dele que decide algo e `is_superuser`, e so onde a regra E o superusuario (helper `ehSuperusuario`). Menu, rotas, botoes e Pagina Inicial leem as duas coisas de `useAcesso()`. O objetivo e UX honesta (nao oferecer o que sera negado), nao seguranca: qualquer flag pode ser burlada no cliente e o backend revalida.

Ha tambem um guard transversal de integracao Google (OAuth): antes de operacoes que tocam o Google Calendar, o frontend confere se a conta corporativa esta conectada e, se nao, conduz o usuario ao fluxo OAuth em vez de deixar a chamada falhar com `403 google_not_connected`.

## Fonte de verdade no codigo

Um contexto e dois hooks (#1269 concluido no PR 7; `usePermissions` e `useCanAccess` foram apagados).

- **Acesso (fonte unica)**: [`v2/frontend/src/contexts/AcessoContext.ts`](../../../frontend/src/contexts/AcessoContext.ts) — `AcessoContext` + `useAcesso(): { caps, ehSuperusuario, loading }`, montado uma vez por `App.tsx` (`montarAcesso(policies, user, loading)`) com o que ele ja carrega. `caps` = `computeCapabilities(policies)`; `ehSuperusuario(user)` e o helper unico para `is_superuser`, usado so onde a regra e o superusuario: importacao pela tela, PA-02 do proprio (ApprovalsPage), campos que so ele grava (Usuarios, Grupos, Municipios) e o widget de debug da Pre-agenda. Sem provedor, ninguem pode nada.
- **Capabilities (autorizacao, policy-pura)**: [`v2/frontend/src/hooks/useCapabilities.ts`](../../../frontend/src/hooks/useCapabilities.ts) — funcao pura `computeCapabilities(policies)` + hook `useCapabilities(policies)`. Sem organograma: cada flag `can*` espelha 1:1 uma policy key, cobrindo as **27** `PUBLIC_POLICY_KEYS` do backend (`rbac/policies.py`).
- **Identidade (display-only)**: [`v2/frontend/src/hooks/useIdentity.ts`](../../../frontend/src/hooks/useIdentity.ts) — `computeIdentity(user)` / `useIdentity(user)`. Setor/funcao + `displayName` + `badge`. **Nao decide autorizacao.**
- **Trava**: [`src/test/lint/acessoSoPorPolicy.test.ts`](../../../frontend/src/test/lint/acessoSoPorPolicy.test.ts) — recusa ler `.setores`, `.funcoes`, `.groups`, `is_superintendencia`, `can_approve_super` e `.is_superuser` em `src/` fora da allowlist de exibicao (`AcessoContext`, `types/usuario.ts`, `useIdentity`, `PerfilPage`, `UsuariosPage` e, ate o PR 8, o campo coordenador do `NewSolicitacaoWizard`), com controles positivos e allowlist por identidade.
- **Guard de rota**: [`v2/frontend/src/components/access/RequirePolicy.tsx`](../../../frontend/src/components/access/RequirePolicy.tsx) — `policy="<key>"` ou uma lista (`policy={['a', 'b']}`, qualquer uma basta) e nega com um `Result` generico. `allow=` so para "autenticado" e para o que e do superusuario. Fail-secure quando faltam `policy` e `allow`.
- **Guard Google OAuth**: [`v2/frontend/src/hooks/useGoogleGuard.tsx`](../../../frontend/src/hooks/useGoogleGuard.tsx) — **export default**; devolve `requireGoogleConnection(action)`, `handleGoogleError(error)`, `isConnected`.
- **Status da integracao Google**: [`v2/frontend/src/hooks/useGoogleIntegration.ts`](../../../frontend/src/hooks/useGoogleIntegration.ts) — `fetchStatus()` le `GET /api/integrations/google/status/`; expoe `status.connected` consumido pelo guard e `status.publishReady`/`status.publishBlockReason` (#1656) consumidos pela pagina "Publicar na agenda" (`pages/Solicitacoes/PublicacaoSetorPage.tsx`).
- **Clientes HTTP**: [`v2/frontend/src/api/me.ts`](../../../frontend/src/api/me.ts) (`getMyPolicies()` le `/api/me/policies/`) e [`v2/frontend/src/api/auth.ts`](../../../frontend/src/api/auth.ts) (`login`/`logout`; `checkAuth()` le `/api/me/`, mas **quem o `App.tsx` usa no boot e `getMe()` de `api/availability.ts`** — `checkAuth` sobrou como checagem pontual de superusuario, via `ehSuperusuario`, em `AdminDAT/UsuariosPage.tsx`, `AdminDAT/GruposPage.tsx` e `AdminDAT/MunicipiosPage.tsx`).
- **Contrato de tipo + runtime guard**: [`v2/frontend/src/types/usuario.ts`](../../../frontend/src/types/usuario.ts) — interface `CurrentUser` e `assertCurrentUserPayload()` (lanca `Invalid /api/me payload shape` se o payload divergir).
- **Wiring / composicao**: [`v2/frontend/src/App.tsx`](../../../frontend/src/App.tsx) carrega `user` e `policies` e os entrega no `AcessoContext.Provider`; [`AppRoutes.tsx`](../../../frontend/src/components/AppRoutes.tsx) (guards por rota), [`AppSidebar.tsx`](../../../frontend/src/components/AppSidebar.tsx) (itens de menu), a Pagina Inicial e os botoes das paginas leem `useAcesso()`.
- **Backend (contraparte autoritativa)**: [`v2/backend/apps/core/views/me.py`](../../../backend/apps/core/views/me.py) (`/api/me/policies/`) e [`v2/backend/apps/core/rbac/policies.py`](../../../backend/apps/core/rbac/policies.py) (`PUBLIC_POLICY_KEYS`, `resolve_public_policies`, `TELAS_DE_ESCOPO`).

## Contratos e invariantes

- **O frontend NUNCA e autoridade.** Toda flag e cosmetica; o backend revalida via `HasPerm`/Policy. Esconder um botao nao substitui o gate de endpoint.
- **SSOT de capability esta no backend.** O frontend reflete `PUBLIC_POLICY_KEYS` recebidas em `/api/me/policies/`; nunca infere acesso a partir de grupo, setor, funcao ou vinculo do `/me` (trava: `acessoSoPorPolicy.test.ts`). O que antes o front calculava sobre o organograma virou policy composta no servidor (PR 7): `access_monthly_availability` (Grade), `access_availability_blocks` (Bloqueios) e `access_travel` (Deslocamentos) = `view_all_availability` OU papel vigente em gerencia ativa listado em `TELAS_DE_ESCOPO` (GERENTE/COORDENADOR/APOIO; Bloqueios tambem FORMADOR) — `_abre_tela_de_escopo` em `rbac/policies.py`. O grupo de setor (Controle, DAT) listado em `TELAS_DE_ESCOPO` so abre a tela com `RBAC_FONTE=uniao` (volta de emergencia do PR 12); no padrao `lotacao` ele e etiqueta. No PR 7 a formula foi copia fiel da do front (provada pessoa a pessoa em `test_rbac_politicas_de_tela.py`); o PR 8 trocou o grupo de funcao pelo papel e o PR 12 tirou o grupo de setor do modo padrao. Quem trabalha numa gerencia com perfil (pacote, ADR-020) recebe as mesmas policies do grupo equivalente e ve as mesmas telas.
- **"Quem e" != "o que pode" (#1269).** `useIdentity` e display-only; autorizacao sai de `useAcesso().caps`. Cumprido desde o PR 7.
- **Paridade de flags `useCapabilities` x `PUBLIC_POLICY_KEYS`.** As 27 keys do backend (`rbac/policies.py`) tem flag nomeada correspondente em `computeCapabilities` (`useCapabilities.ts`); o teste de completude confere a contagem e o conjunto. Policy publica nova = flag nova + caso no teste.
- **Estabilidade do contrato de policy keys.** As keys de `PUBLIC_POLICY_KEYS` sao imutaveis apos release: renomear = breaking change; adicionar = compativel. Remover exige periodo de depreciacao de 2 releases (ver `v2/docs/RBAC_NAMING.md` §9). Os fixtures de `rbac_matrix.test.ts` e o snapshot do backend (`PUBLIC_POLICY_KEYS`) precisam permanecer simetricos.
- **Anonymous nao chama `/me/policies/`.** `App.tsx` so busca policies **depois** de `getMe()` retornar com sucesso, evitando `403`/`401` espurio pre-login. Falha em policies degrada para `[]` (fail-closed: nenhuma capability publica).
- **`policies = []` e ambiguo por design**: significa "ainda carregando" OU "anonymous". A distincao e feita pela flag `loading` em `App.tsx`, nao pelo array vazio.
- **Superuser recebe todas as `PUBLIC_POLICY_KEYS`** via `/me/policies/`; `ehSuperusuario` e so para as regras que SAO do superusuario (importacao pela tela, PA-02, campos so dele, debug), nunca para regra de negocio normal.
- **Semantica das policies e OR.** Usuario obtem a policy se qualquer capability que a satisfaz estiver presente. O conjunto de capabilities que satisfaz uma policy pode mudar sem breaking.
- **Formador owns own**: `access_availability_blocks` inclui o papel FORMADOR vigente (lista em `TELAS_DE_ESCOPO`) porque o escopo do proprio bloqueio (RD-02/RD-03) e garantido pelo queryset do backend.
- **Guard Google (PA-06, controle explicito)**: nenhuma operacao GCal e disparada com conta desconectada. `requireGoogleConnection` retorna `false` e abre modal apenas quando `googleStatus` esta carregado E `connected === false`; com `googleStatus === null` (status ainda desconhecido) ele **permite prosseguir** e delega a deteccao ao backend via `handleGoogleError` (que trata `403` com `code === 'google_not_connected'`). O redirect OAuth sempre carrega `return_to` para voltar a pagina de origem.

## API / Interface

Endpoints backend consumidos (contrato detalhado em `v2/docs/API_REFERENCE.md` e `v2/docs/RBAC_NAMING.md`):

- `GET /api/me/` — perfil do usuario autenticado (`CurrentUser`: `setores[]`, `funcoes[]`, `gerencias[]`, `is_superuser`, `is_superintendencia`, `can_approve_super`, `permissions[]`, ...). `403` com `code: NOT_AUTHENTICATED` se anonimo (o backend so usa `SessionAuthentication`, que nao manda `WWW-Authenticate`; o DRF entao responde 403, nao 401). `gerencias` (PR A, 2026-09-29) = `[{id, rotulo, papeis[]}]` dos vinculos `EquipeGerencia` **vigentes** em gerencia **ativa**, um item por gerencia, ordenados pelo rotulo (nome de tela: `nome_exibicao` ou `nome_setor`). Fica fora do `assertCurrentUserPayload` (payload antigo sem o campo nao derruba o boot; os consumidores usam `?? []`).
  - **Grade Mensal (`FiltersBar`)**: a opcao "Participantes de projetos SUPER" (a antiga "Todas") e as gerencias ativas aparecem so para quem tem a policy `view_all_availability`; os demais veem so as `me.gerencias` com papel GERENTE, COORDENADOR ou APOIO (PR 9: a API recusa o FORMADOR sozinho), com a primeira ja selecionada; sem vinculo e sem policy o select fica desabilitado ("Sem gerencia vinculada"). Grupo de setor (`setores`) e `canSeeAllSectors` **nao** decidem a Grade: o backend autoriza por vinculo (`HasSectorAccess`).
  - **Vinculo de gestao** (PR A; desde o PR 7 calculado no servidor): vinculo GERENTE/COORDENADOR/APOIO vigente em gerencia ativa, mesmo sem grupo de FUNCAO, entra nas policies `access_monthly_availability`, `access_availability_blocks` e `access_travel` (`user_tem_vinculo_de_gestao`, mesma base de `me.gerencias`). FORMADOR por vinculo continua fora. O front nao rele `me.gerencias` para decidir acesso (so a `FiltersBar` usa a lista para escolher a gerencia).
  - **`deve_trocar_senha`** (02/10/2026): `true` quando a senha em uso foi definida por outra pessoa. Opcional em `CurrentUser` e fora do guard `isCurrentUserPayload` (payload antigo sem o campo nao derruba o login); a tela testa `=== true`. Com ele ligado o backend so aceita a troca de senha (ver [rbac.spec](../backend/rbac.spec.md)).
  - **`aviso_senha_redefinida`** (F1, 16/10/2026): `{por, em}` ou `null`; quem redefiniu a senha e quando (`dd/mm/aaaa`). Opcional e fora do guard; o `App.tsx` guarda o valor junto com `trocaPendente` e passa para a `TrocaSenhaObrigatoriaPage` (prop `aviso`).
  - **`redefinicoes_senha`** (F1, revisão): lista `{por, em}` das redefinições por outra pessoa nos últimos 30 dias (AuditLog), da mais nova; não some com a troca de senha. Opcional e fora do guard; o `App.tsx` passa para a `TrocaSenhaObrigatoriaPage` (prop `redefinicoes`) e a `PerfilPage` lê do `user`.
- `GET /api/me/policies/` — array ordenado de strings (subset de `PUBLIC_POLICY_KEYS`); `403` (`NOT_AUTHENTICATED`) se anonimo; superuser recebe todas. Nunca expoe codenames brutos de capability.
- `GET /api/integrations/google/status/` — `{ connected, googleEmail, tokenExpiry, expiresInDays, isExpired, defaultCalendarId, publishReady, publishBlockReason, reconnectRequired }` (dominio camelCase, apos `normalizeGoogleStatus`). `publishBlockReason` e `'no_setor_scope' | 'google_not_connected' | 'google_calendar_not_configured' | null` (#1656); payload antigo sem esses campos normaliza para `publishReady=false` e `publishBlockReason=null` (acoes de publicacao desabilitadas). `reconnectRequired` (#2039) e `true` quando o sistema removeu a conexao porque o Google revogou o acesso (`invalid_grant`) e a pessoa nao reconectou; payload antigo sem o campo normaliza para `false`. O `GoogleIntegrationCard` (`components/google/GoogleIntegrationCard.tsx`) mostra, desconectado com `reconnectRequired`, um `Alert` de aviso (`role="alert"`) acima de "Conectar conta Google"; conectado, e sempre a tag "Conectado" — `isExpired`/`expiresInDays`/`tokenExpiry` descrevem o access token de 1h, renovado sozinho pelo refresh token, e nao geram mais alarme ("Expirado", "Expira em N dias", "Reconectar conta") em nenhum modo.
- `GET /api/oauth/google/start/?return_to=<path>` — inicia o fluxo OAuth (redirect do browser, nao XHR).

Interface publica dos hooks:

- `useAcesso(): { caps: Capabilities; ehSuperusuario: boolean; loading: boolean }` — leitura do `AcessoContext`. `ehSuperusuario(user)` (mesmo arquivo) e o helper unico de `is_superuser`.
- `useCapabilities(policies: readonly string[]): Capabilities` — `can(key)` + 27 flags `can*` 1:1 com as policy keys (PR 7: `canAccessMonthlyAvailability`, `canAccessAvailabilityBlocks`, `canAccessTravel`, `canExecuteRestrictedOperations`, `canCreateSolicitationWithoutPurchase`). Sem `user`.
- `useIdentity(user: CurrentUser | null): Identity` — flags de setor/funcao + `displayName` + `badge`. **Display-only.**
- `useGoogleGuard({ googleStatus, returnTo })` (**export default**) `: { requireGoogleConnection, handleGoogleError, isConnected }`.
- `useGoogleIntegration(): { status, loading, error, fetchStatus, disconnect }`.

Guard de rota (componente, nao hook):

- `<RequirePolicy policy="<key>" policies={policies}>` (ou `policy={['a', 'b']}`: qualquer uma) ou `<RequirePolicy allow={<boolean>}>`; `allow` tem precedencia, e sem nenhum dos dois o resultado e **negar** (`RequirePolicy.tsx`).

## Fluxos principais

**Bootstrap de autorizacao (1x por mount, sem polling de RBAC):**

1. `App.tsx` chama `getMe()` (= `/api/me/`); o payload passa por `assertCurrentUserPayload` (em `api/availability.ts`/`auth.ts`). Sucesso => `setUser`. Excecao: `deve_trocar_senha === true` => `setTrocaPendente(true)`, `user` fica nulo e o passo 2 **nao** roda (o servidor recusaria `/api/me/policies/` com `PASSWORD_CHANGE_REQUIRED`); o App mostra so a `TrocaSenhaObrigatoriaPage` e refaz este passo quando a troca termina.
2. So entao chama `getMyPolicies()` (= `/api/me/policies/`); sucesso => `setPolicies`. Erro nao-auth => log `warn` + degrada para `[]`.
3. `App.tsx` monta `montarAcesso(policies, user, loading)` e o entrega no `AcessoContext.Provider`.
4. Menu (`AppSidebar.tsx`), rotas (`<RequirePolicy policy=...>` em `AppRoutes.tsx`), Pagina Inicial e botoes de pagina leem `useAcesso()`. Rota negada renderiza o `Result` generico `DefaultForbidden` (OWASP — nao revela recurso/permissao necessaria).

**Atualizacao de RBAC**: nao ha polling das capabilities. Mudancas de permissao so refletem apos reload/relogin (logout faz `window.location.reload()`). Os pollings existentes em `App.tsx` sao de dados operacionais e nao re-buscam policies: `useGCalAlertsPolling` e gated por `caps.canAccessControleSection` e `useUnreadNotificationsPolling` por `caps.canManageInternalActions` (`App.tsx`, policies). Os dois usam `hooks/usePolling.ts`, que para com a aba oculta, nao abre carga nova com outra em voo; nenhum dos dois trata o 429 (nao usam o `pausar` do hook) (regras em [pages.spec](./pages.spec.md), "Telas que se atualizam sozinhas").

**Guard Google (caminho feliz + erro):**

1. Pagina (ex: PreAgenda) obtem `googleStatus` via `useGoogleIntegration` e instancia `useGoogleGuard({ googleStatus, returnTo })`.
2. Antes da acao: `if (!requireGoogleConnection('publicar eventos')) return;` — se desconectado, abre `Modal.confirm` e (no `onOk`) redireciona para `/api/oauth/google/start/?return_to=...`.
3. No `catch` da chamada: `if (handleGoogleError(error)) return;` — trata `403 google_not_connected` reabrindo o modal; demais erros seguem o fluxo normal de mensagem.

## Decisoes relacionadas (ADRs)

- `v2/docs/RBAC_NAMING.md` §9 — Policy Resolution Rules, vocabulario canonico, `PUBLIC_POLICY_KEYS`, stability rules e contrato de `GET /api/me/policies/` (Epics 4.1–4.4).
- `v2/docs/rbac_authorization_matrix.md` — matriz canonica modulo×papel/capability×grupo (decisoes D7–D9; D10–D17 §6 Admin-driven Group×Cap; §7 PR 7, telas por policy).
- Epic 3 / Issue #1228 — Capability Policy Layer no frontend. PR 7 das permissoes (15/10/2026) — fonte unica `AcessoContext`; `useCanAccess`/`usePermissions` apagados; excecoes E1–E3 da Pagina Inicial aprovadas pelo dono.
- PR 3 / PR 10 hardening RBAC (2026-04-29/30) — `access_solicitation_approvals` como fonte exclusiva de `canAccessApprovals` (fallback `can_approve_super` removido do contrato do hook).

## Testes que cobrem

- [`v2/frontend/src/hooks/__tests__/useCapabilities.test.ts`](../../../frontend/src/hooks/__tests__/useCapabilities.test.ts) — `computeCapabilities` (paridade flag x policy key, completude: 27).
- [`v2/frontend/src/test/atoresRbac.ts`](../../../frontend/src/test/atoresRbac.ts) — os 10 atores de `matrix.py` (payload de /me + policies medidas no backend) e as personas por pacote ("Ana" ≡ DAT, "Bruno" ≡ Controle): fonte unica das matrizes persona × tela.
- [`v2/frontend/src/test/lint/acessoSoPorPolicy.test.ts`](../../../frontend/src/test/lint/acessoSoPorPolicy.test.ts) — a trava (controles positivos, allowlist por identidade).
- [`v2/frontend/src/pages/Home/__tests__/HomePage.acesso.test.tsx`](../../../frontend/src/pages/Home/__tests__/HomePage.acesso.test.tsx) — cartoes da Pagina Inicial por ator (excecoes E1–E3 anotadas).
- [`v2/frontend/src/hooks/__tests__/useIdentity.test.ts`](../../../frontend/src/hooks/__tests__/useIdentity.test.ts) — `computeIdentity` (setor/funcao, `displayName`, prioridade do `badge`).
- [`v2/frontend/src/hooks/__tests__/rbac_matrix.test.ts`](../../../frontend/src/hooks/__tests__/rbac_matrix.test.ts) — **matriz viva** parametrizada por ator: capabilities derivadas das policies medidas; falha em drift.
- [`v2/frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx`](../../../frontend/src/components/__tests__/AppRoutes.access-by-profile.test.tsx) — guards de rota por perfil (10 atores x 16 rotas criticas, incluindo Editar e as 3 de Compras) e personas por pacote.
- [`v2/frontend/src/components/access/__tests__/RequirePolicy.test.tsx`](../../../frontend/src/components/access/__tests__/RequirePolicy.test.tsx) — o guard em si: concede/nega e nao pisca 403 enquanto `loading`.
- [`v2/frontend/src/components/__tests__/AppSidebar.menu.test.tsx`](../../../frontend/src/components/__tests__/AppSidebar.menu.test.tsx) — menu por ator (topo e filhos de Dashboards, DAT, Controle e Solicitacoes) e personas por pacote; o payload de /me sozinho nao abre item.
- Contraparte backend: `v2/backend/apps/core/tests/test_me_policies.py` e `test_rbac_policies_contract.py` provam o contrato de `/api/me/policies/`; `test_rbac_politicas_de_tela.py` prova que cada policy nova vale sse a formula antiga do front valia (matriz, grupos, vinculos, pacotes).

## Pontos de atencao / dividas conhecidas

- **`useGoogleGuard.tsx` sem teste unitario** — nao ha `useGoogleGuard.test.*` (apenas `useGoogleIntegration.test.ts`). O contrato critico de "permitir prosseguir quando `googleStatus === null`" + tratamento de `403 google_not_connected` nao tem cobertura direta. GAP a fechar.
- **TOCTOU benigno no guard Google**: o status pode estar stale entre `fetchStatus` e a acao; o `handleGoogleError` no `catch` e a rede de seguranca (backend e a autoridade). Por design, mas significa que a UX pode mostrar o modal so apos a tentativa.
- **Sem invalidacao de RBAC em runtime**: mudanca de setor/funcao/grupo de um usuario logado so reflete apos reload/relogin (nao ha refetch de `/me/policies/`). Aceitavel para o tenant atual; revisitar se surgir admin que altere permissoes em tempo real.
- ✅ **Grupos de funcao nas telas de escopo — RESOLVIDO no PR 8 e no PR 12.** No PR 7 os grupos Gerente, Coordenador, Apoio e Formador abriam Grade/Bloqueios/Deslocamentos (copia fiel da regra antiga). O PR 8 trocou o grupo de funcao pelo papel vigente (`TELAS_DE_ESCOPO`), e o campo coordenador opcional do `NewSolicitacaoWizard` saiu da allowlist da trava; o PR 12 deixou o grupo de setor valer so com `RBAC_FONTE=uniao`. Hoje a tela de escopo abre por capacidade ou papel vigente (`_abre_tela_de_escopo`).
- ✅ **Assistente Administrativo sem o setor Controle (R1 do plano) — RESOLVIDO no PR 8.** No PR 7 o grupo tinha capacidades do Controle (compras, pre-agenda, rotinas) e abria o submenu Controle, Compras (`view_compras_stats`), a consulta periodica ao Google e o cartao do Google da Pre-agenda. A migration `0125_funcoes_sem_capacidade` tirou toda capacidade dos grupos de funcao, entao o grupo Assistente Administrativo nao soma nada nem com `RBAC_FONTE=uniao`. Hoje vale o pacote do vinculo EQUIPE/GERENTE (ex.: gerencia CONTROLE), os direitos do papel vigente e o superusuario (SSOT: [`rbac.spec.md`](../backend/rbac.spec.md), itens do PR 12 e da formula da uniao).
- **`policies = []` ambiguo**: o `loading` do `AcessoContext` distingue "carregando" de "sem acesso"; no App ele e sempre `false` depois do boot (o App mostra o carregando antes).

## Divergencias conhecidas

Rastreadas no documento vivo [`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md).

- **`M05-07` (#1655) — RESOLVIDO no PR 7 das permissoes (excecao E1, dono 15/10/2026).** Os cartoes "Enviar Solicitacao" e "Minhas Solicitacoes" e o KPI seguem `create_solicitation`, o mesmo gate da rota. Era: a `HomePage` decidia esses cartoes por `canCoordenador` (`is_superuser || Coordenador/Apoio || DAT`, flag de organograma do `usePermissions`), enquanto as rotas de destino exigiam `create_solicitation`: o DAT via um atalho que dava "Recurso indisponivel" e o Gerente (com a policy) nao via o atalho.
