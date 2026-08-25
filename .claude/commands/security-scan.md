---
description: "Run automated security scan (secrets, deps, code patterns, config)"
argument-hint: "[all|secrets|deps|patterns|config]"
---

# Security Scan

Run the `security-scan` skill to perform automated security analysis.

## Scope

$ARGUMENTS

Default: `all` (run all 4 phases)

## Instructions

1. Load the `security-scan` skill
2. Execute the scan phase(s) requested
3. Report findings with severity classification
4. For CRITICAL/HIGH findings: show exact file, line, and fix
5. For MEDIUM/LOW: summarize and suggest backlog items

## Rules

- Never expose actual secret values in output
- Mark false positives with context
- Reference OWASP codes where applicable
- Cross-reference with `django-security` skill for remediation patterns
