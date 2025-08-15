---
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(python manage.py:*)
argument-hint: "<app> <feature>"
description: Start a TDD cycle for a Django feature
---

## Objective
Start a short TDD loop for: $ARGUMENTS

## Steps
1) Create or update tests to describe the desired behavior (unit/integration).
2) Run tests and confirm they fail.
3) Implement the minimal code to pass.
4) Refactor if needed, keeping tests green.
5) Commit with a descriptive message.
(think harder)
