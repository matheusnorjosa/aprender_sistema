# ADR-010: Deploy Direto para Produção via Portainer

**Status:** Superseded by [ADR-018](ADR-018-pull-based-deploy.md)
**Date:** 2026-01-12
**Superseded:** 2026-07-10 (registrado em 2026-07-24)
**Decider:** Matheus Norjosa

> ⚠️ **Este ADR não descreve mais o sistema.** O deploy é **pull-based** desde
> 2026-07-09/10: **merge na `main` NÃO deploya**, produção só muda por promoção deliberada
> e gated, e **migrations são automáticas** (serviço one-shot `migrate`). Ver
> [ADR-018](ADR-018-pull-based-deploy.md) e o SSOT do mecanismo em
> `v2/docs/specs/infra/deploy.spec.md`.
>
> O texto abaixo é preservado como registro histórico da decisão original. Não o siga.

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

## O que mudou (e por quê)

| Ponto do ADR-010 | Estado hoje (ADR-018) |
|---|---|
| Merge na `main` dispara deploy automático | **Revogado.** Merge faz build+scan+push+assinatura e para aí (`deploy.yaml`, jobs `prepare` e `sign`). |
| Portainer atualiza a stack via `PUT` do CI ao `:9443` público | **Revogado.** O job `deploy` foi deletado (#1516). O `PUT` é feito pelo agente `aprender-applier` em `127.0.0.1:9443`. |
| Migrations rodadas manualmente no container prod | **Revogado.** Serviço one-shot `migrate` aplica no deploy; `web`/`worker`/`beat` aguardam `service_completed_successfully` (#1456). |
| Rollback por `gh workflow run deploy.yaml -f rollback_tag=...` | **Revogado.** Rollback é promoção para trás via `promote.yml` com `rollback: true`. |
| Sem staging remoto; staging gate local é a validação pré-merge | **Continua válido.** Não há ambiente de staging remoto. |
| Tags `latest` rejeitadas em produção; tag imutável `vYYYY.MM.DD-<sha>` | **Continua válido**, agora reforçado por aplicação **por digest**. |
