# ADR-012 — SHA-1 for idempotency / stable identifier hashes

| Field         | Value                                                   |
| ------------- | ------------------------------------------------------- |
| **Status**    | Accepted                                                |
| **Date**      | 2026-05-18                                              |
| **Deciders**  | Backend (Aprender Sistema) — security session 2026-05   |
| **Issue**     | [#1347](https://github.com/matheusnorjosa/aprender_sistema/issues/1347) — SEC-012 |
| **Related**   | PRs #1325–#1353 (security hardening + imports refactor) |

## Context

The codebase uses `hashlib.sha1(...)` with the PEP 644 `usedforsecurity=False`
flag in several modules to compute **stable idempotency keys** (typically
the `external_hash` column) for ETL-style imports. The hashes are never
used as credentials, signatures, integrity proofs, or any other security
primitive — they exist only so an idempotent re-import can detect that
a given row has already been ingested.

During the security hardening sweep (2026-05-14 → 2026-05-17), GitHub
Advanced Security's CodeQL query `py/weak-sensitive-data-hashing`
(CWE-327 / CWE-328 / CWE-916) repeatedly opened alerts on these
call-sites because its taint-tracking does **not** respect the
`usedforsecurity=False` parameter — once it sees a variable named
`certificate`, `id`, `email`, `payload` (etc.) flowing into
`hashlib.sha1`, it reports a high-severity finding regardless of intent.

This ADR documents the project's standing decision on when SHA-1 with
`usedforsecurity=False` is allowed, when it is forbidden, why the
historical hashes cannot be migrated away from SHA-1, and how to handle
the recurring CodeQL false positives without lowering the security
posture for genuine cryptographic uses.

## Problem

Two competing requirements:

1. **Conformance / hygiene** — modern static-analysis tooling rightly
   flags raw SHA-1 use because the algorithm is collision-broken and
   inappropriate for cryptographic security in 2026.
2. **Operational stability** — millions of rows of historical data
   (Compra, Solicitacao, Deslocamento, AcaoControle, AcaoDAT,
   Acompanhamento) are keyed on SHA-1-derived `external_hash` columns.
   Changing the algorithm would silently break deduplication on the
   next ETL run and risk re-inserting duplicates that look new because
   their hash changed.

A blanket ban on SHA-1 is technically pure but operationally destructive.
A blanket pass on SHA-1 is operationally pragmatic but masks future
genuine misuse.

## Decision

SHA-1 with `usedforsecurity=False` is **allowed** if and only if **all**
of the following are true:

1. The hash is used as an **idempotency key**, **deduplication key**, or
   **stable identifier** — never as security primitive.
2. The hash does not protect a secret.
3. The hash does not authenticate data against an adversary.
4. The hash is not used for passwords, tokens, signatures, message
   integrity, certificates, or authorization decisions.
5. The value must remain **stable** for backward compatibility with
   already-persisted rows — switching the digest would break
   deduplication / `external_hash` / a third-party integration.
6. The call passes `usedforsecurity=False` explicitly (PEP 644).
7. A docstring, comment, or test pins the stability expectation and
   references this ADR.

If any condition fails, SHA-1 must NOT be used — see the "Forbidden uses"
section below for the alternatives.

## Allowed uses (current inventory)

| Symbol                                                          | Module                                                                                  | Purpose                                                |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `stable_import_hash(*parts: str)`                               | `apps/core/imports/hashing.py`                                                          | Pipe-joined composite key for import services          |
| `hash_event_v2(row)`                                            | `apps/core/imports/hashing.py` (re-exported from `apps/core/services/normalize.py`)     | 17-field idempotency hash for Acompanhamento ETL       |
| `sha1_str(s)` (delegates to `stable_import_hash`)               | `apps/core/services/controle_imports.py`                                                | Compat wrapper for legacy `Compra.external_hash`       |
| `_compute_external_hash(...)` (delegates to `stable_import_hash`) | `apps/core/services/deslocamentos_import.py`                                          | `Deslocamento.external_hash`                            |
| Inline `hashlib.sha1(..., usedforsecurity=False)`                | `apps/core/services/controle_acoes_import.py` (`AcaoControle.external_hash`)            | Pending migration to `stable_import_hash` (issue #1346) |
| Inline `hashlib.sha1(..., usedforsecurity=False)`                | `apps/core/services/dat_cadastros_import.py` (`AcaoDAT.external_hash`)                  | Pending migration to `stable_import_hash` (issue #1346) |
| Inline `hashlib.sha1(..., usedforsecurity=False)`                | `apps/core/services/eventos_import.py` (`Solicitacao.external_hash` via `_compute_external_hash`) | Pending migration to `stable_import_hash` (issue #1346) |
| `_payload_hash(payload)` (GCal idempotency)                      | `apps/core/services/gcal/utils.py`                                                      | Stable hash of Google Calendar payload                  |

Behaviour for every entry above is pinned by snapshot tests in
`apps/core/tests/test_imports_hashing.py` (PR #1344) and
`apps/core/tests/test_services_normalize_equivalence.py` (PR #1350).

## Forbidden uses

SHA-1 must **never** be used for:

* Passwords or any credential hashing — use a memory-hard KDF (Argon2id
  via `argon2-cffi`, or Django's built-in PBKDF2 hasher).
* Tokens or session identifiers — use `secrets.token_urlsafe` /
  `secrets.token_bytes`.
* Message authentication / signatures — use `hmac.new(..., digestmod=hashlib.sha256)`
  or `hashlib.sha256` directly for integrity proofs.
* Verifying integrity of any data that an adversary may have tampered
  with — use SHA-256 (or stronger) so collision resistance matters.
* Certificate fingerprints presented as security evidence — use SHA-256.
* Authorization / authentication decisions of any kind.
* Hashing data when collision resistance against an attacker is a
  security property of the system.

In any of those cases, choose the modern alternative (Argon2,
PBKDF2-HMAC-SHA256, SHA-256, HMAC-SHA256, `secrets.*`).

## When to use SHA-256 (or stronger) for new code

* Any new feature where collision resistance is part of the threat model
  — even if the value is "just an identifier" today, if it will protect
  something tomorrow, start with SHA-256.
* Any new persisted hash column with no historical baggage — there is no
  reason to start with SHA-1 in 2026.
* Anything that crosses a trust boundary (request → server, server →
  external API verifying integrity, etc.).

For `stable_import_hash`-style idempotency keys in **new** import
services where no historical `external_hash` already exists, prefer
`hashlib.sha256(...)`. Document the choice in the helper's docstring.

## Why historical hashes are not migrated

The persisted `external_hash` values were computed with SHA-1 in earlier
sessions of the ETL pipeline and are now part of the persistent contract
of the data layer:

* `Compra.external_hash`, `Solicitacao.external_hash`,
  `Deslocamento.external_hash`, `AcaoControle.external_hash`,
  `AcaoDAT.external_hash`, plus the Acompanhamento `hash_event_v2`
  output, are all 40-character SHA-1 hexdigests stored in unique-indexed
  columns.
* Re-keying these would require a coordinated migration (compute the
  SHA-256 of every row, swap the unique constraint, update every
  importer atomically with the new helper, deal with rows that arrive
  during the cutover) — a multi-day operation with rollback complexity
  and no security benefit (the hash is not protecting anything from an
  adversary).
* The cost-benefit math does not justify it: the threat model
  here is "two CSVs produce the same row", not "an attacker forges a
  collision".

Hence the explicit decision: **freeze SHA-1 for the historical columns,
SHA-256 for anything new where collision resistance is actually a
property**.

## Relationship with CodeQL `py/weak-sensitive-data-hashing`

CodeQL flags these usages because its dataflow taint heuristic looks at
the *source variable name* — terms like `id`, `email`, `certificate`,
`payload`, `cert` are tagged as sensitive, and any `hashlib.sha1(...)`
sink consuming them produces an alert. The query does **not** read the
`usedforsecurity=False` keyword argument as a sanitizer.

Project policy:

* Do not silence CodeQL automatically. There is no global suppression,
  no `# nosec` blanket, no rewrite to evade the query.
* Analyse every new alert case-by-case.
* Dismiss as `false positive` (via UI or `gh api .../code-scanning/alerts/<n> --method PATCH`)
  **only** when the call passes every criterion in the "Decision"
  section above. The dismissal comment must reference this ADR and the
  specific helper/column being protected.
* Maintain a comment or docstring at the call-site explaining the
  stability requirement.
* Never reuse this pattern for a genuinely security-critical hash.

### Dismissal history (for traceability)

| Alert | Path                                              | PR     | Justification (summarized) |
| ----- | ------------------------------------------------- | ------ | -------------------------- |
| #20   | `services/controle_imports.py:46` `sha1_str`       | #1342  | `Compra.external_hash` idempotency |
| #21   | `services/gcal/utils.py:170` `_payload_hash`       | #1342  | GCal payload stable hash |
| #26   | `services/normalize.py:406` `hash_event_v2`        | #1350  | Acompanhamento ETL idempotency |
| #27   | `imports/hashing.py:186` `hash_event_v2` (moved)   | #1353  | Same as #26 after migration |

All four follow the same dismissal pattern documented here. Any future
alert that does **not** match this pattern must be treated as a real
finding, not dismissed.

## Consequences

### Positive

* Historical idempotency is preserved — no risk of duplicate rows from
  a digest-algorithm cutover.
* Bandit's `B324` weak-hash warning is silenced via PEP 644 — no inline
  `# nosec` litter required.
* The policy is explicit and testable: every dismissed CodeQL alert can
  be audited against the criteria in this ADR.
* New code defaults to SHA-256, so the SHA-1 footprint stops growing.

### Negative

* CodeQL will keep generating false positives whenever any of the
  documented call-sites moves files or gains new callers (see #26 vs #27:
  the very same `hash_event_v2` function generated a new alert just by
  changing path). Each requires a manual dismissal referencing this ADR.
* New contributors must read this ADR before adding a new `hashlib.sha1`
  call. A pre-commit hook or rbac-lint-style guard could be added later
  (out of scope for this ADR).
* A future GitHub feature that finally honours `usedforsecurity=False`
  in CodeQL would render the dismissals redundant; that is acceptable
  — we revisit then.

## Future work

* (Optional) Add a `scripts/sha1_audit.py` that walks the repo and
  surfaces every `hashlib.sha1` call, asserting each is matched to an
  entry in the "Allowed uses" table above. Could run as a `[required]`
  CI check.
* Consider switching `stable_import_hash` to SHA-256 by introducing
  `stable_import_hash_v2(*parts: str) -> str` for **brand-new**
  importers (no migration of existing data). Out of scope here.
* Track SEC-012 closure once this ADR is merged.

## References

* PEP 644 — `usedforsecurity` keyword for `hashlib` constructors.
* CWE-327 — Use of a Broken or Risky Cryptographic Algorithm.
* CWE-328 — Reversible One-Way Hash.
* CWE-916 — Use of Password Hash With Insufficient Computational Effort.
* CodeQL query `py/weak-sensitive-data-hashing` — Python sources.
* OWASP Password Storage Cheat Sheet.
* Internal: `apps/core/imports/README.md` — namespace policy.
* Internal: `apps/core/imports/hashing.py` — `stable_import_hash`,
  `hash_event_v2`.
* Internal: `apps/core/tests/test_services_normalize_equivalence.py`
  (PR #1350) — 75 behavioural snapshots including `hash_event_v2`.
* Internal: `apps/core/tests/test_imports_hashing.py` (PR #1344) —
  byte-equivalence snapshots for `stable_import_hash`.
