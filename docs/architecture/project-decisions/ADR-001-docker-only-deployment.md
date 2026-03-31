# ADR-001: Docker-Only Deployment

**Status:** Accepted
**Date:** 2025-10-01
**Decider:** Matheus Norjosa

## Context

O sistema v1 rodava localmente com dependências instaladas diretamente no OS, causando inconsistências entre ambientes (dev, staging, prod). Diferentes versões de Python, PostgreSQL e Redis entre desenvolvedores geravam bugs não reproduzíveis.

## Decision

v2 roda APENAS em Docker. Todo o stack (Django, PostgreSQL, Redis, Celery, Nginx, Frontend) é containerizado via Docker Compose. Nenhum serviço roda diretamente no host.

## Consequences

- Ambiente 100% reproduzível em qualquer máquina
- `cd v2 && make up` sobe todo o stack em minutos
- CI/CD usa mesmas imagens Docker que produção
- Desenvolvimento local requer Docker instalado (sem exceção)
- v1 permanece congelado (branch `main-v1`) — CP-05

## References

- CP-01 (Cláusula Pétrea)
- `v2/infra/docker-compose.yml`
- `v2/infra/Dockerfile.dev`, `v2/infra/Dockerfile.prod`
