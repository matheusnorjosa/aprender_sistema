# `apps.core.imports` — Canonical Import Helper Namespace

This package is the **SSOT** (single source of truth) for utility helpers
shared across the import services in `apps/core/services/*_import.py`.

## Submodules

| Module                                | Purpose                                                                       |
| ------------------------------------- | ----------------------------------------------------------------------------- |
| `apps.core.imports.normalization`     | Pure string / flag normalization (`normalize_blank`, `normalize_active_flag`, `normalize_uf`, `normalize_cpf_digits`). |
| `apps.core.imports.hashing`           | Deterministic SHA-1 idempotency-key generation (`stable_import_hash`). Not cryptographic. |

## Where to put new helpers

> **All new shared helpers used by import services go here, in
> `apps.core.imports.*`** — never in `apps.core.services.normalize`.

## Migration policy for `apps.core.services.normalize` (legacy)

The pre-existing `apps/core/services/normalize.py` contains import-related
helpers (`norm_text`, `hash_event_v2`, `normalize_sector`,
`normalize_project_alias`, `split_municipios_super`, etc.) that **belong
conceptually in this package** but were not migrated in PR 3 for safety:

* `services/normalize.py` has near-zero test coverage (only one smoke test
  in `test_optional_etl.py`).
* `hash_event_v2` is used to compute `external_hash` for the
  Acompanhamento ETL — moving it without an equivalence test would risk
  silent idempotency corruption on the next ETL run.

### Required steps before migrating the legacy module

1. Create `apps/core/tests/test_services_normalize_equivalence.py` covering
   every public function of `services/normalize.py` with snapshot inputs
   and expected outputs (especially `hash_event_v2`).
2. Move the implementations to `apps.core.imports.normalization` and
   `apps.core.imports.hashing`.
3. Convert `apps/core/services/normalize.py` into a thin re-export module
   for backward compatibility with the existing callers
   (`controle_imports.py`, `controle_acoes_import.py`,
   `dat_cadastros_import.py`, `views_lookup.py`).
4. Open a dedicated PR — do NOT bundle this with feature work.

Until that PR lands, `apps/core/services/normalize.py` is treated as
**legacy preexisting code**, not as a provisional landing zone for new
helpers.

## Scope of PR 3

PR 3 (the introduction of this package) intentionally migrated only the
lowest-risk callers:

* `produtos_import.py`
* `colecoes_import.py`
* `municipios_import.py`
* `deslocamentos_import.py`
* `controle_imports.py::sha1_str` (thin wrapper for compatibility)

The remaining import services (`usuarios_import.py`, `eventos_import.py`,
`bloqueios_import.py`, `equipe_gerencia_import.py`,
`controle_acoes_import.py`, `dat_cadastros_import.py`) carry import-specific
logic enmeshed in their `_normalize_row` functions and will be migrated
incrementally in follow-up PRs.
