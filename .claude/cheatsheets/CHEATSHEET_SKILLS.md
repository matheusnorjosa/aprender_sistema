# Skills Cheatsheet — Claude Code

Quick reference for all 17 available skills.

---

## Domínio e Padrões

| Skill | Quando Usar | Invocação |
|-------|-------------|-----------|
| `aprender-domain` | Regras RF/RD/PA/CP, domínio do negócio | Automático |
| `django-patterns` | Models, Views, Serializers, Services | Automático |
| `etl-guidelines` | Import ETL, dry-run, idempotência | Automático |
| `writing-standards` | Documentação, docstrings, commits | Automático |

---

## Desenvolvimento

| Skill | Quando Usar | Invocação |
|-------|-------------|-----------|
| `test-driven-development` | **ANTES** de implementar features | `/skill test-driven-development` |
| `systematic-debugging` | Debug estruturado 4 fases | `/skill systematic-debugging` |
| `verification-gate` | Verificar ANTES de afirmar sucesso | `/skill verification-gate` |
| `subagent-development` | Implementar via subagents especializados | `/skill subagent-development` |

---

## Planejamento

| Skill | Quando Usar | Invocação |
|-------|-------------|-----------|
| `create_plan` | Planejar features complexas | `/skill create_plan` |
| `implement_plan` | Executar planos de `thoughts/shared/plans/` | `/skill implement_plan` |
| `brainstorming` | Transformar ideias em designs | `/skill brainstorming` |

---

## Sessão e Continuidade

| Skill | Quando Usar | Invocação |
|-------|-------------|-----------|
| `continuity_ledger` | Salvar estado antes de /clear | `/skill continuity_ledger` |
| `create_handoff` | Transferir trabalho para outra sessão | `/skill create_handoff` |
| `resume_handoff` | Continuar de handoff anterior | `/skill resume_handoff` |

---

## Colaboração

| Skill | Quando Usar | Invocação |
|-------|-------------|-----------|
| `parallel-agents` | Coordenar múltiplos subagents | `/skill parallel-agents` |
| `git-worktrees` | Trabalhar em múltiplas branches | `/skill git-worktrees` |
| `receiving-code-review` | Processar feedback de review | `/skill receiving-code-review` |

---

## Detalhes por Skill

### systematic-debugging
**4 Fases:**
1. **Observe** - Reproduzir, coletar dados
2. **Hypothesize** - Formar hipóteses testáveis
3. **Test** - Validar uma hipótese por vez
4. **Fix** - Corrigir root cause, não sintoma

### verification-gate
**Antes de afirmar:**
- [ ] Rodei o teste/comando?
- [ ] Vi output de sucesso?
- [ ] Verifiquei efeitos colaterais?

### parallel-agents
**Padrão:**
```
Task(subagent_type="Explore", prompt="...")  # Paralelo
Task(subagent_type="Plan", prompt="...")     # Paralelo
→ Esperar resultados
→ Sintetizar
```

### continuity_ledger
**Estrutura:**
```markdown
# Session: <nome>
## Goal - O que é sucesso?
## State - Done/Now/Next
## Working Set - Branch, arquivos, comandos
```

### brainstorming
**Output:**
```markdown
# Design: <Feature>
## Chosen Approach
## Key Decisions
## Next Steps
```

---

## Slash Commands Relacionados

| Categoria | Comandos |
|-----------|----------|
| **Planejamento** | `/project_plan`, `/investigate-batch` |
| **Implementação** | `/new-feat`, `/create-feature`, `/migrate` |
| **Qualidade** | `/test-coverage`, `/review`, `/review-staged`, `/review-enhanced` |
| **Negócio** | `/approve-flow`, `/check-conflicts` |
| **ETL** | `/etl-dry`, `/etl-apply` |
| **Git** | `/project_git-pr`, `/trim` |

---

## Agents (Task Tool)

| Agent | Quando Usar |
|-------|-------------|
| `Explore` | Buscar arquivos, entender codebase |
| `Plan` | Arquitetar solução |
| `Bash` | Comandos shell, git, npm |
| `general-purpose` | Tarefas multi-step |

---

## MCP Servers

| MCP | Uso |
|-----|-----|
| `postgres` | Queries SQL (localhost:5434) |
| `github` | Issues, PRs, CI |
| `playwright` | Testes E2E |
| `fetch` | URLs sem restrições |

---

## Quando Usar Cada Skill

```
Nova feature?
  └─ Complexa? → create_plan → implement_plan
  └─ Simples? → test-driven-development

Bug?
  └─ systematic-debugging (4 fases)

Contexto >70%?
  └─ continuity_ledger → /clear

Fim de sessão?
  └─ create_handoff

Múltiplas tasks paralelas?
  └─ parallel-agents + subagent-development

Code review recebido?
  └─ receiving-code-review

Ideia vaga?
  └─ brainstorming

Múltiplas branches?
  └─ git-worktrees
```

---

## Arquivos de Skills

```
.claude/skills/
├── aprender-domain/SKILL.md
├── brainstorming/SKILL.md
├── continuity_ledger/SKILL.md
├── create_handoff/SKILL.md
├── create_plan/SKILL.md
├── django-patterns/SKILL.md
├── etl-guidelines/SKILL.md
├── git-worktrees/SKILL.md
├── implement_plan/SKILL.md
├── parallel-agents/SKILL.md
├── receiving-code-review/SKILL.md
├── resume_handoff/SKILL.md
├── subagent-development/SKILL.md
├── systematic-debugging/SKILL.md
├── test-driven-development/SKILL.md
├── verification-gate/SKILL.md
└── writing-standards/SKILL.md
```
