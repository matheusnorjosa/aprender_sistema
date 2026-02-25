# Plan: CI Backend Runtime Optimization (Safe, No False Green)

Date: 2026-02-25
Status: Draft for execution
Owner: CI/Platform

## 1. Problem statement

The required backend job `[required] backend tests (runner)` runs the full suite for every PR.
Current baseline (phase-08 telemetry):

- median: 588s
- p95: 632s
- workflow wall time ~10 min

The controlled xdist experiment (issue #649) reduced time but introduced instability
(`SessionInterrupted` / shared-state race). Therefore xdist cannot be default for required gates yet.

## 2. Goal

Reduce PR CI time safely, with zero reduction in quality gates and zero false positive/false green risk.

## 3. Non-negotiable constraints

- Keep strict required checks behavior for backend quality.
- Keep full suite coverage target (`--cov-fail-under=80`).
- Do not make xdist default in required backend gate until proven stable.
- Keep deterministic pass/fail semantics (no permissive `continue-on-error`).

## 4. Strategy by phase

## Phase 1 (highest ROI, lowest risk)

### Objective
Skip heavy backend test execution only when PR has no backend impact.

### Scope
- Add changed-files detection job for backend impact.
- Keep workflow trigger broad (no risky path filter at workflow level).
- Execute backend-heavy jobs conditionally with `if:` based on impact output.
- Keep aggregator required job always running and asserting expected outcomes.

### Technical outline
- New job: `backend-impact` outputs `backend_changed=true|false`.
- Backend impact patterns include at least:
  - `v2/backend/**`
  - `v2/infra/Dockerfile`
  - `.github/workflows/ci.yaml`
  - dependency files used by backend test env.
- Jobs gated by impact:
  - `[required] backend tests (runner)`
  - `[required] backend typecheck (pyright)`
  - `[required] docker parity (backend)`
- Aggregator `[required] tests` logic:
  - if backend changed: require all three jobs `success`
  - if backend not changed: require those jobs `skipped`

### Safety checks
- No workflow-level `paths` for required check.
- Add explicit summary line in `GITHUB_STEP_SUMMARY` with impact decision.

### Acceptance criteria
- PR with frontend/docs-only changes avoids backend heavy jobs.
- PR with backend changes keeps current strict behavior.
- Required check policy remains deterministic.

### Rollback
- Single commit rollback to current always-run behavior.

## Phase 2 (medium risk, controlled gain)

### Objective
Reduce backend wall time for backend-changing PRs without xdist.

### Scope
- Split backend test workload by suite groups in separate serial jobs.
- Keep each job serial (no xdist).
- Merge coverage artifacts and enforce threshold in final backend aggregation step.

### Technical outline
- Replace monolithic backend test job by:
  - `backend-tests-core` (`apps/core/tests`)
  - `backend-tests-ingest-devtools` (`apps/dat_ingest/tests apps/dev_tools/tests`)
- Maintain shared env/service setup consistency.
- Generate coverage per job (`coverage.xml` + `.coverage.*` artifacts).
- New combine step/job:
  - download artifacts
  - `coverage combine`
  - `coverage xml`
  - enforce total threshold >= 80

### Safety checks
- Ensure no duplicate counting or missing modules in combined report.
- Validate quality gate semantics unchanged in aggregator.

### Acceptance criteria
- Backend PR critical path reduced vs baseline.
- No increase in flaky failures.
- Coverage threshold enforcement preserved on combined result.

### Rollback
- Revert to single serial backend tests job.

## Phase 3 (optional optimization track, non-blocking)

### Objective
Create an experimentation lane for future speedups without risking required gates.

### Scope
- Add non-required canary workflow/job for xdist experiments.
- Introduce targeted flake triage and stabilization backlog from canary findings.
- Keep required gate on safe serial strategy.

### Technical outline
- Canary runs on schedule + manual dispatch.
- Configurable matrix for xdist modes/workers (`2`, `auto`, `loadscope/loadfile`).
- Publish experiment report artifact with failing tests and failure signatures.

### Safety checks
- Canary never blocks merge.
- Findings create follow-up issues before any promotion to required path.

### Acceptance criteria
- At least 2 weeks of canary evidence before reconsidering required xdist.
- Documented list of non-parallel-safe tests with owner and fix status.

### Rollback
- Disable canary workflow without impacting required checks.

## 5. Success metrics

- Primary:
  - PR wall time p95 reduction for non-backend PRs (target: >50%).
  - PR wall time p95 reduction for backend PRs after phase 2 (target: 15-30%).
- Quality:
  - no increase in flaky reruns/failures.
  - no false green incidents in required backend checks.

## 6. Planned issues

- Phase 1 issue: #675
  - https://github.com/matheusnorjosa/aprender_sistema/issues/675
- Phase 2 issue: #676
  - https://github.com/matheusnorjosa/aprender_sistema/issues/676
- Phase 3 issue: #677
  - https://github.com/matheusnorjosa/aprender_sistema/issues/677

## 7. Execution order

1. Phase 1
2. Phase 2
3. Phase 3

No phase should start before acceptance criteria of previous phase are confirmed.
