# Session: type-hints-tools-setup
Updated: 2026-01-13T13:30:00Z

## Goal
1. Implementar Type Hints 100% (PLAN_type_hints_100.md) - Fases 4-9
2. Garantir que ferramentas sejam lembradas após compactação

## Constraints
- Pyright strict mode (PEP 695)
- `from __future__ import annotations` em todos os arquivos
- Testes excluídos do pyright (fixtures pytest não tipadas)
- Docker obrigatório (CP-01)

## Key Decisions
- Manter `**/tests` no exclude do pyproject.toml (11k erros de fixtures pytest)
- Criar 3 mecanismos de lembrança de ferramentas:
  - CLAUDE.md atualizado com lista completa
  - Hook UserPromptSubmit para injetar lembrete
  - Continuity ledger para estado da sessão

## State
- Done:
  - PR #392 merged (Fases 1-3 type hints - core module)
  - Issues #343-351 fechadas
  - CLAUDE.md atualizado com ferramentas
  - Hook UserPromptSubmit criado (.claude/hooks/tools-reminder.ps1)
- Now: Criar continuity ledger (esta tarefa)
- Next:
  - Completar type hints Fases 4-7 (dev_tools + dat_ingest)
  - Issues #352-357 abertas

## Open Questions
- UNCONFIRMED: Hook UserPromptSubmit funciona corretamente no Windows?

## Working Set
- Branch: `feat/type-hints-full-coverage`
- Key files:
  - `.claude/CLAUDE.md` - Guia principal
  - `.claude/settings.json` - Hooks
  - `.claude/hooks/tools-reminder.ps1` - Lembrete de ferramentas
  - `v2/backend/pyproject.toml` - Config pyright
- Test cmd: `cd v2/backend && npx pyright apps/`

## Ferramentas Disponíveis (IMPORTANTE)

### Skills
| Skill | Uso |
|-------|-----|
| `aprender-domain` | Regras RF/RD/PA/CP |
| `django-patterns` | Padrões Django/DRF |
| `test-driven-development` | ANTES de implementar |
| `create_plan` | Planejar features |
| `implement_plan` | Executar planos |
| `continuity_ledger` | Salvar estado |
| `create_handoff` | Transferir sessão |
| `resume_handoff` | Continuar handoff |

### Slash Commands Principais
- `/project_plan` - Planejar antes de implementar
- `/review`, `/review-enhanced` - Após implementar
- `/approve-flow` - Validar PA-01~07
- `/check-conflicts` - Validar RD-01~08
- `/project_git-pr` - Commits e PRs
- `/test-coverage` - Testes com coverage

### Issues Abertas
- #352: type hints seed commands (dev_tools)
- #353: type hints backfill/fix commands
- #354: type hints dev_tools __init__.py
- #355: type hints dat_ingest services
- #356: type hints ETL commands
- #357: type hints dat_ingest misc
- #358, #359: type hints testes (opcional - excluídos do pyright)
