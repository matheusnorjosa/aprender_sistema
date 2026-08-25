---
name: deprecation-and-migration
description: Deprecate and remove old APIs, models, fields, or dependencies in AS v2 without breaking consumers. Use when replacing a lib/service/model with a new one, consolidating duplicates, or deleting dead code — follow the ordered procedure and its completion gates before removing anything.
---

# Deprecation and Migration — Aprender Sistema

**Code is a liability, not an asset.** Every line costs maintenance, security patches, and onboarding overhead. Deprecation removes code that no longer earns its keep — but only after a replacement exists and every consumer has moved.

## The Procedure

Run these phases in order. Each phase has a **gate**: do not advance until every box is checked. This is the whole skill — the rest of the document is supporting reference.

### Phase 1 — Decide (gate: replacement is real)

- [ ] **Replacement exists and is production-proven.** NEVER deprecate without an alternative; if it doesn't exist, build it first.
- [ ] Confirmed this code provides no remaining unique value.
- [ ] Consumer inventory documented (grep usage; write the list into an issue).
- [ ] Decision recorded: advisory vs compulsory, with reasoning → `reference/advisory-vs-compulsory.md`.
- [ ] Ongoing cost of *keeping* it named (security risk? engineer time? dependency freeze?).

**Gate:** a named replacement + a written consumer inventory exist. Stop here otherwise.

### Phase 2 — Announce + tool (gate: migration is possible, not just declared)

- [ ] Migration guide written, with before/after examples.
- [ ] Migration tooling (codemods, scripts) prepared if the change is non-trivial.
- [ ] Epic + sub-issues created, one per migration phase.
- [ ] Strategy chosen (strangler / adapter / two-phase migration) → `reference/migration-patterns.md`.
- [ ] Deprecation marked *in code* (docstring, `X-Deprecation`/`X-Sunset` header, or nullable field) → `reference/migration-patterns.md`.

**Gate:** a consumer could migrate today using your guide/tooling. A deprecation notice without tooling is a Red Flag (`reference/rationalizations.md`).

### Phase 3 — Migrate consumers (gate: zero remaining usage)

- [ ] Each consumer migrated and verified (tests green).
- [ ] No new usages added during migration (grep guard in CI).
- [ ] Metrics/logs show declining usage of the old system.

**Gate:** zero active consumers, verified via grep + metrics/logs. **The Churn Rule:** if you own the deprecated code, *you* migrate the consumers — don't announce "deprecated" and expect users to move. You own both until the old one is gone.

### Phase 4 — Remove (gate: no trace left)

- [ ] No references in code, tests, docs, or config.
- [ ] ADR/spec status updated (e.g. Accepted → Implemented).
- [ ] `package.json` / `requirements.txt` cleaned.
- [ ] Deprecation warnings removed; old docs deleted or moved to `_archive/`.
- [ ] Epic closed with a summary PR description.

**Gate:** removal is complete only when grep finds nothing across code, tests, docs, and config.

## Worked example: Axios → fetch (Epic #1039)

The axios removal is the canonical run of the procedure above — read it as the template, then apply the phases to your own case.

1. **Trigger (Phase 1):** supply-chain risk on the axios npm package (CVE-2025-27152). Replacement = native `fetch` wrapped in `src/api/config.ts`.
2. **Pin + plan (Phase 1-2):** axios pinned exact as the emergency stopgap; plan captured in `docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md` (full plan archived at `v2/docs/_archive/plans/PLAN_axios_to_fetch_migration.md`).
3. **Tooling (Phase 2):** added `fetchBlob` and `fetchWithErrorMapping` to `config.ts` so clients had feature parity.
4. **Migrate (Phase 3):** moved clients one PR at a time — `acoesNotificacao.ts` (simplest), `adminDAT.ts` (error mapping), `datModule.ts` (blob support) — then the hook/component consumers.
5. **Remove (Phase 4):** deleted the dead client layer and uninstalled axios from `package.json`.
6. **Verify (Phase 4 gate):** ~40KB smaller bundle, zero axios imports, all tests green. There is no `src/api.ts` or `httpClient.ts` — the single wrapper is `config.ts`.

## Decision shortcut

```
1. Still provides unique value? ........ YES: maintain. NO: continue.
2. How many consumers? ................. quantify via grep before anything else.
3. Replacement exists? ................. NO: build it first. Never deprecate without one.
4. Migration cost per consumer? ........ trivial → automate + migrate yourself.
5. Cost of NOT deprecating? ............ security risk / engineer time / dependency freeze?
```

## When this skill applies

- Replacing an old lib/API/model/field with a new one (e.g. axios → fetch).
- Consolidating duplicate systems (e.g. multiple notification paths).
- Removing zombie code — no owner, but still has consumers → `reference/zombie-code.md`.
- Sunsetting unused features (check metrics first).

## Reference

- `reference/migration-patterns.md` — strangler, adapter, two-phase Django migration, in-code deprecation markers.
- `reference/advisory-vs-compulsory.md` — choosing the deprecation mode.
- `reference/zombie-code.md` — detecting ownerless code with live consumers.
- `reference/rationalizations.md` — counters to "it still works" + Red Flags list.
- Epic #1039 — axios → fetch (worked example).
- `docs/architecture/project-decisions/ADR-013-axios-pinning-fetch-migration.md` — axios pin + fetch migration.
- `v2/docs/specs/frontend/api-clients.spec.md` — living index for the `src/api/` layer.
- Memory `project_etl_removed.md` — `apps.dat_ingest` deletion (a completed compulsory removal).
