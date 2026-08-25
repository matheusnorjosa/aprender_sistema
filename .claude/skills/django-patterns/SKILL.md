---
name: django-patterns
description: Django 5.2 + DRF implementation patterns specific to Aprender Sistema v2 (modular apps/core layout, HasPerm RBAC, read/write serializers, service layer, owner-scoped querysets). Use when writing a model, serializer, view/viewset, service, permission, or test in the v2 backend.
---

# Django/DRF Patterns — Aprender Sistema v2

Implementation patterns for the v2 backend. This file holds the AS-v2-specific deltas;
the full copy-paste scaffolds live in `reference/` (see pointers below). For anything
generic to Django/DRF, follow the framework defaults — this skill only documents where
AS v2 diverges.

## Backend layout (modular)

The only real apps are `apps/core` (41 models, `serializers/`, `services/`) and
`apps/dev_tools` (15 seed commands, disabled in prod). `apps/core` is split into Python
packages, each with an `__init__.py` that re-exports its public names:

```
apps/core/
├── models/        # by domain; __init__.py re-exports all models
├── serializers/   # by domain; __init__.py re-exports
├── views/         # compat re-export wrappers (e.g. views/solicitacao.py)
├── views_*.py     # canonical view modules (views_solicitacao.py, views_availability.py, …)
├── views_gcal/    # GCal views
├── rbac/          # RBAC SSOT (HasPerm, helpers, matrix, policies)
└── services/      # business logic (availability_service.py, gcal/, …)
```

**Re-export discipline**: when you add a model/serializer, re-export it in the package's
`__init__.py` so existing imports keep working. Note `apps/core/views/solicitacao.py` is a
thin compat wrapper — the canonical ViewSet lives in `apps/core/views_solicitacao.py`.

## Quick reference

| Task | Pattern | Pointer |
|------|---------|---------|
| Model | SSOT + constraints + indexes + re-export | `reference/model-template.md` |
| Serializer (read) | `StringRelatedField`, formatted fields | `reference/serializer-template.md` |
| Serializer (write) | `PrimaryKeyRelatedField` + validation | `reference/serializer-template.md` |
| ViewSet | thin controller, logic in services | `reference/viewset-template.md` |
| Permission | `HasPerm("codename")` | RBAC section below |
| Owner/sector scope | filter in `get_queryset()` | RBAC section below |
| Test | nested classes per requirement, behavior asserts | `reference/test-template.md` |
| Query perf | `select_related` / `prefetch_related` | Performance section below |

---

## Models

Full scaffold: **`reference/model-template.md`**.

AS-v2 deltas to keep in mind:
- **Timezone**: `DateTimeField` stores UTC; display converts to `America/Fortaleza`.
- **Constraints in the DB**: prefer `CheckConstraint`/`UniqueConstraint` in `Meta`; reach
  for Python validators only when the rule needs relations or runtime data.
- **`save()` deriving fields**: real pattern in `apps/core/models/dat_registro.py` — `save()`
  calls `_calcular_nr_codigos()` to compute `nr_codigos` from `projeto_geral`.
- **Default masks required**: a model field with `default=` makes `ModelSerializer` accept a
  payload that omits it. When the field must be supplied, declare it as
  `ChoiceField(required=True)` on the write serializer (case `Projeto.fluxo`, #1312).

---

## Serializers (DRF)

Full scaffold + gotchas: **`reference/serializer-template.md`**.

Read/write split is the house style: read serializers are user-friendly
(`StringRelatedField`, formatted fields, nested), write serializers take IDs
(`PrimaryKeyRelatedField`) and validate. Pick per request in the ViewSet's
`get_serializer_class()`.

---

## Views / ViewSets

Full scaffold: **`reference/viewset-template.md`**.

AS-v2 deltas:
- **Thin controllers**: views validate + delegate to `apps/core/services/`; keep business
  logic out of the view body.
- **`get_serializer_class()`** switches read vs write by `self.action`.
- **Owner/sector scope** is filtered in `get_queryset()` (see RBAC below), not re-checked in
  the body.
- **`get_permissions()` override hides `@action(permission_classes=...)`** — if a ViewSet
  overrides `get_permissions()`, the action decorator's classes are ignored. Check it before
  assuming an action's permissions. (`SolicitacaoViewSet` does this, mapping `approve`/
  `batch_approve` to the Policy `CanAccessSolicitationApprovals`.)

---

## Permissions (RBAC)

The AS v2 RBAC is **capability-based**. SSOT is `apps.core.rbac` (DRF permissions, helpers,
data-scope constants, matrix, policies). **NEVER** use `user.groups.filter(name=...)` in
views/permissions — it is banned by `scripts/rbac_lint.py` (CI job `[required] backend
rbac-lint`). `apps/core/permissions.py` is a compat shim — import from `apps.core.rbac`.

Canonical idiom — capability codenames are English (`approve_solicitation`,
`create_solicitation`, `import_spreadsheet`, `operate_preagenda`, …):

```python
from apps.core.rbac import HasPerm

permission_classes = [HasPerm("approve_solicitation")]                 # single capability
permission_classes = [HasPerm("approve_solicitation") | HasPerm("create_solicitation")]  # OR
permission_classes = [IsAuthenticated, HasPerm("approve_solicitation")]  # AND
permission_classes = [~HasPerm("bloqueado")]                          # NOT
```

`HasPerm("a") | HasPerm("b")` composition is tactical (ok for ≤2 capabilities). For ≥3 caps,
a shared rule, or "who can see this and why" repeated across sites, promote it to a **Policy
class** in `apps/core/rbac/policies.py` (e.g. `CanAccessSolicitationApprovals`,
`CanUseGcal`).

Programmatic checks outside views (services, signals, commands):

```python
from apps.core.rbac import user_has_any_perm, user_has_all_perms

if user_has_any_perm(user, "approve_solicitation", "create_solicitation"):
    ...
```

**Data-scope / object-level**: filter in `get_queryset()` + capabilities — don't reimplement
identity checks by group.

```python
def get_queryset(self):
    qs = Solicitacao.objects.select_related("solicitante")
    user = self.request.user
    if not user.is_superuser:
        qs = qs.filter(solicitante=user)  # owner-scope
    return qs
```

Full naming convention: `v2/docs/RBAC_NAMING.md` + `v2/docs/specs/backend/rbac.spec.md`.

---

## Testing

Full scaffold + conventions: **`reference/test-template.md`**.

AS-v2 deltas:
- **Nested classes per requirement** (`TestSolicitacaoApproval` → `TestManualApproval` for
  PA-01, `TestPermissions` for PA-02); docstrings name the rule.
- **Test behavior, not implementation** — assert status code / persisted state / audit log,
  never that a method was called.
- **RBAC asserts the 403 status**, not `"Setor" in response.data` (that ties the test to the
  legacy org chart).
- **Determinism**: atomic counter for unique CPF/email (not `abs(hash(str)) % N`); never
  hardcode a date whose assertion depends on a not-yet-reached deadline.
- **Pyright header**: a new test file needs the same `# pyright: ...=false` header its
  neighbors carry, or CI breaks.

Real suites in `apps/core/tests/`: `test_solicitacao_fluxo.py`,
`test_solicitacao_approval_concurrency.py`, `test_views_solicitacao_coverage.py`,
`test_solicitacao_serializer_meet_link.py`.

---

## Performance

Quick rule: `select_related` (FK/OneToOne) + `prefetch_related` (M2M/reverse FK) to kill N+1.
Endpoint-level caching exists (e.g. `availability_check:` keys at `timeout=300` via the
`cache_availability_check` decorator; the monthly availability grid caches in
`views_availability_monthly.py` with a TTL+jitter). For slow endpoints, deep N+1, bundle, or
Core Web Vitals, **use the `performance-optimization` skill** (perf SSOT) — don't duplicate
guidance here.

```python
solicitacoes = Solicitacao.objects.select_related("solicitante")  # avoids N+1
```

---

## Real implementations to copy from

- **CRUD**: models `apps/core/models/solicitacao.py`, `usuario.py`, `organizacao.py`;
  serializers `serializers/solicitacao.py`, `serializers/usuario.py`; view
  `views_solicitacao.py`; permissions `apps/core/rbac`.
- **DAT module** (4-step workflow Carta → Contato → Reunião → Entrega): models
  `models/dat_acao.py`, `dat_cadastro.py`, `dat_registro.py` (`save()` auto-derives
  `nr_codigos`).
- **PlanoFormacoes**: models `models/plano_formacoes.py`, `formacao.py`, `acompanhamento.py`,
  `prova.py`; `recalcular_ch()` + `taxa_realizacao` property.
- **Service layer**: `services/availability_service.py` (RD-01..RD-08),
  `services/gcal/sync.py` + `gcal/payload.py` (RF05/RF06),
  `services/solicitacao_approval.py` (PA-01..PA-07).
- **Import**: command `import_export_contract` + `services/export_contract_importer.py`
  (dry-run by default).

## Related

- **Business rules**: `aprender-domain` skill (CP, RD, PA, RF, DAT, PlanoFormacoes)
- **RBAC**: `v2/docs/RBAC_NAMING.md` + `v2/docs/specs/backend/rbac.spec.md`
- **Performance**: `performance-optimization` skill
- **Imports**: `v2/docs/specs/backend/imports.spec.md` (legacy ETL removed — use
  `import_export_contract` + DRF endpoints)
