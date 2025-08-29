# 🏗️ ESTRATÉGIA DE BRANCHING E DESENVOLVIMENTO - SISTEMA APRENDER

## 📊 ANÁLISE DO SISTEMA ATUAL

### **Arquitetura do Sistema:**
- **Django 5.x** com múltiplos apps
- **PostgreSQL** em produção, SQLite em desenvolvimento
- **Google Sheets/Calendar** integração
- **Docker** para deploy
- **15.000+ linhas** de código

### **Módulos Identificados:**

#### 🔐 **CORE** - Sistema Base
- **Responsabilidade:** Usuários, autenticação, permissões, formadores, municípios, projetos
- **Arquivos principais:** `core/models.py`, `core/views.py`, `core/forms.py`
- **Dependências:** Base do sistema, todos os outros módulos dependem dele
- **Criticidade:** **ALTA** - Mudanças afetam todo o sistema

#### 📊 **PLANILHAS** - Importação e Integração
- **Responsabilidade:** Importação Google Sheets, processamento de dados, validação
- **Arquivos principais:** `planilhas/models.py`, `planilhas/services/`, comandos de importação
- **Dependências:** CORE (usuários, municípios)
- **Tipos de importação identificados:**
  - Importação de Compras (`import_google_sheets_compras`)
  - Análise de Planilhas (`analyze_google_sheets`)
  - Migração de dados (`migrar_planilhas`)
  - Backfill de coleções (`backfill_colecoes`)

#### 📈 **RELATÓRIOS** - Dashboards e Métricas
- **Responsabilidade:** Relatórios executivos, dashboards, métricas de performance
- **Arquivos principais:** `relatorios/`, templates de dashboard
- **Dependências:** CORE, PLANILHAS
- **Criticidade:** MÉDIA

#### 🔗 **API** - Integrações Externas
- **Responsabilidade:** Endpoints REST, integrações com sistemas externos
- **Arquivos principais:** `core/api_views.py`, `core/api_urls.py`
- **Dependências:** CORE
- **Criticidade:** ALTA - Usado por integrações externas

#### 📅 **CALENDAR** - Integração Google Calendar
- **Responsabilidade:** Sincronização com Google Calendar, gestão de eventos
- **Arquivos principais:** `core/services/integrations/google_calendar.py`
- **Dependências:** CORE, Google APIs
- **Criticidade:** MÉDIA - Funcionalidade específica

#### 🎯 **CONTROLE** - Auditoria e Monitoramento
- **Responsabilidade:** Logs, auditoria, segurança, monitoramento
- **Arquivos principais:** Scattered across modules
- **Dependências:** Todos os módulos
- **Criticidade:** ALTA - Segurança e compliance

---

## 🌳 ESTRATÉGIA DE BRANCHING POR FUNCIONALIDADE

### **1. BRANCHES PRINCIPAIS**

```
main (produção estável)
├── develop (integração de features)
├── homolog (ambiente de homologação)
└── hotfix/* (correções emergenciais)
```

### **2. BRANCHES POR MÓDULO/FUNCIONALIDADE**

#### **Core System (Base)**
```
feature/core-auth-*         # Autenticação e permissões
feature/core-users-*        # Gestão de usuários
feature/core-formadores-*   # Gestão de formadores
feature/core-municipios-*   # Gestão de municípios
feature/core-projetos-*     # Gestão de projetos
```

#### **Planilhas e Importação**
```
feature/planilhas-import-*     # Novos tipos de importação
feature/planilhas-compras-*    # Melhorias importação compras
feature/planilhas-validation-* # Validações e qualidade de dados
feature/planilhas-sheets-*     # Integração Google Sheets
```

#### **Relatórios e Dashboards**
```
feature/relatorios-dashboard-* # Novos dashboards
feature/relatorios-metrics-*   # Novas métricas
feature/relatorios-export-*    # Funcionalidades de export
```

#### **API e Integrações**
```
feature/api-endpoints-*    # Novos endpoints
feature/api-auth-*        # Autenticação API
feature/api-integration-* # Integrações externas
```

#### **Calendar e Eventos**
```
feature/calendar-sync-*    # Sincronização
feature/calendar-events-*  # Gestão de eventos
feature/calendar-config-*  # Configurações
```

#### **Controle e Auditoria**
```
feature/controle-logs-*      # Sistema de logs
feature/controle-audit-*     # Auditoria
feature/controle-security-*  # Melhorias de segurança
feature/controle-monitor-*   # Monitoramento
```

### **3. BRANCHES ESPECIALIZADAS**

#### **Correções (Bugs)**
```
fix/core-*        # Correções no sistema base
fix/planilhas-*   # Correções em importações
fix/relatorios-*  # Correções em relatórios
fix/api-*         # Correções na API
fix/calendar-*    # Correções no calendar
```

#### **Refatoração**
```
refactor/core-models-*      # Refatoração de models
refactor/planilhas-services-* # Refatoração de services
refactor/performance-*      # Otimizações de performance
```

#### **Segurança**
```
security/auth-*       # Melhorias de autenticação
security/permissions-* # Melhorias de permissões
security/audit-*      # Melhorias de auditoria
```

---

## 🔄 FLUXO DE DESENVOLVIMENTO

### **Para Novas Funcionalidades:**

```mermaid
main → develop → feature/[modulo]-[funcionalidade] → develop → homolog → main
```

**Exemplo Prático:**
1. `git checkout develop`
2. `git checkout -b feature/planilhas-import-cursos`
3. Desenvolvimento da importação de cursos
4. `git push origin feature/planilhas-import-cursos`
5. Pull Request para `develop`
6. Merge após code review
7. Deploy para `homolog` para testes
8. Merge para `main` após validação

### **Para Correções (Bugs):**

```mermaid
main → fix/[modulo]-[problema] → develop → homolog → main
```

**Exemplo:**
1. `git checkout main`
2. `git checkout -b fix/planilhas-import-compras-duplicatas`
3. Correção específica
4. PR direto para `develop`
5. Hotfix para `main` se crítico

### **Para Correções Emergenciais:**

```mermaid
main → hotfix/[problema-critico] → main (+ merge back to develop)
```

---

## 📋 CONVENÇÕES DE NOMENCLATURA

### **Padrão de Branches:**
- `feature/[modulo]-[funcionalidade]-[descricao-breve]`
- `fix/[modulo]-[problema-especifico]`
- `refactor/[modulo]-[area-refatorada]`
- `security/[area-security]`
- `hotfix/[problema-critico]`

### **Exemplos Reais:**
```
feature/planilhas-import-formacao-csv
feature/core-usuarios-perfil-multiplo
feature/relatorios-dashboard-executivo
fix/planilhas-compras-validacao-quantidade
fix/core-permissions-formador-evento
refactor/planilhas-services-google-sheets
security/auth-session-timeout
hotfix/api-authentication-bypass
```

### **Mensagens de Commit:**
```
[MODULO] Tipo: Descrição breve

Tipo: feat, fix, refactor, security, docs, test
Módulo: core, planilhas, relatorios, api, calendar, controle

Exemplos:
[PLANILHAS] feat: adicionar importação de cursos CSV
[CORE] fix: corrigir validação de permissões de formador
[API] security: adicionar rate limiting nos endpoints
[RELATORIOS] refactor: otimizar queries do dashboard executivo
```

---

## 🎯 VANTAGENS DESTA ESTRATÉGIA

### **✅ Para Desenvolvimento:**
- **Paralelização:** Múltiplos desenvolvedores trabalhando em módulos diferentes
- **Isolamento:** Mudanças não afetam outras funcionalidades
- **Code Review:** Focado no módulo específico
- **Testes:** Mais fácil testar funcionalidades isoladas

### **✅ Para Manutenção:**
- **Rollback Granular:** Reverter apenas a funcionalidade problemática
- **Deploy Incremental:** Subir melhorias por módulo
- **Debugging:** Facilita identificar origem de problemas
- **Documentação:** Histórico claro por funcionalidade

### **✅ Para Qualidade:**
- **Menos Conflitos:** Git merges mais simples
- **Responsabilidade Clara:** Cada branch tem um propósito específico
- **Validação:** Testes específicos por módulo
- **Rastreabilidade:** Histórico de mudanças por funcionalidade

---

## 🚀 IMPLEMENTAÇÃO PRÁTICA

### **1. Configuração Inicial (Agora):**
```bash
# Criar branches base
git checkout -b develop
git checkout -b homolog

# Push das branches
git push -u origin develop
git push -u origin homolog
```

### **2. Regras de Proteção (GitHub):**
- `main`: Requer PR + aprovação + testes passando
- `develop`: Requer PR + aprovação  
- `homolog`: Push direto para testes
- Features: Push direto durante desenvolvimento

### **3. Pipeline CI/CD:**
```yaml
# .github/workflows/ci.yml
on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [feature/*, fix/*, hotfix/*]

jobs:
  test:
    - Executar testes do módulo específico
    - Verificar código quality
    - Executar validações de segurança
```

### **4. Templates de PR:**
```markdown
## Módulo Afetado
[ ] Core [ ] Planilhas [ ] Relatórios [ ] API [ ] Calendar [ ] Controle

## Tipo de Mudança
[ ] Feature [ ] Fix [ ] Refactor [ ] Security [ ] Hotfix

## Checklist
- [ ] Testes executados
- [ ] Documentação atualizada
- [ ] Não quebra funcionalidades existentes
- [ ] Seguiu convenções do módulo
```

---

## 📚 GUIA PARA DESENVOLVEDORES

### **Iniciando uma Nova Feature:**
1. **Identifique o módulo:** Qual app Django será afetado?
2. **Crie a branch:** Seguindo convenção de nomenclatura
3. **Desenvolva isoladamente:** Foque apenas na funcionalidade
4. **Teste localmente:** Execute testes do módulo
5. **Abra PR:** Para `develop` com template preenchido

### **Corrigindo um Bug:**
1. **Identifique a origem:** Em qual módulo está o problema?
2. **Reproduza localmente:** Confirme o bug
3. **Crie branch fix:** Com descrição específica do problema
4. **Implemente correção:** Mínimo de mudanças necessárias
5. **Adicione teste:** Para evitar regressão

### **Trabalhando com Dependências:**
- **Core changes:** Coordene com toda equipe
- **API changes:** Verifique impacto em integrações
- **Model changes:** Crie migrações cuidadosamente
- **Service changes:** Mantenha compatibilidade

---

## 🎯 PRÓXIMOS PASSOS

### **Fase 1: Setup Inicial (Esta semana)**
- [x] Criar documento de estratégia
- [ ] Configurar branches `develop` e `homolog`
- [ ] Configurar regras de proteção no GitHub
- [ ] Criar templates de PR

### **Fase 2: Pipeline CI/CD (Próxima semana)**
- [ ] Configurar GitHub Actions
- [ ] Implementar testes automatizados por módulo
- [ ] Configurar deploy automático para homolog

### **Fase 3: Treinamento Equipe (Quando necessário)**
- [ ] Documentar fluxo de trabalho
- [ ] Criar guia de boas práticas
- [ ] Estabelecer code review guidelines

---

## 🔧 FERRAMENTAS DE APOIO

### **Git Aliases Úteis:**
```bash
git config alias.feature '!f(){ git checkout develop && git checkout -b feature/$1; };f'
git config alias.fix '!f(){ git checkout main && git checkout -b fix/$1; };f'
git config alias.hotfix '!f(){ git checkout main && git checkout -b hotfix/$1; };f'

# Uso:
git feature planilhas-import-cursos
git fix core-permission-bug
git hotfix api-security-issue
```

### **Scripts de Desenvolvimento:**
```bash
# scripts/new-feature.sh
#!/bin/bash
MODULE=$1
FEATURE=$2
git checkout develop
git checkout -b "feature/${MODULE}-${FEATURE}"
echo "Branch feature/${MODULE}-${FEATURE} criada!"
```

---

Essa estratégia transforma o desenvolvimento do sistema em um processo **organizado**, **escalável** e **maintível**, permitindo que múltiplos desenvolvedores trabalhem simultaneamente sem conflitos e com alto controle de qualidade.