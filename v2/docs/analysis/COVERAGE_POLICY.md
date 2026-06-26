# Coverage Policy

Backend coverage gate is unified at **85%** across every enforcement point.

## Thresholds

| Location | Setting | Value |
|----------|---------|-------|
| `v2/backend/pytest.ini` | `[coverage:report] fail_under` | 85 |
| `.github/workflows/ci.yaml` (combine step) | `coverage report --fail-under=85` | 85 |

No other places enforce a backend coverage threshold. Historical plans that
reference `80` are kept for auditability; they do not govern current runs.

## Baseline

Observed on the last backend-touching main run before this policy unification
(run `24585072952`, PR #1148):

| Slice | Coverage |
|-------|---------:|
| `apps/core` (core suite alone) | 87% |
| `apps/dev_tools` (dev_tools suite alone) | 9% (low because the suite
exercises a narrow slice of `apps/` — combine step is the authoritative number) |
| **Combined (core + dev_tools)** | **90%** |

The 85% gate leaves a 5-point headroom above the current combined baseline.

## Regression policy

- A PR is considered in regression if the combined report drops below 85%.
- CI fails the `Combine backend coverage` step when the threshold is breached;
  no further manual review required.
- Raising the threshold is done via a dedicated PR that updates this doc,
  `pytest.ini`, and `ci.yaml` in the same change so the three never drift.

## Roadmap

1. **Now**: 85% combined — enforced.
2. **Next** (#850 phase 2): publish a per-run quality scorecard (pass rate,
   p50/p95 duration per suite, flake rate from `#677` canary) as a CI summary
   artifact. Scorecard is informative until thresholds are agreed.
3. **Later**: raise combined coverage target toward 90% once the scorecard
   stabilizes and flake rate is below the agreed ceiling.

## Related issues

- Epic [#845](https://github.com/matheusnorjosa/aprender_sistema/issues/845) — Testing Maturity
- [#850](https://github.com/matheusnorjosa/aprender_sistema/issues/850) — Unify coverage policy + scorecard
- [#677](https://github.com/matheusnorjosa/aprender_sistema/issues/677) — xdist canary (flake rate input)
- [#268](https://github.com/matheusnorjosa/aprender_sistema/issues/268) — Original coverage bar
