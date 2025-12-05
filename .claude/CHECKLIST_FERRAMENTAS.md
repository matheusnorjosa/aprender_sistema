# Checklist de Ferramentas — Claude Code

**⚠️ IMPORTANTE**: Este arquivo deve ser consultado **SEMPRE** ao retomar uma sessão resumida/compactada para relembrar todas as ferramentas disponíveis.

---

## 🎯 Quando Usar Este Checklist

- ✅ Após resumo/compactação de conversa
- ✅ No início de nova sessão com contexto histórico
- ✅ Quando detectar que estou fazendo tarefas manualmente
- ✅ Antes de análises complexas (review, validação, ETL)

---

## 📋 Ferramentas Disponíveis

### 1. Slash Commands (16 disponíveis)

**Desenvolvimento e Qualidade:**
- `/new-feat <descrição>` - Criar nova feature seguindo padrões
- `/migrate [app]` - Criar e aplicar migrações Django
- `/test-coverage [path]` - Análise de cobertura (90%+ required)
- `/review <arquivo>` - Review básico (170 linhas, 8 categorias)
- `/review-enhanced <arquivo>` - Review completo (573 linhas, 10 categorias) ⭐ **NOVO**

**Fluxos de Negócio:**
- `/approve-flow [test]` - Testar PA-01 a PA-07 (approval policy)
- `/check-conflicts [test]` - Testar RD-01 a RD-08 (availability rules)

**ETL:**
- `/etl-dry <command>` - Rodar ETL em dry-run (preview)
- `/etl-apply <command>` - Rodar ETL com apply (persiste)

**Deploy:**
- `/deploy-staging [type]` - Deploy staging (full/hotfix)

**Project Agents:**
- `/project_git-pr` - Preparar commit + PR description
- `/project_import-formadores` - Importar formadores Excel
- `/project_migrate-models` - Migrations para models
- `/project_tdd <app> <feature>` - Ciclo TDD
- `/project_e2e-smoke` - Smoke test Playwright (RF01→RF07)
- `/project_fix-django-url` - Fix URL reversing issues

---

### 2. Skills (3 disponíveis)

Use `Skill` tool com nome da skill:

- **`aprender-domain`** - Domínio completo (planilhas, fluxos SUPER/NAO_SUPER, RFs, códigos E/M/D/P/T/X)
- **`django-patterns`** - Padrões Django/DRF (models SSOT, serializers, views, services, permissions)
- **`etl-guidelines`** - ETL patterns (dry-run, idempotência, relatórios JSON)

**Quando usar Skills:**
- Precisar contexto detalhado de regras de negócio (aprender-domain)
- Dúvida sobre padrão correto Django/DRF (django-patterns)
- Implementar ou debugar ETL (etl-guidelines)

---

### 3. Task Tool (Agents Especializados)

Use `Task` tool quando:
- Busca exploratória no codebase (use `subagent_type: Explore`)
- Tarefa com múltiplas etapas autônomas (use `subagent_type: general-purpose`)
- Planejamento detalhado (use `subagent_type: Plan`)

**Exemplo**:
```
Task tool:
  subagent_type: Explore
  prompt: "Find all files that handle client errors"
```

---

### 4. Hooks (4 configurados)

**Automáticos** (disparam quando rodo comandos):

- `pytest.*` → 2 beeps (testes completos, ~3-4 min)
- `python manage.py.*--apply` → 2 beeps (ETL apply)
- `docker compose up.*` → 2 beeps (containers)
- Notificação geral → 1 beep (sucesso)

**Não preciso chamar**, são disparados automaticamente.

---

### 5. MCP Servers (4 disponíveis)

Servidores MCP configurados localmente (`.mcp.json` - não vai pro git):

| MCP | Ferramentas | Uso |
|-----|-------------|-----|
| **postgres** | `mcp__postgres__query` | Queries SQL diretas no banco Docker (`localhost:5434`) |
| **github** | `mcp__github__*` | Issues, PRs, comentários via API GitHub |
| **playwright** | `mcp__playwright__*` | Testes E2E, screenshots, automação browser |
| **fetch** | `mcp__fetch__*` | Fetch URLs sem restrições |

**Quando usar MCPs:**
- **postgres**: Debug de dados, verificar estado do banco, queries complexas
- **github**: Criar issues automaticamente, listar PRs, verificar CI
- **playwright**: Testes E2E automatizados, validação visual
- **fetch**: Buscar docs externas, APIs, verificar URLs

---

## 🔍 Checklist: "Devo usar ferramenta ou fazer manual?"

Antes de fazer análises manuais, SEMPRE perguntar:

### Análise de Código
- [ ] Existe slash command? (`/review`, `/review-enhanced`)
- [ ] Devo usar skill? (`django-patterns` para padrões)
- [ ] Devo usar Task/Explore? (busca no codebase)

### Validação de Regras de Negócio
- [ ] Existe slash command? (`/approve-flow`, `/check-conflicts`)
- [ ] Devo consultar skill? (`aprender-domain` para RD/PA/CP)

### ETL / Importação
- [ ] Devo usar slash command? (`/etl-dry`, `/etl-apply`)
- [ ] Devo consultar skill? (`etl-guidelines`)

### Deploy / Infraestrutura
- [ ] Existe slash command? (`/deploy-staging`)
- [ ] Devo usar project agent? (`/project_migrate-models`)

### Planejamento / Features
- [ ] Devo usar slash command? (`/new-feat`, `/project_tdd`)
- [ ] Devo consultar skills? (`aprender-domain`, `django-patterns`)

---

## 📖 Referências Rápidas

**Documentação completa**:
- `.claude/GUIA_USO.md` (657 linhas) - Guia completo de uso
- `.claude/CLAUDE.md` (1,432 linhas) - Regras de negócio
- `.claude/CLAUDE-principles.md` (463 linhas) - Qualidade de código

**Estrutura .claude/**:
```
.claude/
├── CLAUDE.md                  # Regras de negócio ⭐
├── CLAUDE-principles.md       # Qualidade de código
├── GUIA_USO.md                # Guia completo ⭐
├── CHECKLIST_FERRAMENTAS.md   # Este arquivo ⭐
├── MELHORIAS_2025-11-14.md    # Histórico de melhorias
├── settings.json              # Hooks + permissions
├── commands/                  # 16 slash commands
│   ├── review.md              # Original (170L)
│   ├── review-enhanced.md     # Novo (573L) ⭐
│   └── ... (14 outros)
└── skills/
    ├── aprender-domain/       # Domínio completo
    ├── django-patterns/       # Padrões Django/DRF
    └── etl-guidelines/        # ETL patterns
```

---

## ✅ Ação Imediata Após Ler Este Arquivo

Ao retomar sessão resumida, CONFIRMAR mentalmente:

1. ✅ Li o checklist de ferramentas
2. ✅ Sei quais slash commands usar para cada tipo de tarefa
3. ✅ Sei quando consultar skills (aprender-domain, django-patterns, etl-guidelines)
4. ✅ Lembrar de usar Task/Explore para buscas exploratórias
5. ✅ Vou EVITAR fazer tarefas manualmente quando existe ferramenta especializada

---

**Última atualização**: 2025-11-14
**Criado por**: Solicitação do usuário (sessão resumida causa esquecimento de ferramentas)
**Objetivo**: Garantir uso consistente de ferramentas customizadas mesmo após compactação de conversa
