# ADR-006: Sessões em Redis (não PostgreSQL)

**Status:** Accepted
**Date:** 2025-11-17
**Decider:** Matheus Norjosa

## Context

Django default armazena sessões em PostgreSQL (`django.contrib.sessions.backends.db`). Cada request autenticado faz 1 query ao banco apenas para validar sessão — 33% do tempo total de resposta. Com 50 usuários simultâneos, isso gera 50 queries/segundo desnecessárias.

## Decision

Sessões armazenadas em Redis via `django-redis`:

```python
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"  # Redis
```

## Consequences

- Zero queries ao PostgreSQL para validar sessões
- Latência -50% por request (5-10ms economizados)
- Carga no banco -80% (sobra capacidade para queries reais)
- Sessões expiram automaticamente no Redis (TTL)
- Habilita scaling horizontal (stateless app servers)
- Se Redis cair, sessões são perdidas (re-login necessário)

## References

- `v2/backend/config/settings.py` (SESSION_ENGINE)
- `v2/docs/AUDITORIA_PERFORMANCE_CUSTOS.md`
- ADR-014 (Stateless Horizontal Scaling)
