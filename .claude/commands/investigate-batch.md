---
description: Systematic discovery through batched questions before planning (saves tokens)
argument-hint: [topic or goal]
---

# Investigation Protocol (Batched)

Before planning or implementing, investigate: $ARGUMENTS

## Process

### 1. Initial Discovery (Batch 1)
Ask up to 4 questions at once using AskUserQuestion. Group related questions:
- Current state (what exists in the codebase?)
- Desired outcome (what should the feature do?)
- Business rules (which CP/RD/PA/RF rules apply?)
- Constraints (timeline, dependencies, breaking changes?)

### 2. Codebase Analysis
Search for patterns using Task/Explore agent:
- Related Django models/serializers/views
- Existing services that solve similar problems
- Test patterns in the same domain
- Integration points with external systems (GCal, Redis, Celery)

### 3. Domain Context
Load relevant skills if needed:
- `aprender-domain` for business rules (RD, PA, RF)
- `django-patterns` for implementation patterns
- `etl-guidelines` for data import features

### 4. Follow-up Questions (Batch 2, if needed)
Ask remaining questions (max 4 per round):
- Technical unknowns
- Edge cases that need clarification
- RBAC/permissions requirements

### 5. Output
Provide a structured summary:
```markdown
## Understanding
[What I learned about the topic]

## Relevant Rules
- CP-XX: [If applicable]
- RD-XX: [If applicable]
- PA-XX: [If applicable]
- RF-XX: [If applicable]

## Existing Code
- Models: [relevant models]
- Services: [relevant services]
- Tests: [existing test patterns]

## Open Questions
[Any remaining questions that need answers]

## Suggested Approach
[High-level direction based on findings]
```

## Rules
- **Batch up to 4 questions per round** to minimize token usage
- Ask before assuming
- Explore codebase before planning
- Reference existing patterns
- Surface ambiguity early
- Always check CLAUDE.md for business rules

## Token Savings
| Approach | Messages | Tokens |
|----------|----------|--------|
| 1 question at a time | 10+ | ~5000 |
| Batched (4 per round) | 2-3 | ~1500 |

## When to Use
- Complex features that touch multiple domains
- Unclear requirements from stakeholder
- Features involving business rules (RD, PA)
- Before `/new-feat` or `/project_plan`
