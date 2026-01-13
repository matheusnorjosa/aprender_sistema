# Subagent Development

Implement features by delegating to specialized subagents with 2-stage review.

## When to Use

- Complex features requiring multiple parallel workstreams
- Tasks that benefit from specialized focus areas
- When you want to maximize parallel execution

## Process

### 1. Decompose Task
Break the feature into independent units:
- **Exploration tasks** - codebase analysis, pattern discovery
- **Implementation tasks** - writing code, tests
- **Validation tasks** - type checking, linting, test runs

### 2. Spawn Subagents
Use the Task tool with appropriate agent types:

```
Task(subagent_type="Explore", prompt="Find all places where X pattern is used")
Task(subagent_type="Plan", prompt="Design the architecture for feature Y")
Task(subagent_type="Bash", prompt="Run the test suite for module Z")
```

### 3. Two-Stage Review

**Stage 1 - Subagent Completion**
When subagent returns:
- Read the full output
- Verify claims match evidence
- Note any gaps or concerns

**Stage 2 - Integration Review**
Before presenting to user:
- Cross-check subagent outputs for consistency
- Verify no conflicts between parallel work
- Run integration validation (tests, type check)

### 4. Synthesize Results
Combine subagent outputs into coherent response:
- Summarize key findings
- Present unified plan or implementation
- Flag any unresolved conflicts

## Anti-patterns

- **Blind trust**: Always verify subagent claims
- **Over-spawning**: Don't spawn agents for trivial tasks
- **Missing synthesis**: Don't just dump subagent output to user
- **Sequential when parallel**: Spawn independent tasks together

## Example

```
User: "Add authentication to the API"

1. Spawn in parallel:
   - Explore: "Find current auth patterns in codebase"
   - Explore: "List all unprotected endpoints"
   - Plan: "Design session-based auth flow"

2. Review outputs, synthesize plan

3. Spawn implementation:
   - General-purpose: "Implement auth middleware"
   - General-purpose: "Add auth tests"

4. Final review + integration test
```

## Integration with Other Skills

- Use with `parallel-agents` for coordination
- Use with `verification-gate` before claiming success
- Use with `systematic-debugging` if subagent reports issues
