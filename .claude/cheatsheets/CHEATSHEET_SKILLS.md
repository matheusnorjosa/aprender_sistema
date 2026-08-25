# Tooling Cheatsheet — Aprender Sistema v2

> índice — full em `.claude/skills/<nome>/SKILL.md`, `.claude/commands/<nome>.md` e CLAUDE.md

Inventário atual do disco: **23 skills · 18 commands · 4 agent types · 8 MCPs**.
(6 skills são user-invoked — `disable-model-invocation`: create-plan, implement-plan, create-handoff, resume-handoff, continuity-ledger, security-scan.)

**Invocação de skill:** via Skill tool com o **nome direto** (ex.: `test-driven-development`),
não `/skill <nome>`. Comandos slash (`/<nome>`) são os de `.claude/commands/`.

---

## Skills (23)

| Skill | Quando usar |
|-------|-------------|
| `aprender-domain` | Regras de negócio RF/RD/PA/CP |
| `django-patterns` | Models, serializers, views, services (Django/DRF) |
| `django-security` | Auditoria de vulnerabilidades, auth, RBAC, OWASP |
| `frontend-ui-engineering` | UIs React 18 + Antd 5 + Tailwind |
| `performance-optimization` | Endpoints lentos, N+1, bundle, Core Web Vitals |
| `writing-standards` | Docs, docstrings (PEP 257), commits |
| `test-driven-development` | **Antes** de implementar feature/bugfix |
| `debugging-and-error-recovery` | Debug root-cause (testes/builds/runtime) |
| `deprecation-and-migration` | Remover deps, substituir serviços, migrar |
| `subagent-development` | Orquestrar/paralelizar subagents |
| `verification-gate` | Verificar antes de afirmar sucesso |
| `security-scan` | Scan de secrets/deps/code patterns |
| `ci-github-actions` | CI/CD: workflows, gates [required], 3 marcadores do staging gate, promoção para prod (ADR-018) |
| `receiving-code-review` | Processar feedback de review |
| `create-plan` | Planejar features complexas |
| `implement-plan` | Executar planos de `thoughts/shared/plans/` |
| `brainstorming` | Transformar ideias vagas em design |
| `continuity-ledger` | Salvar estado antes de `/clear` |
| `create-handoff` | Transferir trabalho para outra sessão |
| `resume-handoff` | Continuar de handoff anterior |
| `git-worktrees` | Trabalhar em múltiplas branches |
| `graphify` | Knowledge graph local do codebase |
| `etl-guidelines` | **DEPRECATED-OK** — ETL legado removido; usar `import_export_contract` + DRF |

---

## Commands (18)

| Command | Quando usar |
|---------|-------------|
| `/create-feature` | Planejar + implementar feature (substitui o antigo `/new-feat`) |
| `/migrate` | Criar/aplicar migrations Django com validação |
| `/project_plan` | Planejar mudança (sem editar código) |
| `/investigate-batch` | Descoberta via perguntas em lote |
| `/gsd` | Dispatcher: roteia a tarefa para a ferramenta certa |
| `/review-enhanced` | Code review completo 11 categorias (substitui o antigo `/review`) |
| `/review-staged` | Review de staged changes vs padrões AS v2 |
| `/test-coverage` | Testes + cobertura (gate 85%) |
| `/approve-flow` | Testar política PA-01~07 |
| `/check-conflicts` | Testar RF03 / RD-01~08 |
| `/project_e2e-smoke` | Smoke E2E RF01→…→RF07 (Playwright MCP) |
| `/project_fix-django-url` | Investigar/corrigir URL reversing |
| `/project_git-pr` | Commit limpo + descrição de PR |
| `/deploy-staging` | Checklist do release: gate local `staging-full` → merge (build/sign/tag) → `promote.yml` |
| `/security-scan` | Scan de segurança automatizado |
| `/trim` | Reduzir descrição de PR em ~70% |
| `/etl-dry` | **DEPRECATED-OK** — usar `import_export_contract` (dry-run) |
| `/etl-apply` | **DEPRECATED-OK** — usar `import_export_contract --apply` |

---

## Agents (4 types — Task tool)

| Agent | Quando usar |
|-------|-------------|
| `Explore` | Buscar arquivos, varrer/investigar codebase |
| `Plan` | Arquitetar solução antes de implementar |
| `general-purpose` | Tarefas multi-step |
| `Workflow` | Fan-out multi-agent (auditorias, migrações, reviews grandes) |

---

## MCP Servers (8)

| MCP | Uso |
|-----|-----|
| `postgres` | Queries SQL |
| `github` | Issues, PRs, CI |
| `playwright` | Testes E2E |
| `fetch` | URLs |
| `context7` | Docs de libs/frameworks atualizadas |
| `docker` | Operações Docker |
| `tree-sitter` | Análise de AST |
| `devdocs` | Documentação de referência |

---

## Arquivados (NÃO usar — em `.claude/_archive/`)

| Arquivado | Substituto |
|-----------|-----------|
| `/review` | `/review-enhanced` |
| `/new-feat` | `/create-feature` |
| `/project_migrate-models` | `/migrate` |
| `/project_tdd` | skill `test-driven-development` |
| `/project_import-formadores` | (sem substituto — era dead) |
| skill `systematic-debugging` | skill `debugging-and-error-recovery` |
| skill `parallel-agents` | skill `subagent-development` |
