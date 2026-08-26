---
name: findings-crosscheck
description: Adversarially verify REPORTED findings against the real code before any of them becomes a task. Use when an audit, a security scan, another agent's relay, a "N fields are missing / X is broken" list, a bug report, or even your own claim from a past session asserts something is true about the system — triage the falsifiable claims, fan out one verifier per claim (file:line CONFIRMED/REFUTED/RECLASSIFIED), adversarially verify the consequential ones in BOTH directions, reproduce alarming numbers, and only let survivors become work.
---

# Findings Cross-Check — Aprender Sistema v2

**A reported finding is a hypothesis, not a fact.** Reproduce it against the real code before it
becomes a task. A scan that doesn't reach its target returns empty, and empty reads as absence —
so the error is always *directional*: reports hide real state, they don't invent it.

> **SSOT**: the living defect audit is `v2/docs/audits/ACHADOS_REAIS.md` (cross-reference every
> surviving finding there before opening an issue — see [[reference-achados-reais-living-audit]]).
> This skill is the *operational method*; it complements — does not replace — `plan-crosscheck`
> (which verifies a PLAN you are about to write, not findings someone reported).

## When to use

Invoke the moment findings *arrive* — before triaging them into issues, a plan, or a debugging session:

- An external report lands: audit, security/CodeQL scan, a relay from another agent/tool, a
  spreadsheet-reconciliation ("76 fields have no home", "156 events collide").
- A claim asserts the system is broken/missing/dead ("the importer drops these fields", "this
  serializer is unused", "X is not implemented") and you're about to act on it.
- You're revisiting a **claim you or a past session wrote** (a memory, a TODO, an ACHADOS row) and
  the code has moved since.

**Skip when**: the failure is already reproduced as real (a red test, a stack trace) — go straight
to `debugging-and-error-recovery`; or the input is a PLAN you'll implement — use `plan-crosscheck`.

## The method

**1. Triage the report into falsifiable claims, by who can settle them.**
- **System-side** (verifiable in code, file:line) — the bulk; this skill's job.
- **Source-side** (about a spreadsheet/external dataset you can't read locally) — you cannot confirm;
  relay a request for an *aggregate measurement* back (never open PII files).
- **Business decision** (intent, not fact) — route to the owner; don't guess.

**2. Fan out one verifier per claim (or cluster), READ-ONLY, returning file:line.** Use the Workflow
template in [reference/workflow-template.md](reference/workflow-template.md). Each verifier returns
`{verdict, evidence(file:line), how}` where verdict ∈ **CONFIRMED / REFUTED / RECLASSIFIED /
NEEDS-RUNTIME**. A "home exists" can be a same-name field, a **renamed** field, reachable via an
**FK path**, a `@property`, a serializer field, or **derived** — not just a same-name grep. Delegate
the wide reads; keep synthesis in the main context.

**3. Adversarially verify the CONSEQUENTIAL verdicts — in BOTH directions.** Both errors cost:
- a **false GAP** (finder says "missing" but it exists) → *phantom construction work*;
- a **false EXISTS/"fixed"** (finder says "has a home / handled") → *hidden bug or data loss*.

  For a `GAP` verdict, a skeptic tries hard to *find* a home it missed. For an `EXISTS`/fix verdict,
  a skeptic tries to *refute* it: does the claimed home actually store and carry **this** datum, or
  is it a same-named field / a computed property that loses info? Is the fix sufficient, or does a
  residual case survive?

**4. Reproduce every alarming number before it becomes a task.** Measure, don't accept. Coverage that
looks good can hide the *wrong target* — re-measure against the alternative (75.6% vs **100%** flipped
an FK's target). In this project's history: *"57 fields don't arrive"* → **4**; *"4 import defects"* →
**0**; *"76 fields to build"* → **31 already had a home**.

**5. Apply the blind-instrument test.** Ask: *what would I see if my scan were blind?* If the answer is
"exactly this number", it measured nothing — the empty came from the instrument, not the system.
Known blind spots that all read as false absence: filter-by-filename (code lives in packages),
excluded dirs (`services/`), path bugs (a `"/services/"` check that never matches), regex blind to
annotated FKs (`municipio: models.ForeignKey[...]`), a conclusion drawn from a 2-line sample.

**6. Guard your own verification.**
- Don't turn *your* hypothesis into a refuted claim the source never made (unintentional strawman).
- A content-verification guard must check the **axis of the ambiguity**, not the fields that already
  match by construction (checking município+data+hora is a no-op when those are exactly what tied).
- Reproduce the **negatives** too: *"this is junk / doesn't exist"* deserves the same proof as
  *"this is a bug"*.

**7. Only survivors become work.** Cross-reference `ACHADOS_REAIS.md` before opening an issue (avoids
duplicates). Relay corrections back to the source so its map improves. Reclassify honestly: a
"defect" that is really *unimplemented scope* is a different (often deferred) task than a bug.

## Anti-patterns

| Excuse / Red flag | Reality | Action |
|-------------------|---------|--------|
| "The report is detailed, it's probably right" | Detail ≠ verified. The relay that reported 9 findings had all 9 wrong, same direction. | Reproduce each falsifiable claim file:line. |
| "It's not in the model, so it's a gap" | Grep by name misses FK-backed, renamed, folder-nested, and derived homes. | Check field / FK path / property / serializer / derivation before calling GAP. |
| "The scan found nothing there" | A scan that can't reach returns empty = false absence. | Blind-instrument test: would a blind scan show the same? |
| "I verified it exists, done" | An EXISTS can hide a data-loss bug (a unique key that `update_or_create` collapses silently). | Adversarially verify EXISTS too — does it carry THIS datum, is it sufficient? |
| "Adding field X resolves the collision" | X may resolve *because it's noisy*, not because it discriminates; and it may be nullable. | Measure the residual; check stability and the null case. |
| Opening an issue straight from the report | May duplicate an ACHADOS row or an already-merged fix. | Cross-check `ACHADOS_REAIS.md` + PR state first ([[feedback-verify-issue-not-already-resolved]]). |

## Verification checklist

Before any finding becomes a task:
- [ ] Every falsifiable claim has a file:line verdict (CONFIRMED/REFUTED/RECLASSIFIED/NEEDS-RUNTIME).
- [ ] Consequential verdicts got an adversarial second pass in the direction that costs.
- [ ] Every alarming number was reproduced (and measured against the alternative target).
- [ ] Blind-instrument test applied to every "nothing/absent" result.
- [ ] Survivors cross-referenced against `ACHADOS_REAIS.md` (no duplicate issue).
- [ ] Source-side claims relayed back as aggregate measurements; business calls routed to the owner.

## Worked example (this method's origin — the sheets.banco relay, 2026-08-25)

An external agent relayed a field-by-field map of the system. Cross-checked with fan-out + adversarial
verify: of **76** "fields with no home", **31 already had one** (FK/rename/derived — the scan's regex
was blind to annotated FKs); the **"4 import defects"** were **0** (the entities weren't implemented in
that importer at all — reclassified as scope, not bug); and one surviving finding — a dedup hash whose
6-field recipe collided on **284→128** real events — was a genuine silent-data-loss bug
(`update_or_create(external_hash=…)` overwriting in place, counted as success). The relay's *own*
proposed fix ("add `segmento`") was then overturned by measurement (segmento is noisy, 579 empty), and
a stable id (`external_event_id`) turned out to be attachable only heuristically — so a guard that
checked município+data+hora was a **no-op on the exact ambiguous tier**. Every correction, in both
directions, came from reproduction — none from opinion.

## Related skills

- Runs **before** `create-plan` / `debugging-and-error-recovery`: triage the finding first, so only
  survivors become a plan or a bug. (Sibling of `plan-crosscheck`, which sits *after* create-plan.)
- Uses `subagent-development` (fan-out) and the `Workflow` tool for the verifier panel.
- Feeds `verification-gate` (prove your own resulting fix works) once a survivor becomes work.
- Encodes the memories: [[feedback-multi-claude-relay-verify-system-side]] ·
  [[feedback-metadata-vs-code-verification]] · [[feedback-comentario-nao-e-evidencia]] ·
  [[feedback-first-real-execution-latent-bugs]] · [[feedback-workflow-verifier-silent-drop]] ·
  [[reference-dynamic-runtime-audit-playbook]].
