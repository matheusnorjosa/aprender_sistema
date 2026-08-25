# Plano de Melhoria dos Hooks — Aprender Sistema v2

> [!note] HISTÓRICO — encerrado em 2026-06-25. Não é instrução; é registro.
> As ondas 1–5 foram concluídas e o harness fechou 37/37 (ver *Log de progresso*). O valor deste
> arquivo hoje é explicar **por que** a arquitetura de hooks é guarda/injeção/automação separadas —
> não dizer o que fazer.
>
> **Duas premissas do texto original deixaram de valer:**
>
> - ~~"Tudo em `.claude/hooks/` + `.claude/settings.json` é **gitignored → edição local**, sem
>   PR/staging-gate/CP-07"~~ — **revogado pela decisão D3**
>   (`v2/docs/plans/PLAN_doc_drift_2026-08-25.md`, 2026-08-25): a camada de instrução de agente
>   passou a ser **versionada**. Mexer em hook agora é branch + PR, e o gate
>   `v2/backend/scripts/check_agent_instructions.py` proíbe caminho de máquina e credencial nesses
>   arquivos. **Não siga a instrução antiga.**
> - O item **2.6 (W7)** abaixo mandou o `context-injector.py` avisar *"merge na main = deploy pra
>   prod via Portainer"*. Aquilo era o **ADR-010** e foi **revogado pelo ADR-018 em 2026-07-10**
>   (jobs `deploy` e `validate_existing_tag` deletados no **#1516**; a `:9443` deixou de ser
>   pública). O W7 continua existindo no hook, mas hoje avisa o contrário: **o merge não deploya**,
>   produção muda por `promote.yml` gated. O item fica escrito como estava porque registra a decisão
>   de 2026-06-25 — corrigi-lo aqui apagaria o motivo de o aviso existir.
>
> Princípio-guia (esse continua valendo): um hook só ganha o sustento se fizer o que o CLAUDE.md
> **não** pode — **bloqueio duro**, **automação**, ou **injeção genuinamente contextual**. Onde
> repete o CLAUDE.md, é ruído.

## Baseline (auditoria 2026-06-25)

7 hooks: 2 Python (context-injector, intent-detector) + 4 PowerShell + 1 shell.
**Já corrigidos** (turno anterior): CP-07 (`block-push-main.ps1`, era `$env:TOOL_INPUT` morto + `exit 1`),
auto-format (mesma env var fantasma), guidance stale de pytest (UUID-CPF → factory_boy).

**Problemas estruturais restantes:**
- `context-injector.py` mistura **guarda** (quer bloquear) com **injeção** (só sabe `exit 0` + texto).
- Duplicação com CLAUDE.md (rodapés "General Rules").
- Heurísticas de baixa precisão (secrets-blocker burlável; N+1 falso-positivo).
- **Zero bloqueios duros** contra os erros que de fato derrubam site / vazam segredo / crasham prod.
- **Sem harness de teste** → foi assim que os 2 hooks morreram caladinhos.

---

## Arquitetura-alvo

```
guardrails.py       (PreToolUse Edit|MultiEdit|Write|Bash, exit 2)  ← TODOS os hard-blocks
context-injector.py (PreToolUse Edit|Write|Bash, exit 0)            ← só injeção, ENXUTA + warns
intent-detector.py  (UserPromptSubmit, exit 0)                      ← nudge de skill/command (mantém)
graphify-reminder   (PreToolUse Bash, exit 0)                       ← mantém (já lê stdin certo)
graphify-sync.ps1   (Stop, automação)                              ← graphify update se código mudou
tools/post-compact/github-mcp                                       ← mantêm
+ test_hooks.py     (harness, rodar manual: py -3 .claude/hooks/test_hooks.py)
```

Regra de wiring crítica: `guardrails.py` roda **sem** `2>/dev/null || true` (senão engole o `exit 2`).
Fail-open: erro interno do guardrails → `exit 0` (nunca travar o agente por bug de hook).

---

## Onda 1 — `guardrails.py` (hard-blocks) + rewire + fold do block-push-main

- [x] **1.1** Criar `guardrails.py` (PreToolUse Edit|MultiEdit|Write|Bash; lê stdin JSON; `exit 2` bloqueia; fail-open):
  - [x] **G1** push-to-main (CP-07) — `git push` + `main` word-boundary (poupa `main-v1`). [port do block-push-main]
  - [x] **G2** restart do **daemon** Docker "pelado" — `systemctl restart docker` / `service docker restart` **sem** `kesl` no comando → block (race KESL derruba site). `docker compose restart` (containers) NÃO bloqueia.
  - [x] **G3** segredo em `git add` — `.env` (bare) / `.env.local` / `*.pem` / `*.key` / `sa.json` / `id_rsa` / `*.p12` / `*.pfx`. **NÃO** bloqueia `.env.example` / `.env.production` / `.env.staging` (templates do repo). Escopo = só `git add` (evita falso-positivo em mensagem de commit). Limitação documentada: `git add -A`/`git add .` não nomeia o path → não pega (confiar no `.gitignore`).
  - [x] **G4** menção ao Claude — `Generated with Claude Code` / `Co-Authored-By: Claude` em `git commit` ou `gh pr create|edit` → block.
  - [x] **G5** Vite `manualChunks` — ao editar `vite.config.*`, `new_string`/`content`/`edits[].new_string` contém `manualChunks` → block (crashou prod; deixar Rollup auto-chunkar). **Decisão:** bloqueia QUALQUER `manualChunks` (memória diz "Nunca"); se houver necessidade real comprovada, relaxar conscientemente.
- [x] **1.2** Rewire `settings.json`: PreToolUse passa a ter `guardrails.py` (1ª, sem `|| true`), `context-injector.py`, `graphify-reminder.ps1`. Remover a entrada inline do `block-push-main`.
- [x] **1.3** Deletar `block-push-main.ps1` (absorvido pelo G1).
- [x] **1.4** Verificar empiricamente cada guard (pipe JSON → exit esperado).

**DoD Onda 1:** 5 guards passam casos positivos (block, exit 2) E negativos (allow, exit 0); settings.json é JSON válido; nenhum guard bloqueia comando legítimo (main-v1, docker+kesl, .env.example, commit normal, edit normal).

## Onda 2 — Enxugar `context-injector.py` (A.2 + A.3) + warns (B.5/6/7)

- [x] **2.1** Cortar duplicação com CLAUDE.md: remover rodapés "General Rules" genéricos (Pyright/Black/isort/CP-04 já no contexto). **Manter** os gotchas não-óbvios (fetchpriority minúsculo).
- [x] **2.2** Heurística de secrets honesta: parar de pular cego em "test"/"mock"; só pular se o **valor** for placeholder óbvio (changeme/xxx/your-key/example). Continua warn.
- [x] **2.3** N+1 → aviso honesto ("possível N+1, confira select_related/prefetch_related") em vez de afirmação.
- [x] **2.4** **W5** warn RBAC: editar `.py` fora da whitelist do rbac_lint com `.groups.filter(name`/`.groups.exclude(name`/`groups__name=` → lembrar do `[required]` rbac-lint + escape `# noqa: RBAC-<tipo>-allowed`.
- [x] **2.5** **W6** reforçar `github_pr_context`: se `gh pr create` com `--body` inline, checar os **3 marcadores** (`(8/8 PASS)`, `Evidencia anexada`, `ALL 8 CHECKS PASSED`) e avisar se faltar.
- [x] **2.6** **W7** reforçar `git_merge_cleanup_context`: em `gh pr merge`/`git merge` pra main, lembrar "merge na main = **deploy pra prod** via Portainer; CI verde + evidência staging?".

**DoD Onda 2:** SKILL injeta só o contextual/não-óbvio; warns W5/W6/W7 disparam nos casos certos; `py -3 -m py_compile` limpo.

## Onda 3 — `graphify-sync.ps1` (Stop, automação)

- [x] **3.1** Criar `graphify-sync.ps1`: no Stop, se `git status --porcelain` tem arquivo `.py`/`.ts`/`.tsx` E `graphify-out/graph.json` existe → `graphify update .` (best-effort, swallow output, exit 0 sempre).
- [x] **3.2** Wire em `settings.json` Stop (junto do hook existente). Timeout generoso (60s).
- [x] **3.3** Verificar gate: sem mudança de código → no-op; com mudança → roda. Documentar que roda a cada Stop com código sujo (fácil desabilitar se incomodar).

**DoD Onda 3:** roda graphify só quando há código alterado; nunca bloqueia o Stop; AST-only (sem custo de API).

## Onda 4 — Harness `test_hooks.py` (A.4)

- [x] **4.1** Criar `test_hooks.py` standalone: pipa JSON representativo pros 7 hooks (via subprocess: `py -3` p/ Python, `powershell -File` p/ PS), assere exit code + substring.
- [x] **4.2** Cobrir: guardrails (todos G1-G5, positivo+negativo), context-injector (3 amostras), intent-detector (2), graphify-reminder, tools-reminder, auto-format (smoke), graphify-sync (smoke).
- [x] **4.3** Rodar verde; exit 1 se qualquer caso falhar.

**DoD Onda 4:** `py -3 .claude/hooks/test_hooks.py` → todos PASS; é o regression-gate dos hooks daqui pra frente.

## Onda 5 — Memória + fechamento

- [x] **5.1** Atualizar memória `project_hooks_system.md` (nova arquitetura guarda/injeção/automação + harness).
- [x] **5.2** Rodar o harness completo uma última vez; conferir `settings.json` válido.

**DoD Onda 5:** memória reflete o estado novo; harness verde.

---

## O que deliberadamente NÃO fazemos (anti-sprawl)
- Mais hooks de texto advisório repetindo CLAUDE.md/skills.
- Bloqueio local que **duplica** gate de CI já `[required]` (rbac-lint como block → warn basta).
- Heurísticas "espertas" frágeis (lint de performance, "código ruim") — fadiga de alerta.

## Log de progresso
- **2026-06-25** — Plano criado. Preflight ok (graphify no PATH, py 3.14.6, graph existe, vite.config.ts único, rbac_lint V001 mapeado).
- **2026-06-25 — TODAS as ondas 1–5 concluídas** (edição local; `.claude` gitignored). Harness **37/37 verde**.
  - **Onda 1** ✅ — `guardrails.py` criado (G1–G5), wired no `settings.json` (1º, sem `|| true`), `block-push-main.ps1` absorvido/deletado. **17/17** casos (block exit 2 + allow exit 0). Bug pego no caminho: stdin no Windows = **cp1252** → BOM/acento quebra `json.loads` → fix `sys.stdin.buffer.read().decode("utf-8-sig")` (aplicado também em context-injector + intent-detector, bug latente).
  - **Onda 2** ✅ — context-injector enxuto (rodapés "General Rules" removidos), secrets-blocker julga o VALOR (placeholder vs real), N+1 → aviso honesto, **W5** rbac groups.filter, **W6** 3-marcadores no `gh pr create`, **W7** `gh pr merge`=deploy-prod. Smoke 9/9.
  - **Onda 3** ✅ — `graphify-sync.ps1` (Stop) + wire; gate por `.py/.ts/.tsx` no `git status`; no-op verificado (186ms quando só `.md` muda).
  - **Onda 4** ✅ — `test_hooks.py` harness cobrindo os 7 hooks; **37/37**, exit 0. Regression-gate dos hooks.
  - **Onda 5** ✅ — memória `project_hooks_system.md` atualizada (arquitetura nova + cp1252 gotcha).
  - **Estado final dos hooks:** guardrails.py · context-injector.py · intent-detector.py · graphify-reminder.ps1 · graphify-sync.ps1 · tools-reminder.ps1 · post-compact-reminder.sh · auto-format-python.ps1 · github-mcp.sh + test_hooks.py.
