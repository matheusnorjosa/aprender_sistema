---
name: receiving-code-review
description: Triage and respond to code review feedback for AS v2. Use when a PR has review comments, the user shares feedback, CI/linting flags issues, or after /review-staged or /review-enhanced runs.
---

# Receiving Code Review

## Process

### Phase 1: Collect All Feedback

Before responding to any comment:
1. Read ALL comments/feedback first
2. Categorize by type
3. Note patterns

### Phase 2: Categorize Feedback

| Category | Action | Priority |
|----------|--------|----------|
| **Bug/Error** | Must fix | Critical |
| **Security** | Must fix | Critical |
| **Performance** | Evaluate impact | High |
| **Style/Convention** | Follow project standards | Medium |
| **Suggestion** | Consider, discuss if unclear | Low |
| **Question** | Answer, clarify intent | Medium |

### Phase 3: Respond Systematically

For each comment:

```markdown
### Comment: [Summary]
- **Type**: [Bug/Style/Suggestion/etc]
- **Action**: [Fixed/Discussed/Declined]
- **Commit**: [If fixed, reference commit]
- **Note**: [Brief explanation if needed]
```

### Phase 4: Learn and Apply

After addressing all feedback:
1. Identify patterns in the feedback
2. Apply the same fix to similar code elsewhere in the PR
3. If the feedback reveals a missing guideline, update `CLAUDE.md` or the relevant pattern (see Integration)

## Response Templates

### Accepting Feedback
```
Fixed in [commit]. Thanks for catching this!
```

### Discussing Tradeoff
```
Considered this, but went with X because [reason].
Open to changing if you feel strongly about Y.
```

### Declining with Reason
```
Intentionally left as-is because [reason].
[Optional: reference to documentation/decision]
```

### Asking for Clarification
```
Could you elaborate on what you mean by [X]?
I understood [my interpretation] - is that correct?
```

## Common Review Types

### From Reviewers

- **Nit**: Minor style issue, low priority
- **Suggestion**: Optional improvement
- **Question**: Clarification needed
- **Blocking**: Must address before merge

### From CI/Linting

- **Error**: Must fix
- **Warning**: Should address
- **Info**: Consider for future

### From `/review-enhanced`

Process each category:
1. Security findings → Address immediately
2. Performance issues → Evaluate impact
3. Accessibility → Follow a11y standards
4. Code clarity → Improve if reasonable
5. Compliance (CP/RD/PA/RF) → Must comply

## Anti-patterns

- **Ignoring patterns**: If the same feedback repeats, fix the root cause, not each instance
- **Silent fixes**: Acknowledge feedback when fixing
- **Blind acceptance**: Understand why before changing

## Checklist After Review

- [ ] All blocking comments addressed
- [ ] Non-blocking items triaged
- [ ] Tests still pass
- [ ] Type check still passes
- [ ] Responded to all comments
- [ ] Pushed updated commits
- [ ] Re-requested review if needed

## Integration

- Use with `verification-gate` before claiming fixes done
- Use with `debugging-and-error-recovery` for complex bugs found in review
- Update `CLAUDE.md` or patterns if review reveals missing guidelines
