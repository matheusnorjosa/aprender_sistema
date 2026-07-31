---
title: Specs de Frontend
status: active
last_verified: 2026-07-24
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
| [`pages.spec.md`](./pages.spec.md) | inventário de rotas × páginas × guard aplicado | `src/components/AppRoutes.tsx`, `src/components/access/RequirePolicy.tsx`, `src/pages/` (15 diretórios de domínio) | canonical |
| [`hooks-rbac.spec.md`](./hooks-rbac.spec.md) | camada de identidade/capability e guards | `hooks/useCapabilities`, `useIdentity`, `usePermissions` (`@deprecated`), `useCanAccess`, `useGoogleGuard` | canonical |
| [`api-clients.spec.md`](./api-clients.spec.md) | wrapper `fetch` + CSRF + clientes por domínio | `src/api/` (16 arquivos: `config.ts` + 15 clientes) | canonical |

Números conferidos contra o código em 2026-07-24: **41 páginas lazy-loaded** (40 em
`AppRoutes.tsx` + `LoginPage` em `App.tsx`), **51 `<Route>`** dos quais 6 são redirects de
URLs legadas, **15 diretórios** em `src/pages/`, **16 arquivos** em `src/api/`. A contagem
antiga de "45+ pages" e "6/14 documentadas" não correspondia ao código.

## Divergências vivas em produção

`pages.spec.md` e `hooks-rbac.spec.md` trazem uma seção de divergências conhecidas entre o
que a tela oferece e o que o backend aceita (HomePage, Deslocamentos, Pré-agenda, DAT/Compras,
DAT/Registros, paginação). O rastreamento é do documento vivo
[`ACHADOS_REAIS.md`](../../audits/ACHADOS_REAIS.md) — as specs linkam, não duplicam.
