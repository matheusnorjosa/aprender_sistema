# Projeto: Aprender Sistema (AS) v2 — Guia Completo

**Última Atualização**: 2026-01-19

## 🎯 Filosofia — Ultrathink

> *Não estamos aqui para escrever código. Estamos aqui para fazer diferença.*

**Princípios**: Think Different → Obsess Over Details → Plan Like Da Vinci → Craft, Don't Code → Iterate Relentlessly → Simplify Ruthlessly

---

## 📊 Status do Projeto

| Métrica | Valor | Status |
|---------|-------|--------|
| **Models** | 33 (28 core + 5 dat_ingest) | ✅ Modular |
| **API Endpoints** | 87+ | ✅ Documentados |
| **Testes** | 1.707 (130 arquivos) | ✅ 85%+ coverage |
| **Type Hints** | 100% | ✅ Pyright strict |
| **Management Commands** | 38 | ✅ ETL + Seeds |
| **Frontend Pages** | 45+ | ✅ Lazy loading |

### ✅ Iniciativas Concluídas

| Iniciativa | PR/Commit | Data |
|------------|-----------|------|
| Epic #405: API Best Practices 10/10 | #433, #434, #435 | ✅ 2026-01-19 |
| Epic #423: React Performance | #430, #431 | ✅ 2026-01-19 |
| Type Hints 100% (Phases 1-9) | #392, #394 | ✅ Completo |
| Maturity Gaps (10 gaps) | #390 | ✅ Completo |
| Infraestrutura 3-VM | #391 | ✅ Completo |
| Multi-Sector Availability | #389 | ✅ Completo |
| Backup Automation + WAL | #388 | ✅ Completo |

---

## Contexto do Projeto

- **Objetivo**: Substituir 82.389 fórmulas Excel por plataforma web (solicitação → aprovação → Google Calendar)
- **Stack**: Python 3.12 + Django 5.2 + DRF + PostgreSQL 15 + Redis 7 (Docker)
- **Frontend**: React 18 + Vite 7 + Ant Design 5 + Tailwind CSS
- **Timezone**: `America/Fortaleza` (UTC storage)
- **Type Checking**: Pyright strict mode (PEP 695)

---

## 🔧 Ferramentas (.claude/) — USO OBRIGATÓRIO

> **REGRA**: Antes de qualquer tarefa, verificar se existe ferramenta adequada.

### 📚 Skills (Conhecimento Especializado)

| Skill | Quando Usar |
|-------|-------------|
| `aprender-domain` | Implementar features, validar RF/RD/PA/CP |
| `django-patterns` | Implementar código Django (models, views, services) |
| `etl-guidelines` | Criar comandos de importação ETL |
| `writing-standards` | Documentação, docstrings, commits |
| `test-driven-development` | **ANTES** de implementar features/bugfixes |
| `create_plan` | Planejar features complexas |
| `implement_plan` | Executar planos de `thoughts/shared/plans/` |
| `continuity_ledger` | Salvar estado antes de /clear |
| `create_handoff` / `resume_handoff` | Transferir trabalho entre sessões |

### ⚡ Slash Commands

| Categoria | Comandos |
|-----------|----------|
| **Planejamento** | `/project_plan`, `/investigate-batch` |
| **Implementação** | `/new-feat`, `/create-feature`, `/migrate` |
| **Qualidade** | `/test-coverage`, `/review`, `/review-staged`, `/review-enhanced` |
| **Negócio** | `/approve-flow`, `/check-conflicts` |
| **ETL** | `/etl-dry`, `/etl-apply` |
| **Deploy** | `/deploy-staging` |
| **Git** | `/project_git-pr`, `/trim` |

### 🤖 Agents (Task Tool)

| Agent | Quando Usar |
|-------|-------------|
| `Explore` | Buscar arquivos, entender codebase |
| `Plan` | Arquitetar solução antes de implementar |
| `Bash` | Comandos shell, git, npm, docker |

### 🔌 MCP Servers

| MCP | Uso |
|-----|-----|
| **postgres** | Queries SQL (`localhost:5434`) |
| **github** | Issues, PRs, CI status |
| **playwright** | Testes E2E, screenshots |
| **fetch** | URLs sem restrições |

---

## ⚖️ CLÁUSULAS PÉTREAS — IMUTÁVEIS

### CP-01: REQUIRE_DOCKER=1 (v2 ONLY)
v2 DEVE rodar APENAS em Docker: `cd v2 && make up`

### CP-02: Política de Aprovação (PA-01 a PA-07)

| Regra | Descrição |
|-------|-----------|
| PA-01 | Sem auto-aprovação para SUPER. NAO_SUPER é auto-aprovado |
| PA-02 | Superintendência, DAT ou superuser podem aprovar |
| PA-03 | Integrações externas só após aprovação |
| PA-04 | Estado inicial: `pendente` (SUPER) ou `aprovado` (NAO_SUPER) |
| PA-05 | Registrar em `AuditLog` |
| PA-06 | Esconder botões para perfis sem permissão |
| PA-07 | 6 testes obrigatórios em `test_approval_policy_PA.py` |

### CP-03: Regras de Disponibilidade (RD-01 a RD-08)

| Regra | Descrição |
|-------|-----------|
| RD-01 | Não-sobreposição (fim==início = OK) |
| RD-02 | Bloqueio total (T) impede eventos |
| RD-03 | Bloqueio parcial (P) impede subintervalo |
| RD-04 | Buffer deslocamento (D) entre municípios |
| RD-05 | Capacidade diária (M) por formador |
| RD-06 | Timezone America/Fortaleza, storage UTC |
| RD-07 | Prioridade: Bloqueios → Conflitos → Buffer → Limite |
| RD-08 | Mensagens estruturadas: formador, data, intervalo, tipo |

### CP-04 a CP-08

- **CP-04**: Workflow Sub-Agents (Entender → Planejar → Implementar → Testar → Infra → ETL → UI/UX)
- **CP-05**: v1 congelado (branch `fix/v1-*` + PR para `main-v1`)
- **CP-06**: Conventional commits (`<type>(<scope>): <message>`)
- **CP-07**: Nunca push direto na main (PR obrigatório)
- **CP-08**: `INCLUDE_DEV_TOOLS=false` em produção

---

## 🏗️ Arquitetura Atual

### Backend (33 Models)

```
apps/
├── core/                    # App principal (28 models)
│   ├── models/             # Usuario, Solicitacao, AvailabilityBlock, etc
│   ├── serializers/        # 11 arquivos modulares
│   ├── views/              # ViewSets organizados
│   ├── services/           # Lógica de negócio
│   │   ├── availability_service.py  # RD-01~RD-08
│   │   ├── gcal/           # Google Calendar (6 arquivos)
│   │   └── ...
│   └── tests/              # 106 arquivos, 1.326 testes
├── dat_ingest/             # ETL (5 models, 20 commands)
└── dev_tools/              # Seeds (14 commands, prod disabled)
```

### Frontend (45+ Pages)

```
src/
├── pages/                  # 45+ páginas lazy-loaded
│   ├── Solicitacoes/       # Wizard 4-step, lista, edição
│   ├── Aprovacoes/         # Fluxo PA-01~07
│   ├── Disponibilidade/    # Grade mensal + bloqueios
│   ├── DATModule/          # 7 páginas DAT
│   ├── AdminDAT/           # 6 páginas admin
│   └── Dashboards/         # KPIs, GCal, Equipe
├── components/             # 19 componentes reutilizáveis
├── hooks/                  # 5 custom hooks
└── api/                    # 11 clientes axios
```

### Infraestrutura de Produção (3 VMs)

| VM | Specs | Função |
|----|-------|--------|
| VM01_App | 4vCPU/16GB/60GB | Nginx + Gunicorn + Celery |
| VM02_Banco | 4vCPU/16GB/300GB | PostgreSQL 15 |
| VM03_Redis | 2vCPU/4GB/20GB | Cache + Sessions + Broker |

---

## 🔐 RBAC (Setor + Função)

### Setores (9)
Superintendência, Vidas, Fluir, ACerta, Brincando, Sou da Paz, DAT, Controle, Gerência

### Funções (4)
Formador, Coordenador, Apoio de Coordenação, Gerente

### Aprovação SUPER
```python
can_approve_super = is_superuser OR ("Gerente" IN funcoes AND "Superintendência" IN setores)
```

---

## 📦 Management Commands (38 total)

### Core (4 commands)
- `preagenda_to_gcal` — Sync Google Calendar
- `rotate_gcal_encryption_key` — Rotação de chave OAuth
- `compliance_audit` — Auditoria PA/RD
- `lgpd_export` — Export LGPD

### ETL/dat_ingest (20 commands)
- `etl_all` — Pipeline completo
- `etl_upsert_acompanhamento` — Solicitações + Participations
- `etl_import_acoes_controle` — AcaoControle
- `etl_import_dat_cadastros` — AcaoDAT
- ... (16 mais)

### Seeds/dev_tools (14 commands)
- `seed_rbac` — Grupos e permissões
- `seed_tipos_evento` — TipoEvento default
- `seed_e2e_users` — Usuários E2E
- ... (11 mais)

---

## 📋 API Endpoints (87+)

### Principais Rotas

| Categoria | Endpoints | Permissão |
|-----------|-----------|-----------|
| **Auth** | `/auth/login/`, `/auth/logout/`, `/csrf/` | AllowAny |
| **Solicitações** | `/solicitacoes/` (CRUD + approve/reject) | IsAuthenticated |
| **Availability** | `/availability/check/`, `/availability/monthly/` | IsControleOrSuper |
| **GCal** | `/gcal/publish-batch/`, `/gcal/dashboard/*` | IsControleOrSuper |
| **DAT Module** | `/dat/registros/`, `/dat/acoes-ciclo/`, etc | IsDATOrSuper |
| **Admin** | `/municipios/`, `/projetos/`, `/usuarios-admin/` | IsDAT |

---

## 🧪 Testes (1.707 total)

| App | Arquivos | Testes |
|-----|----------|--------|
| **core** | 106 | 1.326 |
| **dat_ingest** | 21 | 348 |
| **dev_tools** | 3 | 33 |

### Testes Críticos (CI Required)
- `test_approval_policy_PA.py` — PA-01~07 (6 testes)
- `test_availability_service.py` — RD-01~08 (17 testes)
- `test_models_constraints.py` — Integridade DB
- `test_google_oauth.py` — OAuth flow (42 testes)

---

## 📖 Documentação Principal

| Documento | Propósito |
|-----------|-----------|
| [PROJETO_ORIGEM.md](../v2/docs/PROJETO_ORIGEM.md) | Origem, RFs, stack |
| [GUIDE_GCAL.md](../v2/docs/GUIDE_GCAL.md) | Integração Google Calendar |
| [GUIDE_AVAILABILITY.md](../v2/docs/GUIDE_AVAILABILITY.md) | Regras RD-01~08 |
| [DEPLOY_CHECKLIST.md](../v2/docs/DEPLOY_CHECKLIST.md) | Checklist produção |
| [SLO_DEFINITIONS.md](../v2/docs/SLO_DEFINITIONS.md) | Métricas de performance |
| [DISASTER_RECOVERY.md](../v2/docs/DISASTER_RECOVERY.md) | DR procedures |
| [PLAN_api_best_practices.md](../v2/docs/PLAN_api_best_practices.md) | **API 10/10** (Epic #405) |

### 🚧 Planos em Andamento

| Plano | Epic | Status |
|-------|------|--------|
| [Refatoração Valores Hardcoded](../v2/docs/PLAN_hardcoded_values_refactor.md) | #437 | 🆕 Novo |

---

### 🚀 Epic #437: Refatoração de Valores Hardcoded

**Objetivo**: Eliminar valores hardcoded no frontend e backend, centralizando em constantes e configurações.

**Plano Detalhado**: [PLAN_hardcoded_values_refactor.md](../v2/docs/PLAN_hardcoded_values_refactor.md)

**Estimativa Total**: ~9 horas

#### Issues Críticas (Fase 1)

| Issue | Título | Prioridade |
|-------|--------|------------|
| #438 | Criar estrutura de constantes frontend | 🔴 CRÍTICO |
| #439 | Consolidar cores no ThemeContext | 🔴 CRÍTICO |
| #440 | Corrigir anos hardcoded (dinâmico) | 🔴 CRÍTICO |
| #441 | Corrigir lista de UFs incompleta | 🔴 CRÍTICO |
| #442 | Mover portas OAuth para env vars | 🔴 CRÍTICO |

#### Issues Médias (Fase 2)

| Issue | Título | Prioridade |
|-------|--------|------------|
| #443 | Centralizar timeouts no backend | 🟡 MÉDIO |
| #444 | Centralizar page sizes | 🟡 MÉDIO |
| #445 | Consolidar listas de UF duplicadas | 🟡 MÉDIO |
| #446 | Mover URLs externas para config | 🟡 MÉDIO |

**Ordem de Execução**:
```
Fase 1 (Paralelo):   #438 + #440 + #441 + #442
Fase 2 (Sequencial): #439 (depende de #438)
Fase 3 (Paralelo):   #443 + #444 + #445 + #446
```

**Verificação**:
```bash
cd v2/frontend && npm run build  # Frontend
cd v2/backend && pyright apps/   # Backend
docker exec aprender_v2-web-1 pytest  # Testes
```

---

### ✅ Epic #423: React Performance Optimization (CONCLUÍDO)

**Objetivo**: Aplicar 45 regras de React Performance da Vercel Engineering no módulo Solicitações.

**Score**: 7.25/10 → 9.5+/10

**Arquivos**:
- `v2/frontend/src/pages/Solicitacoes/MySolicitacoesPage.jsx`
- `v2/frontend/src/pages/Solicitacoes/NewSolicitacaoWizard.jsx`
- `v2/frontend/src/pages/Solicitacoes/EditSolicitacaoPage.jsx`

| Ordem | Issue | Descrição | Prioridade |
|-------|-------|-----------|------------|
| 1 | #424 | antd direct imports | 🔴 CRÍTICO |
| 2 | #425 | @ant-design/icons direct imports | 🔴 CRÍTICO |
| 3 | #426 | memoize steps array (280 linhas) | 🟡 MÉDIO |
| 4 | #427 | memoize columns array (115 linhas) | 🟡 MÉDIO |
| 5 | #428 | memoize rangeValue computation | 🟡 MÉDIO |

**Execução**:
```
Fase 1 (Paralelo):  #424 + #425 → Bundle Size (-300-600ms TTI)
Fase 2 (Sequencial): #426 → #427 → #428 → Re-renders
```

**Verificação após cada issue**:
```bash
cd v2/frontend && npm run build  # Verificar bundle size
npm run test                      # Testes unitários
```

**Review final**: `/review-enhanced v2/frontend/src/pages/Solicitacoes`

---

**Issues relacionadas (API)**: #406, #407, #408, #409, #410, #411, #412

| Issue | Categoria | Score |
|-------|-----------|-------|
| #406 | Query Optimization | 7→10 |
| #407 | Error Handling | 4→10 |
| #408 | Pagination | 7→10 |
| #409 | Rate Limiting | 6→10 |
| #410 | API Versioning | 2→10 |
| #411 | Response Consistency | 5→10 |
| #412 | OpenAPI Documentation | 3→10 |

**Ordem de Execução** (após merge PR #413):

| Ordem | Issue | Tempo | Justificativa |
|-------|-------|-------|---------------|
| 1 | #406 Query Optimization | 2h | Mais fácil, ganho imediato |
| 2 | #407 Error Handling | 4h | Base para outras melhorias |
| 3 | #409 Rate Limiting | 2h | Depende de Error Handling |
| 4 | #408 Pagination | 2h | Independente |
| 5 | #411 Response Consistency | 3h | Usa Error Handling |
| 6 | #410 API Versioning | 3h | Independente |
| 7 | #412 OpenAPI Documentation | 6h | Por último, documenta tudo |

**Total**: ~22h de implementação

📋 **Plano detalhado**: [PLAN_api_best_practices.md](../v2/docs/PLAN_api_best_practices.md) contém código específico para cada issue.

---

## Quick Reference

```bash
# Docker
cd v2 && make up

# Testes
docker exec aprender_v2-web-1 pytest apps/core/tests/ -v

# Type check
cd v2/backend && pyright apps/core apps/dat_ingest

# ETL dry-run
make etl-acomp-dry

# E2E tests
make test-e2e
```

---

## Fluxos Principais (RF)

| RF | Descrição | Status |
|----|-----------|--------|
| RF01 | Importação de dados (ETL) | ✅ 20 comandos |
| RF02 | Solicitar evento | ✅ Wizard 4-step |
| RF03 | Verificar conflitos | ✅ RD-01~08 |
| RF04 | Aprovar/Reprovar | ✅ PA-01~07 |
| RF05 | Google Calendar | ✅ Service Account + OAuth |
| RF06 | Google Meet links | ✅ Automático |
| RF07 | Auditoria | ✅ AuditLog completo |
| RF08 | Grade mensal | ✅ Virtualização + cache |
