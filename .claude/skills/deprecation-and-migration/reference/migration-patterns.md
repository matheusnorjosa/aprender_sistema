# Migration Patterns

Reference for checklist step "Migration tooling / strategy". Pick the pattern that fits the change; combine when needed.

## Strangler Pattern

Run old and new in parallel. Shift traffic incrementally.

```python
# Django: feature flag controls which service runs
from django.conf import settings

def dispatch_to_service(request):
    if settings.FEATURE_FLAGS.get('use_new_service'):
        return NewService().handle(request)
    return OldService().handle(request)
```

## Adapter Pattern

Keep the old interface, delegate to the new implementation:

```python
# Old signature, new backend
class LegacyCalendarService:
    def __init__(self):
        self.new_service = NewCalendarService()

    def publish_event(self, sol_id: int) -> OldResponse:
        # New service uses a different ID type
        new_response = self.new_service.publish(str(sol_id))
        return self._convert_to_old_format(new_response)
```

## Two-Phase Django Migration

For schema changes that carry data. `Solicitacao.local` is a real CharField — this is the safe rename-with-backfill shape:

```python
# Migration N: Add new field (nullable), keep old
operations = [
    migrations.AddField('Solicitacao', 'local_v2', models.TextField(blank=True)),
]

# Migration N+1: Data migration (backfill)
operations = [
    migrations.RunPython(copy_local_to_v2, reverse_noop),
]

# Migration N+2: After consumers updated, remove old + rename
operations = [
    migrations.RemoveField('Solicitacao', 'local'),
    migrations.RenameField('Solicitacao', 'local_v2', 'local'),
]
```

## Marking deprecated code in place

### Django model

```python
class OldModel(models.Model):
    """
    DEPRECATED: Use NewModel instead.
    Migration plan: Issue #NNNN. Removal target: after all consumers migrated.
    """
    class Meta:
        # Don't add new indexes/constraints to deprecated models
        pass
```

### Django field

```python
class Solicitacao(models.Model):
    # DEPRECATED: use new_status instead
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    # Then: data migration to backfill new_status, then remove old_status in a separate migration.
```

### API endpoint

```python
class OldViewSet(ModelViewSet):
    """DEPRECATED: use /api/new-endpoint/ instead."""

    def list(self, request):
        response = super().list(request)
        response['X-Deprecation'] = 'Deprecated. Use /api/new-endpoint/'
        response['X-Sunset'] = '<RFC 8594 sunset date>'
        return response
```

### Frontend dependency removal

Phased removal, one PR per phase (the axios -> `fetch` removal in SKILL.md is the worked example):

```
Phase 0: Add missing helpers to the replacement wrapper (e.g. fetchBlob, fetchWithErrorMapping in config.ts)
Phase 1: Migrate the simplest client (e.g. acoesNotificacao.ts)
Phase 2: Migrate moderate clients (e.g. adminDAT.ts — with error mapping)
Phase 3: Migrate the largest client (e.g. datModule.ts — with blob support)
Phase 4: Migrate consumers (hooks, components)
Phase 5: Delete the dead client + uninstall the dependency from package.json
```
