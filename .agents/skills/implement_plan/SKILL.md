---
description: Implement an approved plan wave-by-wave with verification gates. Use when a plan path is given, when resuming after /clear, or when create_plan output is ready to build.
disable-model-invocation: true
---

# Implement Plan

Implement an approved technical plan. Plans live in `thoughts/shared/plans/`
(where `create_plan` writes) or `v2/docs/plans/` (project-canonical for new
plans). Each plan has waves with specific changes and success criteria.

## Steps

1. **Get the plan path.** If none was provided, ask for one.
2. **Read the plan completely.** Note existing checkmarks (`- [x]`); the first
   unchecked wave is where you start.
3. **Read the context.** The original ticket, every file the plan mentions, and
   any `CONTEXT.md` in directories you will modify.
4. **Pick the execution mode** by plan size (see `reference/execution-modes.md`):
   1 wave / ≤3 tasks → Mode 1; 2-3 waves → Mode 2; 4+ waves → Mode 3.
5. **Create a todo list** to track progress.
6. **Execute the current wave** following the protocol in
   `reference/execution-modes.md` (load context → run parallel tasks → adapt to
   reality → update checkmarks).
7. **Pass the verification gate** before marking the wave complete — backend
   tests, Pyright, and frontend lint/typecheck (see `reference/verification-gate.md`).
8. **Transition.** Commit if the wave is independently valuable (CP-06). If
   context > 70%, save the continuity ledger (`continuity_ledger` skill) and
   suggest `/clear`. Repeat from step 6 for the next unchecked wave.

Done when every wave is checked and the verification gate passes.

## Reference

- `reference/execution-modes.md` — the three modes, wave protocol, and Mode-3 transition script.
- `reference/verification-gate.md` — the gate commands, AS-specific implementation rules, and error recovery.
