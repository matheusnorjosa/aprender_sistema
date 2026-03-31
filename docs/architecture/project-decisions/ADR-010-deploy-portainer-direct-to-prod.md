# ADR-010: Deploy Direto para Produção via Portainer

**Status:** Accepted
**Date:** 2026-01-12
**Decider:** Matheus Norjosa

## Context

Projeto operado por solo developer. Não há infraestrutura de staging remoto. O ciclo de feedback precisa ser rápido: desenvolver → testar localmente → mergear → produção.

## Decision

- Merge na main dispara deploy automático em produção via Portainer
- Sem ambiente staging remoto (validação local substitui)
- CI faz build + scan + push de imagem Docker com tag imutável `vYYYY.MM.DD-<sha>`
- Portainer atualiza stack na VM de produção
- Tags `latest` rejeitadas em produção
- Staging gate local (`make staging-full`, 8 smoke tests) é a validação pré-merge
- PRs exigem evidência `ALL 8 CHECKS PASSED` no body

## Consequences

- Deploy em produção a cada merge (responsabilidade alta por PR)
- Staging gate local obrigatório antes de mergear
- Rollback por tag imutável: `gh workflow run deploy.yaml -f rollback_tag=vYYYY.MM.DD-<sha>`
- Migrations precisam ser rodadas manualmente no container prod (`python manage.py migrate`)

## References

- `docs/operations/deploy.md`
- `v2/docs/DEPLOY_CHECKLIST.md`
- `.github/workflows/deploy.yaml`
