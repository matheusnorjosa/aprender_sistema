# 📚 Índice da Documentação - AS v2

**Última Atualização**: 2026-01-13

---

## 📊 Visão Geral do Sistema

| Métrica | Valor |
|---------|-------|
| **Models** | 33 (28 core + 5 dat_ingest) |
| **API Endpoints** | 87+ |
| **Testes** | 1.707 (130 arquivos) |
| **Type Hints** | 100% (Pyright strict) |
| **Management Commands** | 38 |
| **Frontend Pages** | 45+ |
| **Documentos** | 70+ arquivos |

---

## 🎯 Guias Principais

### 1. 📋 **CLAUDE.md** (Guia Principal)

**Arquivo**: [.claude/CLAUDE.md](../../.claude/CLAUDE.md)

**Quando usar**: Ponto de entrada para qualquer trabalho no projeto.

**Conteúdo**:
- Status atual do projeto
- Ferramentas disponíveis (skills, commands, agents)
- Cláusulas Pétreas (CP-01 a CP-08)
- Arquitetura Backend/Frontend
- RBAC e permissões
- Quick reference

---

### 2. 🔐 **RBAC e Controle de Acesso**

**Arquivo**: [RBAC_COMPLETO.md](./RBAC_COMPLETO.md)

**Quando usar**: Entender grupos, permissões, páginas acessíveis.

**Conteúdo**:
- 9 setores + 4 funções
- Permissões Django granulares
- Páginas acessíveis por perfil
- Regra de aprovação SUPER

---

### 3. 🏢 **Estrutura Organizacional**

**Arquivo**: [MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md](./MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md)

**Quando usar**: Entender hierarquia Gerências → Setores → Projetos.

---

### 4. 📄 **Origem do Projeto**

**Arquivo**: [PROJETO_ORIGEM.md](./PROJETO_ORIGEM.md)

**Quando usar**: Entender contexto, RFs, stack tecnológico.

**Conteúdo**:
- Lógica das planilhas originais
- Códigos de disponibilidade (E/M/D/P/T/X)
- Stack tecnológica
- Requisitos Funcionais (RF01-RF08)

---

## 📑 Documentação Técnica

### 📡 **API Reference**

**Arquivo**: [API_REFERENCE.md](./API_REFERENCE.md)

- 87+ endpoints documentados
- 26 ViewSets
- Permissões por endpoint
- Códigos de erro e paginação

---

### 🗓️ **Google Calendar Integration**

**Arquivo**: [GUIDE_GCAL.md](./GUIDE_GCAL.md)

- RF05/RF06 completo
- Service Account vs OAuth
- Dry-run/apply workflow
- Fake vs Google client
- Meet link generation

---

### 📅 **Regras de Disponibilidade**

**Arquivo**: [GUIDE_AVAILABILITY.md](./GUIDE_AVAILABILITY.md)

- RD-01 a RD-08 completo
- Implementação em availability_service.py
- Códigos de conflito (X, T, P, D, M)
- Testes obrigatórios

---

### ✅ **Política de Aprovação**

**Arquivo**: [IMPLEMENTACAO_PA.md](./IMPLEMENTACAO_PA.md)

- PA-01 a PA-07 completo
- Fluxo SUPER vs NAO_SUPER
- Implementação técnica

---

### 📊 **SLOs e Performance**

**Arquivo**: [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md)

- Métricas de latência (p50, p95, p99)
- Targets de disponibilidade
- Alertas configurados

---

### 🔄 **Backup e Disaster Recovery**

**Arquivos**:
- [BACKUP_OPERATIONS.md](./BACKUP_OPERATIONS.md)
- [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md)
- [GUIDE_DR.md](./GUIDE_DR.md)

---

### 🚀 **Deploy e Produção**

**Arquivos**:
- [DEPLOY_CHECKLIST.md](./DEPLOY_CHECKLIST.md) - Checklist completo
- [GO_LIVE_CHECKLIST.md](./GO_LIVE_CHECKLIST.md) - Validações pré-go-live
- [SCALING.md](./SCALING.md) - Escalabilidade

---

## 🏗️ Planos de Implementação

### ✅ Concluídos

| Plano | Status | PR |
|-------|--------|-----|
| [PLAN_type_hints_100.md](./PLAN_type_hints_100.md) | ✅ Completo | #392, #394 |
| [PLAN_maturity_gaps.md](./PLAN_maturity_gaps.md) | ✅ Completo | #390 |
| [PLAN_infrastructure_scaling.md](./PLAN_infrastructure_scaling.md) | ✅ Completo | #391 |
| [PLAN_multi_sector_availability.md](./PLAN_multi_sector_availability.md) | ✅ Completo | #389 |
| [PLAN_dev_tools_app.md](./PLAN_dev_tools_app.md) | ✅ Completo | #340 |
| [PLAN_separate_dev_prod.md](./PLAN_separate_dev_prod.md) | ✅ Completo | #339 |

---

## 🛠️ Documentação de Desenvolvimento

### 📝 **Padrões de Código**

**Arquivos**:
- [TYPE_HINTS_GUIDE.md](./TYPE_HINTS_GUIDE.md) - Guia de type hints
- [PYRIGHT_SETUP.md](./PYRIGHT_SETUP.md) - Configuração Pyright
- [TESTING_POLICY.md](./TESTING_POLICY.md) - Política de testes

---

### 🔧 **Infraestrutura**

**Arquivos**:
- [LOGGING.md](./LOGGING.md) - Structured logging
- [OBSERVABILITY.md](./OBSERVABILITY.md) - Métricas e monitoramento
- [ENV_VARS_ETL.md](./ENV_VARS_ETL.md) - Variáveis de ambiente

---

### 🪝 **Dev Hooks**

**Arquivo**: [DEV_HOOKS.md](./DEV_HOOKS.md)

- Hooks de desenvolvimento
- Automações locais

---

## 📦 Módulos Específicos

### 📊 **DAT Module**

**Arquivo**: [SPEC_DAT_REGISTROS.md](./SPEC_DAT_REGISTROS.md)

- Acompanhamento de turmas
- Workflow FORMAR/AVALIAR
- CRUD e filtros

---

### 🗺️ **Mapa do Brasil**

**Arquivo**: [BACKLOG_MAPA_BRASIL.md](./BACKLOG_MAPA_BRASIL.md)

- Funcionalidades planejadas
- Integração com Leaflet

---

## 📋 Referência de Arquitetura

### Backend (33 Models)

| App | Models | Arquivos |
|-----|--------|----------|
| **core** | 28 | Usuario, Solicitacao, AvailabilityBlock, Municipio, Projeto, Gerencia, TipoEvento, Produto, Participation, Compra, Deslocamento, AcaoControle, AcaoDAT, Config, AuditLog, GoogleOAuthCredential, DATRegistro, DATArea, DATCoordenador, DATAcao, DATCompra, DATCadastro, DATFormacao, PlanoFormacoes, Formacao, Acompanhamento, Prova, ProjetoGeral |
| **dat_ingest** | 5 | ImportLog, StgUsuario, StgMunicipio, StgProjeto, StgTipoEvento |
| **dev_tools** | 0 | - |

---

### API Endpoints (87+)

| Categoria | Quantidade | Exemplos |
|-----------|------------|----------|
| **Auth** | 4 | login, logout, csrf, ping |
| **Solicitações** | 12 | CRUD, approve, reject, preview, publish |
| **Availability** | 4 | check, check-many, monthly, blocks |
| **GCal** | 15 | publish-batch, dashboard, insights |
| **DAT Module** | 18 | registros, acoes, compras, cadastros |
| **Admin** | 12 | usuarios, municipios, projetos, grupos |
| **Options** | 7 | lookups para dropdowns |
| **Metrics** | 8 | map, coordinators, quality |
| **Health** | 4 | readyz, healthz, features |

---

### Management Commands (38)

| App | Commands | Exemplos |
|-----|----------|----------|
| **core** | 4 | preagenda_to_gcal, compliance_audit, lgpd_export |
| **dat_ingest** | 21 | etl_all, etl_upsert_*, import_* |
| **dev_tools** | 15 | seed_*, backfill_*, cleanup_* |

---

### Testes (1.707)

| Categoria | Arquivos | Testes |
|-----------|----------|--------|
| **API/Views** | 23 | ~280 |
| **Services** | 25 | ~350 |
| **Models** | 1 | 3 |
| **Compliance (PA/RD)** | 11 | ~28 |
| **ETL** | 13 | ~130 |
| **OAuth/Auth** | 8 | ~70 |
| **RBAC** | 5 | ~25 |
| **GCal** | 15 | ~50 |
| **Frontend E2E** | 5 | 46 |

---

## 🔗 Referências Cruzadas

| Se você quer... | Consulte... |
|-----------------|-------------|
| Entender o projeto | [PROJETO_ORIGEM.md](./PROJETO_ORIGEM.md) |
| Saber permissões por grupo | [RBAC_COMPLETO.md](./RBAC_COMPLETO.md) |
| Configurar Google Calendar | [GUIDE_GCAL.md](./GUIDE_GCAL.md) |
| Entender regras de disponibilidade | [GUIDE_AVAILABILITY.md](./GUIDE_AVAILABILITY.md) |
| Ver fluxo de aprovação | [IMPLEMENTACAO_PA.md](./IMPLEMENTACAO_PA.md) |
| Preparar deploy | [DEPLOY_CHECKLIST.md](./DEPLOY_CHECKLIST.md) |
| Configurar hierarquia | [GUIA_HIERARQUIA_ORGANIZACIONAL.md](./GUIA_HIERARQUIA_ORGANIZACIONAL.md) |
| Ver SLOs definidos | [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md) |
| Procedimentos de DR | [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md) |

---

## 📁 Estrutura de Diretórios

```
aprender_sistema/
├── .claude/                    # Guias e ferramentas Claude
│   ├── CLAUDE.md              # Guia principal
│   ├── skills/                # Skills especializadas
│   └── hooks/                 # Git hooks
├── v2/
│   ├── backend/
│   │   ├── apps/
│   │   │   ├── core/          # App principal (28 models)
│   │   │   ├── dat_ingest/    # ETL (5 models)
│   │   │   └── dev_tools/     # Seeds (prod disabled)
│   │   └── config/            # Django settings
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── pages/         # 45+ páginas
│   │   │   ├── components/    # 19 componentes
│   │   │   └── api/           # 11 clientes
│   │   └── e2e/               # Testes Playwright
│   ├── infra/                 # Docker + configs
│   │   ├── production/        # Configs 3-VM
│   │   └── nginx/             # Nginx configs
│   └── docs/                  # 70+ documentos
└── thoughts/                  # Handoffs e ledgers
```

---

## 📊 Estatísticas

- **Total de documentos**: 70+ arquivos
- **Última atualização global**: 2026-01-13
- **Linhas de código backend**: ~65.000
- **Linhas de código frontend**: ~14.000
- **Cobertura de testes**: 85%+

---

**Mantido por**: Claude Code + Equipe AS v2
