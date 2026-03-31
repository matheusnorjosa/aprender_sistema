# Architecture Decision Records (ADR)

Registro de decisões arquiteturais do Aprender Sistema v2.

Cada ADR documenta: contexto (problema), decisão (o que foi escolhido e por quê), e consequências (o que muda).

## Índice

| ADR | Título | Status | Data |
|-----|--------|--------|------|
| [ADR-001](ADR-001-docker-only-deployment.md) | Docker-Only Deployment | Accepted | 2025-10-01 |
| [ADR-002](ADR-002-approval-policy-manual.md) | Política de Aprovação Manual (PA-01~07) | Accepted | 2025-10-23 |
| [ADR-003](ADR-003-availability-rules-timezone.md) | Regras de Disponibilidade e Timezone (RD-01~08) | Accepted | 2025-10-15 |
| [ADR-004](ADR-004-conventional-commits-branch-protection.md) | Conventional Commits e Branch Protection | Accepted | 2025-10-01 |
| [ADR-005](ADR-005-ssot-postgresql.md) | Single Source of Truth em PostgreSQL | Accepted | 2025-10-01 |
| [ADR-006](ADR-006-session-storage-redis.md) | Sessões em Redis | Accepted | 2025-11-17 |
| [ADR-007](ADR-007-django-5.2-lts-upgrade.md) | Upgrade Django 5.2 LTS | Accepted | 2026-03-31 |
| [ADR-008](ADR-008-gcal-deterministic-requestid.md) | RequestId Determinístico para Google Calendar | Accepted | 2026-03-31 |
| [ADR-009](ADR-009-public-repo-sanitization.md) | Repositório Público com Sanitização | Accepted | 2026-03-09 |
| [ADR-010](ADR-010-deploy-portainer-direct-to-prod.md) | Deploy Direto para Produção via Portainer | Accepted | 2026-01-12 |
| [ADR-011](ADR-011-polling-over-websocket.md) | Polling HTTP sobre WebSocket | Accepted | 2026-03-31 |
| [ADR-012](ADR-012-dependency-guardrails.md) | Guardrails Arquiteturais de Dependência | Accepted | 2026-01-15 |
| [ADR-013](ADR-013-axios-pinning-fetch-migration.md) | Pin Axios + Migração Fetch API | Accepted | 2026-03-31 |
| [ADR-014](ADR-014-stateless-horizontal-scaling.md) | Arquitetura Stateless para Scaling | Accepted | 2026-01-12 |
| [ADR-015](ADR-015-testing-policy.md) | Política de Testes | Accepted | 2026-02-24 |

## Como Adicionar um Novo ADR

1. Copiar o template abaixo
2. Salvar como `ADR-XXX-slug.md` (próximo número sequencial)
3. Adicionar entrada neste índice

### Template

```markdown
# ADR-XXX: [Título]

**Status:** Accepted | Deprecated | Superseded by ADR-YYY
**Date:** YYYY-MM-DD
**Decider:** [nome]

## Context
[O problema que levou à decisão]

## Decision
[O que foi escolhido e por quê]

## Consequences
[O que muda, o que fica proibido, o que é recomendado]

## References
[Links, issues, benchmarks]
```
