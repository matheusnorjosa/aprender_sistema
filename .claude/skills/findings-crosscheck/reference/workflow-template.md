# Workflow template — findings cross-check fan-out

Copy-paste scaffold for step 2–3 of `findings-crosscheck`: fan out one verifier per claim-cluster,
then adversarially verify the *consequential* verdicts in the direction that costs. Distilled from the
two real fan-outs of 2026-08-25 (the 54-field home-check and the external_hash collision check).

Pass your real claim list in `CLUSTERS`. Each verifier is READ-ONLY and returns file:line verdicts.
The adversarial pass fires only for GAP verdicts + any you flag as high-stakes (a false EXISTS there
would hide a bug). Keep synthesis in the main context — the workflow returns structured data.

```javascript
export const meta = {
  name: 'findings-crosscheck',
  description: 'Verify reported findings against the code (file:line), then adversarially re-check the consequential ones',
  phases: [{ title: 'Verify' }, { title: 'Adversarial' }],
}

const REPO = '.'  // repo root = the working directory (backend at v2/backend/apps/core).
                  // NEVER hardcode an absolute path here — use $CLAUDE_PROJECT_DIR; a hardcoded c:\… path once broke CI.

// One entry per coherent cluster of claims (group by the model/file they touch).
const CLUSTERS = [
  { key: 'usuario',   claims: ['usuario.nome_completo', 'usuario.email', '...'] },
  { key: 'importer',  claims: ['formacao.numero_formacao writes?', '...'] },
  // ...
]

const FINDER_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: { findings: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    properties: {
      claim: { type: 'string' },
      verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'RECLASSIFIED', 'NEEDS_RUNTIME'] },
      how: { type: 'string' },            // direct field / renamed / via FK <path> / property / derived / gap
      evidence: { type: 'string' },       // file:line — required
    }, required: ['claim', 'verdict', 'evidence'],
  } } }, required: ['findings'],
}
const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    claim: { type: 'string' }, upheld: { type: 'boolean' },
    corrected_verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'RECLASSIFIED', 'NEEDS_RUNTIME'] },
    evidence: { type: 'string' },
  }, required: ['claim', 'upheld', 'corrected_verdict', 'evidence'],
}

// Flag the claims where a WRONG "exists/fixed" would hide a bug (verify those too, not just GAPs).
const HIGH_STAKES = new Set([/* 'the dedup key is unique', ... */])

const results = await pipeline(CLUSTERS,
  (c) => agent(
    `READ-ONLY (do NOT edit). Repo: ${REPO}. For each claim decide if the SYSTEM already has a home / the claim holds, and return a per-claim verdict with file:line. A "home" = same-name field, RENAMED field, reachable via an FK path (name it), a @property, a serializer field, or DERIVED — not just a same-name grep. If a dynamic **payload could write it without a literal line, mark NEEDS_RUNTIME (don't assert absence). The hints in the claims are a SOURCE's bet — may be wrong; verify. Claims:\n- ${c.claims.join('\n- ')}`,
    { label: `verify:${c.key}`, phase: 'Verify', agentType: 'general-purpose', schema: FINDER_SCHEMA }
  ).then(r => ({ cluster: c.key, findings: (r && r.findings) || [] })),

  (fr) => {
    const consequential = fr.findings.filter(f => f.verdict === 'GAP_REAL' || f.verdict === 'REFUTED' || HIGH_STAKES.has(f.claim))
    if (!consequential.length) return { ...fr, verified: [] }
    return parallel(consequential.map(f => () => agent(
      `READ-ONLY. Repo: ${REPO}. Adversarially re-check ONE claim.\nClaim: ${f.claim}\nFinder verdict: ${f.verdict} — ${f.how} (${f.evidence})\n` +
      (f.verdict === 'REFUTED'
        ? `Finder says NO home / claim false. Aggressively try to FIND a home it missed (rename, FK, property, serializer, related model). If found, correct it.`
        : `Finder says it holds/has a home. Try to REFUTE: does that home actually STORE and CARRY this exact datum, or is it a same-named field / a computed property that loses info? Is any residual case left? Verify the AXIS of the ambiguity, not fields that already match.`),
      { label: `adv:${f.claim}`, phase: 'Adversarial', agentType: 'general-purpose', schema: VERIFY_SCHEMA }
    )).then(vs => ({ ...fr, verified: vs.filter(Boolean) }))
  }
)

return { results: results.filter(Boolean) }  // synthesize + reproduce numbers + blind-instrument test in the main context
```

## Notes

- **Pipeline, not barrier**: each cluster's adversarial pass starts as soon as its finder returns.
- **Reproduce numbers yourself** after the workflow — a count the finders echo is not a measurement;
  re-derive it and measure against the alternative target.
- **NEEDS_RUNTIME** verdicts (dynamic `**payload`, "only visible when the import runs") are the
  author's honest limit — settle them by running the thing on an isolated clone, not by reading more.
  See [[reference-dynamic-runtime-audit-playbook]] and [[reference-slice-import-validation-playbook]].
- **Cross-check survivors** against `ACHADOS_REAIS.md` before the fan-out result becomes issues.
