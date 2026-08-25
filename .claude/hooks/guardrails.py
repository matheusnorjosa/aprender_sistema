#!/usr/bin/env python3
"""
Claude Code Hook: Guardrails (HARD BLOCKS)

Single source of truth for blocking dangerous tool calls.
Event: PreToolUse(Edit|MultiEdit|Write|Bash). Reads the tool payload from stdin
(JSON) -- Claude Code delivers hook input on stdin, NOT via env vars.

Exit codes:
  2 -> BLOCK the tool call (stderr is fed back to Claude as the reason)
  0 -> allow (default)
Fail-open: any internal error exits 0, so a bug in this hook never freezes the
agent by blocking every tool.

Guards:
  G1  push-to-main (CP-07)              Bash
  G2  Docker daemon restart "pelado"    Bash   (Kaspersky KESL race -> site down)
  G3  secret file in `git add`          Bash
  G4  "Generated with Claude Code" /
      Co-Authored-By: Claude            Bash   (git commit / gh pr create|edit)
  G5  Vite manualChunks                 Edit|MultiEdit|Write (vite.config.*)
"""

import json
import re
import sys


# --------------------------------------------------------------------------
# Bash guards
# --------------------------------------------------------------------------

def g1_push_main(cmd: str) -> str:
    """CP-07: block a `git push` whose target is the literal `main` branch.

    Scoped PER sub-command: `git push <feature>` chained with a command that
    merely mentions `main` (e.g. `gh pr create --base main`) must NOT block --
    only a `git push` that itself targets `main`.
    `(?<![\\w/-])main(?![\\w-])` matches `origin main` / `HEAD:main` / `main`
    but NOT `main-v1` (CP-05), `feat/main`, or `main-thing`.
    """
    # Join line-continuations, then split on shell separators so a `main` from an
    # unrelated chained command is never attributed to `git push`.
    joined = re.sub(r"\\\s*\n", " ", cmd)
    for part in re.split(r"&&|\|\||[;|\n]", joined):
        if re.search(r"git\s+push", part) and re.search(r"(?<![\w/-])main(?![\w-])", part):
            return "CP-07: push direto na main bloqueado. Use branch + PR."
    return ""


def g2_docker_restart(cmd: str) -> str:
    """Block a bare restart of the Docker *daemon* on VM01.

    `systemctl restart docker` / `service docker restart` without restarting
    Kaspersky KESL first races the antivirus and takes the site down. The safe
    sequence (`systemctl restart kesl && sleep 10 && systemctl restart docker`)
    contains `kesl`, so it is allowed. `docker compose restart` (containers,
    not the daemon) never matches.
    """
    daemon = re.search(
        r"(systemctl\s+restart\s+docker(?:\.service|\.socket)?\b|service\s+docker\s+restart\b)",
        cmd,
    )
    if daemon and "kesl" not in cmd.lower():
        return (
            "Nunca reinicie o daemon do Docker direto na VM01 (race do Kaspersky KESL -> site cai). "
            "Sequencia obrigatoria: systemctl restart kesl && sleep 10 && systemctl restart docker."
        )
    return ""


# Secret FILE patterns -- applied only to `git add` (paths), never to commit messages.
# `.env.example` / `.env.production` / `.env.staging` are templates checked into the
# repo by design (real secrets live in Portainer), so they must NOT match.
_SECRET_FILE_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\.env(?![.\w/])", ".env"),
    (r"\.env\.local\b", ".env.local"),
    (r"\.pem\b", ".pem"),
    (r"\.key\b", ".key"),
    (r"\bsa\.json\b", "sa.json"),
    (r"\bid_rsa\b", "id_rsa"),
    (r"\.p12\b", ".p12"),
    (r"\.pfx\b", ".pfx"),
)


def g3_secret_add(cmd: str) -> str:
    """Block staging an obvious secret file via `git add`."""
    if not re.search(r"\bgit\s+add\b", cmd):
        return ""
    for pattern, label in _SECRET_FILE_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return (
                f"Possivel segredo no `git add`: '{label}'. Segredos reais vivem no Portainer, "
                f"nunca no repo. Se for falso-positivo (ex: .env.example/.env.production = templates), "
                f"adicione o arquivo nominalmente sem o padrao bloqueado."
            )
    return ""


_CLAUDE_MENTION = re.compile(
    r"(generated with claude code|co-authored-by:\s*claude|claude\s+<noreply@anthropic)",
    re.IGNORECASE,
)


def g4_claude_mention(cmd: str) -> str:
    """Block Claude attribution in commits or PRs (standing project rule)."""
    is_commit = re.search(r"\bgit\s+commit\b", cmd)
    is_pr = re.search(r"\bgh\s+pr\s+(create|edit)\b", cmd)
    if (is_commit or is_pr) and _CLAUDE_MENTION.search(cmd):
        return (
            "Regra do projeto: nunca incluir 'Generated with Claude Code' / "
            "'Co-Authored-By: Claude' em commit ou PR."
        )
    return ""


# --------------------------------------------------------------------------
# Edit/Write guards
# --------------------------------------------------------------------------

def _edit_content(tool_input: dict) -> str:
    """Concatenate the written content across Edit / Write / MultiEdit shapes."""
    content = tool_input.get("new_string") or tool_input.get("content") or ""
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        content += "\n" + "\n".join(
            str(e.get("new_string", "")) for e in edits if isinstance(e, dict)
        )
    return content


def g5_manual_chunks(tool_input: dict) -> str:
    """Block Vite manualChunks (it broke Rollup deps and crashed prod)."""
    file_path = str(tool_input.get("file_path", ""))
    if not re.search(r"vite\.config\.(js|ts|mjs|cjs)$", file_path):
        return ""
    if "manualChunks" in _edit_content(tool_input):
        return (
            "Vite `manualChunks` e proibido neste projeto (quebrou deps do Rollup e crashou a prod). "
            "Deixe o Rollup fazer o chunking automatico. Necessidade real comprovada exige relaxar "
            "este guardrail conscientemente."
        )
    return ""


# --------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------

def main() -> int:
    try:
        # Read bytes and force UTF-8 (utf-8-sig strips a BOM). On Windows the
        # default text stdin is cp1252, which would mojibake/BOM-break the JSON.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        if not raw.strip():
            return 0
        data = json.loads(raw)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {}) or {}
    except Exception:
        return 0  # fail-open: never block on malformed input

    reasons: list[str] = []
    try:
        if tool_name == "Bash":
            cmd = str(tool_input.get("command", ""))
            for guard in (g1_push_main, g2_docker_restart, g3_secret_add, g4_claude_mention):
                reason = guard(cmd)
                if reason:
                    reasons.append(reason)
        elif tool_name in ("Edit", "Write", "MultiEdit"):
            reason = g5_manual_chunks(tool_input)
            if reason:
                reasons.append(reason)
    except Exception:
        return 0  # fail-open on any internal error

    if reasons:
        sys.stderr.write("BLOQUEADO pelo guardrails de hooks (.claude/hooks/guardrails.py):\n")
        for reason in reasons:
            sys.stderr.write(f"  - {reason}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
