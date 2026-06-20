# 📚 Índice da Documentação - AS v2

**Última Atualização**: 2026-03-09

---

## 📊 Visão Geral do Sistema

| Métrica | Valor |
|---------|-------|
| **Models** | 28 (core) |
| **API Endpoints** | 87+ |
| **Testes** | 1.707 (130 arquivos) |
| **Type Hints** | 100% (Pyright strict) |
| **Management Commands** | 38 |
| **Frontend Pages** | 45+ |
| **Documentos** | 70+ arquivos |

---

## 🎯 Guias Principais

### 0. 🔒 **Política Público x Privado**

**Arquivo**: [PUBLIC_PRIVATE_POLICY.md](./PUBLIC_PRIVATE_POLICY.md)

**Quando usar**: Antes de criar/editar docs em repositório público.

---

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
- 13 setores + 5 funções
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

### 🧾 **Relatórios e Consolidados**

**Arquivos**:
- [reports/README.md](./reports/README.md) - Índice dos relatórios técnicos
- [RELATORIO_TECNICO_ARQUITETURA_2026-03-06.md](./reports/RELATORIO_TECNICO_ARQUITETURA_2026-03-06.md)
- [BACKLOG_QUALIDADE_SISTEMA_2026-03-06.md](./reports/BACKLOG_QUALIDADE_SISTEMA_2026-03-06.md)
- [ESTIMATIVAS_PRAZOS_QUALIDADE_2026-03-06.md](./reports/ESTIMATIVAS_PRAZOS_QUALIDADE_2026-03-06.md)
- [CLASSIFICACAO_PUBLICO_PRIVADO_2026-03-09.md](./reports/CLASSIFICACAO_PUBLICO_PRIVADO_2026-03-09.md)
- [relatorio_deploy.md](./reports/relatorio_deploy.md)

---

### 🔎 **Análises Técnicas**

**Arquivos**:
- [analysis/README.md](./analysis/README.md) - Índice das análises técnicas
- [ANALISE_COMPLETA_SISTEMA.md](./_archive/analysis/ANALISE_COMPLETA_SISTEMA.md)
- [ANALISE_ESCALABILIDADE.md](./_archive/analysis/ANALISE_ESCALABILIDADE.md)

---

### 🛡️ **Hardening Cybersegurança (Execução)**

**Arquivos**:
- [plans/PLAN_cybersecurity_hardening_2026-03-09.md](./plans/PLAN_cybersecurity_hardening_2026-03-09.md)
- [issues/README.md](./issues/README.md)
- [issues/security_hardening_2026-03-09/README.md](./issues/security_hardening_2026-03-09/README.md)

---

## 🏗️ Planos de Implementação

### 🧭 Ativos (2026-03)

- [plans/README.md](./plans/README.md)
- [PLAN_API_CANONICA_DEFINITIVA_2026-03-09.md](./plans/PLAN_API_CANONICA_DEFINITIVA_2026-03-09.md)
- [PLAN_cybersecurity_hardening_2026-03-09.md](./plans/PLAN_cybersecurity_hardening_2026-03-09.md)

---

### ✅ Concluídos

| Plano | Status | PR |
|-------|--------|-----|
| [PLAN_type_hints_100.md](./_archive/plans/PLAN_type_hints_100.md) | ✅ Completo | #392, #394 |
| [PLAN_maturity_gaps.md](./_archive/plans/PLAN_maturity_gaps.md) | ✅ Completo | #390 |
| [PLAN_infrastructure_scaling.md](./_archive/plans/PLAN_infrastructure_scaling.md) | ✅ Completo | #391 |
| [PLAN_multi_sector_availability.md](./_archive/plans/PLAN_multi_sector_availability.md) | ✅ Completo | #389 |
| [PLAN_dev_tools_app.md](./_archive/plans/PLAN_dev_tools_app.md) | ✅ Completo | #340 |
| [PLAN_separate_dev_prod.md](./_archive/plans/PLAN_separate_dev_prod.md) | ✅ Completo | #339 |

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

---

### 🪝 **Dev Hooks**

**Arquivo**: [DEV_HOOKS.md](./DEV_HOOKS.md)

- Hooks de desenvolvimento
- Automações locais

---

## 📦 Módulos Específicos

### 📊 **DAT Module**

**Arquivo**: [SPEC_DAT_REGISTROS.md](./_archive/SPEC_DAT_REGISTROS.md) _(arquivado)_

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

### Backend (28 Models)

| App | Models | Arquivos |
|-----|--------|----------|
| **core** | 28 | Usuario, Solicitacao, AvailabilityBlock, Municipio, Projeto, Gerencia, TipoEvento, Produto, Participation, Compra, Deslocamento, AcaoControle, AcaoDAT, Config, AuditLog, GoogleOAuthCredential, DATRegistro, DATArea, DATCoordenador, DATAcao, DATCompra, DATCadastro, DATFormacao, PlanoFormacoes, Formacao, Acompanhamento, Prova, ProjetoGeral |
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
| Auditoria de regras hardcoded (2026-05) | [audits/PLATFORM_HARDCODED_RULES_AUDIT_2026-05.md](./audits/PLATFORM_HARDCODED_RULES_AUDIT_2026-05.md) |

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
