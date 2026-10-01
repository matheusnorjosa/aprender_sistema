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
  - v2/frontend/src/components/ResponsiveTable.tsx
  - v2/frontend/src/components/AcoesLinha.tsx
  - v2/frontend/src/components/textoDaTag.ts
  - v2/frontend/src/hooks/useResponsive.ts
  - v2/frontend/src/test/larguraTela.ts
  - v2/frontend/src/components/AppHeader.tsx
  - v2/frontend/e2e/checklist/menu-lateral-teclado.spec.ts
  - v2/frontend/e2e/checklist/accessibility.spec.ts
  - v2/frontend/e2e/checklist/mais-acoes-teclado.spec.ts
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
- **Aprovações = policy exclusiva.** `/solicitacoes/aprovacoes` depende **somente** da policy pública `access_solicitation_approvals` (`AppRoutes.tsx`). O legacy `can_approve_super` foi removido do contrato do FE (PR 10 hardening RBAC). A página carrega `getMe()` em paralelo com as policies para a segregação (PA-02, PR B1): a linha da **própria** solicitação (não-superuser) sai sem checkbox e sem Aprovar/Reprovar, com a Tag "Sua solicitação" e o Tooltip "Outra pessoa aprovadora precisa decidir" — o backend recusa com 403 `self_approval_forbidden` de qualquer forma. Regra do dono (30/09): para a gerência da Superintendência por vínculo, o backend só aceita decidir solicitação do fluxo SUPER da Superintendência; a tela não esconde Aprovar/Reprovar nas outras linhas (com a trava de cadastro, toda pendente SUPER está nesse escopo — 0 fora em 30/09) e, se aparecer uma, o clique recebe o 403 `out_of_approval_scope` com a mensagem e o lote conta o item em "N erro(s)".
- **Redirects preservam deep-links.** As 6 URLs legadas (`/aprovacoes`, `/disponibilidade`, `/bloqueios`, `/deslocamentos`, `/meus-eventos`, `/dat/importacao`) redirecionam com `<Navigate replace>` para a rota canônica sob `/solicitacoes/*` ou `/dat/importacoes`.

## Padrão responsivo

**A regra (dono, 29/09/2026):** nenhuma tela rola na horizontal, nem a página nem dentro de tabela, grade ou card, e nenhum conteúdo fica cortado sem reticências, em **360, 768, 1024 e 1280 px**. A largura de 1024 é a de um notebook de 1366 px com escala de 125% no Windows. Reflow sem rolagem também é critério da WCAG 2.1 (1.4.10). Esta seção é a SSOT do padrão.

- **Como se mede.** Três critérios: a página não rola (`documentElement.scrollWidth - clientWidth ≤ 0`); nenhum elemento com `overflow-x` auto ou scroll tem `scrollWidth - clientWidth > 1` (só o primeiro critério não enxerga a tabela do AntD, que rola dentro de `.ant-table-content`); e nenhum elemento com `overflow-x` hidden ou clip corta conteúdo sem `text-overflow: ellipsis`. No corte ficam de fora campos de formulário, caixas invisíveis ou sem largura, `aria-hidden` e uma lista curta de internos do AntD e do Leaflet que escondem conteúdo de propósito (`CORTE_PERMITIDO`; desde o C1, também os itens da sidebar recolhida, cujo rótulo vai para o Tooltip, e o texto `sr-only`, com um controle que prova que a mesma caixa sem a classe continua sendo corte).
- **Barra de rolagem.** A 360 e 768 px a barra é sobreposta, como no celular. A 1024 e 1280 px ela ocupa 15 px, como no Chrome do Windows: o Chromium headless esconde a barra (`--hide-scrollbars`), e o spec de desktop tira esse flag.
- **Trava 1, Playwright.** [`sem-rolagem-horizontal.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.spec.ts) (360 e 768) e [`sem-rolagem-horizontal.desktop.spec.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.desktop.spec.ts) (1024 e 1280) abrem cada rota de `AppRoutes` com um perfil que a acessa, mais a tela de login e as vistas alternativas declaradas (Coordenadores "Lista" e "Por área", Mapa "Lista" e, desde o C1, Usuários `#expandida`, a linha expandida a 360, 768 e 1024 px, e `#detalhe`, o Drawer, procurado fora de `main` com `foraDeMain` porque o AntD o põe por portal; desde o C2, `#expandida` das 7 rotas de Admin DAT do C2, nas larguras em que há coluna escondida). `/dat/admin/grupos` é medida com o superusuário, o único que vê a coluna Ações; setores e funções, o mesmo componente, com o perfil DAT. A medição e as pré-condições ficam em [`sem-rolagem-horizontal.medicao.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.medicao.ts).
- **Pré-condições: a tela, não só a casca.** Antes de medir, a rota tem de mostrar o seu título em `main`, a casca autenticada (header com "Sair"; a tela de login também tem `main`), nenhum Result/Alert de erro, "Algo deu errado" ou "Recurso indisponível", a linha de tabela com o texto do seed e nenhuma requisição da mesma origem com falha (4xx, 5xx ou `requestfailed`). Controles provam que cada uma reprova o seu caso (chunk da página abortado, sessão perdida, API com 403, erro da própria página). Sem isso, uma tela quebrada passaria por "sem rolagem" ou, estando em `PENDENTES`, mandaria tirar a combinação da lista.
- **Dados.** Vêm de `seed_frontend_contract_data`, com textos de 80+ caracteres em todo campo de tabela, porque tabela vazia nunca estoura. Rotas, títulos, textos do seed, vistas alternativas e aliases ficam em [`sem-rolagem-horizontal.rotas.ts`](../../../frontend/e2e/checklist/sem-rolagem-horizontal.rotas.ts). [`AppRoutes.semRolagemHorizontal.test.ts`](../../../frontend/src/components/__tests__/AppRoutes.semRolagemHorizontal.test.ts) lê o `AppRoutes` pela árvore do TypeScript e reprova rota nova sem entrada lá; ele também confere que cada texto procurado existe no seed do backend. O que não é medido fica em `NAO_MEDIDOS`, com o motivo (Home com outros perfis, modo Google da Pré-agenda, passos do wizard, ImportUploader depois da validação, modais).
- **Trava 2, lint.** `Table` do AntD só entra por `components/ResponsiveTable`, criado no C1 e isento para sempre. A regra cobre os barris (`antd`, `antd/es`, `antd/lib`, com `/index` ou `.js`, e o bundle de `antd/dist`), os caminhos profundos de `antd/*/table` (menos a `interface`, só tipos), o `rc-table`, e `import()`/`require` de antd. Os arquivos que já importavam `Table` (27 no C0, 26 depois do C1, 21 depois do C2) estão em [`eslint.tabela-antd-allowlist.js`](../../../frontend/eslint.tabela-antd-allowlist.js), cada um com o PR do Programa C que o tira; o tamanho dela é exatamente `TETO_ALLOWLIST` (21), que só desce. [`tabelaAntdRestrita.test.ts`](../../../frontend/src/test/lint/tabelaAntdRestrita.test.ts) tem um controle por forma de contorno e compara identidade: o conjunto de arquivos de `src/` que importam `Table`, medido com os comentários `eslint-disable` desligados, tem de ser exatamente a allowlist.
- **Referência: o Chromium Linux da CI.** A medição que vale é a do job `[required] checklist tests`. As fontes do Linux (Liberation/DejaVu) são mais largas que a Segoe UI do Windows, e uma tabela no limite pode rolar só lá. Essas combinações vão para `PENDENTES_SO_LINUX`, com o motivo em comentário, e o spec só as trata como falha esperada quando `process.platform === 'linux'`: rodando no Windows elas passam, sem "Expected to fail, but passed".
- **Dívida medida (`PENDENTES`).** Em 29/09/2026, 126 combinações rota × largura rolavam ou cortavam em todas as plataformas, em 34 chaves (31 das 42 rotas medidas, mais 3 vistas alternativas), e mais 2 só no Linux da CI (`/dashboards` e `/dashboards/gcal` a 1280 px, por +18 e +4 px); 26 chaves falham até a 1280 px no Windows e 28 na CI. O C1 (30/09/2026) tirou 9: as 4 de `/dat/admin/usuarios` e 5 que a sidebar nova liberou (Mapa e Mapa "Lista", edição de solicitação e Coordenadores "Por área" a 768 px; Notificações Internas a 1024 px), conferidas com texto alargado em até 1,5 px por letra para não voltarem na fonte mais larga da CI. O C2 (30/09/2026) tirou 27: todas as combinações de `/dat/admin/grupos`, `/setores`, `/funcoes`, `/gerencias`, `/municipios` e `/produtos` (4 cada) e de `/dat/admin/projetos-gerais` (3; a 1280 px ela já não rolava). Ficam 90 + 2 em 26 chaves; 19 delas ainda falham a 1280 px no Windows. `/dat/admin/projetos` segue em `PENDENTES`. Cada combinação roda com `test.fail`: quando a tela é consertada, o teste passa a falhar e a combinação tem de sair da lista. [`semRolagemHorizontal.pendentes.test.ts`](../../../frontend/src/components/__tests__/semRolagemHorizontal.pendentes.test.ts) trava as duas listas: toda combinação tem de estar na linha de base medida (a só-Linux na sua), uma combinação não pode estar nas duas, e o tamanho somado é exatamente um teto que só desce. A `LINHA_DE_BASE` já não tem as 9 do C1 nem as 27 do C2, e cada PR que tira uma combinação de `PENDENTES` a tira também da linha de base: o que ficasse lá poderia voltar a `PENDENTES` sem o ratchet ver (um caso por combinação do C1 e do C2 prova que ela não volta). A lista e a allowlist só encolhem, e o Programa C (C1 a C7) zera as duas.
- **Tela nova ou alterada.** Nada de `scroll={{ x }}` nem de largura fixa maior que a tela. A tabela é o `ResponsiveTable`, as ações são o `AcoesLinha` e o detalhe segue o piloto de Usuários (abaixo).

### O padrão (C1, piloto em `/dat/admin/usuarios`)

- **`ResponsiveTable`** ([`components/ResponsiveTable.tsx`](../../../frontend/src/components/ResponsiveTable.tsx)): a tabela do app. O tipo não aceita `scroll` nem coluna `fixed` (o teste tem `@ts-expect-error` para as duas, conferido por `npx tsc --noEmit -p tsconfig.eslint.json`, porque o tsconfig do build exclui os testes). Cada coluna declara a partir de que largura aparece com o `responsive` do AntD, pela constante `VISIVEL_A_PARTIR` (`sm` 576, `md` 768, `lg` 992, `xl` 1200, `xxl` 1600); sem `responsive`, aparece sempre. O que está escondido na largura atual aparece na linha expandida, como `<Descriptions column={1}>`, com o `title` (obrigatório) e o `render` da própria coluna: nada some da tela. `tableLayout="fixed"`, `width` só nas colunas estreitas e `ellipsis` nas de texto. Densidade `middle`, e `small` abaixo de `md`. A prop obrigatória `nomeDaLinha(registro)` nomeia o botão de expandir, "Expandir linha de Maria", com `aria-expanded` e a classe `.ant-table-row-expand-icon` do AntD (o +/-); o nome não usa "detalhes", que é o do botão do nome na mesma linha ("Ver detalhes de Maria"). A coluna do botão tem cabeçalho só para leitor de tela ("Detalhes", `sr-only`).
- **Prioridades.** Sempre na linha: identidade (o nome, que abre o detalhe), estado e ações. As demais sobem por largura (em Usuários: E-mail a partir de `md`, Setor de `lg`, Função de `xl`). **Nunca na grade, só no detalhe:** ID, CPF, username (em produção é o CPF), telefone e textos longos (cargo, observações).
- **`AcoesLinha`** ([`components/AcoesLinha.tsx`](../../../frontend/src/components/AcoesLinha.tsx)): botões só de ícone, com Tooltip e nome acessível "rótulo: alvo" (ex.: "Editar: Maria Aparecida"). Até 3 ícones; da 4ª ação em diante, o menu "Mais ações". No celular (abaixo de `sm`, `compacto`), todas as ações ficam no menu, num botão só. A largura da coluna vem de `larguraAcoesLinha(quantidade, compacto)`. O Tooltip abre no hover e no foco, e o Esc o fecha sem tirar o foco (WCAG 1.4.13; ele abre quando um modal devolve o foco ao ícone). Escolher uma ação no menu devolve o foco ao "Mais ações", e o modal que a ação abre o devolve ali ao fechar. Pelo Enter, o menu não reabre: o rc-menu chama a ação já no keydown, e o `AcoesLinha` cancela esse keydown (sem isso, o keypress caía no botão, virava clique e reabria o menu por cima do modal). Teste no Chromium, onde o jsdom não chega: [`mais-acoes-teclado.spec.ts`](../../../frontend/e2e/checklist/mais-acoes-teclado.spec.ts), a 360 px em Usuários, no projeto `checklist`.
- **Detalhe por assunto.** Um `Drawer` aberto pelo nome (link na cor da marca: o azul padrão do link do AntD dá 4,1:1 no branco) mostra tudo, sem corte, em seções: em Usuários, Dados pessoais · Lotação · Acesso. A edição continua no modal de sempre (botão "Editar" no detalhe e na linha). Histórico ficou de fora: o `AuditLog` filtra por quem agiu (`usuario`), não pelo usuário alterado.
- **Usuários: ordem e login.** A lista abre ordenada pelo nome (`ordering=first_name,last_name,id`, e não pelo username, que é o CPF); a coluna Nome ordena no servidor nos dois sentidos (`-first_name,-last_name,-id` na decrescente) e E-mail também, com o id desempatando (`email,id`). A ordenação é controlada (`sortOrder`): o Nome já abre com a seta e o `aria-sort` crescentes, a ordem escolhida vale na busca, na paginação, no Atualizar, no salvar e no excluir, e limpar a ordenação volta ao padrão. Coluna que ordena no servidor segue esse molde, para a seta e o `aria-sort` mostrarem a ordem que a lista tem. O login aparece mascarado no detalhe e no campo Username do modal Editar quando é CPF (só dígitos ou `000.000.000-00`), com a regra do `cpf_masked` do backend (`***.***.` e os 6 últimos), para login e CPF mascarados não se completarem; username que não é CPF aparece como está. O form guarda o valor real, que o Salvar manda como antes. Excluir e Redefinir senha identificam a pessoa pelo nome.
- **Tags com cor.** O AntD pinta o preset com a cor 7 sobre a cor 1, e green, gold e orange reprovam 4,5:1; o texto dessas tags vai para `TEXTO_DA_TAG` (green-8, orange-8, gold-9), em [`components/textoDaTag.ts`](../../../frontend/src/components/textoDaTag.ts) desde o C2, usado por Usuários e pelas telas do C2.
- **Layout.** A sidebar depende da janela ([`useResponsive`](../../../frontend/src/hooks/useResponsive.ts)): `sobreposta` abaixo de 992 px (fechada, abre por cima do conteúdo), `recolhida` de 992 a 1279 px (só ícones, 80 px; o botão do header a abre por cima) e `aberta` a partir de 1280 px (250 px). Os breakpoints do AntD medem a janela, não o contêiner, por isso a sidebar só ocupa 250 px quando sobra largura. `theme.screens` do Tailwind usa as mesmas quebras do AntD. Cabeçalho de página com `flex flex-wrap gap-3`.
- **Sidebar por cima do conteúdo** (sobreposta aberta, ou recolhida aberta pelo ☰; `sidebarSobrepondo`): funciona como diálogo. O foco vai ao 1º link; cabeçalho e conteúdo ficam `inert`; fecham a navegação o Esc, o fundo escuro, o botão "Fechar menu" (dentro da navegação, só enquanto ela sobrepõe, fora de qualquer `inert`: com o ☰ inerte e o fundo `aria-hidden`, é a saída de quem usa leitor de tela no toque), escolher um item e a troca de rota por fora do menu; ao fechar, o foco volta ao ☰ ("Menu principal", com `aria-expanded` e `aria-controls`). O Enter num link navega: o rc-menu chama o `onClick` do Menu já no keydown, e a sidebar ignora esse evento e fecha pelo clique que o `<a>` gera (fechando no keydown, o foco ia ao ☰ antes da ação padrão do link). Sobreposta fechada, a navegação fica `inert`. O foco nos links, nos títulos de submenu, no `<ul>` raiz do menu (parada de Tab do rc-menu) e no "Fechar menu" tem anel de duas cores (branco por fora, preto por dentro, `App.css`), que dá 3:1 em todo fundo da sidebar; o anel padrão do AntD ali dá 1,73:1. Testes: `App.menuSobreposto.test.tsx`, `AppSidebar.menu.test.tsx` e, no Chromium (o jsdom não reproduz a ordem keydown, foco e clique), [`menu-lateral-teclado.spec.ts`](../../../frontend/e2e/checklist/menu-lateral-teclado.spec.ts), no projeto `checklist` do job `[required] checklist tests`.
- **Testes.** O mock de `matchMedia` ([`src/test/larguraTela.ts`](../../../frontend/src/test/larguraTela.ts), instalado no `setup.ts`) avalia `min-width`/`max-width` contra 1280 px por padrão; `definirLarguraTela(px)` muda a largura (e o `innerWidth`) no teste. Sem ele, toda coluna com `responsive` sumiria nos testes.

### C2: Admin DAT

Grupos RBAC, Setores e Funções (um componente, `GruposPage`), Gerências, Municípios, Produtos e Projetos Gerais seguem o padrão: `ResponsiveTable`, `AcoesLinha` (Editar e Excluir; no celular, o menu "Mais ações"), cabeçalho com `flex flex-wrap` e busca com `maxWidth: 100%`.

- **Na linha e na linha expandida.** Sempre na linha: o nome (em Gerências, o setor pelo `rotulo`), o estado e as ações; as demais colunas sobem por largura e o que some vai para a linha expandida. O ID saiu da grade e não aparece em outro lugar. Não há Drawer: as telas têm poucos campos, e o que já era só do formulário (código interno, descrição de Gerências e Projetos Gerais, divisor, multiplicador) continua só no modal de edição. A Descrição de Produtos e o Rótulo nas planilhas de Gerências só entram na linha a partir de `xxl` (1600 px); abaixo disso, ficam na linha expandida.
- **Nome acessível.** O alvo das ações e da linha expandida é o nome do registro; em Municípios, "Nome - UF", porque há municípios de mesmo nome em UFs diferentes.
- **Identidade inteira.** Sem Drawer, a coluna de identidade (o nome; em Gerências, o setor) quebra linha em vez de cortar com reticências, nas 5 telas: o nome aparece inteiro na grade, em toda largura. Abaixo de `sm`, Municípios mostra a UF junto do nome e Produtos o código (a chave única; o nome pode repetir).
- **Grupos sem superusuário.** A coluna Ações não aparece, e um aviso único acima da tabela diz "Somente superusuário cria, edita ou exclui." (a regra P0-1 não mudou). Para grupo reservado, a ação vira "Excluir (reservado)", com cadeado e sem cor de perigo: antes o botão ficava desabilitado; agora a ação mostra o aviso de exclusão bloqueada, também numa região `role="status"` para o leitor de tela (o toast do AntD não é região viva), e não abre confirmação (o `AcoesLinha` não tem estado desabilitado).
- **Membros de Grupos.** O Salvar grava os membros por full-replace, a partir da lista de usuários carregada à parte. Sem essa lista inteira carregada, o campo fica desabilitado, o modal diz que os membros não serão alterados (com o motivo e "Tentar de novo") e o Salvar não chama `sync-members`. O resumo distingue carregando ("aguardando a lista de usuários…") de falhou ("não carregou") e, sem a lista, não mostra contagem de membros; o Salvar sem a lista é aviso (`message.warning`), não sucesso. O Editar põe os membros com o campo não tocado (`setFields` com `touched: false`): o modal não é destruído ao fechar, e o `setFieldsValue` marcava o campo como tocado a partir da 2ª abertura; aí a lista que chegava depois ("Tentar de novo", a recarga depois de salvar) não entrava, e o Salvar mandava o campo vazio ou velho (`user_ids: []`, ou menos membros). O recarregamento da lista "velha" (2 minutos) ao abrir o Editar saiu: reabria esse caminho. Os membros aparecem pelo nome e e-mail, nunca pelo username (CPF). Em Funções, as frases concordam no feminino ("Nenhuma função", "esta função", "Nome da Função").
- **Falha ao carregar.** O `ResponsiveTable` aceita `erro` e `onTentarDeNovo`: o motivo e "Tentar de novo" aparecem no lugar das linhas, e não "Não há dados", e a paginação some (o total seria o da carga anterior). Se o "Tentar de novo" carrega, as linhas tomam o lugar do botão e o foco que estava nele vai para a tabela (contêiner com `tabIndex=-1`, fora do Tab), não para o body; quem já saiu do botão fica onde está. O vazio da tela (`locale.emptyText`, o que diz o que fazer) sai na cor de texto secundário (`colorTextSecondary`): o AntD pinta o vazio da tabela com a de texto desabilitado (#bfbfbf, 1,83:1 no branco). As 5 telas usam, e o título perde a contagem enquanto a lista falha ("(0)" diria que não há registro). O erro de validação do salvar mostra o motivo do backend (`errors` por campo) no toast e no campo do formulário.
- **Opções que não carregaram.** [`FalhaAoCarregar`](../../../frontend/src/components/FalhaAoCarregar.tsx): Alert (`role="alert"`) com o motivo e "Tentar de novo" logo abaixo do campo (`extra` do `Form.Item`), nunca no `notFoundContent` do Select (lá o botão ficava num portal fora do Tab e o alerta dentro do listbox, `aria-required-children` critical no axe); o Select fica desabilitado enquanto está sem opções por erro. O erro fica na tela até a resposta, com o botão em loading: se falhar de novo, o foco continua no botão; se carregar e o foco ainda estiver nele (o aviso sai e o foco cai no body), vai para o campo que carregou, e quem já foi digitar em outro campo durante a espera fica onde está (a tela atualiza com `flushSync`, para o Select já estar habilitado; antes o aviso sumia no clique e o foco caía no body, fora do modal). O nome do botão diz o que recarrega ("Tentar de novo: carregar os projetos", "… as coleções", "… os setores"; o texto visível segue "Tentar de novo", no começo do nome, WCAG 2.5.3): o modal de Produtos tem dois. Usam: Setor canônico (Gerências), Projeto e Coleção (Produtos) e o filtro "Filtrar por projeto" de Produtos, cujo aviso fica na página, abaixo do cabeçalho. Com o filtro de projeto sem resultado, a grade diz "Nenhum produto para o projeto X." e oferece "Limpar filtro de projeto", como a UF em Municípios; com a busca também, cita as duas ("Nenhum produto para "abc" no projeto X.") e oferece "Limpar busca e filtro de projeto" (o campo de busca é controlado, para esvaziar junto). O botão some com o clique, e o foco vai para a busca.
- **Acessibilidade (axe).** `/dat/admin/usuarios` e as 7 rotas do C2 estão no axe (`wcag2a`, `wcag2aa`, `wcag21aa`, sem violação `serious` ou `critical`) do job `[required] checklist tests`, em [`accessibility.spec.ts`](../../../frontend/e2e/checklist/accessibility.spec.ts), a 360 e 1280 px, com login real e as linhas do seed (o `entrar` e o `verificarTela` do spec de rolagem). O mesmo arquivo mede o estado de erro das opções (500 simulado): o modal de Gerências sem os setores, a página de Produtos sem os projetos e o modal de Produtos sem os projetos e as coleções, com axe, o Tab chegando a cada "Tentar de novo" e o foco indo ao campo quando a carga volta; e o vazio de Produtos com filtro de projeto e busca (o contraste do texto do vazio é medido a 1280 px: a 360 o axe não decide o fundo da tabela e deixa o texto em `incomplete`). Violação que já existia e fica registrada: o Form.Item obrigatório passa `aria-required="true"` ao Select, e o rc-select 14.16 (antd 5.29) o põe no combobox e também no div raiz, que não tem role (axe: [critical] `aria-allowed-attr`, no Projeto de Produtos). O leitor de tela lê o do combobox; o conserto pede mexer no rc-select, e o teste tira da conta só esse nó.
- **Excluir.** A confirmação cita o nome do registro e abre com o foco no Cancelar (`autoFocusButton: 'cancel'`). A contagem de projetos do backend é só dos ativos: em Gerências, com projetos ativos vinculados, excluir só mostra o aviso "Não é possível excluir" (cita os ativos e diz que gerência com projetos ou equipes vinculados, mesmo inativos, não pode ser excluída), com "Entendi" e sem "Sim, excluir", porque a contagem já prova a recusa; sem projetos ativos, a confirmação normal, e equipe ou projeto inativo vinculado (FK `PROTECT` de Projeto e de EquipeGerencia) volta no 409; Projetos Gerais diz que os projetos da família, ativos e inativos, ficam sem projeto geral (`SET_NULL`). Registro em uso (`ProtectedError`) volta 409 com os tipos de registro que impedem ("Este registro não pode ser excluído porque está em uso (Projetos)."), nunca os registros em si, e a tela mostra esse motivo no toast.
- **Estado.** As 5 telas com a coluna "Situação", com Ativo/Inativo (`TEXTO_DA_TAG`), como em Usuários. "Usa AVALIAR" de Projetos Gerais segue Sim/Não.
- **Projetos Gerais: cálculo.** O Select de "Cálculo de códigos" tem rótulos curtos (Por aluno, Por professor, Não se aplica: com a fórmula, cortava a 360 px); a fórmula aparece abaixo do campo ("Cálculo: alunos ÷ divisor.") e na coluna ("Por aluno (alunos ÷ divisor)").
- **Importação de Municípios.** A pendência mostra o nome do município (chave `municipio` do backend) e "Inalterados" conta só as inalteradas (`stats.unchanged`, em `ImportResult.unchanged`); as rejeitadas ficam só nos erros.
- **Testes.** `GruposPage.responsivo.test.tsx`, `GerenciasPage.responsivo.test.tsx`, `MunicipiosPage.responsivo.test.tsx`, `ProdutosPage.responsivo.test.tsx` e `ProjetosGeraisPage.responsivo.test.tsx` (em `pages/AdminDAT/__tests__/`) cobrem as colunas por largura, a linha expandida, a troca de largura com a página aberta, o contraste das etiquetas, o nome acessível das ações e a confirmação de Excluir; os `*.salvar.test.tsx` das 5 telas cobrem o salvar, a exclusão (com o 409) e as falhas de carga, inclusive o Tab até o "Tentar de novo" das opções e o foco depois dele; o de Grupos cobre os caminhos da lista de usuários (nunca carregou, carregando, falhou, carregou, reabrir o Editar, criar grupo, trocar de grupo com o modal aberto), sem `user_ids: []` nem menos membros para grupo que já existe.

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
| `/solicitacoes/:id/editar` | `Solicitacoes/EditSolicitacaoPage` | `allow={canCoordenador \|\| canApproveSuper}` (#1169) — **não** é "autenticado". A aprovadora por vínculo abre qualquer uma (ler é global), mas só salva as próprias, as do fluxo SUPER da Superintendência e as das gerências de um 2º vínculo de GERENTE dela; fora disso dá 403 e a tela mostra o `detail` do backend ("A gerência da Superintendência só edita ou exclui solicitações do fluxo SUPER da Superintendência."; sem `detail`, o texto padrão); mover para projeto fora desse alcance dá 400 e a tela mostra o motivo de `errors.projeto`. O seletor de projeto (`/lookup/projetos/`) só oferece esse alcance (regra do dono, 30/09) |
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

> **Projetos — campo Gerência (regra do dono, 30/09):** o backend só aceita `fluxo = SUPER` em projeto da gerência `SUPERINTENDENCIA` (trava de cadastro, [`politica-aprovacao.spec.md`](../domain/politica-aprovacao.spec.md) PA-04). O modal da `AdminDAT/ProjetosPage` tem o Select "Gerência" (gerências **ativas**, pelo `rotulo`; `listGerencias({ ativo: true })`) e manda `gerencia` no POST/PATCH. É **obrigatório ao criar** (todo projeto pertence a uma gerência, decisão do dono 29/09); na edição vem preenchido com a gerência atual, que aparece pelo rótulo mesmo se estiver inativa. O 400 da trava (erro sem campo, `errors.non_field_errors`) aparece junto do campo Gerência, e abrir criar ou editar zera o form (o erro não sobra para outro projeto). Na edição a gerência não é obrigatória (projeto antigo sem gerência salva sem escolher), mas todo salvar manda `fluxo` (e `gerencia`, quando o campo tem valor): um SUPER antigo fora da Superintendência só salva escolhendo essa gerência ou mudando o fluxo. Se `listGerencias` falhar, o modal mostra um Alert com o motivo e avisa que sem a lista não dá para criar projeto nem trocar a gerência. Sem coluna nova na tabela: a coluna Setor já mostra o rótulo da gerência (PR A).

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
