# Advisory vs Compulsory Deprecation

Decide the deprecation *mode* in checklist step 4 ("Decision: advisory vs compulsory").

| Type | When | How |
|------|------|-----|
| **Advisory** | Replacement works, old is stable | Warnings, docs, nudges. Consumers migrate on their own timeline. |
| **Compulsory** | Security risk, blocks progress, or maintenance is unsustainable | Hard deadline + migration tooling + support. |

**Default to advisory.** Compulsory requires *providing* migration tooling — you cannot just announce a deadline and walk away (see the Churn Rule in SKILL.md).

## AS v2 examples

- **Compulsory:** axios pin + migration to native `fetch` (supply-chain risk, CVE-2025-27152). Tracked as Epic #1039; see `docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md`.
- **Advisory:** legacy settings keys — keep working, mark as deprecated, let consumers move when convenient.
