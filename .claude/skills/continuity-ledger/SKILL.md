---
name: continuity-ledger
description: Preserve session state across /clear in long-running sessions. Use before running /clear, when context usage passes ~70%, or for multi-day implementations and large refactors you pick up and put down. Unlike handoffs (cross-session), a ledger preserves state within one session.
---

# Continuity Ledger

Maintain a ledger file that survives `/clear`. Clear instead of compact: each compaction is lossy compression — after several, you work with degraded context. Clearing then reading the ledger gives fresh context with full signal.

## When NOT to Use

- Quick tasks (< 30 min)
- Simple bug fixes
- Single-file changes
- Already using handoffs for cross-session transfer

## Process

### 1. Determine Ledger File

Check if a ledger already exists:
```bash
ls thoughts/ledgers/CONTINUITY_CLAUDE-*.md 2>/dev/null
```

- **If exists**: Update the existing ledger
- **If not**: Create new file: `thoughts/ledgers/CONTINUITY_CLAUDE-<session-name>.md`
  - First ensure directory exists: `mkdir -p thoughts/ledgers`
  - Use kebab-case for session name (e.g., `rbac-refactor`, `import-migration`)

### 2. Create/Update Ledger

Use this template structure:

```markdown
# Session: <name>
Updated: <ISO timestamp>

## Goal
<Success criteria - what does "done" look like?>

## Constraints
<Tech requirements, patterns to follow, things to avoid>

## Key Decisions
<Choices made with brief rationale>
- Decision 1: Chose X over Y because...
- Decision 2: ...

## State
- Done: <completed items>
- Now: <current focus - ONE thing only>
- Next: <queued items in priority order>

## Open Questions
- UNCONFIRMED: <things needing verification after clear>
- UNCONFIRMED: <assumptions that should be validated>

## Working Set
<Active files, branch, test commands>
- Branch: `feat/xyz`
- Key files: `v2/backend/apps/core/`, `v2/backend/apps/core/tests/`
- Test cmd: `docker exec aprender_dev-web-1 pytest apps/core/tests/ -v`
- Type check: `cd v2/backend && pyright apps/core config`
```

### 3. Update Guidelines

**When to update the ledger:**
- Session start: Read and refresh
- After major decisions
- Before `/clear`
- At natural breakpoints
- When context usage >70%

**What to update:**
- Move completed items from "Now" to "Done"
- Update "Now" with current focus
- Add new decisions as they're made
- Mark items as UNCONFIRMED if uncertain

### 4. After Clear Recovery

When resuming after `/clear`:

1. **Read the ledger** — `cat thoughts/ledgers/CONTINUITY_CLAUDE-<name>.md`
2. **Review UNCONFIRMED items**
3. **Ask 1-3 targeted questions** to validate assumptions
4. **Update ledger** with clarifications
5. **Continue work** with fresh context

## Template Response

After creating/updating the ledger, respond:

```
Continuity ledger updated: thoughts/ledgers/CONTINUITY_CLAUDE-<name>.md

Current state:
- Done: <summary>
- Now: <current focus>
- Next: <upcoming>

Ready for /clear - read the ledger to resume.
```

## Reference

How a ledger compares to CLAUDE.md / TodoWrite / handoffs, plus a full worked example (an `rbac-capability-rename` session) → `reference/comparison-and-example.md`.

## Additional Notes

- **Keep it concise** - Brevity matters for context
- **One "Now" item** - Forces focus, prevents sprawl
- **UNCONFIRMED prefix** - Signals what to verify after clear
- **Update frequently** - Stale ledgers lose value quickly
- **Clear > compact** - Fresh context beats degraded context
