---
description: "Get Shit Done — dispatcher that routes tasks to the right tool"
argument-hint: "Describe what you want to do"
---

# Get Shit Done — Dispatcher

Analyze the user's request and route to the most appropriate tool. You are a dispatcher — you never do the work yourself.

## Routing Rules

Match the FIRST rule that applies:

| If the request describes... | Route to |
|-----------------------------|----------|
| Planning a feature, "plan", "how should we" | `create-plan` (skill) or `/project_plan` |
| Implementing a plan from thoughts/shared/plans/ | `implement-plan` (skill) |
| A bug, error, crash, "broken", "failing" | `debugging-and-error-recovery` skill |
| Research, "how does X work", exploring code | `Explore` agent |
| New feature, "add", "create", "implement" | `/create-feature` |
| Code review, "review this", PR review | `/review-enhanced` |
| Testing, "write tests", "test this" | `test-driven-development` skill + `/test-coverage` |
| Import, data migration (ETL legado REMOVIDO) | `import_export_contract` (dry-run default, `--apply` exige allowlist) ou `make import-compras-dry`/`import-acoes-dry`/`import-cadastros-dry` / endpoints DRF — ver `v2/docs/specs/backend/imports.spec.md` |
| Deploy, staging, production | `/deploy-staging` |
| Approval flow validation | `/approve-flow` |
| Availability/conflict rules | `/check-conflicts` |
| Git, commit, PR | `/project_git-pr` |
| Quick fix (typo, config, ≤3 files) | Do it directly — no plan needed |
| Save state before /clear | `continuity-ledger` skill |
| Transfer to another session | `create-handoff` skill |
| "What tools do I have?" | List all available skills and commands |

## Process

1. **Parse** the user's request
2. **Route** to the best tool using the table above
3. **Confirm** the routing: "Routing to `/command` — this will [brief description]. Proceed?"
4. **Execute** on confirmation

## Scope Check

If the request spans multiple concerns (e.g., "add feature + deploy"):
- Split into sequential steps
- Route each step to the appropriate tool
- Present the execution plan before starting

## Context

$ARGUMENTS
