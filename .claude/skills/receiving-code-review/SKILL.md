# Receiving Code Review

Process feedback systematically and learn from reviews.

## When to Use

- PR has review comments
- User shares feedback on code
- CI/linting provides suggestions
- After `/review` or `/review-enhanced` runs

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
1. Identify patterns in feedback
2. Update personal checklist
3. Apply learnings to similar code elsewhere
4. Consider if project patterns need updating

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

- **Defensive reactions**: Take feedback constructively
- **Ignoring patterns**: If same feedback repeats, fix root cause
- **Over-explaining**: Keep responses concise
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
- Use with `systematic-debugging` for complex bugs found in review
- Update `CLAUDE.md` or patterns if review reveals missing guidelines
