#!/usr/bin/env python3
"""Regression harness for .claude/hooks.

Run:  py -3 .claude/hooks/test_hooks.py

Pipes representative JSON (clean UTF-8, as Claude Code delivers it) to each hook
and asserts exit code and/or output substring. Exits 1 if any case fails. This is
the piece whose absence let two hooks silently die (env-var stdin + exit-1 block).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS = Path(__file__).resolve().parent
PY = sys.executable

results: list[tuple[str, bool, str]] = []
skipped: list[str] = []


def _run(cmd: list[str], payload: dict) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
    )
    return proc.returncode, (proc.stdout + proc.stderr).decode("utf-8", "replace")


def run_py(hook: str, payload: dict) -> tuple[int, str]:
    return _run([PY, str(HOOKS / hook)], payload)


# PowerShell nao existe no runner Linux do CI. Os hooks .ps1 sao de notificacao e
# formatacao; os guards que sustentam CP-05/CP-07 sao Python e continuam sendo
# exercitados. Pular o que nao da para rodar e melhor que nao rodar nada — foi a
# ausencia deste harness no CI que deixou o PR #1847 quebrar os guards em silencio.
POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")


def run_ps(hook: str, payload: dict) -> tuple[int, str]:
    return _run([POWERSHELL, "-ExecutionPolicy", "Bypass", "-File", str(HOOKS / hook)], payload)


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def edit(file_path: str, new_string: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": file_path, "new_string": new_string}}


def write(file_path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


# --------------------------------------------------------------------------
# guardrails.py -- exit-code based (2 = block, 0 = allow)
# --------------------------------------------------------------------------
GUARDRAILS_CASES = [
    ("G1 push main", bash("git push origin main"), 2),
    ("G1 push main-v1 (CP-05)", bash("git push origin main-v1"), 0),
    # False-positive regression: feature push chained with a PR whose --base is main.
    ("G1 push feature + gh pr --base main", bash("git push -u origin fix/x && gh pr create --base main"), 0),
    ("G1 gh pr --base main only (no push)", bash("gh pr create --base main --title x"), 0),
    ("G1 push feature then checkout main", bash("git push origin feat/y && git checkout main"), 0),
    ("G1 push main piped", bash("git push origin main | cat"), 2),
    ("G2 docker daemon pelado", bash("systemctl restart docker"), 2),
    ("G2 docker+kesl seq", bash("systemctl restart kesl && sleep 10 && systemctl restart docker"), 0),
    ("G2 compose restart", bash("docker compose restart web"), 0),
    ("G3 git add .env", bash("git add .env"), 2),
    ("G3 git add .env.example", bash("git add .env.example"), 0),
    ("G3 git add .env.production", bash("git add v2/.env.production"), 0),
    ("G3 git add sa.json", bash("git add secrets/sa.json"), 2),
    ("G4 co-author trailer", bash('git commit -m x --trailer "Co-Authored-By: Claude <noreply@anthropic.com>"'), 2),
    ("G4 gh pr generated-with", bash('gh pr create --body "Generated with Claude Code"'), 2),
    ("normal commit", bash('git commit -m "feat(backend): x"'), 0),
    ("git status", bash("git status"), 0),
    ("G5 vite manualChunks", write("v2/frontend/vite.config.ts", "manualChunks: {}"), 2),
    ("G5 vite clean", write("v2/frontend/vite.config.ts", "export default {}"), 0),
    ("G5 MultiEdit manualChunks", {"tool_name": "MultiEdit", "tool_input": {"file_path": "v2/frontend/vite.config.ts", "edits": [{"new_string": "manualChunks: ()=>{}"}]}}, 2),
    ("edit models.py normal", edit("apps/core/models.py", "x"), 0),
]
for name, payload, expected in GUARDRAILS_CASES:
    rc, _ = run_py("guardrails.py", payload)
    check(f"guardrails: {name}", rc == expected, f"exit={rc} exp={expected}")


# --------------------------------------------------------------------------
# context-injector.py -- output-substring based
# --------------------------------------------------------------------------
CONTEXT_CASES = [
    ("models guidance", edit("v2/backend/apps/core/models.py", "x"), "Model Guidelines", True),
    ("api guidance", edit("v2/frontend/src/api/foo.ts", "x"), "API Client", True),
    ("W5 rbac in view", edit("v2/backend/apps/core/views_x.py", 'user.groups.filter(name="DAT")'), "RBAC V001", True),
    ("W5 rbac in test (whitelisted)", edit("v2/backend/apps/core/tests/test_x.py", 'user.groups.filter(name="DAT")'), "RBAC V001", False),
    ("W6 pr missing markers", bash('gh pr create --body "## Summary"'), "marcadores do staging", True),
    ("W6 pr with exact markers", bash('gh pr create --body "(8/8 PASS) Evidencia anexada no PR ALL 8 CHECKS PASSED"'), "marcadores do staging", False),
    # W7 mudou de sentido no ADR-018 (#1516): o merge NAO deploya mais. O aviso
    # existe para nao deixar o agente acreditar que a versao ja esta em prod.
    ("W7 gh pr merge -> release", bash("gh pr merge 1 --squash"), "NAO deploya", True),
    ("W7 git merge local", bash("git merge main"), "NAO deploya", False),
    ("secret real value", write("x.py", 'password = "S3cretValue99"'), "segredo hardcoded", True),
    ("secret placeholder", write("x.py", 'password = "changeme1"'), "segredo hardcoded", False),
    ("N+1 in view", edit("apps/core/views_y.py", "Foo.objects.filter(a=1)"), "Possivel N+1", True),
    ("CP-06 bad commit msg", bash('git commit -m "bad message"'), "CP-06", True),
]
for name, payload, sub, want in CONTEXT_CASES:
    _, out = run_py("context-injector.py", payload)
    check(f"context-injector: {name}", (sub in out) == want, f"'{sub}' found={sub in out} want={want}")


# --------------------------------------------------------------------------
# intent-detector.py
# --------------------------------------------------------------------------
INTENT_CASES = [
    ("PR intent", {"prompt": "preciso abrir pr disso"}, "Pre-PR", True),
    ("deploy intent", {"prompt": "vamos fazer deploy em producao"}, "Deploy", True),
    ("security intent", {"prompt": "tem um xss aqui"}, "Security", True),
    ("noise", {"prompt": "oi tudo bem"}, "auto-detected", False),
]
for name, payload, sub, want in INTENT_CASES:
    _, out = run_py("intent-detector.py", payload)
    check(f"intent-detector: {name}", (sub in out) == want, f"'{sub}' found={sub in out} want={want}")


# --------------------------------------------------------------------------
# PowerShell hooks -- smoke
# --------------------------------------------------------------------------
if not POWERSHELL:
    skipped.append("hooks .ps1 (powershell ausente)")
else:
    _, out = run_ps("tools-reminder.ps1", {"prompt": "x"})
    check("tools-reminder: emits reminder", "skill/command/agent" in out)

    rc, _ = run_ps("graphify-reminder.ps1", bash("grep foo src/"))
    check("graphify-reminder: runs clean", rc == 0, f"exit={rc}")

    rc, _ = run_ps("auto-format-python.ps1", write("src/foo.ts", "x"))
    check("auto-format: no-op on .ts", rc == 0, f"exit={rc}")

    rc, _ = run_ps("graphify-sync.ps1", {"hook_event_name": "Stop"})
    check("graphify-sync: exit 0", rc == 0, f"exit={rc}")


# --------------------------------------------------------------------------
# WIRING -- roda cada hook EXATAMENTE como esta no settings.json, de um cwd
# NAO-RAIZ. Pega regressao de path relativo: um comando como
# `py -3 .claude/hooks/guardrails.py` (relativo) nao acha o script quando o cwd
# nao e a raiz do repo -> python sai com exit 2 -> guardrails BLOQUEIA por engano.
# (Foi exatamente o bug que mordeu em 2026-06-26.) Testa a integracao, nao so a unidade.
# --------------------------------------------------------------------------
SETTINGS = HOOKS.parent / "settings.json"   # .claude/settings.json
NONROOT = tempfile.gettempdir()             # garantidamente != raiz do repo

# Hooks NOSSOS (exclui plugins externos thedotmack/song) que precisam de path ABSOLUTO.
HOOK_SCRIPTS = (
    "guardrails.py", "context-injector.py", "intent-detector.py", "post-compact-reminder.sh",
    "tools-reminder.ps1", "graphify-reminder.ps1", "auto-format-python.ps1", "graphify-sync.ps1",
)


def _wired_command(substr: str) -> str | None:
    """Acha no settings.json o comando wired que referencia `substr`."""
    try:
        cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return None
    for event in cfg.get("hooks", {}).values():
        for group in event:
            for h in group.get("hooks", []):
                if substr in h.get("command", ""):
                    return h["command"]
    return None


def _script_path(command: str, scriptname: str) -> str | None:
    """Extrai o path do script de dentro do comando wired."""
    for tok in command.split():
        if scriptname in tok:
            return tok.strip('"')
    m = re.search(r'-File\s+"([^"]+)"', command)
    return m.group(1) if m else None


PROJECT_DIR = str(HOOKS.parent.parent)


def _ancorado(p: str | None) -> bool:
    """O path do hook precisa resolver a partir da RAIZ, nao do cwd.

    Duas formas valem: path absoluto, ou `$CLAUDE_PROJECT_DIR/...`. A segunda passou
    a ser a forma exigida quando `.claude/` virou versionado (decisao D3, 2026-08-25):
    `v2/backend/scripts/check_agent_instructions.py` PROIBE caminho de maquina nos
    arquivos rastreados, entao `os.path.isabs()` sozinho reprovaria justamente a
    correcao prescrita. O que continua reprovado e o path RELATIVO (.claude/hooks/...),
    que false-bloqueia quando o cwd nao e a raiz.
    """
    return bool(p) and (os.path.isabs(p) or p.startswith("$CLAUDE_PROJECT_DIR"))


def _resolve(p: str) -> str:
    return p.replace("$CLAUDE_PROJECT_DIR", PROJECT_DIR).replace("\\", os.sep)


# (1) Estatico (deterministico): todo hook nosso usa path ancorado na raiz.
for _script in HOOK_SCRIPTS:
    _cmd = _wired_command(_script)
    if _cmd is None:
        continue  # hook nao wired -- ok
    _p = _script_path(_cmd, _script)
    check(f"wiring: {_script} ancorado na raiz no settings.json", _ancorado(_p), f"path={_p!r}")

# (2) Runtime: o guardrails resolve + decide de um cwd NAO-RAIZ (via PY, sem ambiguidade de shell).
_gcmd = _wired_command("guardrails.py")
_gpath = _script_path(_gcmd, "guardrails.py") if _gcmd else None
if not (_gpath and _ancorado(_gpath)):
    # Sem else, estes dois casos sumiam em silencio e o harness ficava verde por
    # vacuidade -- foi assim que o #1847 quebrou os guards sem ninguem ver.
    check("wiring: guardrails testavel em runtime", False, f"nao wired/ancorado: path={_gpath!r}")
else:
    _gpath = _resolve(_gpath)
    _rc = subprocess.run([PY, _gpath], input=json.dumps(bash("git push origin main")).encode("utf-8"), capture_output=True, cwd=NONROOT).returncode
    check("wiring: guardrails BLOQUEIA de cwd nao-raiz (exit 2)", _rc == 2, f"exit={_rc}")
    _rc = subprocess.run([PY, _gpath], input=json.dumps(bash("git status")).encode("utf-8"), capture_output=True, cwd=NONROOT).returncode
    check("wiring: guardrails LIBERA benigno de cwd nao-raiz (exit 0)", _rc == 0, f"exit={_rc}")


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
# Piso anti-vacuidade: um harness que roda pouco passa por nao testar. O runner
# Linux do CI nao tem powershell e pula 4 casos; abaixo disso algo sumiu.
MINIMO = 45

fails = [r for r in results if not r[1]]
for name, ok, detail in results:
    line = f"{'PASS' if ok else 'FAIL'}  {name}"
    if not ok and detail:
        line += f"  [{detail}]"
    print(line)
for motivo in skipped:
    print(f"SKIP  {motivo}")
print()
print(f"{len(results) - len(fails)}/{len(results)} passed")

if len(results) < MINIMO:
    print(f"ERRO: so {len(results)} casos rodaram (minimo {MINIMO}). Verde por vacuidade.")
    sys.exit(1)
sys.exit(1 if fails else 0)
