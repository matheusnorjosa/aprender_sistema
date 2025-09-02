# Projeto: Sistema de Aprendizagem

## Contexto do Projeto
- Sistema Django para gestão de aprendizagem
- Branch atual: feature/importacoes-planilhas
- Funcionalidades recentes implementadas:
  - Importação de dados de planilhas Google
  - Comando `import_google_sheets_compras` para controle de compras
  - Comando `analyze_google_sheets` para análise de planilhas
  - Sistema de vinculação automática de cursos a projetos
  - Auditoria de segurança e importações

## Estado Atual - Janeiro 2025
- Código limpo (git status clean)
- Branch: feature/importacoes-planilhas
- Sistema de importação de planilhas de cursos implementado
- **NOVA**: Sistema de Pré-Agenda implementado completo ✅
- **NOVA**: Ambientes de desenvolvimento unificados ✅
- Sistema de permissões modernizado com Django Groups & Permissions

## Comandos Úteis do Projeto
- `python manage.py import_google_sheets_compras` - Importar dados de compras
- `python manage.py analyze_google_sheets` - Analisar planilhas Google

## ✅ SESSÃO ATUAL: Sistema de Pré-Agenda e Unificação de Ambientes (Janeiro 2025)

### 🎯 Sistema de Pré-Agenda COMPLETO:
- **Problema resolvido**: Menu pré-agenda não aparecia (era cache do navegador)
- **Status PRE_AGENDA**: Novo status adicionado ao modelo SolicitacaoStatus
- **Views implementadas**: ControlePreAgendaView, CriarEventoGoogleCalendarView, RemoverEventoPreAgendaView
- **Template criado**: `core/templates/core/controle/pre_agenda.html` com interface completa
- **URLs configuradas**: `/controle/pre-agenda/`, criar e remover eventos
- **Menu atualizado**: Link "Pré-Agenda" adicionado na seção Controle do menu lateral
- **Fluxo correto**: Solicitação → PRE_AGENDA → Controle cria manualmente → APROVADO

### 🔄 UNIFICAÇÃO DE AMBIENTES COMPLETA:
- **Descoberta**: Na verdade só havia desenvolvimento + produção (não homologação)
- **settings.py UNIFICADO**: Um arquivo único para todos os ambientes
- **Controle por variável**: ENVIRONMENT=development|staging|production
- **Arquivos antigos**: Movidos para `old_configs/` (backup)
- **Documentação**: Criado `ENVIRONMENT_UNIFICATION.md`
- **Benefício**: Simplificação até completar o sistema

### 🔍 INVESTIGAÇÃO DO SISTEMA:
- **Grupos atuais**: 6 grupos (coordenador, superintendencia, controle, formador, diretoria, admin)
- **Grupos removidos**: RH, Financeiro, Logística (migração para Django Groups & Permissions)
- **Django Admin**: Apenas 2 seções (Autenticação + Core) - apps relatorios/api vazios
- **Ambiente atual**: Desenvolvimento local (SQLite, DEBUG=True)

## Organização de Arquivos
- Arquivos de teste organizados na pasta `/tests`
- Documentação movida para `/docs`
- **NOVO**: `old_configs/` - Backup de configurações antigas

## Opções de Deploy Gratuito Analisadas
- **RENDER** (Recomendado): PostgreSQL gratuito, deploy automático, 30 dias
- **PythonAnywhere**: Gratuito permanente, limitações de CPU
- **Railway**: Não mais gratuito ($5/mês trial)
- **Fly.io**: Complexo, $5 crédito mensal

## Estratégia de Branching Implementada ✅
- **Branches principais criadas:** `main`, `develop`, `homolog`
- **Documento completo:** `docs/ESTRATEGIA_BRANCHING_DESENVOLVIMENTO.md`
- **Script de apoio:** `scripts/git-flow.py` (facilita criação de branches)
- **Template de PR:** `.github/PULL_REQUEST_TEMPLATE.md`

## Automação e Melhores Práticas Preparadas ⚙️
**Status:** Arquivos criados, aguardando commit/push para ativar

### Arquivos de Automação Criados:
- **CI/CD Pipeline:** `.github/workflows/ci.yml` (testes automáticos, análise código)
- **Proteção Branches:** `.github/workflows/branch-protection.yml` 
- **Conventional Commits:** `.gitmessage` (template configurado)
- **Code Ownership:** `CODEOWNERS` (responsabilidades definidas)
- **Issue Templates:** `.github/ISSUE_TEMPLATE/` (bug reports, features)
- **Documentação:** `docs/REFINAMENTOS_MELHORES_PRATICAS.md`

### Funcionalidades que serão ativadas após commit:
- ✅ Testes automáticos por módulo
- ✅ Análise de código (Black, Flake8, Bandit)
- ✅ Validação nomenclatura de branches  
- ✅ Deploy automático para homologação
- ✅ Proteção automática branches main/develop
- ✅ Templates estruturados para PRs e Issues

## Próximas Tarefas - Deploy Online
- [ ] Configurar deploy no Render (recomendação principal)
- [ ] Configurar variáveis de ambiente
- [ ] Realizar testes do sistema online
- [ ] Permitir acesso da equipe para testes

## Arquivos Importantes Criados/Modificados Nesta Sessão
- `core/models.py` - Status PRE_AGENDA adicionado
- `core/migrations/0015_add_pre_agenda_status.py` - Migração do novo status
- `core/views/controle_pre_agenda_views.py` - Views completas da pré-agenda
- `core/templates/core/controle/pre_agenda.html` - Interface da pré-agenda
- `core/templates/core/base.html` - Menu lateral atualizado
- `core/urls.py` - URLs da pré-agenda
- `aprender_sistema/settings.py` - Versão unificada
- `ENVIRONMENT_UNIFICATION.md` - Documentação da unificação

## Como Usar o Sistema Unificado
```bash
# Desenvolvimento (padrão)
python manage.py runserver

# Produção
ENVIRONMENT=production SECRET_KEY=xxx ALLOWED_HOSTS=xxx DB_PASSWORD=xxx python manage.py runserver

# Staging  
ENVIRONMENT=staging DB_PASSWORD=xxx python manage.py runserver
```

## Notas de Desenvolvimento
- Preferir edição de arquivos existentes ao invés de criar novos
- Sempre verificar convenções do código antes de fazer alterações
- Executar testes após mudanças significativas
- **Para ver menu pré-agenda**: Limpar cache do navegador (Ctrl+Shift+R)