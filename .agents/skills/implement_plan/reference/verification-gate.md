# Verification Gate

Run before marking any wave complete. ALL must pass.

```bash
# Backend
docker exec aprender_dev-web-1 pytest apps/core/tests/ -q
docker exec aprender_dev-web-1 pytest apps/dev_tools/tests/ -q
cd v2/backend && pyright apps/core config

# Frontend (if modified)
cd v2/frontend && npm run lint && npm run typecheck
```

## AS-specific implementation rules

- **Before coding**: Load the `test-driven-development` skill. Write tests first.
- **Models**: Follow `django-patterns` — constraints at the DB level, validators for business rules.
- **Serializers**: Read/write separation, action-specific serializers.
- **Views**: Thin controllers, business logic in `services/`.
- **Availability**: Changes must pass the availability suites (RD-01..RD-08).
- **Approval**: Changes must pass the approval suites (PA-01..PA-07).
- **Type hints**: Pyright strict mode — run `pyright apps/core config` after changes.
- **Formatting**: Black + isort (the auto-format hook handles this).

## Error recovery

If a task fails:

1. Do NOT retry blindly — diagnose the root cause.
2. Check whether the plan's assumptions still hold.
3. If the approach is fundamentally wrong, flag it to the user before continuing.
4. Use the `debugging-and-error-recovery` skill for complex failures.
