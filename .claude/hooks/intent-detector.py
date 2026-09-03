#!/usr/bin/env python3
"""
Claude Code Hook: Intent Detector

Detects user intent from prompt text and suggests relevant skills,
commands, or agents. Runs on UserPromptSubmit event.

Events: UserPromptSubmit
"""

import json
import re
import sys


def detect_intent(prompt: str) -> str:
    """Detect user intent and return relevant suggestions."""
    prompt_lower = prompt.lower()
    parts = []

    # PR readiness detection
    if re.search(r"ready.*pr|gh pr create|create pr|open pr|abrir pr|criar pr", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Pre-PR Readiness (auto-detected)")
        parts.append("Before creating a PR, ensure:")
        parts.append("1. Use o agente pre-pr-validator for full CI validation")
        parts.append("2. PR body must include staging gate checkboxes:")
        parts.append("   - [x] make staging-full executado com sucesso (8/8 PASS)")
        parts.append("   - [x] Evidencia anexada no PR")
        parts.append("   ALL 8 CHECKS PASSED")
        parts.append("3. Title: type(scope): description (under 70 chars)")
        parts.append("4. Never include 'Generated with Claude Code'")
        parts.append("</system-reminder>")

    # Approval flow detection
    if re.search(r"approv|aprovac|pa-0[1-7]|fluxo.*super|permiss.*super", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Approval Policy Detected (auto-detected)")
        parts.append("Use /approve-flow to validate PA-01 to PA-07 compliance.")
        parts.append("Rules: superuser OR (Gerente + Superintendencia) can approve.")
        parts.append("Use aprender-domain skill for full business rules reference.")
        parts.append("</system-reminder>")

    # Availability/conflict detection
    if re.search(r"availab|disponibil|conflict|rd-0[1-8]|bloqueio|block", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Availability Rules Detected (auto-detected)")
        parts.append("Use /check-conflicts to validate RD-01 to RD-08 compliance.")
        parts.append("Timezone: America/Fortaleza (UTC storage, local display).")
        parts.append("Use aprender-domain skill for full business rules reference.")
        parts.append("</system-reminder>")

    # Deploy detection
    if re.search(r"deploy|promote|producao|production|portainer|staging", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Deploy Detected (auto-detected)")
        parts.append("ADR-018 (2026-07-10): merge na main NAO deploya -- deploy.yaml so")
        parts.append("builda/assina/libera a tag (jobs deploy e validate_existing_tag")
        parts.append("DELETADOS no #1516). O modelo 'merge = deploy' do ADR-010 esta REVOGADO.")
        parts.append("Producao muda por promocao humana: gh workflow run promote.yml")
        parts.append("-f release=<tag>, gated no Environment `production` (required reviewer);")
        parts.append("a VM01 puxa o ponteiro assinado e aplica por digest em 127.0.0.1:9443.")
        parts.append("Rollback = promote.yml com rollback: true na tag anterior.")
        parts.append("Migrations sao automaticas e bloqueantes (#1456) -- nao rode a mao em prod.")
        parts.append("Use /deploy-staging for the pre-merge gate checklist.")
        parts.append("CRITICAL: NEVER run systemctl restart docker on VM01.")
        parts.append("Compose changes: Portainer Editor + re-captura do trust/compose.pinned.yml.")
        parts.append("</system-reminder>")

    # Security detection
    if re.search(r"security|vulnerab|owasp|cve|sec-|hardening|injection|xss|csrf", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Security Context Detected (auto-detected)")
        parts.append("Use /security-scan for automated security scanning.")
        parts.append("Use django-security skill for OWASP/IDOR/RBAC guidance.")
        parts.append("SEC-001..012 fechados (2026-04); hardening segue continuo (LGPD, pos-V1, authz).")
        parts.append("</system-reminder>")

    # Feature implementation detection
    if re.search(r"implement|feature|funcionalidade|new feat|nova func", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Feature Implementation Detected (auto-detected)")
        parts.append("CP-04 Workflow: Entender -> Planejar -> Implementar -> Testar")
        parts.append("Use /create-feature or /project_plan to plan before implementing.")
        parts.append("Use test-driven-development skill for TDD approach.")
        parts.append("</system-reminder>")

    # Review detection
    if re.search(r"review|revisar|code review|verificar codigo", prompt_lower):
        parts.append("<system-reminder>")
        parts.append("## Code Review Detected (auto-detected)")
        parts.append("Use /review-staged for standard AS v2 compliance review.")
        parts.append("Use /review-enhanced for 11-category comprehensive review.")
        parts.append("</system-reminder>")

    return "\n".join(parts)


def main() -> None:
    """Main dispatcher for UserPromptSubmit."""
    try:
        # Read bytes and force UTF-8 (utf-8-sig strips a BOM). On Windows the
        # default text stdin is cp1252, which would mojibake non-ASCII prompts.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        if not raw.strip():
            return

        data = json.loads(raw)
        # UserPromptSubmit receives the prompt text
        prompt = data.get("prompt", data.get("tool_input", {}).get("prompt", ""))
        if not prompt:
            return
    except (json.JSONDecodeError, KeyError):
        return

    result = detect_intent(prompt)
    if result:
        print(result)


if __name__ == "__main__":
    main()
