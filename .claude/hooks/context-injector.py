#!/usr/bin/env python3
"""
Claude Code Hook: Context Injector

Injects relevant project documentation into Claude's context based on
the tool being used and the files/commands being operated on.

Events: PreToolUse (Edit, Write, Bash)

How it works:
1. Reads tool input from stdin (JSON)
2. Matches against rules (file extension, command keywords, path)
3. Returns relevant documentation as stdout (injected into context)
4. Returns empty string if no match (nothing injected)
"""

import json
import os
import re
import sys
from pathlib import Path

# Root of the project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = PROJECT_ROOT / "v2" / "docs"
CLAUDE_DIR = PROJECT_ROOT / ".claude"
# Diretorio de memoria do Claude Code para ESTE projeto.
# Derivado do caminho do repo, nao fixo: funciona em qualquer maquina/clone.
_slug = (
    str(Path(__file__).resolve().parents[2])
    .replace(":", "-")
    .replace("\\", "-")
    .replace("/", "-")
    .lstrip("-")
)
MEMORY_DIR = Path(os.path.expanduser("~")) / ".claude" / "projects" / _slug / "memory"


# Tudo que este modulo le do disco acaba impresso no stdout, que vira contexto
# de sessao e transcript. Arquivos de memoria sao escritos por agente e podem
# conter qualquer coisa, inclusive segredo colado por engano.
# CodeQL py/clear-text-logging-sensitive-data (high) apontou exatamente isso
# quando .claude/ passou a ser versionado e entrou no escopo de analise.
_SEGREDOS = [
    re.compile(r"\bghp_[A-Za-z0-9]{30,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
    # credencial embutida em URL de conexao: preserva o esquema e o host
    re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s:/@]+:[^\s:/@]+@"),
    # atribuicao explicita de segredo
    re.compile(
        r"(?i)\b([A-Z_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY)[A-Z_]*\s*[=:]\s*)\S+"
    ),
]


def _redige(texto: str) -> str:
    """Mascara segredo antes de qualquer coisa ir para o stdout."""
    for rx in _SEGREDOS:
        texto = rx.sub(
            lambda m: (m.group(1) if m.groups() else "") + "<redigido>", texto
        )
    return texto


def read_file(path: Path, max_lines: int = 80) -> str:
    """Read a file, truncated to max_lines. Secrets are redacted."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        content = "\n".join(lines[:max_lines])
        if len(lines) > max_lines:
            content += f"\n\n... ({len(lines) - max_lines} lines truncated)"
        return _redige(content)
    except Exception:
        return ""


def read_section(path: Path, start_marker: str, end_marker: str = "") -> str:
    """Read a section of a file between markers. Secrets are redacted."""
    try:
        text = path.read_text(encoding="utf-8")
        start = text.find(start_marker)
        if start == -1:
            return ""
        if end_marker:
            end = text.find(end_marker, start + len(start_marker))
            return _redige(text[start : end if end != -1 else start + 2000])
        return _redige(text[start : start + 2000])
    except Exception:
        return ""


# ============================================================================
# RULE DEFINITIONS
# ============================================================================


def python_code_context(tool_input: dict) -> str:
    """Hook 1: Python code guidelines when editing .py files in apps/."""
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py"):
        return ""
    if "apps/" not in file_path and "config/" not in file_path:
        return ""

    parts = []
    parts.append("<system-reminder>")
    parts.append("## Python/Django Code Guidelines (auto-injected)")
    parts.append("")

    # Core patterns based on file type
    if "models" in file_path or "model" in file_path:
        parts.append("### Model Guidelines")
        parts.append(
            "- Use CheckConstraint with `condition=` (Django 5.2+, not `check=`)"
        )
        parts.append("- Always define `__str__`, `Meta.ordering`, `Meta.verbose_name`")
        parts.append("- Use `UniqueConstraint` over `unique_together`")
        parts.append(
            "- Pyright strict mode  -- all fields need type annotations (PEP 695)"
        )
        parts.append("- Timezone: always store UTC, display America/Fortaleza")

    elif "serializer" in file_path:
        parts.append("### Serializer Guidelines")
        parts.append("- Explicit field lists (never `fields = '__all__'`)")
        parts.append("- Validate at serializer level, not view level")
        parts.append("- Use `SerializerMethodField` for computed fields")
        parts.append("- Read-only fields for audit (created_at, updated_at)")

    elif "views" in file_path or "view" in file_path:
        parts.append("### View Guidelines")
        parts.append("- Always set `permission_classes` explicitly")
        parts.append("- Use `select_related`/`prefetch_related` in `get_queryset()`")
        parts.append(
            "- Return proper HTTP status codes (201 for create, 204 for delete)"
        )
        parts.append(
            '- RBAC: permission_classes = [HasPerm("codename")] from apps.core.rbac (compose with HasPerm("a") | HasPerm("b"))'
        )

    elif "test" in file_path:
        parts.append("### Test Guidelines")
        parts.append("- Use `default_test_user` fixture from conftest.py")
        parts.append(
            "- factory_boy factories (UsuarioFactory, etc.) with `factory.Sequence` for unique cpf/email (deterministic, xdist-safe; NEVER hash()%N) [#1404]"
        )
        parts.append("- Coverage target: 85%+ backend")
        parts.append("- Mark slow tests with `@pytest.mark.slow`")

    elif "service" in file_path:
        parts.append("### Service Guidelines")
        parts.append("- Business logic lives in services/, not views/")
        parts.append("- Services are stateless functions, not classes")
        parts.append("- Always validate inputs at the boundary")

    elif "permission" in file_path:
        parts.append("### Permission/RBAC Guidelines")
        parts.append(
            '- Canonical idiom: permission_classes = [HasPerm("codename")] from apps.core.rbac (compose with HasPerm("a") | HasPerm("b"))'
        )
        parts.append(
            "- Helpers in apps/core/rbac/; NEVER user.groups.filter(name=...) (banned by scripts/rbac_lint.py, CI required job)"
        )
        parts.append(
            "- 13 Setores: Superintendencia, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Diretoria, Comercial, Relacionamento, Logistica Viagens, Logistica Galpao"
        )
        parts.append(
            "- 5 Funcoes: Formador, Coordenador, Apoio de Coordenacao, Gerente, Assistente Administrativo"
        )
        parts.append("- Approval: superuser OR (Gerente + Superintendencia)")
        parts.append("- All authorization MUST be server-side (never trust client)")
        parts.append("- Check /approve-flow and /check-conflicts commands")

    # Security-sensitive files
    if "approval" in file_path or "aprovacao" in file_path:
        parts.append("")
        parts.append("### PA (Approval Policy) Rules")
        parts.append("- PA-01 to PA-07 apply to SUPER flow")
        parts.append("- Run /approve-flow to validate compliance")
        parts.append("- Superuser OR (Gerente + Superintendencia) can approve")

    if "availability" in file_path or "disponibilidade" in file_path:
        parts.append("")
        parts.append("### RD (Availability) Rules")
        parts.append("- RD-01 to RD-08 with timezone America/Fortaleza")
        parts.append("- Run /check-conflicts to validate compliance")
        parts.append("- Always use UTC storage, Fortaleza display")

    # NB: generic rules (Pyright/Black/isort/CP-04) live in CLAUDE.md (always in
    # context) -- not re-injected here. This hook injects only the per-file-type
    # specifics above, which CLAUDE.md does NOT carry.
    parts.append("</system-reminder>")

    return "\n".join(parts)


def typescript_code_context(tool_input: dict) -> str:
    """Hook 2: TypeScript/React guidelines when editing .ts/.tsx files."""
    file_path = tool_input.get("file_path", "")
    if not (file_path.endswith(".ts") or file_path.endswith(".tsx")):
        return ""
    if "src/" not in file_path:
        return ""

    parts = []
    parts.append("<system-reminder>")
    parts.append("## TypeScript/React Code Guidelines (auto-injected)")
    parts.append("")

    if "pages/" in file_path:
        parts.append("### Page Component Guidelines")
        parts.append("- All pages must be lazy-loaded via React.lazy()")
        parts.append("- Use `usePermissions()` hook for RBAC checks")
        parts.append("- Mobile responsive: check `useResponsive()` hook")

    elif "api/" in file_path:
        parts.append("### API Client Guidelines")
        parts.append("- Use `fetchAPI()` from api/config.ts (NOT axios)")
        parts.append("- CSRF token handled automatically by fetchAPI")
        parts.append(
            "- Auth errors (401/403) are silenced in console  -- don't re-add logging"
        )

    elif "components/" in file_path:
        parts.append("### Component Guidelines")
        parts.append("- Ant Design v5 components with ConfigProvider theme")
        parts.append(
            "- Brand colors via ConfigProvider theme tokens (not a custom hook)"
        )

    elif "hooks/" in file_path:
        parts.append("### Hook Guidelines")
        parts.append("- Custom hooks in src/hooks/")
        parts.append("- Use `useCallback` for memoized async functions")
        parts.append("- Cleanup with `useRef(isMounted)` pattern")

    # Only the non-obvious gotchas (the rest is generic / in CLAUDE.md).
    parts.append("")
    parts.append("### Gotchas (nao-obvios)")
    parts.append("- React 19 (migrado de 18, #1675/#1687)  -- `fetchPriority` e prop camelCase; lowercase quebra sob React 19")
    parts.append(
        "- Vite `manualChunks` e bloqueado (crashou prod)  -- deixe o Rollup auto-chunkar"
    )
    parts.append("</system-reminder>")

    return "\n".join(parts)


def git_commit_context(command: str) -> str:
    """Hook 3: Git commit guidelines + validation."""
    if "git commit" not in command and "git add" not in command:
        return ""

    # Validate commit message format if -m is present
    match = re.search(r'-m\s+["\']([^"\']+)["\']', command)
    if match:
        msg = match.group(1)
        valid_pattern = (
            r"^(feat|fix|refactor|test|docs|style|perf|ci|chore)\([^)]+\):\s.+"
        )
        if not re.match(valid_pattern, msg):
            return """<system-reminder>
WARNING: CP-06 VIOLATION -- Invalid commit message format.
Expected: type(scope): message
Got: {}
Valid types: feat, fix, refactor, test, docs, style, perf, ci, chore
Valid scopes: backend, frontend, infra, ci, deps, security
</system-reminder>""".format(msg)

    return """<system-reminder>
## Git Commit Guidelines (auto-injected)

### CP-06: Conventional Commits OBRIGATÓRIO
Format: `type(scope): message`

Types: feat, fix, refactor, test, docs, style, perf, ci, chore
Scopes: backend, frontend, infra, ci, deps, security

Examples:
- `feat(backend): add availability conflict detection`
- `fix(frontend): resolve CSRF token refresh on login`
- `perf(infra): optimize nginx gzip compression`

### Rules
- CP-07: NEVER push directly to main  -- use PR workflow
- Message in English, lowercase first word after colon
- Use HEREDOC for multi-line commit messages
- Stage specific files (not `git add -A`)
- Never commit .env, credentials, or secrets
</system-reminder>"""


def github_pr_context(command: str) -> str:
    """Hook 4: GitHub PR guidelines + staging-gate marker check (W6)."""
    if "gh pr create" not in command and "gh pr edit" not in command:
        return ""

    parts = []

    # W6: if the PR body is inline, verify the 3 EXACT staging-gate markers
    # ('Evidencia' WITHOUT accent). Can't see --body-file content, so only warn
    # when the body is on the command line.
    has_inline_body = "--body " in command or "--body=" in command or " -b " in command
    if has_inline_body:
        markers = ("(8/8 PASS)", "Evidencia anexada", "ALL 8 CHECKS PASSED")
        missing = [m for m in markers if m not in command]
        if missing:
            parts.append("<system-reminder>")
            parts.append(
                "## WARNING: marcadores do staging gate ausentes (auto-detected)"
            )
            parts.append(
                "O corpo do PR precisa dos 3 marcadores EXATOS (sem acento em 'Evidencia'):"
            )
            parts.append("  - [x] make staging-full executado com sucesso (8/8 PASS)")
            parts.append("  - [x] Evidencia anexada no PR")
            parts.append("  ALL 8 CHECKS PASSED")
            parts.append("Faltando: " + ", ".join(missing))
            parts.append("</system-reminder>")

    parts.append("""<system-reminder>
## GitHub PR Guidelines (auto-injected)

### Staging Gate (REQUIRED in PR body)
```
## Staging gate
- [x] make staging-full executado com sucesso (8/8 PASS)
- [x] Evidencia anexada no PR

ALL 8 CHECKS PASSED
```

### PR Title
- Under 70 characters
- Conventional commit format: `type(scope): description`

### PR Body Structure
```
## Summary
<1-3 bullet points>

## Staging gate
<checkboxes above>
```

### Rules
- Never include "Generated with Claude Code" in descriptions
- Base branch: main (unless fix/v1-* for v1)
- Required checks must pass before merge
</system-reminder>""")

    return "\n".join(parts)


def docker_stack_context(command: str) -> str:
    """Hook 5: Docker/Stack guidelines."""
    keywords = [
        "docker compose",
        "make up",
        "make down",
        "docker-compose",
        "docker build",
    ]
    if not any(kw in command for kw in keywords):
        return ""

    return """<system-reminder>
## Docker/Stack Guidelines (auto-injected)

### CP-01: v2 runs ONLY in Docker
```bash
cd v2 && make up  # Development
```

### CRITICAL: NEVER restart Docker service on VM01
`systemctl restart docker` causes Kaspersky KESL race condition -> site goes down.
If truly needed: `systemctl restart kesl && sleep 10 && systemctl restart docker`

### Production Stack (Portainer)
- Compose in Portainer Editor (NOT docker-compose CLI)
- ENV vars in Portainer Environment variables (NOT .env files)
- Real secrets in Portainer on Golden VMs, .env.production in repo are dev templates
- ADR-018: quem faz o PUT e o aprender-applier em 127.0.0.1:9443, com o
  trust/compose.pinned.yml da propria VM. Editou o compose no Editor? re-capture o
  pinado, senao `compose_check_drift` recusa o proximo deploy.

### Network Segmentation
- backend-internal: web, redis, worker, beat (driver: bridge, NOT internal)
- frontend-proxy: frontend, web (driver: bridge, NOT internal)
- shared_proxy: frontend, NPM (external: true)
- `internal: true` on any network needing external access = BREAKS EVERYTHING

### Redis Container
- NO cap_drop: ALL (breaks Alpine entrypoint)
- NO read_only: true (needs write to /data)
- Keep only: no-new-privileges:true
</system-reminder>"""


def deploy_context(command: str) -> str:
    """Hook 6: Deploy guidelines (modelo ADR-018, pull-based)."""
    keywords = ["deploy", "portainer", "promote", "staging-gate", "make deploy"]
    if not any(kw in command for kw in keywords):
        return ""

    return """<system-reminder>
## Deploy Guidelines (auto-injected)  --  ADR-018 (2026-07-10), pull-based

### REVOGADO: "merge na main deploya"
Era o ADR-010. O ADR-018 o superseded: os jobs `deploy` e `validate_existing_tag`
do deploy.yaml foram DELETADOS (#1516) e a :9443 deixou de ser publica.
Se voce leu isso em algum doc, o doc esta velho.

### Fluxo atual (producao PUXA; o CI nao empurra)
1. Merge na main -> deploy.yaml ("Build, sign and release"): build/scan/push no
   Docker Hub + cosign keyless + SLSA + tag imutavel vYYYY.MM.DD-<sha7>. PARA AQUI.
2. Promocao humana: `gh workflow run promote.yml -f release=<tag>` -- workflow_dispatch
   atras do GitHub Environment `production` (required reviewer). Resolve tag->digest,
   exige imagens assinadas, assina o production.json (sequence monotonica) e publica
   no branch protegido `deploy-pointer`. promote.yml TAMBEM nao deploya.
3. VM01 (systemd ~60s): aprender-deployer le/verifica o ponteiro; aprender-applier
   (unico com o token do Portainer) confere anti-rollback + drift do compose, exige
   backup de DB fresco, faz o PUT em 127.0.0.1:9443 e confirma em localhost.

### Rollback
Promocao PARA TRAS pelo mesmo gate: promote.yml com `rollback: true` na tag anterior
(ainda exige sequence > selo). NAO existe `gh workflow run deploy.yaml -f rollback_tag=...`.
Nao ha auto-rollback -- migrations sao forward-only.

### Migrations
Automaticas e BLOQUEANTES (#1456): servico one-shot `migrate` no docker-compose.prod.yml;
web/worker/beat sobem so com `depends_on: service_completed_successfully`.
Rodar `manage.py migrate` a mao em producao esta REVOGADO.

### Verificacao pos-deploy
- A verdade e o digest verificado no PUT, nao a cor de um job de CI -- mas esse digest
  fica no selo do applier, DENTRO da VM. A rota /api/version/ NAO devolve digest: o
  payload e {"version": ...}, com git_sha/build_date so para is_staff
  (v2/backend/apps/core/views_health.py:93-99).
- Conferir /api/version/ (a TAG) contra o release do production.json, e /api/readyz/.
- O applier confirma de DENTRO da VM -> imune ao false-red do :9443.

### Compose
Mudanca no compose exige update manual no Portainer Editor E re-captura do
trust/compose.pinned.yml na VM -- senao `compose_check_drift` RECUSA o proximo deploy.

### Producao / hosts
IPs e hosts NAO ficam aqui: v2/docs/specs/infra/deploy.spec.md + v2/docs/DEPLOY_CHECKLIST.md
</system-reminder>"""


def test_context(command: str) -> str:
    """Hook 7: Test guidelines."""
    keywords = ["pytest", "vitest", "test-coverage", "make test"]
    if not any(kw in command for kw in keywords):
        return ""

    parts = []
    parts.append("<system-reminder>")
    parts.append("## Test Guidelines (auto-injected)")
    parts.append("")

    if "pytest" in command or "make test" in command:
        parts.append("### Backend (pytest)")
        parts.append("- Fixture: `default_test_user` auto-injected via pre_save signal")
        parts.append(
            "- factory_boy + `factory.Sequence` for unique fields (deterministic, xdist-safe) [#1404]"
        )
        parts.append("- Coverage target: 85%+ (path to 90%)")
        parts.append(
            "- `--reuse-db` local; CI gate uses `--no-migrations` (schema from models, #1404)"
        )
        parts.append(
            "- Markers: `@pytest.mark.slow`, `@pytest.mark.performance`, `@pytest.mark.migrations`"
        )
        parts.append(
            "- Run: `docker exec aprender_dev-web-1 pytest apps/core/tests/ -v`"
        )

    if "vitest" in command:
        parts.append("### Frontend (vitest)")
        parts.append("- Coverage: ratchet no baseline (statements 44 / branches 35 / functions 33 / lines 44) -- nao baixar")
        parts.append("- Pool: single-thread (race condition protection)")
        parts.append("- Environment: jsdom")
        parts.append("- Run: `cd v2/frontend && npx vitest`")

    parts.append("</system-reminder>")
    return "\n".join(parts)


def etl_context(command: str) -> str:
    """Hook 8: ETL guidelines."""
    if "etl-" not in command and "etl_" not in command:
        return ""

    return """<system-reminder>
## Importacao de Dados (auto-injected)

O ETL legado (`apps.dat_ingest`, comandos `etl_*`) foi **REMOVIDO** (#967/#971) — `make etl-*` nao existe mais.

### Caminho atual
- Command: `import_export_contract` (dry-run por padrao; `--apply` exige allowlist; never-overwrite de campos protegidos).
- API DRF: `POST /api/<recurso>/import/` (alvos `make import-compras-dry` / `import-acoes-dry` / `import-cadastros-dry`).
- Spec viva: `v2/docs/specs/backend/imports.spec.md`; contratos em `v2/docs/imports/`.

### Regras
- SEMPRE dry-run primeiro; idempotencia via `external_hash` SHA1 (ADR-012).
- `INCLUDE_DEV_TOOLS=false` em producao (CP-08).
</system-reminder>"""


# ============================================================================
# PRIORITY 2 HOOKS
# ============================================================================


def cp01_docker_only_context(command: str) -> str:
    """CP-01: Block python manage.py outside Docker."""
    if "python manage.py" in command or "python3 manage.py" in command:
        if "docker exec" not in command and "docker compose" not in command:
            return """<system-reminder>
WARNING: CP-01 VIOLATION -- v2 runs ONLY in Docker.
Use: docker exec aprender_dev-web-1 python manage.py <command>
Or:  cd v2 && make up (then exec into container)
NEVER run manage.py directly on host.
</system-reminder>"""
    return ""


def cp05_v1_branch_context(command: str) -> str:
    """CP-05: v1 frozen -- only fix/v1-* branches allowed."""
    if "git checkout" in command or "git switch" in command:
        if "main-v1" in command and "fix/v1-" not in command:
            return """<system-reminder>
WARNING: CP-05 -- v1 is frozen.
Only fix/v1-* branches can target main-v1.
Create: git checkout -b fix/v1-<description> main-v1
</system-reminder>"""
    return ""


def cp08_dev_tools_context(command: str) -> str:
    """CP-08: INCLUDE_DEV_TOOLS=false in production."""
    if "INCLUDE_DEV_TOOLS" in command and "true" in command.lower():
        if "prod" in command.lower() or "production" in command.lower():
            return """<system-reminder>
CRITICAL: CP-08 VIOLATION -- INCLUDE_DEV_TOOLS must be false in production.
Dev tools (silk, debug_toolbar) are disabled in production for security.
</system-reminder>"""
    return ""


def secrets_blocker_context(tool_input: dict) -> str:
    """Detect hardcoded secrets in code being written."""
    content = tool_input.get("new_string", "") or tool_input.get("content", "")
    if not content:
        return ""

    # Patterns capture the secret VALUE (group 1) so we judge the value itself,
    # instead of muting on any "test"/"mock" keyword anywhere (trivially bypassed).
    secret_patterns = [
        (r'(?:password|passwd|pwd)\s*=\s*["\']([^"\']{8,})', "password"),
        (r'(?:secret_key|SECRET_KEY)\s*=\s*["\']([^"\']{8,})', "SECRET_KEY"),
        (r'(?:api_key|API_KEY|apikey)\s*=\s*["\']([^"\']{8,})', "API key"),
        (r'(?:token|TOKEN)\s*=\s*["\']([^"\']{8,})', "token"),
        (r'(?:private_key|PRIVATE_KEY)\s*=\s*["\']([^"\']+)', "private key"),
    ]

    # Obvious placeholders / env-var references -- not real secrets.
    placeholder = re.compile(
        r"^(x{3,}|\.{3,}|changeme|placeholder|example|dummy|fake|todo|your[-_]?\w+|"
        r"<[^>]+>|\$\{?\w+\}?|os\.environ|os\.getenv|getenv|settings\.)",
        re.IGNORECASE,
    )

    for pattern, name in secret_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if not match:
            continue
        value = (match.group(1) or "").strip()
        if not value or placeholder.match(value):
            continue
        return """<system-reminder>
WARNING: possivel segredo hardcoded ({}) no codigo.
Use variaveis de ambiente (os.getenv / .env). Segredos reais vivem no Portainer.
Se for placeholder/fixture, ignore.
</system-reminder>""".format(name)
    return ""


def git_merge_cleanup_context(command: str) -> str:
    """Post-merge cleanup reminder + W7 release warning for `gh pr merge`."""
    if "git merge" not in command and "gh pr merge" not in command:
        return ""

    parts = ["<system-reminder>"]
    # W7: desde o ADR-018 (#1516) o merge na main NAO deploya -- ele so builda,
    # assina e libera. O aviso existe para nao reintroduzir o modelo revogado
    # (ADR-010) nem deixar acreditar que o merge ja colocou a versao em prod.
    if "gh pr merge" in command:
        parts.append("## Merge na main NAO deploya (ADR-018) -- auto-detected")
        parts.append(
            "O merge dispara deploy.yaml ('Build, sign and release'): build/scan/push +"
        )
        parts.append(
            "cosign + tag imutavel vYYYY.MM.DD-<sha7>. Producao NAO muda com isso."
        )
        parts.append(
            "Para levar a prod: gh workflow run promote.yml -f release=<tag> (gate do"
        )
        parts.append(
            "Environment `production`, required reviewer). A VM01 puxa e aplica por digest."
        )
        parts.append("Confirme antes do merge: CI verde + evidencia do staging gate no PR.")
        parts.append("")
    parts.append("## Post-Merge Reminder")
    parts.append(
        "Considere o agente post-merge-cleanup: deleta branches mergeadas, atualiza main,"
    )
    parts.append(
        "confere o run do deploy.yaml (build/assinatura -- nao e deploy) e faz prune de refs."
    )
    parts.append("</system-reminder>")
    return "\n".join(parts)


def n1_query_warning_context(tool_input: dict) -> str:
    """Warn about potential N+1 queries in views."""
    file_path = tool_input.get("file_path", "")
    content = tool_input.get("new_string", "") or ""

    if not file_path.endswith(".py"):
        return ""
    if "views" not in file_path:
        return ""

    # Heuristic, low-precision -- phrased as a "check", not an assertion.
    if ".objects.all()" in content or ".objects.filter(" in content:
        if "select_related" not in content and "prefetch_related" not in content:
            return """<system-reminder>
## Possivel N+1 (auto-detected, confira)
Vi um QuerySet sem select_related/prefetch_related neste view. Pode ser falso-positivo
(count simples, sem acesso a relacao). SE houver FK/M2M acessada por item:
- .select_related('fk') para ForeignKey
- .prefetch_related('m2m') para ManyToMany
</system-reminder>"""
    return ""


def rbac_groups_filter_warning_context(tool_input: dict) -> str:
    """W5: warn when an edit introduces user.groups.filter(name=...) outside the
    rbac_lint whitelist -- the [required] backend rbac-lint job (V001) fails CI."""
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith(".py"):
        return ""
    content = tool_input.get("new_string", "") or tool_input.get("content", "")
    if not content:
        return ""
    norm = file_path.replace("\\", "/")
    # rbac_lint V001 whitelist (mirrors scripts/rbac_lint.py).
    whitelisted = any(
        s in norm
        for s in (
            "/tests/",
            "/migrations/",
            "/fixtures/",
            "/apps/core/rbac/",
            "/apps/dev_tools/",
            "/constants.py",
            "/permissions.py",
            "/rbac_helpers.py",
            "/scripts/rbac_lint.py",
            "/scripts/rbac_codemod.py",
        )
    )
    if whitelisted:
        return ""
    if (
        re.search(r"\.groups\.(filter|exclude)\(\s*name", content)
        or "groups__name=" in content
    ):
        return """<system-reminder>
## WARNING: RBAC V001 (auto-detected)
`user.groups.filter(name=...)` e banido pelo rbac_lint ([required] backend rbac-lint) fora da whitelist.
Use HasPerm("<codename>") / user_has_any_perm(user, "<codename>") (apps.core.rbac).
Uso legitimo (composite/block/data-scope)? Adicione `# noqa: RBAC-<tipo>-allowed` na linha.
</system-reminder>"""
    return ""


# ============================================================================
# DISPATCHER
# ============================================================================


def main() -> None:
    """Main dispatcher  -- reads stdin, matches rules, outputs context."""
    try:
        # Read bytes and force UTF-8 (utf-8-sig strips a BOM). On Windows the
        # default text stdin is cp1252, which would mojibake non-ASCII input.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        if not raw.strip():
            return

        data = json.loads(raw)
        tool_name = data.get("tool_name", "")
        tool_input = data.get("tool_input", {})
    except (json.JSONDecodeError, KeyError):
        return

    results = []

    if tool_name in ("Edit", "Write"):
        # Check file-based rules
        ctx = python_code_context(tool_input)
        if not ctx:
            ctx = typescript_code_context(tool_input)
        if ctx:
            results.append(ctx)

        # Additional file-based checks
        secrets = secrets_blocker_context(tool_input)
        if secrets:
            results.append(secrets)

        n1 = n1_query_warning_context(tool_input)
        if n1:
            results.append(n1)

        rbac = rbac_groups_filter_warning_context(tool_input)
        if rbac:
            results.append(rbac)

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        # Check command-based rules (collect ALL matches, not just first)
        for checker in [
            cp01_docker_only_context,
            cp05_v1_branch_context,
            cp08_dev_tools_context,
            git_commit_context,
            github_pr_context,
            docker_stack_context,
            deploy_context,
            test_context,
            etl_context,
            git_merge_cleanup_context,
        ]:
            ctx = checker(command)
            if ctx:
                results.append(ctx)

    if results:
        # Redige na FRONTEIRA de saida, nao so na leitura: aqui passa tudo que
        # o hook injeta no transcript, venha de arquivo de memoria, do comando
        # inspecionado ou de qualquer checker futuro. Sanitizar na origem exige
        # lembrar de fazer em cada nova fonte; sanitizar na saida, nao.
        print(_redige("\n".join(results)))


if __name__ == "__main__":
    main()
