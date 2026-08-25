# Backend Performance Reference (Django / DRF / PostgreSQL / Celery)

Anti-pattern catalogue and profiling recipes. Inline workflow lives in `SKILL.md`.

## Query Profiling

Count queries inside a view using the dev shell (debug toolbar lives in `dev_tools`):

```bash
docker exec aprender_dev-web-1 python manage.py shell
```

```python
from django.db import connection, reset_queries
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def profile_view():
    reset_queries()
    # call your code
    print(f"Queries: {len(connection.queries)}")
    for q in connection.queries[-5:]:
        print(q['sql'][:200])
```

`django-debug-toolbar` is available in dev (`requirements-dev.txt`).

## Anti-Patterns

### N+1 Queries

```python
# BAD: N+1 (one query per solicitacao for coordenador)
for sol in Solicitacao.objects.filter(status='aprovado'):
    print(sol.coordenador.usuario.full_name)  # +1 query each

# GOOD: select_related for FK, prefetch_related for M2M / reverse FK
(
    Solicitacao.objects
    .filter(status='aprovado')
    .select_related('usuario', 'municipio', 'tipo_evento', 'projeto', 'coordenador')
    .prefetch_related('formadores', 'participations__usuario')
)
```

`SolicitacaoViewSet.get_queryset()` (`apps/core/views_solicitacao.py`) is the
canonical example of this pattern in the codebase.

### Unbounded Queries

```python
# BAD: No pagination
return Solicitacao.objects.all()

# GOOD: DRF pagination (PageNumberPagination configured in apps/core/pagination.py)
```

### Missing Indexes

Check `v2/backend/apps/core/migrations/0066_data_integrity_indexes_on_delete.py`
for existing composite indexes (e.g. `Index(fields=["usuario", "status", "inicio"])`).

```python
class Meta:
    indexes = [
        models.Index(fields=['usuario', 'status']),
        models.Index(fields=['inicio', 'fim']),
        models.Index(fields=['gcal_status', 'gcal_last_sync_at']),
    ]
```

### Slow Aggregations

```python
# BAD: Loop + per-row count in Python
total = 0
for s in solicitacoes:
    total += s.participations.count()

# GOOD: SQL aggregation
from django.db.models import Count
stats = Solicitacao.objects.aggregate(
    total_participations=Count('participations'),
)
```

When mixing `.annotate(Count())` with `.values_list()`, drop residual ordering
first (`qs.order_by()`) — `Meta.ordering` silently fragments the GROUP BY.

## Celery Task Profiling

```bash
# Celery app is named "config" (config/celery.py)
docker exec aprender_dev-worker-1 celery -A config inspect active
docker exec aprender_dev-worker-1 celery -A config inspect stats
```

Split long-running tasks instead of running them inline.

## Backend Caching (Django + Redis)

```python
from django.core.cache import cache

def get_availability_monthly(user_id, year, month):
    key = f"availability:{user_id}:{year}:{month}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    result = expensive_query(user_id, year, month)
    cache.set(key, result, timeout=300)  # 5 min
    return result

# Cache-aside with granular invalidation: delete only affected keys
def invalidate_user_availability(user_id):
    for key in cache.keys(f"availability:{user_id}:*"):
        cache.delete(key)
```
