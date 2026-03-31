# ADR-009: Repositório Público com Sanitização

**Status:** Accepted
**Date:** 2026-03-09
**Decider:** Matheus Norjosa

## Context

O repositório é público no GitHub. Documentação interna continha IPs de produção, nomes de DB, e procedimentos que não deveriam ser expostos. Arquivos `.env` com dados reais foram commitados acidentalmente.

## Decision

- `v2/docs/` contém APENAS documentação pública e sanitizada
- Conteúdo sensível em `v2/docs/private/` (ignorado pelo Git) ou vault externo
- Arquivos `.env` operacionais NUNCA versionados — apenas templates `.example`
- Scan reports locais (audit/bandit) não versionados
- Placeholders em exemplos: `<token>`, `<senha>`, `<ip-privado>`
- Workflow: escrever em private → sanitizar → publicar em docs/

## Consequences

- Zero segredos no histórico Git (após filter-repo cleanup)
- Templates `.example` servem como referência sem dados reais
- `.gitignore` bloqueia `.env.*` exceto `.env.*.example`
- Contribuidores externos não acessam infra interna

## References

- `v2/docs/PUBLIC_PRIVATE_POLICY.md`
- `v2/.gitignore`
- PLAN-security-audit-env-cleanup.md
