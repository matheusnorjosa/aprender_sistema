# Phase 08: CI Test Optimization Plan

## F2.1 - Controlled `pytest-xdist` experiment (Issue #649)

### Experiment metadata
- Date: 2026-02-24
- PR: #665
- Workflow run: `22366920610`
- Job: `[required] backend tests (runner)` (`64735282997`)
- Tested mode: `pytest -n auto --dist loadscope`

### Result
- Runtime observed: `266.36s` (`0:04:26`)
- Test outcome: `1 failed, 1716 passed, 28 skipped`
- Failing test: `apps/core/tests/test_config_api.py::test_config_validation`

### Failure signals collected
- Multiple unique constraint conflicts reported in Postgres logs during parallel execution.
- Evidence indicates race/state coupling in parts of the suite under full xdist parallelism.

### Decision
- Do **not** adopt xdist as default in required backend CI yet.
- Keep xdist toggle available in workflow for targeted follow-up experiments.

### Rollback / toggle policy
- Default (safe): `PYTEST_XDIST_ENABLED=0`
- Controlled re-test: set `PYTEST_XDIST_ENABLED=1` in `.github/workflows/ci.yaml`

### Next technical step
- Isolate and fix stateful/non-parallel-safe tests first, then re-run the experiment.

## F2.2 - Controlled Playwright checklist workers experiment (Issue #650)

### Experiment setup
- Scope: checklist-only CI job (`[required] checklist tests (meta, a11y, security)`)
- Change: run checklist with `--workers=2`
- Control point: `CHECKLIST_PLAYWRIGHT_WORKERS` in `.github/workflows/frontend-ci.yml`

### Rollback
- Fast rollback: set `CHECKLIST_PLAYWRIGHT_WORKERS=1`

### Validation target
- Reduce checklist duration without increasing retries/flaky failures.
