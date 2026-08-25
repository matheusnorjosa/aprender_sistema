---
name: plan-crosscheck
description: >
  Adversarially cross-check an implementation plan against the REAL code before
  writing any of it. Fans out one verifier per plan-part that reads the code,
  confirms or refutes each claim with file:line, gives the concrete edit, and
  hunts for gaps — plus one skeptic that finds what the plan forgot. Use after
  drafting any non-trivial plan (multi-file, auth/RBAC/data-scope, migrations,
  many call-sites, contract/schema changes), BEFORE implementing.
---

# Plan Cross-Check

A plan is a **hypothesis**, not a fact. Line numbers drift, call-sites get
missed, `ativo`-style filters are applied inconsistently, edge cases hide behind
reverse relations. Before spending effort implementing, **prove the plan against
the real code** — and let the human approve the *revised* plan, not the guess.

This skill sits between `create-plan` and `implement-plan`:
`create-plan` → **plan-crosscheck** → `implement-plan`.
It complements `verification-gate` (which verifies *finished work*); this verifies
the *plan*.

## When to use

Run it once a plan exists and **before** the first edit, when the plan is
non-trivial in any of these ways:
- touches **many files / call-sites** (e.g. "update all N places that read X");
- changes **authorization, RBAC, or data-scope** (a missed site is an access leak);
- adds a **migration / schema / DB constraint** (ordering, backfill, deploy risk);
- changes a **shared contract** (serializer, importer, API) with downstream readers;
- crosses subsystems where you can't hold every detail in one head.

**Skip it** for trivial one-file changes with no auth/migration/contract surface —
there a single inline re-read of the file is enough. Don't fan out to prove a typo.

## The method

1. **Split the plan into PARTS** that can each be verified independently — usually
   one per subsystem or file-group (model+migration, the auth core, the view layer,
   the writer, tests/fixtures). Aim for 3–6 parts.

2. **One verifier per part** (Workflow fan-out, or parallel `Agent` calls if
   Workflow isn't opted-in). Give each verifier the **full plan** plus its assigned
   part, and require it to **read the actual code** and return the structured
   verdict below. Verifiers are **read-only** — they check, they don't edit.

3. **Always add one ADVERSARIAL / completeness verifier** whose only job is to break
   the plan: *"what did this forget, where does it break?"* It must
   `grep` for **every** usage — including **reverse relations / `related_name`**
   (`obj.related_set`, `field__lookup`), admin, serializers, signals, management
   commands, and the **frontend/API** — to catch call-sites the plan never listed.
   It also probes migration/deploy risk and **tests that depend on the current
   (possibly buggy) behavior** and will flip red.

4. **Synthesize** the verifier results into a **revised plan**: fold in the
   corrections, add the missed sites, resolve or escalate each risk. Surface the
   *furos* (gaps) and material changes to the human, and get approval on the revised
   plan. **Do not start implementing while any part is `plano-tem-furo`.**

## Verifier output schema (reuse verbatim)

```
{
  part:          string,                                  // which plan part
  verdict:       "plano-ok" | "plano-ok-com-ajustes" | "plano-tem-furo",
  verified:      string[],   // plan claims CONFIRMED in code, each with file:line
  corrections:   string[],   // where the plan is wrong/incomplete + the concrete fix
  exact_changes: string[],   // the real edit per file:line (what to change to what)
  risks:         string[],   // edge-cases / gotchas the plan doesn't cover
}
```

## Verifier prompt shape (per part)

> Here is the PLAN: `<full plan>`.
> VERIFY PART N against `<the exact files/lines it touches>`. Confirm each claim
> with file:line, or refute it. For every change the plan proposes, read the
> current code and give the **exact** edit (current line → new line). Flag any
> place the change doesn't compose (e.g. `.exists()` vs `.values_list()` vs a
> reverse-relation join). List risks the plan misses. Read-only — don't edit.

## Discipline (what makes it worth the tokens)

- **Evidence, not memory** — every "verified" item carries `file:line`. A claim
  without a line reference isn't verified.
- **The helper must compose** — when the plan says "reuse one predicate across N
  sites", have a verifier confirm the sites are shape-compatible (a reusable `Q`
  composes into `.filter`/`.exists`/reverse joins; a ready-made queryset often
  doesn't). Getting this wrong is the classic authz-drift bug.
- **`get_queryset` must match object-permission** — for data-scope, the list filter
  and the object-level check must use the **same** definition, or "list shows it but
  the object 404s".
- **Behavior changes are decisions, not side effects** — if the cross-check reveals
  the plan *fixes a latent bug* (e.g. an inactive/expired row that currently still
  grants access), name it explicitly and get the human to accept the access change.
- **Reverse relations are where sites hide** — grep `related_name` and `__` lookups,
  not just the model class name.
- **Cross the result back before coding** — the plan may change materially; the
  human approves the revised plan.

## Relation to other skills

- `create-plan` produces the plan; **plan-crosscheck** stress-tests it; `implement-plan`
  executes the approved, revised plan (with `test-driven-development`).
- `verification-gate` verifies *finished* work; this verifies the *plan*.
- Pair with `software-engineering` / `ponytail` (don't cross-check speculative
  over-engineering into existence — cut it first, then verify what remains).
