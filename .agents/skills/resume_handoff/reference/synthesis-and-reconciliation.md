# Synthesis template and divergence reconciliation

Consult this when presenting the analysis (Step 2) and when the current codebase
has diverged from the handoff state.

## Analysis presentation template (Step 2)

```
I've analyzed the handoff from [date] by [researcher]. Here's the current situation:

**Original Tasks:**
- [Task 1]: [Status from handoff] → [Current verification]
- [Task 2]: [Status from handoff] → [Current verification]

**Key Learnings Validated:**
- [Learning with file:line reference] - [Still valid/Changed]
- [Pattern discovered] - [Still applicable/Modified]

**Recent Changes Status:**
- [Change 1] - [Verified present/Missing/Modified]
- [Change 2] - [Verified present/Missing/Modified]

**Artifacts Reviewed:**
- [Document 1]: [Key takeaway]
- [Document 2]: [Key takeaway]

**Recommended Next Actions:**
Based on the handoff's action items and current state:
1. [Most logical next step based on handoff]
2. [Second priority action]
3. [Additional tasks discovered]

**Potential Issues Identified:**
- [Any conflicts or regressions found]
- [Missing dependencies or broken code]

Shall I proceed with [recommended action 1], or would you like to adjust the approach?
```

## Reconciliation by divergence type

The handoff state is a snapshot; the codebase may have moved. Match the situation
and adapt the plan before proposing actions:

- **Clean continuation** — all handoff changes present, no conflicts. Proceed with
  the recommended actions from "Action Items & Next Steps".
- **Diverged codebase** — some changes missing/modified, new related code added since
  the handoff. Reconcile the differences and adapt the plan to current state.
- **Incomplete handoff work** — tasks marked `work in progress`/`in_progress` in the
  handoff. Re-understand the partial implementation and finish it before new work.
- **Stale handoff** — significant time passed, major refactoring occurred. The original
  approach may no longer apply; re-evaluate strategy before committing to it.
