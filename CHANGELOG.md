# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository hygienization and professional documentation structure
- Comprehensive CONTRIBUTING.md with development guidelines
- SECURITY.md with security policies and vulnerability reporting
- Keep a Changelog format for version tracking

### Changed
- Menu navigation fixed - custom management pages instead of Django admin
- Enhanced .gitignore with security protections and cleanup patterns

### Security
- Security analysis completed - zero critical vulnerabilities found
- Enhanced .gitignore to prevent credential commits

## [1.3.0] - 2025-09-11

### Added
- **Sistema de Pré-Agenda completo**: Novo status PRE_AGENDA e interface para controle manual
- Menu "Pré-Agenda" na seção Controle do menu lateral
- Views para criação e remoção de eventos de pré-agenda
- Template `core/templates/core/controle/pre_agenda.html` com interface completa
- URLs configuradas: `/controle/pre-agenda/`, criar e remover eventos

### Changed
- **Unificação de Ambientes**: settings.py unificado com controle por variável ENVIRONMENT
- Menu lateral atualizado com melhor acessibilidade (CSS para estados hover/focus)
- Sistema de permissões modernizado com Django Groups & Permissions

### Fixed
- Menu pré-agenda não aparecia (problema de cache do navegador resolvido)
- Fluxo correto implementado: Solicitação → PRE_AGENDA → Controle → APROVADO

### Technical
- Migração 0015_add_pre_agenda_status.py aplicada
- Arquivos de configuração antiga movidos para `old_configs/` (backup)
- Documentação completa da unificação em `ENVIRONMENT_UNIFICATION.md`

## [1.2.0] - 2025-09-05

### Added
- Sistema de bloqueios de agenda para formadores
- Página de bloqueios com interface padronizada
- Template `core/templates/core/bloqueio_form.html` modernizado

### Fixed
- Erro 500 na página de bloqueios (bloco `{% block content %}` não fechado)
- Inconsistência visual da página de bloqueios (adequada ao padrão)
- Páginas de deslocamentos readicionadas ao git

### Changed
- Template bloqueios convertido para herança de `base.html`
- CSS padronizado com estilos `.modern-select` e `.select-container`
- Suporte completo a `help_text` em todos os campos

## [1.1.0] - 2025-09-05

### Added
- Sistema de estratégia de branching implementado
- Branches principais criadas: `main`, `develop`, `homolog`
- Documentação completa em `docs/ESTRATEGIA_BRANCHING_DESENVOLVIMENTO.md`
- Script de apoio `scripts/git-flow.py` para facilitar criação de branches
- Template de PR `.github/PULL_REQUEST_TEMPLATE.md`

### Added - Automação e CI/CD
- Pipeline CI/CD: `.github/workflows/ci.yml` (testes automáticos, análise código)
- Proteção de branches: `.github/workflows/branch-protection.yml`
- Conventional Commits: `.gitmessage` (template configurado)
- Code ownership: `CODEOWNERS` (responsabilidades definidas)
- Issue templates: `.github/ISSUE_TEMPLATE/` (bug reports, features)

### Changed
- Organização de arquivos: testes movidos para `/tests`, documentação para `/docs`
- Refinamentos de melhores práticas documentados

## [1.0.0] - 2025-08-15

### Added
- **Sistema de Importação de Planilhas Google**:
  - Comando `import_google_sheets_compras` para controle de compras
  - Comando `analyze_google_sheets` para análise de planilhas
  - Sistema de vinculação automática de cursos a projetos
- **Auditoria e Logs**:
  - Sistema completo de auditoria de segurança
  - Logs detalhados de importações e operações críticas
- **Docker Configuration**:
  - Sistema Docker funcionando perfeitamente
  - PostgreSQL 15 configurado e funcional
  - Container Django 5.2.4 rodando sem erros
  - Docker-compose com ambiente staging configurado

### Added - Data & Setup
- **Database Initialization**:
  - Migrations aplicadas com sucesso (migration 0009 corrigida)
  - Dados iniciais de teste criados:
    - 5 municípios (Fortaleza, Caucaia, Maracanaú, Sobral, Juazeiro do Norte)
    - 4 tipos de evento (Formação Inicial, Continuada, Workshop, Seminário)
    - 3 projetos (Alfabetização, Matemática, Ciências)
    - 3 formadores (Ana Silva, João Santos, Maria Oliveira)
  - Superuser criado: admin/admin123
  - 6 grupos Django configurados (coordenador, superintendencia, controle, formador, diretoria, admin)

### Added - Authentication & Menu
- **CPF-based Authentication System**:
  - Sistema de autenticação customizado baseado em CPF
  - CSRF configuration otimizada para desenvolvimento
  - Admin user configurado com CPF "99999999999"
- **Navigation System**:
  - Menu "Gestão" implementado com páginas personalizadas
  - Links para gestão_formadores, gestão_municipios, gestão_tipos_evento, gestão_projetos
  - Correção completa da navegação (substituindo links do Django admin)

### Fixed - System Issues
- **Container Issues Resolved**:
  - Container `aprender_web` não iniciava: MCP server desabilitado para compatibilidade Docker
  - Migration 0009 com erro: função `sync_users_to_groups` temporariamente simplificada
  - SQLite em vez de PostgreSQL: variável `ENVIRONMENT: staging` adicionada ao docker-compose.yml
- **Authentication & Navigation**:
  - CSRF token errors resolvidos com configuração adequada
  - Menu navigation corrigido - "CADASTROS" para "Gestão" com URLs corretas
  - Server startup issues resolvidos

### Technical Details
- **Environment Setup**:
  - Docker: http://localhost:8000 (PostgreSQL)
  - Local: http://localhost:8001 (SQLite) 
  - Admin: http://localhost:8000/admin (admin/admin123)
- **Known Warnings** (Expected):
  - MCP tools registration failures (MCP desabilitado para Docker)
  - Redis indisponível (usando LocMem cache como fallback)

### Changed
- Arquivos de configuração unificados para melhor manutenibilidade
- Sistema de grupos e permissões modernizado

### Security
- MCP server desabilitado em ambiente Docker por questões de segurança
- Credenciais adequadamente configuradas via variáveis de ambiente
- Sistema de auditoria implementado para rastreamento de operações

## [0.9.0] - 2025-07-20 

### Added
- Sistema base Django 5.2 + PostgreSQL 15
- Modelos principais: Usuario, Formador, Projeto, Municipio, TipoEvento
- Sistema de solicitações e aprovações
- Integração básica com Google Calendar API
- Interface de disponibilidade (mapa mensal)
- Sistema de bloqueios de agenda

### Added - Initial Features
- Home consolidando links principais
- API de disponibilidades + visualização
- Cadastro de solicitações de eventos
- Fluxo básico de aprovações
- Logs de auditoria para operações críticas

### Technical
- Estrutura base Django com app 'core'
- Migrações iniciais aplicadas
- Docker + docker-compose configurado
- Importação inicial de formadores
- Templates base criados

---

## Convenções de Versionamento

Este projeto segue [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Mudanças incompatíveis na API ou breaking changes
- **MINOR** (0.X.0): Novas funcionalidades mantendo compatibilidade
- **PATCH** (0.0.X): Correções de bugs mantendo compatibilidade

### Tipos de Mudanças

- **Added**: Novas funcionalidades
- **Changed**: Mudanças em funcionalidades existentes  
- **Deprecated**: Funcionalidades que serão removidas
- **Removed**: Funcionalidades removidas
- **Fixed**: Correções de bugs
- **Security**: Correções de vulnerabilidades

### Branch Strategy

- `main`: Produção (releases estáveis)
- `homolog`: Staging (testes finais)  
- `develop`: Development (integração contínua)
- `feature/*`: Features em desenvolvimento
- `fix/*`: Correções de bugs
- `chore/*`: Tarefas técnicas

---

<div align="center">
  <strong>📋 Sistema Aprender - Changelog</strong><br>
  <em>Registro completo de evolução do projeto</em><br>
  <small>Formato baseado em <a href="https://keepachangelog.com/">Keep a Changelog</a></small>
</div>