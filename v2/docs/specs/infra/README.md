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

## Specs planejadas (Fase 3-4)

| Spec | Estado da doc hoje | Fonte canônica / código |
|---|---|---|
| `deploy.spec.md` | reescrever (`docs/architecture/infrastructure.md` diz "GitHub Pages") | ADR-010, `.github/workflows/deploy.yaml` |
| `environments.spec.md` | migrar | `v2/infra/ENVIRONMENTS.md`, `docker-compose*.yml` |
| `ci.spec.md` | consolidar | `.github/workflows/`, `docs/operations/ci-*.md` |

> Status: esqueleto. Nenhuma spec escrita ainda (Fase 0).
> Lembrete (auditoria): o deploy é Portainer→prod (ADR-010), **sem staging remoto**; merge na main = deploy em produção.
