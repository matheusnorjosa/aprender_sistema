# Projeto: Aprender Sistema (AS) — Guia do Claude Code

## 🎯 Filosofia — Ultrathink

> *Não estamos aqui para escrever código. Estamos aqui para fazer diferença.*

**Princípios**: Think Different → Obsess Over Details → Plan Like Da Vinci → Craft, Don't Code → Iterate Relentlessly → Simplify Ruthlessly

Seu código deve: funcionar com workflow humano, parecer intuitivo, resolver o problema *real*, deixar o codebase melhor.

---

## ⚠️ IMPORTANTE: Ao Retomar Sessão Resumida

1. ✅ **LEIA**: [.claude/CHECKLIST_FERRAMENTAS.md](.claude/CHECKLIST_FERRAMENTAS.md) — Lista de slash commands, skills, hooks
2. ✅ **EVITE**: Tarefas manuais quando existe ferramenta (use `/review-enhanced`, skill `aprender-domain`)
3. ✅ **PERGUNTE**: "Existe slash command, skill ou agent para isso?"

---

## Contexto do Projeto

- **Objetivo**: Substituir planilhas por plataforma web (solicitação → aprovação → Google Calendar)
- **Stack**: Python 3.12 + Django 5.2 + DRF + PostgreSQL 15 + Redis 7 (Docker)
- **Frontend**: React (Vite) + Tailwind + Ant Design
- **Timezone**: `America/Fortaleza`
- **Type Checking**: Pyright strict mode (PEP 695)

---

## 🔧 Ferramentas (.claude/)

### Slash Commands Principais

| Categoria | Comandos |
|-----------|----------|
| **Dev/Quality** | `/new-feat`, `/create-feature`, `/migrate`, `/test-coverage`, `/review`, `/review-staged`, `/trim` |
| **Fluxos Negócio** | `/approve-flow` (PA-01 a PA-07), `/check-conflicts` (RD-01 a RD-08) |
| **ETL** | `/etl-dry`, `/etl-apply` |
| **Deploy** | `/deploy-staging` |
| **Project Agents** | `/project_git-pr`, `/project_tdd`, `/project_plan`, `/project_e2e-smoke` |

### Skills Especializadas

- **aprender-domain** — Domínio completo (planilhas, fluxos SUPER/NAO_SUPER, RFs, códigos E/M/D/P/T/X)
- **django-patterns** — Padrões Django/DRF (models, views, services, testes)
- **etl-guidelines** — Guidelines ETL (dry-run, idempotência, relatórios)

### MCP Servers

| MCP | Uso |
|-----|-----|
| **postgres** | Queries SQL (`localhost:5434`) |
| **github** | Issues, PRs, CI status |
| **playwright** | Testes E2E, screenshots |
| **fetch** | URLs sem restrições |

📖 **Guia Completo**: [.claude/GUIA_USO.md](.claude/GUIA_USO.md)

---

## ⚖️ CLÁUSULAS PÉTREAS — IMUTÁVEIS

### 🐳 CP-01: REQUIRE_DOCKER=1 (v2 ONLY)

v2 DEVE rodar APENAS em Docker. Comando: `cd v2 && make up`

### 🔒 CP-02: Política de Aprovação (PA-01 a PA-07)

| Regra | Descrição |
|-------|-----------|
| PA-01 | Sem auto-aprovação para **SUPER**. NAO_SUPER é auto-aprovado |
| PA-02 | **Superintendência**, **DAT** ou **superuser** podem aprovar |
| PA-03 | Integrações externas só após aprovação |
| PA-04 | Estado inicial: `pendente` (SUPER) ou `aprovado` (NAO_SUPER) |
| PA-05 | Registrar em `Aprovacao` e `LogAuditoria` |
| PA-06 | Esconder botões para perfis sem permissão |
| PA-07 | Testes obrigatórios (5 testes específicos) |

### 📅 CP-03: Regras de Disponibilidade (RD-01 a RD-08)

| Regra | Descrição |
|-------|-----------|
| RD-01 | Não-sobreposição (fim==início = OK) |
| RD-02 | Bloqueio total (T) impede eventos |
| RD-03 | Bloqueio parcial (P) impede subintervalo |
| RD-04 | Buffer deslocamento (D) entre municípios |
| RD-05 | Capacidade diária (M) por formador |
| RD-06 | Timezone America/Fortaleza, storage UTC |
| RD-07 | Prioridade: Bloqueios → Conflitos → Buffer → Limite |
| RD-08 | Mensagens: formador, data, intervalo, tipo |

### 🔄 CP-04: Workflow de Sub-Agents

1. Entender → 2. Planejar → 3. Implementar → 4. Testar → 5. Infra → 6. ETL → 7. UI/UX

### 🚫 CP-05: Nunca Tocar v1 Sem Aprovação

v1 está congelado. Qualquer mudança exige branch `fix/v1-*`, PR para `main-v1`, CI verde.

### 📝 CP-06: Padrões de Commit/Branch/PR

- **Commits**: `<type>(<scope>): <message>` (feat, fix, chore, docs, test, refactor)
- **Branches**: `<type>/<nome>` (feat/v2-*, fix/v2-*)
- **PRs**: Squash and merge, CI verde obrigatório

### 🚫 CP-07: Nunca Push Direto na Main

Fluxo: branch → commits → push → PR → CI verde → merge via GitHub

### 🛠️ CP-08: INCLUDE_DEV_TOOLS (Ferramentas de Desenvolvimento)

| Ambiente | INCLUDE_DEV_TOOLS | Resultado |
|----------|-------------------|-----------|
| Dev | `true` (default) | Seeds disponíveis |
| Staging | `true` | Seeds disponíveis |
| Prod | `false` | Seeds indisponíveis |

**Commands em `apps/dev_tools`**:
- `seed_*` — Dados iniciais (usuarios, projetos, RBAC)
- `backfill_*` — Migracoes de dados
- `fix_*` — Correcoes unicas
- `cleanup_e2e_data` — Limpeza E2E

**Commands em `apps/core`** (sempre disponíveis):
- `preagenda_to_gcal` — Sync Google Calendar
- `rotate_gcal_encryption_key` — Rotacao de chave

---

## 🏗️ Arquitetura Atual

- **Backend Modular**: `models/`, `serializers/`, `views/`, `services/gcal/` (PRs #213-#217)
- **Type Hints**: Pyright strict mode - [Plano 100% Coverage](../v2/docs/PLAN_type_hints_100.md) (Epic #342)
- **RBAC**: Setor + Função ([PLANO_RBAC_SETOR_FUNCAO.md](.claude/PLANO_RBAC_SETOR_FUNCAO.md))
- **Observabilidade**: Structured Logging (MP2), Monitoramento via plataforma do provedor
- **Maturidade**: [Plano Gaps de Maturidade](../v2/docs/PLAN_maturity_gaps.md) (Epic #360)
- **Infraestrutura**: [Plano de Produção 3 VMs](../v2/docs/PLAN_infrastructure_scaling.md) (Epic #371)
- **Multi-Setor**: [Plano Disponibilidade Multi-Setor](../v2/docs/PLAN_multi_sector_availability.md) (Epic #379)

📖 **Documentação Detalhada**:
- Origem: [v2/docs/PROJETO_ORIGEM.md](../v2/docs/PROJETO_ORIGEM.md)
- Type Hints: Pyright 1.1.382, `cd v2/backend && pyright apps/core`
- Google Calendar: [v2/docs/GUIDE_GCAL.md](../v2/docs/GUIDE_GCAL.md)
- Deploy: [v2/docs/DEPLOY_CHECKLIST.md](../v2/docs/DEPLOY_CHECKLIST.md)

### 🖥️ Infraestrutura de Produção

| VM | Specs | Função |
|----|-------|--------|
| VM01_App | 4vCPU/16GB/60GB | Nginx + Gunicorn + Celery |
| VM02_Banco | 4vCPU/16GB/300GB | PostgreSQL |
| VM03_Redis | 2vCPU/4GB/20GB | Cache + Sessions + Broker |

---

## 🔐 RBAC Resumido

- **SETOR** (9): Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Gerência
- **FUNÇÃO** (4): Formador, Coordenador, Apoio de Coordenação, Gerente
- **Aprovação SUPER**: `is_superuser OR ("Gerente" IN funcoes AND "Superintendência" IN setores)`

---

## Boas Práticas

### Python/Django
- PEP8, PEP20, type hints, docstrings, DRY
- Models = fonte de verdade, views curtas, lógica em services
- select_related/prefetch, URLs nomeadas, testes obrigatórios

### Gerais
- KISS, YAGNI, clareza > esperteza
- Commits pequenos, atômicos
- Logs e auditoria obrigatórios

---

## Fluxos Principais

| RF | Descrição | Status |
|----|-----------|--------|
| RF02 | Solicitar evento | ✅ |
| RF03 | Verificar conflitos | ✅ |
| RF04 | Aprovar/Reprovar | ✅ |
| RF05 | Google Calendar | ✅ |
| RF06 | Google Meet links | ✅ |

---

## Ações Prioritárias do Claude

1. Usar ferramentas `.claude/` proativamente
2. Ler código e entender contexto
3. Planejar passo a passo (`/project_plan`)
4. Commits pequenos, atômicos, testados
5. Conventional commits
6. Validar com UX/IHC e regras de disponibilidade

---

## Quick Reference

```bash
# Testes
python manage.py test

# Type check
cd v2/backend && pyright apps/core

# Docker
cd v2 && make up
```
