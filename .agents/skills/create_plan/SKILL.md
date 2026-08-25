---
name: create_plan
description: Create detailed implementation plans through interactive research. Use when the user asks to plan a feature/epic/refactor before implementing, or invokes /create_plan with a ticket/spec.
argument-hint: "[optional: ticket #1234 or spec path]"
model: opus
disable-model-invocation: true
---

# Create Plan

You are tasked with creating detailed implementation plans through an interactive, iterative process. You should be skeptical, thorough, and work collaboratively with the user to produce high-quality technical specifications.

## Initial Response

When this command is invoked:

1. **Check if parameters were provided**:
   - If a file path or ticket reference was provided as a parameter, skip the default message
   - Immediately read any provided files FULLY
   - Begin the research process

2. **If no parameters provided**, respond with:
```
I'll help you create a detailed implementation plan. Let me start by understanding what we're building.

Please provide:
1. The task/ticket description (or reference to a ticket file)
2. Any relevant context, constraints, or specific requirements
3. Links to related research or previous implementations

Tip: You can also invoke this command with a GitHub issue or spec directly: `/create_plan #1234` or `/create_plan v2/docs/specs/backend/imports.spec.md`
For deeper analysis, try: `/create_plan think deeply about #1234`
```

Then wait for the user's input.

## Process Steps

### Step 0: Discuss Phase

Before any research or planning, identify gray areas that need user decisions.

1. **Scan for ambiguity** — Read the task/ticket and identify:
   - Decisions that affect architecture (which approach? which library?)
   - UX choices (behavior on edge cases, error states)
   - Scope boundaries (what's in, what's deliberately out)

2. **Present gray areas** — Show max 5 items:
```
Before I research, I need your input on these decisions:

1. [Decision A] — Option X vs Option Y
2. [Decision B] — Include or exclude?
3. [Decision C] — Approach 1 vs Approach 2

Which would you like to discuss? (or "skip" to let me decide)
```

3. **Capture decisions** — Record each decision in the plan under a `## Decisions` section. Mark user choices explicitly and "Claude's discretion" for delegated items.

4. **Scope guardrail** — If the user suggests additions beyond the original scope, flag it:
```
"[Feature X] would be a new capability — that's its own phase/ticket.
Let's keep this focused on [original scope]."
```

### Step 1: Context Gathering & Initial Analysis

1. **Read all mentioned files immediately and FULLY**:
   - **Primary context source**: living specs in `v2/docs/specs/` (SDD model, ADR-017) —
     start at `v2/docs/specs/INDEX_SDD.md`, then read the relevant spec
     (`specs/domain/`, `specs/backend/`, `specs/frontend/`, `specs/infra/`)
   - Ticket files, research documents, related plans
   - CONTEXT.md files in relevant directories (services/, dev_tools/), if present
   - **IMPORTANT**: Use the Read tool WITHOUT limit/offset parameters
   - **CRITICAL**: DO NOT spawn sub-tasks before reading these files yourself

2. **Spawn initial research tasks to gather context**:
   Before asking the user any questions, use specialized agents to research in parallel:
   - Use `Explore` agents to find related code, patterns, and potential conflicts
   - Use Context7 MCP to fetch current docs for libraries involved
   - Check existing tests that cover the area being modified

3. **Present findings** to the user before proceeding to planning

### Step 2: Write the Plan

Write the plan to `thoughts/shared/plans/PLAN-{name}.md`.
Use the structure and context-rot rules in `reference/plan-template.md`.

### Step 3: Review & Iteration

Present the plan to the user. Iterate until approved.
On approval, the plan is ready for `/implement_plan`.

## AS-Specific Rules

- Always check `aprender-domain` skill for RF/RD/PA/CP compliance
- Always check `django-patterns` skill for Django/DRF conventions
- Plans touching availability must reference RD-01~08
- Plans touching approval must reference PA-01~07
- Plans must specify which tests to run for verification
- Plans for epics should use wave-based execution (Wave 1, 2, 3...)
