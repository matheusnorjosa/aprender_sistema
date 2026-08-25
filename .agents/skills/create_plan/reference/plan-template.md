# Plan file template

Write the plan to `thoughts/shared/plans/PLAN-{name}.md` using this structure:

```markdown
# Plan: {Title}

## TL;DR
{What, why, and recommended approach in 2-3 sentences}

## Decisions
{Captured from discuss phase — locked choices and delegated items}

## Phases (Wave-based)
Group steps by dependency. Mark parallelism explicitly.

### Wave 1 (parallel)
- [ ] Phase 1.1: {task} — {files to modify}
- [ ] Phase 1.2: {task} — {files to modify}

### Wave 2 (depends on Wave 1)
- [ ] Phase 2.1: {task} — {files to modify}

## Relevant Code
- `path/to/file.py:function_name` — {what to reuse or modify}

## Verification
1. {Specific test command or check}
2. {Manual verification step}

## Scope Boundaries
- IN: {what's included}
- OUT: {what's deliberately excluded}
```

## Context rot prevention (plans with 3+ waves)

- Each wave should be executable in a **fresh context window**.
- Include enough context in each wave description that an agent can execute it after `/clear`.
- Reference specific files, functions, and patterns — not "the approval service".
- Each wave ends with a verification step that proves it worked.
