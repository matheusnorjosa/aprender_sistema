---
name: brainstorming
description: Explore the solution space before committing to an approach. Use when the user has a rough idea, when multiple valid approaches exist, or in early-stage feature design before coding.
---

# Brainstorming

Transform a vague idea into a concrete design through structured dialogue. Work the phases in order; finish when you have produced the design doc at the end.

## Phase 1: Understand the seed

Ask clarifying questions until you can answer:

- **Goal**: What problem are we solving?
- **Context**: What exists today?
- **Constraints**: What limits apply?
- **Success**: How will we know it works?

Question catalog by domain (features / architecture / UX): `reference/question-frameworks.md`.

## Phase 2: Generate options

Present 2–4 distinct approaches (more than 4 is analysis paralysis):

```markdown
## Option A: [Name]
- Approach: [Brief description]
- Pros: [Benefits]
- Cons: [Drawbacks]
- Effort: [Relative complexity]
```

## Phase 3: Explore trade-offs

For each option, weigh: technical implications, maintenance burden, future flexibility, team familiarity. Make every assumption explicit.

## Phase 4: Converge

Recommend one option with rationale, list the open questions per path, and propose the next concrete step. Emit the design doc:

```markdown
# Design: [Feature Name]

## Summary
[1-2 sentence description]

## Chosen Approach
[Selected option with rationale]

## Key Decisions
- Decision 1: [Choice] because [reason]

## Open Questions
- [ ] Question 1

## Next Steps
1. [First concrete action]
```

## Next

- Feed the design doc into the `create-plan` skill.
- Persist decisions under `thoughts/shared/`.
