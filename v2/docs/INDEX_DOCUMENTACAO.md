# 📚 Índice da Documentação - AS v2

**Última Atualização**: 2025-12-01

---

## 🎯 Guias Principais

### 1. 🔐 **RBAC e Controle de Acesso**
**Arquivo**: [`RBAC_COMPLETO.md`](./RBAC_COMPLETO.md)

**Quando usar**: Entender grupos, permissões, páginas acessíveis, flags especiais.

**Conteúdo**:
- 6 grupos do sistema (Superintendência, Gerência, Controle, DAT, Coordenador, Formador)
- Estatísticas atualizadas (128 usuários)
- Permissões Django granulares
- Páginas acessíveis por perfil
- HomePage cards por perfil
- Vulnerabilidades identificadas
- FAQ completo

**Atualizado em**: 2025-12-01

---

### 2. 🏢 **Estrutura Organizacional**
**Arquivo**: [`MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md`](./MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md)

**Quando usar**: Entender hierarquia Gerências → Setores → Projetos → Pessoas.

**Conteúdo**:
- 8 Gerências (SUPERINTENDENCIA, GERENCIA 2-6, GINDIVIDUAL)
- 10 Setores (Super, Vidas, Fluir, ACerta, Brincando, etc.)
- 46 Projetos (31 únicos + variantes)
- Mapeamento de pessoas por cargo
- GAPs e inconsistências

**Atualizado em**: 2025-12-01 (estatísticas)
**Criado em**: 2025-11-14

---

### 3. 📄 **Arquitetura Geral do Projeto**
**Arquivo**: [`PROJETO_ORIGEM.md`](./PROJETO_ORIGEM.md)

**Quando usar**: Entender origem, stack, modelos principais, RFs.

**Conteúdo**:
- Lógica das planilhas originais
- Códigos de disponibilidade (E/M/D/P/T/X)
- Stack tecnológica (Django + React)
- Modelos principais
- Funcionalidades atuais
- RFs (RF01-RF08)

---

### 4. 👥 **Hierarquia Organizacional (Guia de Uso)**
**Arquivo**: [`GUIA_HIERARQUIA_ORGANIZACIONAL.md`](./GUIA_HIERARQUIA_ORGANIZACIONAL.md)

**Quando usar**: Usar modelo EquipeGerencia, configurar Apoio de Coordenação, gerenciar hierarquia.

**Conteúdo**:
- Como usar modelo EquipeGerencia (Gerente → Coordenador → Apoio → Formador)
- Configurar grupo "Apoio de Coordenação"
- Gerências Individuais (múltiplos grupos)
- Comandos úteis e troubleshooting

**Criado em**: 2025-12-01 ✨ NOVO

---

## 📑 Documentação Técnica

### 🗓️ **Google Calendar Integration**
**Arquivo**: [`GUIDE_GCAL.md`](./GUIDE_GCAL.md)

- RF05/RF06 completo
- Service Account vs OAuth
- Dry-run/apply
- Fake vs Google client

---

### ✅ **Política de Aprovação Manual**
**Arquivo**: [`IMPLEMENTACAO_PA.md`](./IMPLEMENTACAO_PA.md)

- PA-01 a PA-07
- Fluxo SUPER vs NAO_SUPER
- Implementação técnica

---

### 🔄 **Operações de Backup**
**Arquivo**: [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md)

- Backup PostgreSQL
- Restore procedures
- Disaster recovery

---

### 🚀 **Go Live Checklist**
**Arquivo**: [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md)

- Preparação para produção
- Validações obrigatórias
- Smoke tests

---

## 🗂️ Documentação de Planejamento e Implementações

### 🏢 **Hierarquia Organizacional (Proposta e Implementação)**
**Arquivo**: [`PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md`](./PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md)

**Status**: ✅ IMPLEMENTADO (2025-12-01)

**Conteúdo**:
- Análise de estrutura organizacional real da empresa
- Problemas identificados (projetos sem gerência, papel Apoio faltando)
- Decisões tomadas (baseadas em feedback do usuário)
- Implementação completa:
  - Modelo EquipeGerencia
  - Grupo "Apoio de Coordenação" (5 permissões)
  - Correção de projetos (ACerta → GERENCIA 4, Cataventos → SUPER)
  - Frontend RBAC atualizado
- Situação final: 7 gerências, 32 projetos, 7 grupos Django

**Relacionado**: Veja [`GUIA_HIERARQUIA_ORGANIZACIONAL.md`](./GUIA_HIERARQUIA_ORGANIZACIONAL.md) para uso prático.

---

### 📊 **Mapeamento de Projetos**
**Arquivo**: [`MAPEAMENTO_PROJETOS_PLANILHA.md`](./MAPEAMENTO_PROJETOS_PLANILHA.md)

- Projetos da planilha original
- Fluxos SUPER vs NAO_SUPER

---

### 📈 **Análise de Escalabilidade**
**Arquivo**: [`ANALISE_ESCALABILIDADE.md`](./ANALISE_ESCALABILIDADE.md)

- Performance e custos
- Otimizações futuras

---

### 🏗️ **Blueprint do Sistema**
**Arquivo**: [`BLUEPRINT.md`](./BLUEPRINT.md)

- Arquitetura de alto nível
- Decisões técnicas

---

## 🛠️ Documentação de Desenvolvimento

### 🪝 **Dev Hooks**
**Arquivo**: [`DEV_HOOKS.md`](./DEV_HOOKS.md)

- Hooks de desenvolvimento
- Automações locais

---

### 🔧 **Variáveis de Ambiente ETL**
**Arquivo**: [`ENV_VARS_ETL.md`](./ENV_VARS_ETL.md)

- Configuração de ETLs
- Variáveis obrigatórias

---

### 🐛 **Correções de Dados**
**Arquivo**: [`DATA_FIXES.md`](./DATA_FIXES.md)

- Scripts de correção
- Histórico de fixes

---

## 📦 Backlog

### 🗺️ **Mapa do Brasil**
**Arquivo**: [`BACKLOG_MAPA_BRASIL.md`](./BACKLOG_MAPA_BRASIL.md)

- Funcionalidades planejadas
- Issue #208

---

### 📦 **Code Splitting (Frontend)**
**Arquivo**: [`BACKLOG_FRONTEND_CODE_SPLITTING.md`](./BACKLOG_FRONTEND_CODE_SPLITTING.md)

- Otimizações de bundle
- Lazy loading

---

## 🤖 Agentes e Automações

### 🤖 **Agents**
**Arquivo**: [`AGENTS.md`](./AGENTS.md)

- Configuração de agents
- Workflows automatizados

---

## 🗂️ Arquivo (Memória)

Documentos históricos em [`memoria/`](./memoria/):
- Relatórios de sessões passadas
- Análises completas
- Planos de correção
- Boilerplates

---

## 🔗 Referências Cruzadas

| Se você quer... | Consulte... |
|-----------------|-------------|
| **Saber quais páginas cada grupo pode acessar** | [`RBAC_COMPLETO.md`](./RBAC_COMPLETO.md) |
| **Entender a hierarquia Gerências/Setores/Projetos** | [`MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md`](./MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md) |
| **Ver permissões Django granulares** | [`RBAC_COMPLETO.md`](./RBAC_COMPLETO.md) (seção 5) |
| **Entender RFs e regras de disponibilidade** | [`PROJETO_ORIGEM.md`](./PROJETO_ORIGEM.md) |
| **Configurar Google Calendar** | [`GUIDE_GCAL.md`](./GUIDE_GCAL.md) |
| **Entender fluxo de aprovação** | [`IMPLEMENTACAO_PA.md`](./IMPLEMENTACAO_PA.md) |
| **Preparar deploy** | [`GO_LIVE_CHECKLIST.md`](./GO_LIVE_CHECKLIST.md) |
| **Configurar hierarquia organizacional** | [`GUIA_HIERARQUIA_ORGANIZACIONAL.md`](./GUIA_HIERARQUIA_ORGANIZACIONAL.md) ✨ NOVO |
| **Entender decisões de hierarquia** | [`PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md`](./PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md) ✨ NOVO |
| **Usar modelo EquipeGerencia** | [`GUIA_HIERARQUIA_ORGANIZACIONAL.md`](./GUIA_HIERARQUIA_ORGANIZACIONAL.md) (seção 2) ✨ NOVO |
| **Configurar grupo "Apoio de Coordenação"** | [`GUIA_HIERARQUIA_ORGANIZACIONAL.md`](./GUIA_HIERARQUIA_ORGANIZACIONAL.md) (seção 3) ✨ NOVO |

---

## 📊 Estatísticas de Documentação

**Total de documentos**: 22+ arquivos
**Última atualização global**: 2025-12-01
**Documentos atualizados hoje**: 5
- RBAC_COMPLETO.md (criado)
- MAPEAMENTO_COMPLETO_SETORES_GERENCIAS.md (atualizado)
- INDEX_DOCUMENTACAO.md (criado e atualizado)
- PROPOSTA_HIERARQUIA_ORGANIZACIONAL.md (criado e implementado) ✨
- GUIA_HIERARQUIA_ORGANIZACIONAL.md (criado) ✨

**Implementações concluídas hoje**: 1
- ✅ Hierarquia Organizacional Completa (modelo EquipeGerencia + grupo Apoio de Coordenação)

---

**Gerado em**: 2025-12-01
**Última atualização**: 2025-12-01 18:50 BRT
**Mantido por**: Claude Code + Equipe AS v2
