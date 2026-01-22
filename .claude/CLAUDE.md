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
| Epic #437: Refatoração Hardcoded | #448 | ✅ 2026-01-19 |
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
| [Backend Code Formatting](../v2/docs/PLAN_backend_code_formatting.md) | #450 | 🆕 Novo |

---

### 🚀 Epic #450: Backend Code Formatting (Black + isort + Flake8)

**Objetivo**: Formatar todo o backend Python com Black e isort, corrigir erros de Flake8, e tornar o lint obrigatório no CI.

**Plano Detalhado**: [PLAN_backend_code_formatting.md](../v2/docs/PLAN_backend_code_formatting.md)

#### Métricas

| Métrica | Valor |
|---------|-------|
| Total de arquivos Python | 396 |
| Arquivos precisando Black | 330 (83%) |
| Arquivos precisando isort | 251 |
| Erros Flake8 total | 713 |

#### Issues

| Fase | Issue | Descrição | Prioridade |
|------|-------|-----------|------------|
| 1 | #451 | Configuração de Ferramentas | 🔴 CRÍTICO |
| 2 | #452 | Formatação com Black | 🔴 CRÍTICO |
| 3 | #453 | Ordenação de Imports (isort) | 🔴 CRÍTICO |
| 4 | #454 | Remoção de Imports Não Usados | 🟡 MÉDIO |
| 5 | #455 | Correção de Variáveis Não Usadas | 🟡 MÉDIO |
| 6 | #456 | Correções Manuais (F541, F811, E722) | 🟡 MÉDIO |
| 7 | #457 | Tornar Lint Obrigatório no CI | 🔴 CRÍTICO |
| 8 | #458 | Pre-commit Hooks (Opcional) | 🟢 BAIXO |

**Ordem de Execução**:
```
Fase 1 (Config)     → Base para todas as outras
Fase 2-3 (Paralelo): Black + isort → Formatação automática
Fase 4-6 (Sequencial): autoflake → F841 → Manual → Correções
Fase 7 (CI)         → Só após tudo formatado
Fase 8 (Opcional)   → Pre-commit para devs
```

**Verificação**:
```bash
cd v2/backend
black --check .
isort --check .
flake8 .
pyright apps/core apps/dat_ingest config
pytest apps/ -q
```

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

---

## 🚀 Epic #459: Refatoração de Código - Plano Mestre

**Objetivo**: Refatorar arquivos longos e de difícil manutenção, aplicando boas práticas de programação sem alterar comportamento, rotas ou contratos públicos.

**Data**: 2026-01-19 | **Última Atualização**: 2026-01-19
**Branch**: `refactor/epic-459-code-quality`

**Score Atual**: Frontend 8.0/10 | Backend 8.0/10
**Score Meta**: Frontend 9.0/10 | Backend 9.0/10

### 📊 Progresso por Item

| Item | Descrição | Status | Notas |
|------|-----------|--------|-------|
| §1 | Services views_solicitacao.py | ✅ DONE | 1234→821 linhas (-33%) |
| §2 | Memoização CoordenadoresPage | ✅ DONE | useMemo/useCallback aplicado |
| §3 | Memoização AcoesPage | ✅ DONE | useMemo/useCallback aplicado |
| §4 | Hook useGoogleGuard | ✅ DONE | -150 linhas duplicadas |
| §5 | Modularizar ETL acompanhamento | ⏭️ SKIP | Bem estruturado internamente |
| §6 | Separar ViewSets dat_module | ⏭️ SKIP | Bem estruturado (748 linhas, 6 ViewSets) |
| §7 | Separar google_oauth.py | ✅ DONE | 672→54 linhas (+oauth/) |
| §8 | Mover lógica tasks.py | ⏭️ SKIP | Já delega para services |
| §9 | Fatiar views_metrics.py | ✅ DONE | 592→30 linhas (+views/metrics/) |
| §10 | Dividir serializers/dat_module | ✅ DONE | 558→6 módulos (+dat_module/) |
| §11 | Mixin/factory permissões | ⏭️ SKIP | Padrão claro, lógica complexa variada |
| §12 | Padronizar error handling | ✅ DONE | Response→ValidationAPIError |
| §13 | N+1 availability_service | ⏭️ SKIP | Sem N+1 (só campos diretos) |
| §14 | constants/styles.js | ✅ DONE | Estilos centralizados |
| §15 | (coberto por §4) | ✅ DONE | - |
| §16-18 | Otimizações leves | ✅ DONE | useMemo em 4 páginas |

### Regras Gerais

- ❌ Não mudar comportamento, rotas, payloads ou status codes
- ❌ Não adicionar dependências novas
- ❌ Não alterar contratos públicos
- ✅ Manter lint/estilo do projeto
- ✅ Manter i18n/labels e strings
- ✅ Evitar regressões de autorização
- ✅ Comentários só para blocos realmente complexos

---

### 🔴 ALTA PRIORIDADE (1-9)

#### §1. Backend: Extrair Services de views_solicitacao.py

**Arquivo**: `v2/backend/apps/core/views_solicitacao.py` (~1234 linhas, 15+ métodos)

**Problema**: God class com approve/reject/publish/perform_create misturados. Lógica de negócio em views.

**Solução**:
- Criar `apps/core/services/solicitacao_approval.py` (approve, reject, batch_approve, batch_reject)
- Criar `apps/core/services/solicitacao_publish.py` (publish, preview, resync, cancel)
- View delega para services
- Usar `ValidationAPIError` em vez de `Response()` direto para erros

**Arquivos Criados**:
- `v2/backend/apps/core/services/solicitacao_approval.py`
- `v2/backend/apps/core/services/solicitacao_publish.py`

**Arquivos Modificados**:
- `v2/backend/apps/core/views_solicitacao.py`

---

#### §2. Frontend: Refatorar CoordenadoresPage.jsx

**Arquivo**: `v2/frontend/src/pages/DATModule/CoordenadoresPage.jsx` (~945 linhas)

**Problema**: 3 views (Cards/Table/Area) + CRUD + stats misturados em um arquivo.

**Solução**:
- Extrair `components/CoordenadoresTable.jsx`
- Extrair `components/CoordenadoresCards.jsx`
- Extrair `components/CoordenadoresAreaView.jsx`
- Extrair `components/CoordenadoresFilters.jsx`
- Extrair `components/CoordenadoresStats.jsx`
- Criar `hooks/useCoordenadoresPage.js` para lógica de estado
- Aplicar `useMemo` em columns e groupByArea
- Aplicar `useCallback` em handlers

**Arquivos Criados**:
- `v2/frontend/src/pages/DATModule/Coordenadores/components/CoordenadoresTable.jsx`
- `v2/frontend/src/pages/DATModule/Coordenadores/components/CoordenadoresCards.jsx`
- `v2/frontend/src/pages/DATModule/Coordenadores/components/CoordenadoresAreaView.jsx`
- `v2/frontend/src/pages/DATModule/Coordenadores/components/CoordenadoresFilters.jsx`
- `v2/frontend/src/pages/DATModule/Coordenadores/components/CoordenadoresStats.jsx`
- `v2/frontend/src/pages/DATModule/Coordenadores/hooks/useCoordenadoresPage.js`

**Arquivos Modificados**:
- `v2/frontend/src/pages/DATModule/CoordenadoresPage.jsx` (delega para componentes)

---

#### §3. Frontend: Otimizar AcoesPage.jsx

**Arquivo**: `v2/frontend/src/pages/DATModule/AcoesPage.jsx` (~933 linhas)

**Problema**: Columns/render sem memoização, múltiplos view modes.

**Solução**:
- Aplicar `useMemo` em columns array
- Aplicar `useCallback` em handlers pesados
- Extrair view modes para componentes se simples (opcional)

**Arquivos Modificados**:
- `v2/frontend/src/pages/DATModule/AcoesPage.jsx`

---

#### §4. Frontend: Deduplicar Modal.confirm em PreAgendaPage.jsx

**Arquivo**: `v2/frontend/src/pages/PreAgenda/PreAgendaPage.jsx` (~939 linhas)

**Problema**: Modal.confirm + guardas Google OAuth duplicados (~150 linhas duplicadas).

**Solução**:
- Criar hook `useGoogleGuard` para verificação OAuth
- Criar helper `confirmWithGoogleCheck` para modais com verificação
- Manter useMemo existente nas colunas

**Arquivos Criados**:
- `v2/frontend/src/hooks/useGoogleGuard.js`

**Arquivos Modificados**:
- `v2/frontend/src/pages/PreAgenda/PreAgendaPage.jsx`

---

#### §5. Backend: Modularizar etl_upsert_acompanhamento.py

**Arquivo**: `v2/backend/apps/dat_ingest/management/commands/etl_upsert_acompanhamento.py` (~798 linhas)

**Problema**: ETL monolítico sem separação de responsabilidades.

**Solução**:
- Criar `dat_ingest/etl/parsers/acompanhamento_parser.py`
- Criar `dat_ingest/etl/normalizers/acompanhamento_normalizer.py`
- Criar `dat_ingest/etl/importers/acompanhamento_importer.py`
- Command apenas orquestra

**Arquivos Criados**:
- `v2/backend/apps/dat_ingest/etl/__init__.py`
- `v2/backend/apps/dat_ingest/etl/parsers/__init__.py`
- `v2/backend/apps/dat_ingest/etl/parsers/acompanhamento_parser.py`
- `v2/backend/apps/dat_ingest/etl/normalizers/__init__.py`
- `v2/backend/apps/dat_ingest/etl/normalizers/acompanhamento_normalizer.py`
- `v2/backend/apps/dat_ingest/etl/importers/__init__.py`
- `v2/backend/apps/dat_ingest/etl/importers/acompanhamento_importer.py`

**Arquivos Modificados**:
- `v2/backend/apps/dat_ingest/management/commands/etl_upsert_acompanhamento.py`

---

#### §6. Backend: Separar ViewSets em dat_module.py

**Arquivo**: `v2/backend/apps/core/views/dat_module.py` (~747 linhas)

**Problema**: Múltiplos ViewSets misturados (DATRegistro, DATAcao, DATCompra, etc.).

**Solução**:
- Criar `views/dat_module/` diretório
- Separar: `dat_registros.py`, `dat_acoes.py`, `dat_compras.py`, `dat_plano_formacoes.py`
- `views/dat_module/__init__.py` re-exporta para manter imports

**Arquivos Criados**:
- `v2/backend/apps/core/views/dat_module/__init__.py`
- `v2/backend/apps/core/views/dat_module/dat_registros.py`
- `v2/backend/apps/core/views/dat_module/dat_acoes.py`
- `v2/backend/apps/core/views/dat_module/dat_compras.py`
- `v2/backend/apps/core/views/dat_module/dat_plano_formacoes.py`

**Arquivos Removidos**:
- `v2/backend/apps/core/views/dat_module.py` (substituído pelo diretório)

---

#### §7. Backend: Separar Responsabilidades em google_oauth.py

**Arquivo**: `v2/backend/apps/core/services/google_oauth.py` (~671 linhas)

**Problema**: OAuth + encryption/token management misturados.

**Solução**:
- Criar `services/oauth/` diretório
- Separar: `token_manager.py` (criptografia, refresh, storage)
- Separar: `oauth_flow.py` (authorization URL, callback handling)
- `google_oauth.py` importa e re-exporta para compatibilidade

**Arquivos Criados**:
- `v2/backend/apps/core/services/oauth/__init__.py`
- `v2/backend/apps/core/services/oauth/token_manager.py`
- `v2/backend/apps/core/services/oauth/oauth_flow.py`

**Arquivos Modificados**:
- `v2/backend/apps/core/services/google_oauth.py` (delega para módulos)

---

#### §8. Backend: Mover Lógica de Negócio de tasks.py

**Arquivo**: `v2/backend/apps/core/tasks.py` (~594 linhas)

**Problema**: Celery tasks com lógica de negócio inline.

**Solução**:
- Mover lógica para services existentes ou novos
- Tasks apenas orquestram (chamam service, tratam retry)
- Usar services de §1 e §7 onde aplicável

**Arquivos Modificados**:
- `v2/backend/apps/core/tasks.py`

---

#### §9. Backend: Fatiar views_metrics.py

**Arquivo**: `v2/backend/apps/core/views_metrics.py` (~592 linhas)

**Problema**: Múltiplos endpoints e aggregations inline.

**Solução**:
- Criar `views/metrics/` diretório
- Separar por domínio: `solicitacao_metrics.py`, `formador_metrics.py`, `dashboard_metrics.py`
- Mover lógica de aggregation para services se complexa

**Arquivos Criados**:
- `v2/backend/apps/core/views/metrics/__init__.py`
- `v2/backend/apps/core/views/metrics/solicitacao_metrics.py`
- `v2/backend/apps/core/views/metrics/formador_metrics.py`
- `v2/backend/apps/core/views/metrics/dashboard_metrics.py`

**Arquivos Removidos**:
- `v2/backend/apps/core/views_metrics.py` (substituído pelo diretório)

---

### 🟡 MÉDIA PRIORIDADE (10-15)

#### §10. Backend: Dividir serializers/dat_module.py

**Arquivo**: `v2/backend/apps/core/serializers/dat_module.py` (~558 linhas)

**Problema**: 16+ serializers em um arquivo.

**Solução** (implementada):
- Criar `serializers/dat_module/` diretório
- Separar por modelo: `dat_area.py`, `dat_coordenador.py`, `dat_acao.py`, `dat_compra.py`, `dat_cadastro.py`, `dat_formacao.py`
- `__init__.py` re-exporta para manter imports
- `dat_module.py` mantido como thin wrapper para backward compatibility

**Arquivos Criados**:
- `v2/backend/apps/core/serializers/dat_module/__init__.py`
- `v2/backend/apps/core/serializers/dat_module/dat_area.py`
- `v2/backend/apps/core/serializers/dat_module/dat_coordenador.py`
- `v2/backend/apps/core/serializers/dat_module/dat_acao.py`
- `v2/backend/apps/core/serializers/dat_module/dat_compra.py`
- `v2/backend/apps/core/serializers/dat_module/dat_cadastro.py`
- `v2/backend/apps/core/serializers/dat_module/dat_formacao.py`

**Arquivos Modificados**:
- `v2/backend/apps/core/serializers/dat_module.py` (thin re-export wrapper)

---

#### §11. Backend: Criar Mixin/Factory para Permissões

**Problema**: IsControleOrSuper e similares repetidos 73x com padrão idêntico.

**Solução**:
- Criar `permissions/base.py` com `GroupPermissionMixin`
- Criar factory `create_group_permission(groups: list[str])`
- Aplicar onde trivial (não alterar permissões existentes, só refatorar)

**Arquivos Criados**:
- `v2/backend/apps/core/permissions/base.py`

**Arquivos Modificados**:
- `v2/backend/apps/core/permissions.py` (usa base)

---

#### §12. Backend: Padronizar Error Handling

**Problema**: Mistura de `Response()` direto e `ValidationAPIError` para erros.

**Solução**:
- Usar `ValidationAPIError` (já existe) em vez de `Response({"detail": ...}, status=400)`
- Não mudar respostas de sucesso
- Foco em views_metrics.py e outros com Response direto para erros

**Arquivos Modificados**:
- `v2/backend/apps/core/views_metrics.py` (se ainda existir após §9)
- Outros views com Response direto para erros

---

#### §13. Backend: Corrigir N+1 em availability_service.py

**Arquivo**: `v2/backend/apps/core/services/availability_service.py`

**Problema**: Loops sem `select_related`/`prefetch_related` onde acessa FKs.

**Solução**:
- Adicionar `select_related('usuario', 'municipio')` onde aplicável
- NÃO alterar monthly_grid_service.py ou views_gcal/batch.py (já otimizados)
- NÃO alterar loaders.py (só parseia Excel)

**Arquivos Modificados**:
- `v2/backend/apps/core/services/availability_service.py`

---

#### §14. Frontend: Extrair Inline Styles Repetidos

**Problema**: 434 inline styles, muitos repetidos.

**Solução**:
- Criar `constants/styles.js` para estilos repetidos
- Aplicar onde há repetição clara
- Não mudar UI visualmente

**Arquivos Criados**:
- `v2/frontend/src/constants/styles.js`

**Arquivos Modificados**:
- Páginas com inline styles repetidos

---

#### §15. Frontend: Deduplicar Modal/OAuth Guard (Referência §4)

**Nota**: Este item é coberto por §4 (PreAgendaPage.jsx). O hook `useGoogleGuard` criado em §4 pode ser reutilizado em outras páginas se necessário.

---

### 🟢 BAIXA PRIORIDADE (16-18)

#### §16. Frontend: Otimização Leve em Outros Arquivos Longos

**Arquivos**:
- `Dashboards/GCalDashboardPage.jsx` (~896 linhas)
- `DATModule/ComprasPage.jsx` (~890 linhas)
- `DATModule/PlanoFormacoesPage.jsx` (~861 linhas)
- `MapaBrasil/MapaBrasilPage.jsx` (~860 linhas)
- `DATModule/FormacoesPage.jsx` (~803 linhas)
- `App.jsx` (~663 linhas)

**Solução**:
- Aplicar `useMemo`/`useCallback` onde cabível
- Fatiamento leve se simples
- Sem regressão de funcionalidade

---

#### §17. Frontend: Manter Padrões de Memoização Existentes

**Nota**: Garantir que refatorações não removam `useMemo`/`useCallback` existentes (ex: PreAgendaPage columns).

---

#### §18. Backend: Garantir Não-Regressão de Autorização

**Nota**: Em todos os refactors de permissão, garantir que:
- Testes de permissão existentes passem
- Comportamento de autorização não mude
- Rodar `pytest apps/core/tests/test_approval_policy_PA.py -v` após mudanças

---

### Verificação

```bash
# Backend
cd v2/backend
pytest apps/ -q --tb=short
pyright apps/core apps/dat_ingest

# Frontend
cd v2/frontend
npm run build
npm run lint

# Docker rebuild
cd v2
COMPOSE_PROJECT_NAME=aprender_v2 docker compose -f infra/docker-compose.yml up -d --build
```

---

### Issues Derivadas

| Issue | Seção | Prioridade | Descrição |
|-------|-------|------------|-----------|
| #459 | Epic | 📋 EPIC | Epic: Refatoração de Código - Plano Mestre |
| #460 | §1 | 🔴 HIGH | Extrair services de views_solicitacao.py |
| #461 | §2 | 🔴 HIGH | Refatorar CoordenadoresPage.jsx |
| #462 | §3 | 🔴 HIGH | Otimizar AcoesPage.jsx |
| #463 | §4 | 🔴 HIGH | Deduplicar Modal.confirm em PreAgendaPage.jsx |
| #464 | §5 | 🔴 HIGH | Modularizar etl_upsert_acompanhamento.py |
| #465 | §6 | 🔴 HIGH | Separar ViewSets em dat_module.py |
| #466 | §7 | 🔴 HIGH | Separar responsabilidades em google_oauth.py |
| #467 | §8 | 🔴 HIGH | Mover lógica de negócio de tasks.py |
| #468 | §9 | 🔴 HIGH | Fatiar views_metrics.py |
| #469 | §10 | 🟡 MEDIUM | Dividir serializers/dat_module.py |
| #470 | §11 | 🟡 MEDIUM | Criar mixin/factory para permissões |
| #471 | §12 | 🟡 MEDIUM | Padronizar error handling |
| #472 | §13 | 🟡 MEDIUM | Corrigir N+1 em availability_service.py |
| #473 | §14 | 🟡 MEDIUM | Extrair inline styles repetidos |
| #474 | §16-18 | 🟢 LOW | Otimização leve e garantia de não-regressão |
