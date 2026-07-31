---
title: Specs de Infra
status: active
last_verified: 2026-07-24
owner: infra
related:
  - ../INDEX_SDD.md
---

# Specs de Infra (deploy, ambientes, CI)

Voltar ao [índice SDD](../INDEX_SDD.md).

## Specs — origem de cada uma

| Spec | Estado | Fonte canônica / código |
|---|---|---|
| [`deploy.spec.md`](./deploy.spec.md) | ✅ escrita | `docker-compose.prod.yml`, `deploy.yaml`, `promote.yml`, `v2/infra/deployer/`, ADR-018 |
| [`environments.spec.md`](./environments.spec.md) | ✅ escrita | `v2/infra/ENVIRONMENTS.md`, `docker-compose*.yml` |
| [`ci.spec.md`](./ci.spec.md) | ✅ escrita | `.github/workflows/`, `docs/operations/ci-*.md` |

> **Modelo de deploy: pull-based** ([ADR-018](../../../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md),
> que **supersede** o ADR-010). **Merge na `main` NÃO deploya** — ele só faz build, scan,
> push e assinatura. Produção muda por promoção deliberada (`promote.yml`, gated) aplicada
> pelo agente `aprender-deployer` na VM01, por digest, em `127.0.0.1:9443`. **Não há
> staging remoto.** SSOT do mecanismo: [`deploy.spec.md`](./deploy.spec.md).
