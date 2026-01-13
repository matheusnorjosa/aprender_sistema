# Brainstorming

Transform vague ideas into concrete designs through structured dialogue.

## When to Use

- User has a rough idea but unclear implementation
- Multiple valid approaches exist
- Requirements need exploration before coding
- Early-stage feature design

## Process

### Phase 1: Understand the Seed

Ask clarifying questions to understand:
- **Goal**: What problem are we solving?
- **Context**: What exists today?
- **Constraints**: What limits apply?
- **Success**: How will we know it works?

### Phase 2: Generate Options

Present 2-4 distinct approaches:

```markdown
## Option A: [Name]
- Approach: [Brief description]
- Pros: [Benefits]
- Cons: [Drawbacks]
- Effort: [Relative complexity]

## Option B: [Name]
...
```

### Phase 3: Explore Trade-offs

For each option, discuss:
- Technical implications
- Maintenance burden
- Future flexibility
- Team familiarity

### Phase 4: Converge

Guide toward decision:
- Recommend an option with rationale
- Identify open questions for each path
- Propose next concrete step

## Question Framework

### For Features
- "What triggers this action?"
- "Who should have access?"
- "What happens on failure?"
- "How does this interact with X?"

### For Architecture
- "What's the expected scale?"
- "Where does state live?"
- "What's the consistency requirement?"
- "How do we test this?"

### For UX
- "What's the happy path?"
- "What feedback does user get?"
- "What's reversible vs permanent?"
- "How does this fit existing patterns?"

## Output Format

After brainstorming, produce:

```markdown
# Design: [Feature Name]

## Summary
[1-2 sentence description]

## Chosen Approach
[Selected option with rationale]

## Key Decisions
- Decision 1: [Choice] because [reason]
- Decision 2: [Choice] because [reason]

## Open Questions
- [ ] Question 1
- [ ] Question 2

## Next Steps
1. [First concrete action]
2. [Second action]
```

## Anti-patterns

- **Analysis paralysis**: Limit to 3-4 options max
- **Premature optimization**: Focus on clarity first
- **Hidden assumptions**: Make all assumptions explicit
- **Skipping to code**: Design before implementation

## Integration

- Output can feed into `create_plan` skill
- Use `EnterPlanMode` for complex features
- Document decisions in `thoughts/shared/`
