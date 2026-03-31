# ADR-004: Conventional Commits e Branch Protection

**Status:** Accepted
**Date:** 2025-10-01
**Decider:** Matheus Norjosa

## Context

Histórico de commits inconsistente dificultava rastreabilidade de mudanças. Pushs diretos na main causavam deploys não revisados em produção.

## Decision

- **CP-06**: Conventional commits obrigatórios: `type(scope): message`
  - Types: feat, fix, chore, docs, test, refactor, ci, perf, style
  - Scope: backend, frontend, infra, ci, security, tests
- **CP-07**: Push direto na main proibido (enforced por Git hook)
  - Todo código via PR com CI verde
  - Staging gate obrigatório para mudanças de runtime

## Consequences

- Commits legíveis e buscáveis por tipo
- PRs obrigatórios com checklist técnico
- CI valida lint, testes, typecheck, security antes do merge
- Deploy automático após merge na main (sem staging remoto)

## References

- CP-06, CP-07 (Cláusulas Pétreas)
- `.github/pull_request_template.md`
- `.github/workflows/ci.yaml`
