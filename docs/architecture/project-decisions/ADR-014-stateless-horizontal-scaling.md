# ADR-014: Arquitetura Stateless para Scaling Horizontal

**Status:** Accepted
**Date:** 2026-01-12
**Decider:** Matheus Norjosa

## Context

O sistema precisa escalar sem redesign quando o número de usuários crescer. Aplicações com estado no servidor (sessões em disco, uploads locais) não escalam horizontalmente.

## Decision

Todos os componentes stateless:

| Componente | Storage | Tecnologia |
|------------|---------|------------|
| Django App | Stateless | Gunicorn (gthread) |
| Sessions | Redis | django-redis |
| Cache | Redis | django-redis |
| Media Files | S3/MinIO | django-storages |
| Task Queue | Redis | Celery broker |
| Database | PostgreSQL | Persistente |

Configurações:
- `CONN_MAX_AGE=60` (connection pooling)
- `least_conn` no Nginx (não round_robin)
- Migrations em job separado (1 instância)
- Celery workers escalam independentemente: `concurrency = 2 * CPU`

## Consequences

- Múltiplas instâncias web sem shared state
- Load balancer distribui requests sem sticky sessions
- Redis como ponto central de estado efêmero
- Se Redis cair: sessões perdidas, cache frio (graceful degradation)
- PostgreSQL é o único ponto de estado persistente

## References

- `v2/docs/SCALING.md`
- `v2/backend/config/settings.py` (SESSION_ENGINE, CACHES)
- ADR-006 (Session Storage Redis)
