# AS v2 Error Patterns, Fallbacks, and Instrumentation

Reference for the `debugging-and-error-recovery` skill. Consult the relevant
section once Step 2 (Localize) points at one of these layers.

## AS v2-Specific Error Patterns

### CSRF Token Errors (frontend)

```
Symptom: 403 "CSRF Failed" on POST/PATCH/DELETE

Root causes:
1. fetchAPI not used (raw fetch without CSRF header)
2. Session expired → CSRF token stale
3. Cookie `csrftoken` blocked by browser

Fix: Always use fetchAPI from src/api/config.ts — handles CSRF + retry automatically
```

### Django Migration Conflicts

```
Symptom: "Conflicting migrations detected"

Root causes:
1. Two branches added migrations with same number
2. Dev DB has migration applied but branch removed it

Fix:
  # If conflict between branches:
  docker exec aprender_dev-web-1 python manage.py makemigrations --merge

  # If local DB out of sync:
  docker exec aprender_dev-web-1 python manage.py showmigrations core
  # Fake reverse if needed:
  docker exec aprender_dev-web-1 python manage.py migrate core <target> --fake
```

### Celery Task Not Running

```
Symptom: Task queued but not executed

Triage:
1. Check worker running: docker ps | grep worker
2. Check REDIS_PASSWORD (memory: project_celery_broken.md)
3. Check task registered: docker exec aprender_dev-worker-1 celery -A config inspect registered
4. Check worker logs: docker logs aprender_dev-worker-1 --tail 100

Common fix: missing CELERY_BROKER_URL with password (PR #1089)
```

### GCal Sync Stuck

```
Symptom: Solicitacao.gcal_status='PENDING' for hours

Triage:
1. Circuit breaker open? — check logs; breaker lives in
   apps.core.services.gcal.circuit_breaker (gcal_breaker / CircuitBreakerError)
2. Token expired? → check GoogleOAuthCredential.token_expiry (is_expired / days_until_expiry)
3. Retry exhausted? → check Solicitacao.gcal_last_error

Tools:
  docker exec aprender_dev-web-1 python manage.py shell
  >>> from apps.core.models import Solicitacao
  >>> from apps.core.services.gcal import resync_solicitacao
  >>> resync_solicitacao(Solicitacao.objects.get(pk=<pk>))
```

### Docker Container Unhealthy

```
Symptom: docker ps shows "unhealthy"

NEVER DO: systemctl restart docker
(Memory: feedback_docker_never_restart.md — Kaspersky race condition)

DO:
  make down && make up
  # or for single container:
  docker compose restart web
```

### React Bundle Errors in Production (not in dev)

```
Symptom: "Cannot read property 'X' of undefined" in prod, works in dev

Common causes:
1. Vite manualChunks misordered deps (NEVER use manualChunks)
2. Missing envvar at build time (VITE_API_URL)
3. Tree-shaking dropped a side-effect-import

Fix:
- Check vite.config.ts has no manualChunks
- Verify build envvars match runtime
- Use explicit side-effect imports if needed
```

### Pyright Strict Errors

```
Symptom: pyright strict mode fails

Common fixes:
- Add explicit types on function signatures
- Use `cast()` when you know the type but Pyright can't infer
- Narrow Optional[X] with `if x is None: return`
- For Django QuerySets: use `from django.db.models import QuerySet`
```

## Safe Fallback Patterns

When under time pressure:

```python
# Django: safe default for missing config
def get_feature_flag(name: str) -> bool:
    try:
        return Config.objects.get(key=name).value.get('enabled', False)
    except Config.DoesNotExist:
        logger.warning(f"Missing config: {name}, defaulting to False")
        return False
```

```tsx
// React: graceful component degradation
function DashboardChart({ data }) {
  if (!data || data.length === 0) {
    return <Empty description="Sem dados para o período" />;
  }
  try {
    return <Chart data={data} />;
  } catch (e) {
    logger.error('Chart render failed:', e);
    return <Alert type="error" message="Não foi possível renderizar" />;
  }
}
```

## Instrumentation

### When to add logging

- Cannot localize failure to specific code path
- Intermittent issue that needs monitoring
- Multiple components interacting

### When to remove it

- Bug fixed and regression test added
- Log is dev-only (noise in prod)
- Contains sensitive data (ALWAYS remove)

### Permanent (keep)

- Error boundaries in React with reporting
- API error logging with request context (Django middleware)
- Performance metrics at critical flows
- Structured logs (memory: SEC-016)
