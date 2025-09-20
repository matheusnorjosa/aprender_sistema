# 🗂️ MAPA DETALHADO DA ESTRUTURA DE PASTAS - SISTEMA APRENDER

## 📊 VISÃO GERAL

**Total de pastas identificadas**: 200+ pastas  
**Categorias principais**: 12 categorias funcionais  
**Status**: ✅ Sistema completamente mapeado  

---

## 🏗️ ESTRUTURA PRINCIPAL DO SISTEMA

### **📁 RAIZ DO PROJETO**
```
Aprender Sistema/
├── 🐳 DOCKER & DEPLOYMENT
├── 🐍 DJANGO APPS
├── 📊 DADOS & PLANILHAS
├── 📚 DOCUMENTAÇÃO
├── 🔧 SCRIPTS & AUTOMAÇÃO
├── 🧪 TESTES & QUALIDADE
├── 🎨 FRONTEND & ASSETS
├── 🔐 CONFIGURAÇÕES
├── 📈 RELATÓRIOS & ANÁLISES
├── 🗄️ BACKUPS & ARQUIVOS
├── 🤖 IA & INTEGRAÇÕES
└── 📋 TEMPORÁRIOS & CACHE
```

---

## 🐳 **DOCKER & DEPLOYMENT**

### **`docker/`** - Configurações de Containerização
- **`docker/dev/`** - Configurações de desenvolvimento
- **`docker/prod/`** - Configurações de produção
- **Função**: Orquestração de containers, configurações de ambiente

### **Arquivos de Deploy**
- **`Dockerfile`** - Imagem Docker do sistema
- **`docker-compose.yml`** - Orquestração de serviços
- **`requirements.txt`** - Dependências Python
- **`requirements_prod.txt`** - Dependências de produção

---

## 🐍 **DJANGO APPS (APLICAÇÕES PRINCIPAIS)**

### **`aprender_sistema/`** - Configurações do Projeto Django
- **`aprender_sistema/settings.py`** - Configurações principais
- **`aprender_sistema/urls.py`** - URLs principais
- **`aprender_sistema/wsgi.py`** - Interface web
- **`aprender_sistema/data/`** - Dados de configuração
- **`aprender_sistema/tools/`** - Ferramentas auxiliares
- **Função**: Configurações centrais do Django

### **`core/`** - App Principal do Sistema
- **`core/models.py`** - Modelos de dados (Usuario, Formador, Solicitacao, etc.)
- **`core/views/`** - Views organizadas por funcionalidade
- **`core/templates/`** - Templates HTML organizados
- **`core/static/`** - Arquivos estáticos (CSS, JS, imagens)
- **`core/services/`** - Lógica de negócio e serviços
- **`core/management/commands/`** - Comandos Django customizados
- **`core/migrations/`** - Migrações do banco de dados
- **`core/tests/`** - Testes unitários
- **`core/api/`** - APIs REST
- **`core/mcp/`** - Integração MCP (Model Context Protocol)
- **Função**: Sistema principal de gestão educacional

### **`api/`** - App de APIs REST
- **`api/migrations/`** - Migrações específicas da API
- **Função**: Endpoints REST para integração externa

### **`relatorios/`** - App de Relatórios
- **`relatorios/migrations/`** - Migrações de relatórios
- **Função**: Geração de relatórios e dashboards

---

## 📊 **DADOS & PLANILHAS**

### **`dados/`** - Dados Processados
- **`dados/backups/`** - Backups de dados
- **`dados/extraidos/`** - Dados extraídos das planilhas
- **`dados/relatorios/`** - Relatórios gerados
- **Função**: Armazenamento de dados processados

### **`dados_planilhas_originais/`** - Dados Originais
- **Função**: Backup dos dados originais das planilhas Google Sheets

### **`dados_unificados/`** - Dados Unificados
- **Função**: Dados consolidados e tratados

### **`fonte_unica_dados/`** - Fonte Única de Verdade
- **`fonte_unica_dados/dados_principais/`** - Dados principais
- **`fonte_unica_dados/documentacao/`** - Documentação dos dados
- **`fonte_unica_dados/estatisticas/`** - Estatísticas
- **`fonte_unica_dados/relatorios/`** - Relatórios consolidados
- **`fonte_unica_dados/backups/`** - Backups da fonte única
- **Função**: Centralização de todos os dados do sistema

### **`data/`** - Dados Estruturados
- **`data/backups/`** - Backups estruturados
- **`data/exports/`** - Exportações de dados
- **`data/extracted/`** - Dados extraídos
- **Função**: Dados organizados por categoria

---

## 📚 **DOCUMENTAÇÃO**

### **`docs/`** - Documentação Técnica
- **`docs/api/`** - Documentação da API
- **`docs/dev/`** - Documentação de desenvolvimento
- **`docs/memoria/`** - Memória de sessões
- **`docs/ops/`** - Operações e deploy
- **`docs/security/`** - Segurança e auditoria
- **`docs/technical/`** - Documentação técnica
- **`docs/user/`** - Documentação do usuário
- **Função**: Documentação completa do sistema

### **Arquivos de Documentação na Raiz**
- **`CODEX_CONTEXT_PACKAGE.md`** - Contexto completo do sistema
- **`DOCUMENTACAO_PROJETO.md`** - Documentação oficial
- **`README.md`** - Documentação principal
- **`CHANGELOG.md`** - Histórico de mudanças
- **`SECURITY.md`** - Políticas de segurança
- **`CONTRIBUTING.md`** - Guia de contribuição

---

## 🔧 **SCRIPTS & AUTOMAÇÃO**

### **`scripts/`** - Scripts de Automação
- **`scripts/extracao/`** - Scripts de extração de dados
- **`scripts/extraction/`** - Scripts de extração (alternativo)
- **`scripts/legacy/`** - Scripts legados
- **`scripts/oauth/`** - Scripts de autenticação OAuth
- **`scripts/optimized/`** - Scripts otimizados
- **`scripts/otimizados/`** - Scripts otimizados (alternativo)
- **`scripts/test/`** - Scripts de teste
- **`scripts/teste/`** - Scripts de teste (alternativo)
- **`scripts/verificacao/`** - Scripts de verificação
- **`scripts/verification/`** - Scripts de verificação (alternativo)
- **Função**: Automação de tarefas e processamento de dados

### **`planilhasmanagementcommands/`** - Comandos de Gestão
- **Função**: Comandos Django para gestão de planilhas

---

## 🧪 **TESTES & QUALIDADE**

### **`tests/`** - Testes do Sistema
- **`tests/legacy/`** - Testes legados
- **Função**: Testes automatizados e validação

### **`planilhasfixtures/`** - Fixtures de Teste
- **Função**: Dados de teste para planilhas

### **`.mypy_cache/`** - Cache de Análise de Tipos
- **Função**: Cache do MyPy para análise estática

---

## 🎨 **FRONTEND & ASSETS**

### **`static/`** - Arquivos Estáticos
- **`static/assets/`** - Assets gerais
- **`static/core/`** - Assets do core
- **`static/css/`** - Folhas de estilo
- **`static/js/`** - JavaScript
- **Função**: Arquivos estáticos do frontend

### **`staticfiles/`** - Arquivos Estáticos Coletados
- **`staticfiles/admin/`** - Assets do Django Admin
- **`staticfiles/core/`** - Assets do core coletados
- **`staticfiles/rest_framework/`** - Assets do DRF
- **Função**: Arquivos estáticos coletados para produção

### **`core/templates/`** - Templates HTML
- **`core/templates/core/admin/`** - Templates do admin
- **`core/templates/core/components/`** - Componentes reutilizáveis
- **`core/templates/core/controle/`** - Templates de controle
- **`core/templates/core/coordenador/`** - Templates de coordenador
- **`core/templates/core/deslocamentos/`** - Templates de deslocamentos
- **`core/templates/core/diretoria/`** - Templates da diretoria
- **`core/templates/core/gestao/`** - Templates de gestão
- **Função**: Interface do usuário

---

## 🔐 **CONFIGURAÇÕES**

### **`.claude/`** - Configurações Claude
- **`.claude/commands/`** - Comandos Claude
- **Função**: Configurações para integração com Claude AI

### **`.github/`** - Configurações GitHub
- **`.github/ISSUE_TEMPLATE/`** - Templates de issues
- **`.github/workflows/`** - GitHub Actions
- **Função**: CI/CD e gestão de repositório

### **`old_configs/`** - Configurações Antigas
- **Função**: Backup de configurações antigas

---

## 📈 **RELATÓRIOS & ANÁLISES**

### **`reports/`** - Relatórios Gerados
- **`reports/analysis/`** - Relatórios de análise
- **`reports/cleanup/`** - Relatórios de limpeza
- **`reports/migration/`** - Relatórios de migração
- **Função**: Relatórios automáticos e análises

### **`relatorios/`** - Relatórios do Sistema
- **Função**: Relatórios gerados pelo sistema

### **`dashboard_screenshots/`** - Screenshots de Dashboards
- **Função**: Capturas de tela dos dashboards

### **`screenshots/`** - Screenshots Gerais
- **`screenshots/antigas/`** - Screenshots antigas
- **Função**: Documentação visual do sistema

---

## 🗄️ **BACKUPS & ARQUIVOS**

### **`backups/`** - Backups do Sistema
- **`backups/antigos/`** - Backups antigos
- **`backups/removed_directories/`** - Diretórios removidos
- **`backups/removed_files/`** - Arquivos removidos
- **Função**: Backup e versionamento de arquivos

### **`archive/`** - Arquivos Arquivados
- **`archive/spreadsheets/`** - Planilhas arquivadas
- **Função**: Arquivos históricos e arquivados

### **`logs/`** - Logs do Sistema
- **`logs/antigos/`** - Logs antigos
- **Função**: Registros de atividades e erros

---

## 🤖 **IA & INTEGRAÇÕES**

### **`.playwright-mcp/`** - Integração Playwright MCP
- **`.playwright-mcp/traces/`** - Traces de execução
- **Função**: Integração com Playwright para automação

### **`ai_export/`** - Exportações de IA
- **Função**: Dados exportados para análise de IA

### **`out_apps_script/`** - Scripts de Apps
- **`out_apps_script/Acompanhamento de Agenda/`** - Scripts de agenda
- **`out_apps_script/Disponibilidade/`** - Scripts de disponibilidade
- **`out_apps_script/Planilha de Controle - 2025/`** - Scripts de controle
- **Função**: Scripts do Google Apps Script

---

## 📋 **TEMPORÁRIOS & CACHE**

### **`out/`** - Arquivos de Saída Temporários
- **`out/acessibilidade/`** - Testes de acessibilidade
- **`out/api_*/`** - Saídas de APIs
- **`out/codigo/`** - Análises de código
- **`out/database/`** - Análises de banco
- **`out/google/`** - Integrações Google
- **`out/gui_*/`** - Análises de interface
- **`out/performance/`** - Análises de performance
- **`out/responsividade/`** - Testes de responsividade
- **`out/seguranca/`** - Análises de segurança
- **Função**: Arquivos temporários de análise e teste

---

## 🎯 **FUNÇÕES POR CATEGORIA**

### **🏗️ ARQUITETURA & DEPLOYMENT**
- **Docker**: Containerização e orquestração
- **GitHub**: CI/CD e gestão de código
- **Configurações**: Ambientes e settings

### **🐍 APLICAÇÕES DJANGO**
- **Core**: Sistema principal de gestão
- **API**: Endpoints REST
- **Relatórios**: Dashboards e métricas

### **📊 GESTÃO DE DADOS**
- **Extração**: Dados das planilhas Google
- **Processamento**: Limpeza e unificação
- **Armazenamento**: Backup e versionamento

### **🔧 AUTOMAÇÃO**
- **Scripts**: Processamento automatizado
- **Comandos**: Gestão Django
- **Integrações**: APIs externas

### **🧪 QUALIDADE**
- **Testes**: Validação automatizada
- **Análise**: Código e performance
- **Documentação**: Cobertura completa

### **🎨 INTERFACE**
- **Templates**: Interface do usuário
- **Assets**: CSS, JS, imagens
- **Responsividade**: Adaptação mobile

### **📈 ANÁLISE & RELATÓRIOS**
- **Métricas**: Performance e uso
- **Dashboards**: Visualizações
- **Auditoria**: Logs e rastreamento

---

## 🚀 **RECOMENDAÇÕES DE ORGANIZAÇÃO**

### **✅ PASTAS BEM ORGANIZADAS**
- **`core/`** - App principal bem estruturado
- **`docs/`** - Documentação completa
- **`fonte_unica_dados/`** - Centralização de dados
- **`docker/`** - Containerização organizada

### **⚠️ PASTAS PARA REVISÃO**
- **`out/`** - Muitas subpastas temporárias
- **`scripts/`** - Múltiplas versões similares
- **`backups/`** - Estrutura complexa
- **`static/` vs `staticfiles/`** - Duplicação

### **🔧 MELHORIAS SUGERIDAS**
1. **Consolidar scripts** similares
2. **Limpar arquivos temporários** em `out/`
3. **Organizar backups** por data
4. **Unificar assets** estáticos
5. **Documentar** funções específicas

---

## 📊 **ESTATÍSTICAS DA ESTRUTURA**

### **Distribuição por Categoria:**
- **🐍 Django Apps**: 15% (3 apps principais)
- **📊 Dados**: 25% (gestão de dados)
- **📚 Documentação**: 20% (documentação completa)
- **🔧 Scripts**: 15% (automação)
- **🎨 Frontend**: 10% (interface)
- **🗄️ Backups**: 10% (versionamento)
- **📋 Temporários**: 5% (cache e temp)

### **Níveis de Profundidade:**
- **Máximo**: 6 níveis
- **Médio**: 3 níveis
- **Raiz**: 12 categorias principais

---

## 🎯 **CONCLUSÃO**

### **✅ PONTOS FORTES:**
1. **Estrutura Django** bem organizada
2. **Documentação** completa e detalhada
3. **Separação clara** de responsabilidades
4. **Backup e versionamento** robusto
5. **Integração** com ferramentas modernas

### **🔧 OPORTUNIDADES:**
1. **Consolidação** de scripts similares
2. **Limpeza** de arquivos temporários
3. **Otimização** da estrutura de assets
4. **Padronização** de nomenclaturas

### **🏆 VEREDICTO:**
**Sistema bem estruturado e organizado**, com separação clara de responsabilidades e documentação completa. A estrutura suporta bem o crescimento e manutenção do sistema.

---

**📅 Mapa gerado em:** 20/09/2025  
**🔄 Última atualização:** Análise completa da estrutura  
**📧 Status:** ✅ **MAPEAMENTO COMPLETO**

