# Execution Modes

Pick the mode by plan size. The selection criterion is the only thing you need
before starting; the protocol below applies once a mode is chosen.

| Plan size                       | Mode |
|---------------------------------|------|
| 1 wave, ≤3 tasks                | 1 — Direct Implementation |
| 2-3 waves                       | 2 — Wave-based Orchestration |
| 4+ waves (large epics)          | 3 — Fresh Context per Wave |

## Mode 1: Direct Implementation

For small plans (1 wave, ≤3 tasks).

- You implement each task yourself.
- Context accumulates in the main conversation.

## Mode 2: Wave-based Orchestration

For plans with 2+ waves. Adapted from GSD's context-rot prevention.

- Each wave executes in a focused context.
- Agents execute tasks within each wave in parallel.
- Between waves: verify, update checkmarks, then proceed.
- If context reaches 70%: save ledger (`continuity_ledger` skill), `/clear`, resume from plan.

## Mode 3: Fresh Context per Wave

For plans with 4+ waves or context-heavy tasks.

- Save the continuity ledger before each wave.
- Each wave starts with fresh context (after `/clear`).
- The agent reads plan + ledger to resume exactly where it left off.
- Eliminates context rot entirely.

## Wave Execution Protocol

### Before each wave

1. **Load context**: Read the plan, identify the current wave.
2. **Check dependencies**: All previous waves completed? Tests passing?
3. **Identify parallel tasks**: Tasks within a wave without dependencies.
4. **Spawn agents**: For parallel tasks, use `Explore` / `general-purpose` (or `Workflow` for fan-out).

### During execution

1. Follow the plan's intent while adapting to reality.
2. For each task:
   - Read target files fully before editing.
   - Make changes following the `django-patterns` skill.
   - Run relevant tests after each change.
   - Update the checkbox in the plan: `- [x] Task completed`.
3. If something doesn't match the plan, explain why and adapt.

### After each wave

1. **Verify**: Run the wave's verification steps (see `verification-gate.md`).
2. **Commit**: If the wave is independently valuable, commit with conventional format (CP-06).
3. **Update plan**: Mark the wave as complete.
4. **Context check**: If context > 70%, save the ledger and suggest `/clear`.

### Wave transition (Mode 3)

When transitioning between waves in fresh-context mode:

```
Wave N complete. Verification passed.

Before proceeding to Wave N+1:
1. Saving continuity ledger...
2. Updating plan checkmarks...

Ready for /clear — I'll resume from Wave N+1 on reload.
```
