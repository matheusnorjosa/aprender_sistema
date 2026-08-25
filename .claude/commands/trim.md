---
description: Reduce current PR description by 70% while preserving essential information
---

# Trim PR Description

Reduce the current PR description by 70%.

## Rules

### Keep
- Core summary (what changed)
- Critical test steps
- Breaking changes
- Required actions
- Compliance notes (CP, RD, PA, RF references)

### Remove
- Redundant explanations
- Obvious details
- Verbose formatting
- Repeated information
- Implementation details (focus on WHAT, not HOW)

### Technique
1. Read current description
2. Identify essential information
3. Rewrite concisely
4. Target: 30% of original length

## Format

**Before:**
```markdown
## Summary
This PR implements the RF03 conflict detection system that allows
the system to verify availability conflicts for formadores. The
implementation follows RD-01 to RD-08 rules defined in CLAUDE.md.
We added a new service layer function that checks for overlaps,
blocks, travel buffers, and daily capacity limits.

## Changes
- Added new availability_service.py with check_conflicts function
- Created AvailabilityResult and ConflictDetail dataclasses
- Implemented conflict detection for RD-01 (overlap)
- Implemented conflict detection for RD-02 (total block)
- Implemented conflict detection for RD-03 (partial block)
- Implemented conflict detection for RD-04 (travel buffer)
- Implemented conflict detection for RD-05 (daily capacity)
- Added timezone-aware comparison (RD-06)
- Added API endpoint at /api/availability/check/
- Added 17 unit tests covering all rules
...
```

**After:**
```markdown
## Summary
RF03: Conflict detection following RD-01 to RD-08.

## Changes
- `availability_service.check_conflicts()` with all 8 rules
- API: `/api/availability/check/` + `/check-many/`
- 17 tests (100% rule coverage)

## Compliance
RD-01 to RD-08 validated
```

## Process

1. Get current PR description:
```bash
gh pr view --json body -q .body
```

2. Apply trimming rules

3. Output the trimmed version ready to update:
```bash
gh pr edit --body "$(cat <<'EOF'
[trimmed content]
EOF
)"
```

## Output
Provide the trimmed PR description ready to replace the original.
