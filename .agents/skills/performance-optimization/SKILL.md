---
name: performance-optimization
description: Profile and optimize AS v2 performance (Django backend + React frontend). Use when an endpoint is slow, a request fires N+1 queries, the bundle grows, or Core Web Vitals miss target.
---

# Performance Optimization — Aprender Sistema

**Measure before optimizing.** Profile first, identify the actual bottleneck, fix it, measure again. Don't scatter `React.memo` or `select_related` on a hunch.

AS v2 has active perf epics: **#777 (grid phases)**, **#866 (ACID)**. PR #1160 cut monthly grid p95 by -69% (phase 2).

## Workflow

```
1. MEASURE  → Establish baseline (numbers, not feelings)
2. IDENTIFY → Find the actual bottleneck (profile, don't guess)
3. FIX      → Address that specific bottleneck
4. VERIFY   → Measure again, confirm improvement vs baseline
5. GUARD    → Add a test/monitor to prevent regression
```

Done when: before/after numbers are recorded, the targets below are met, and a guard exists.

## Where to look

- Backend (query profiling, N+1, indexes, aggregations, Celery, Redis cache): [reference/backend.md](reference/backend.md)
- Frontend (Lighthouse, bundle analysis, re-renders, Antd, code splitting, images, caching): [reference/frontend.md](reference/frontend.md)

## Targets (CI enforced)

### Backend (Django/DRF)

| Metric | Target | Where |
|--------|--------|-------|
| API p95 latency | ≤ 200ms | gunicorn logs |
| DB queries per request | ≤ 10 | `django-debug-toolbar` (dev) |
| Cache hit rate (Redis) | ≥ 70% | availability queries |
| Monthly grid p95 | ≤ baseline −69% | after #777 phase 2 |

### Frontend (React/Vite), from `v2/frontend/lighthouserc.cjs`

| Metric | Target | Severity |
|--------|--------|----------|
| Lighthouse Performance | ≥ 70 | error (fails CI) |
| Lighthouse Accessibility | ≥ 90 | error (fails CI) |
| LCP | ≤ 2.5s | error |
| CLS | ≤ 0.1 | error |
| Total Blocking Time | ≤ 300ms | error |
| Initial JS bundle (gzipped) | ≤ 250KB | Antd is the main weight |
| `manualChunks` in vite.config | none | breaks dep ordering (prod crash) |

Current Lighthouse: Desktop 95, Mobile 79 (mobile bottleneck = antd bundle).

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "It's fast on my machine" | Profile on prod-like conditions (docker + realistic data volume) |
| "Users won't notice" | RUM from real users. 100ms matters. |
| "Framework handles perf" | Django/React prevent some issues, not N+1 or bundle bloat |
| "We'll optimize later" | Perf debt compounds. Fix N+1 and bundle issues now. |
| "The DB is fast enough" | Check query count and duration per request |

## Verification

After a perf change:

- [ ] Before/after measurements with specific numbers
- [ ] Bottleneck identified (not guessed)
- [ ] Core Web Vitals in target range
- [ ] Bundle size change reviewed
- [ ] No new N+1 queries
- [ ] Lighthouse CI passes
- [ ] Existing tests still pass

## References

- Epic #777: Monthly grid optimization · Epic #866: ACID/deadlock handling
- PR #1160: Phase 2 grid p95 -69%
- Memory: Lighthouse scores · `feedback_no_manual_chunks.md` · `feedback_react18_fetchpriority.md`
