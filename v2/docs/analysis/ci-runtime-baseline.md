# CI Runtime Telemetry

- Generated at (UTC): `2026-02-24T20:09:58.022512+00:00`
- Repo: `matheusnorjosa/aprender_sistema`
- Workflows: `CI – Continuous Integration, frontend-ci, Security Scan`
- Runs per workflow: `30`

| Workflow | Job | Samples | Median (s) | P95 (s) | Min (s) | Max (s) |
|---|---|---:|---:|---:|---:|---:|
| CI – Continuous Integration | [required] backend tests (runner) | 21 | 588.0 | 632.0 | 233.0 | 634.0 |
| CI – Continuous Integration | [required] backend typecheck (pyright) | 12 | 72.0 | 78.0 | 62.0 | 78.0 |
| CI – Continuous Integration | [required] docker parity (backend) | 21 | 128.0 | 135.0 | 118.0 | 149.0 |
| CI – Continuous Integration | [required] lint | 21 | 25.0 | 28.0 | 20.0 | 34.0 |
| CI – Continuous Integration | [required] tests | 21 | 3.0 | 4.0 | 2.0 | 4.0 |
| Security Scan | [required] Container Scan | 22 | 134.0 | 166.0 | 116.0 | 167.0 |
| Security Scan | [required] Frontend Dependencies | 22 | 22.0 | 25.0 | 19.0 | 32.0 |
| Security Scan | [required] Python Dependencies | 22 | 45.0 | 53.0 | 39.0 | 53.0 |
| Security Scan | [required] Secret Detection | 22 | 17.0 | 49.0 | 15.0 | 89.0 |
| frontend-ci | [required] build/lint do frontend | 20 | 55.0 | 59.0 | 47.0 | 68.0 |
| frontend-ci | [required] checklist tests (meta, a11y, security) | 20 | 90.0 | 162.0 | 72.0 | 488.0 |
| frontend-ci | [required] react doctor quality gate | 20 | 33.0 | 36.0 | 28.0 | 38.0 |

## Regression Check

- No p95 regressions detected against baseline threshold.
