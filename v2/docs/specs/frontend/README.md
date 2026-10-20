---
title: Specs de Frontend
status: active
last_verified: 2026-10-19
owner: frontend
related:
  - ../INDEX_SDD.md
  - ../../audits/ACHADOS_REAIS.md
---

# Specs de Frontend (`v2/frontend/src`)

Voltar ao [índice SDD](../INDEX_SDD.md).

## Specs vivas

| Spec | Cobre | Código | Status |
|---|---|---|---|
| [`pages.spec.md`](./pages.spec.md) | inventário de rotas × páginas × guard aplicado | `src/components/AppRoutes.tsx`, `src/components/access/RequirePolicy.tsx`, `src/pages/` (16 diretórios de domínio) | canonical |
| [`hooks-rbac.spec.md`](./hooks-rbac.spec.md) | camada de identidade/capability e guards | `contexts/AcessoContext` (`useAcesso`), `hooks/useCapabilities`, `useIdentity`, `useGoogleGuard` | canonical |
| [`api-clients.spec.md`](./api-clients.spec.md) | wrapper `fetch` + CSRF + clientes por domínio | `src/api/` (17 arquivos: `config.ts`, `unwrapList.ts` + 15 clientes) | canonical |

Números conferidos contra o código em 2026-10-20: **43 páginas lazy-loaded** (41 em
`AppRoutes.tsx` + `LoginPage` e `TrocaSenhaObrigatoriaPage` em `App.tsx`), **53 `<Route>`** dos
quais 6 são redirects de URLs legadas e 1 é a rota coringa `*`, **16 diretórios** de domínio em `src/pages/`, **17 arquivos**
em `src/api/` (fora os testes). O detalhe vive em [`pages.spec.md`](./pages.spec.md) e
[`api-clients.spec.md`](./api-clients.spec.md). A contagem
antiga de "45+ pages" e "6/14 documentadas" não correspondia ao código.

## Divergências vivas em produção

`pages.spec.md` e `hooks-rbac.spec.md` trazem uma seção de divergências conhecidas entre o
que a tela oferece e o que o backend aceita (HomePage, Deslocamentos, Pré-agenda, DAT/Compras,
DAT/Registros, paginação). O rastreamento é do documento vivo
[`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md) — as specs linkam, não duplicam.

## Ver também

Sistema de cor e tema (paleta da marca, tokens claro/escuro, cadeia SSOT e racional WCAG do
acento do tema escuro): [`DESIGN_SYSTEM.md`](../../DESIGN_SYSTEM.md).
