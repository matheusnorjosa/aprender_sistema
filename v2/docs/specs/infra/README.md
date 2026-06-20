---
title: Specs de Infra
status: active
last_verified: 2026-06-19
owner: infra
related:
  - ../INDEX_SDD.md
---

# Specs de Infra (deploy, ambientes, CI)

Voltar ao [índice SDD](../INDEX_SDD.md).

## Specs (escritas em 2026-06-19) — origem de cada uma

| Spec | Estado | Fonte canônica / código |
|---|---|---|
| [`deploy.spec.md`](./deploy.spec.md) | ✅ **escrita** (2026-06-19, verificada contra a stack viva do Portainer) | `docker-compose.prod.yml`, `deploy.yaml`, ADR-010 |
| `environments.spec.md` | planejado (migrar) | `v2/infra/ENVIRONMENTS.md`, `docker-compose*.yml` |
| `ci.spec.md` | planejado (consolidar) | `.github/workflows/`, `docs/operations/ci-*.md` |

> Status: **specs escritas** (Fase 3-4, 2026-06-19); `deploy.spec.md` preenchida na verificação dev × prod de 2026-06-19. Links vivos no [índice SDD](../INDEX_SDD.md).
> Lembrete (auditoria): o deploy é Portainer→prod (ADR-010), **sem staging remoto**; merge na main = deploy em produção.
