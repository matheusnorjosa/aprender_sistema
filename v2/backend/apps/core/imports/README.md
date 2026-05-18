# `apps.core.imports` — Canonical Import Helper Namespace

This package is the **SSOT** (single source of truth) for utility helpers
shared across the import services in `apps/core/services/*_import.py`.

## Submodules

| Module                                | Purpose                                                                       |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| `apps.core.imports.normalization`     | String / flag normalization (`normalize_blank`, `normalize_active_flag`, `normalize_uf`, `normalize_cpf_digits`) plus legacy text helpers (`norm_text`, `normalize_sector`, `normalize_project_alias`, `split_municipios_super`, `parse_date_iso`, `parse_time_iso`, `normalize_email`, `normalize_date_field`, `normalize_time_field`). |
| `apps.core.imports.hashing`           | Deterministic SHA-1 idempotency-key generation (`stable_import_hash`, `hash_event_v2`). Not cryptographic. |

## Where to put new helpers

> **All new shared helpers used by import services go here, in
> `apps.core.imports.*`** — never in `apps.core.services.normalize`.

## `apps.core.services.normalize` is a compat wrapper

As of PR for issue #1349, `apps/core/services/normalize.py` is a thin
**re-export wrapper** over `apps.core.imports.*`. It exists only so the
existing callers keep working without touching their import lines:

* `apps.core.services.controle_imports`
* `apps.core.services.controle_acoes_import`
* `apps.core.services.dat_cadastros_import`
* `apps.core.views_lookup`

The wrapper preserves byte-for-byte behaviour — equivalence is pinned by
[`apps/core/tests/test_services_normalize_equivalence.py`](../tests/test_services_normalize_equivalence.py)
(75 snapshots, see PR #1350).

### Future cleanup (optional, not blocking)

After a soak period, callers may migrate their imports to read directly
from `apps.core.imports.*` and the wrapper can be removed. This is a
mechanical change (sed/codemod) and should be a single PR.

## Legacy quirks (intentionally preserved)

Some pre-existing behaviours of the legacy helpers are arguably "bugs"
but are kept exactly as-is for compatibility (see `# NOTE:` comments in
the test snapshots):

* `split_municipios_super("nan")` → `["nan"]` (does NOT filter the
  literal string).
* `parse_date_iso` rejects `/` and the BR `DD/MM/YYYY` format (use
  `normalize_date_field` for BR).
* `parse_time_iso("08")` rejects formats without `:`.
* `normalize_email("inválido")` → `"inválido"` (no format validation,
  only lowercase + strip).
* `norm_text(None)` returns `""` (defensive, despite the `s: str`
  signature).

Any change to these behaviours must be a dedicated PR that breaks the
snapshot tests intentionally.

## SHA-1 idempotency policy

Both `stable_import_hash` and `hash_event_v2` use `hashlib.sha1` with
`usedforsecurity=False` (PEP 644). This is documented because:

* The hashes are **idempotency keys**, not cryptographic security.
* Migrating to SHA-256 would break historical `external_hash` values
  stored in `Compra`, `Solicitacao`, `Deslocamento`, `AcaoControle`,
  `AcaoDAT`, and `Acompanhamento`.
* CodeQL's `py/weak-sensitive-data-hashing` flags these via dataflow
  taint — alerts #20, #21, and #26 have been dismissed as
  `false positive` with the same justification.
* A formal ADR is tracked in issue #1347.

## Scope of historical PRs

| PR | What |
|---|---|
| #1344 | Created the package + modern helpers (`normalize_blank`, etc.) + `stable_import_hash`. Migrated 4 low-risk services. |
| #1350 | Snapshot tests for the legacy `services/normalize.py` (75 cases). |
| #1349 (this PR) | Moved the 10 legacy helpers into the canonical namespace + converted `services/normalize.py` into a compat wrapper. |

Remaining work tracked in issue #1346 (migrate the other 6 import
services to use the modern helpers).
