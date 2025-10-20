# 📚 GUIAS E ESTRATÉGIAS COMPLETO - SISTEMA APRENDER

**Versão**: 2.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Guias Consolidados

---

## 📑 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Guia de Desenvolvimento Operacional](#guia-de-desenvolvimento-operacional)
3. [Guia de Usuário por Perfil](#guia-de-usuário-por-perfil)
4. [Estratégia de Branching e Desenvolvimento](#estratégia-de-branching-e-desenvolvimento)
5. [Refinamentos e Melhores Práticas](#refinamentos-e-melhores-práticas)
6. [Workflows e Processos](#workflows-e-processos)

---

## 🎯 RESUMO EXECUTIVO

Este documento consolida todos os guias de desenvolvimento, estratégias de branching, melhores práticas e workflows do Sistema Aprender.

### Status Geral: ✅ **GUIAS CONSOLIDADOS**

### Principais Características:
- ✅ **Guia operacional completo** para desenvolvimento e deploy
- ✅ **Guias por perfil de usuário** detalhados
- ✅ **Estratégia de branching** moderna e eficiente
- ✅ **Melhores práticas 2025** implementadas
- ✅ **Workflows automatizados** com CI/CD

---

## 🛠️ GUIA DE DESENVOLVIMENTO OPERACIONAL

### Visão Geral
Este guia completo fornece todas as informações necessárias para desenvolvimento, deploy, manutenção e operação do Sistema Aprender. É destinado a desenvolvedores, DevOps e administradores de sistema.

### Pré-requisitos
```bash
# Softwares necessários:
- Python 3.13+
- PostgreSQL 15+
- Docker & Docker Compose
- Git
- Node.js 18+ (opcional, para ferramentas frontend)

# Ferramentas recomendadas:
- VS Code com extensões Django/Python
- pgAdmin para PostgreSQL
- Redis Desktop Manager (opcional)
```

### Setup Inicial (Desenvolvimento)
```bash
# 1. Clonar repositório
git clone <repository-url>
cd aprender-sistema

# 2. Configurar ambiente
cp .env.example .env
# Editar .env com suas configurações

# 3. Inicializar com Docker
docker-compose up -d

# 4. Aplicar migrações
docker-compose exec web python manage.py migrate

# 5. Criar superusuário
docker-compose exec web python manage.py createsuperuser

# 6. Popular dados iniciais
docker-compose exec web python manage.py populate_data
```

### Estrutura do Projeto
```
aprender_sistema/
├── core/                    # App principal
│   ├── models.py           # Modelos Django
│   ├── views/              # Views modulares
│   ├── services/           # Camada de serviços
│   ├── management/         # Comandos Django
│   └── templates/          # Templates HTML
├── api/                    # API REST
├── planilhas/              # Integração Google Sheets
├── relatorios/             # Relatórios e dashboards
├── docker/                 # Configurações Docker
├── docs/                   # Documentação
└── scripts/                # Scripts de automação
```

### Comandos de Desenvolvimento
```bash
# Desenvolvimento diário
docker-compose up -d                    # Iniciar ambiente
docker-compose logs -f web              # Ver logs
docker-compose exec web python manage.py shell  # Shell Django

# Migrações
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Testes
docker-compose exec web python manage.py test
docker-compose exec web python manage.py test --parallel

# Linting
docker-compose exec web black .
docker-compose exec web flake8 .
docker-compose exec web isort .
```

### Deploy e Produção
```bash
# Build para produção
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d

# Verificar saúde
curl http://localhost/health/

# Logs de produção
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 👥 GUIA DE USUÁRIO POR PERFIL

### Introdução
Este guia descreve **como usar o Sistema Aprender** de acordo com seu **perfil de usuário**.

### Acesso ao Sistema
**URL de Acesso**:
- Desenvolvimento: `http://localhost:8000`
- Produção: `https://[domínio-de-produção]`

**Login**:
1. Acesse a URL do sistema
2. Clique em "Entrar" no menu superior
3. Digite seu **CPF** (11 dígitos sem pontos/traços) e **senha**
4. Clique em "Login"

### Perfil: Coordenador

#### Funcionalidades Disponíveis
- ✅ **Solicitar Evento**: Criar novas solicitações de eventos
- ✅ **Meus Eventos**: Visualizar eventos criados
- ✅ **Disponibilidade**: Ver disponibilidade de formadores
- ✅ **Relatórios**: Relatórios básicos

#### Workflow Principal
1. **Criar Solicitação**:
   - Acesse "Solicitar Evento"
   - Preencha dados do evento
   - Selecione formadores
   - Envie para aprovação

2. **Acompanhar Status**:
   - Acesse "Meus Eventos"
   - Visualize status da solicitação
   - Receba notificações de mudanças

#### Permissões
- `add_solicitacao` - Criar solicitações
- `change_solicitacao` - Editar próprias solicitações
- `view_solicitacao` - Visualizar solicitações
- `view_eventogooglecalendar` - Visualizar eventos
- `view_disponibilidadeformadores` - Visualizar disponibilidade

### Perfil: Superintendência/Gerente

#### Funcionalidades Disponíveis
- ✅ **Aprovações**: Aprovar/reprovar solicitações
- ✅ **Relatórios**: Relatórios gerenciais
- ✅ **Logs**: Visualizar logs de auditoria
- ✅ **Coordenadores**: Gerenciar coordenadores

#### Workflow Principal
1. **Aprovar Solicitações**:
   - Acesse "Aprovações Pendentes"
   - Revise detalhes da solicitação
   - Aprove ou reprove com justificativa

2. **Monitorar Sistema**:
   - Acesse "Relatórios"
   - Visualize métricas e indicadores
   - Acompanhe performance

#### Permissões
- Todas as permissões de coordenador
- `change_aprovacao` - Aprovar/reprovar solicitações
- `view_aprovacao` - Visualizar aprovações
- `view_logauditoria` - Visualizar logs
- `view_relatorios` - Visualizar relatórios

### Perfil: Controle

#### Funcionalidades Disponíveis
- ✅ **Google Calendar**: Sincronizar eventos
- ✅ **Pré-agenda**: Gerenciar agenda
- ✅ **Compras**: Gerenciar compras
- ✅ **Formações**: Acompanhar formações
- ✅ **Municípios**: Gerenciar municípios

#### Workflow Principal
1. **Sincronizar Agenda**:
   - Acesse "Controle Google Calendar"
   - Sincronize eventos aprovados
   - Gerencie conflitos de agenda

2. **Gerenciar Compras**:
   - Acesse "Compras"
   - Registre compras realizadas
   - Acompanhe entregas

#### Permissões
- Todas as permissões de superintendência
- `sync_calendar` - Sincronizar com Google Calendar
- `add_eventogooglecalendar` - Criar eventos no Google Calendar
- `change_eventogooglecalendar` - Editar eventos no Google Calendar
- `view_compra` - Visualizar compras
- `add_compra` - Criar compras
- `change_compra` - Editar compras

### Perfil: Formador

#### Funcionalidades Disponíveis
- ✅ **Meus Eventos**: Visualizar eventos atribuídos
- ✅ **Disponibilidade**: Bloquear agenda
- ✅ **Relatórios**: Relatórios de atividades

#### Workflow Principal
1. **Gerenciar Disponibilidade**:
   - Acesse "Disponibilidade"
   - Bloqueie datas indisponíveis
   - Informe motivos de bloqueio

2. **Executar Eventos**:
   - Acesse "Meus Eventos"
   - Visualize eventos atribuídos
   - Marque eventos como realizados

#### Permissões
- `view_solicitacao` - Visualizar próprias solicitações
- `view_disponibilidadeformadores` - Visualizar disponibilidade
- `add_disponibilidadeformadores` - Bloquear agenda

### Perfil: Diretoria

#### Funcionalidades Disponíveis
- ✅ **Relatórios**: Relatórios estratégicos
- ✅ **Dashboard**: Visão geral do sistema
- ✅ **Métricas**: Indicadores de performance
- ✅ **Auditoria**: Logs de auditoria

#### Workflow Principal
1. **Monitorar Sistema**:
   - Acesse "Dashboard"
   - Visualize métricas gerais
   - Acompanhe indicadores

2. **Analisar Relatórios**:
   - Acesse "Relatórios"
   - Gere relatórios estratégicos
   - Exporte dados para análise

#### Permissões
- `view_relatorios` - Visualizar relatórios
- `view_solicitacao` - Visualizar todas as solicitações
- `view_aprovacao` - Visualizar aprovações
- `view_logauditoria` - Visualizar logs
- `view_eventogooglecalendar` - Visualizar eventos

### FAQ - Perguntas Frequentes

#### Como alterar minha senha?
1. Acesse seu perfil
2. Clique em "Alterar Senha"
3. Digite senha atual e nova senha
4. Confirme a alteração

#### Como visualizar eventos passados?
1. Acesse "Meus Eventos" ou "Relatórios"
2. Use os filtros de data
3. Selecione período desejado
4. Visualize resultados

#### Como bloquear minha agenda?
1. Acesse "Disponibilidade"
2. Clique em "Bloquear Agenda"
3. Selecione datas e horários
4. Informe motivo do bloqueio
5. Salve as alterações

---

## 🏗️ ESTRATÉGIA DE BRANCHING E DESENVOLVIMENTO

### Análise do Sistema Atual

#### Arquitetura do Sistema:
- **Django 5.x** com múltiplos apps
- **PostgreSQL** em produção, SQLite em desenvolvimento
- **Google Sheets/Calendar** integração
- **Docker** para deploy
- **15.000+ linhas** de código

#### Módulos Identificados:

##### 🔐 CORE - Sistema Base
- **Responsabilidade:** Usuários, autenticação, permissões, formadores, municípios, projetos
- **Arquivos principais:** `core/models.py`, `core/views.py`, `core/forms.py`
- **Dependências:** Base do sistema, todos os outros módulos dependem dele
- **Criticidade:** **ALTA** - Mudanças afetam todo o sistema

##### 📊 PLANILHAS - Importação e Integração
- **Responsabilidade:** Importação Google Sheets, processamento de dados, validação
- **Arquivos principais:** `planilhas/models.py`, `planilhas/services/`, comandos de importação
- **Dependências:** CORE (usuários, municípios)
- **Tipos de importação identificados:**
  - Importação de Compras (`import_google_sheets_compras`)
  - Análise de Planilhas (`analyze_google_sheets`)
  - Migração de dados (`migrar_planilhas`)
  - Backfill de coleções (`backfill_colecoes`)

##### 📈 RELATÓRIOS - Dashboards e Métricas
- **Responsabilidade:** Relatórios, dashboards, visualizações
- **Arquivos principais:** `relatorios/views.py`, `relatorios/templates/`
- **Dependências:** CORE, PLANILHAS
- **Criticidade:** **MÉDIA** - Funcionalidade de apoio

##### 🔌 API - Integração Externa
- **Responsabilidade:** APIs REST, integração com sistemas externos
- **Arquivos principais:** `api/views.py`, `api/serializers.py`
- **Dependências:** CORE
- **Criticidade:** **MÉDIA** - Integração com sistemas externos

### Estratégia de Branching

#### Estrutura de Branches
```
main (produção)
├── develop (desenvolvimento)
├── feature/core-autenticacao
├── feature/planilhas-importacao
├── feature/relatorios-dashboard
├── feature/api-integracao
├── hotfix/correcao-critica
└── release/v1.2.0
```

#### Convenções de Nomenclatura
- **Feature branches**: `feature/modulo-funcionalidade`
- **Hotfix branches**: `hotfix/descricao-correcao`
- **Release branches**: `release/versao`
- **Bugfix branches**: `bugfix/descricao-bug`

#### Workflow de Desenvolvimento
1. **Criar feature branch** a partir de `develop`
2. **Desenvolver funcionalidade** com commits pequenos
3. **Criar Pull Request** para `develop`
4. **Code review** e testes
5. **Merge** após aprovação
6. **Deploy** para ambiente de teste

### CI/CD Pipeline

#### Pipeline Implementado
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.13]
        django-version: [5.2]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python manage.py test
    
    - name: Run linting
      run: |
        black --check .
        flake8 .
        isort --check-only .
```

#### Features Implementadas
- ✅ **Análise de código automática** (Black, Flake8, isort)
- ✅ **Testes por módulo** (estratégia matricial)
- ✅ **Validação de nomenclatura de branches**
- ✅ **Deploy automático para homologação**
- ✅ **Análise de segurança** (Bandit, Safety)
- ✅ **Cobertura de testes por módulo**

---

## 🏆 REFINAMENTOS E MELHORES PRÁTICAS

### Análise Comparativa

#### Nossa Estratégia Original vs Melhores Práticas 2025

| Aspecto | Nossa Implementação | Melhores Práticas | Status |
|---------|-------------------|------------------|---------|
| **Estrutura de Branches** | Git Flow híbrido | GitHub Flow + Feature Branches | ✅ EXCELENTE |
| **Nomenclatura** | `feature/modulo-funcionalidade` | `type/scope-description` | ✅ PERFEITO |
| **Organização por Módulo** | Por app Django | Por contexto de negócio | ✅ INOVADOR |
| **CI/CD** | ❌ Não tinha | Essencial em 2025 | ✅ ADICIONADO |
| **Proteção de Branches** | ❌ Manual | Automática | ✅ IMPLEMENTADO |
| **Templates** | ✅ PR template | Issues + PR templates | ✅ COMPLETO |
| **Conventional Commits** | ❌ Faltava | Padrão da indústria | ✅ ADICIONADO |

### Melhorias Implementadas

#### 1. 🤖 CI/CD Pipeline Completa
**Arquivo:** `.github/workflows/ci.yml`

**Features implementadas:**
- ✅ **Análise de código automática** (Black, Flake8, isort)
- ✅ **Testes por módulo** (estratégia matricial)
- ✅ **Validação de nomenclatura de branches**
- ✅ **Deploy automático para homologação**
- ✅ **Análise de segurança** (Bandit, Safety)
- ✅ **Cobertura de testes por módulo**

#### 2. 🔒 Proteção de Branches Automática
**Configuração:** GitHub Branch Protection Rules

**Proteções implementadas:**
- ✅ **Require pull request reviews** (2 aprovações)
- ✅ **Require status checks** (CI/CD pipeline)
- ✅ **Require up-to-date branches** (merge conflicts)
- ✅ **Restrict pushes** (apenas via PR)
- ✅ **Require linear history** (no merge commits)

#### 3. 📝 Conventional Commits
**Padrão implementado:** Conventional Commits 1.0.0

**Tipos de commit:**
- `feat:` - Nova funcionalidade
- `fix:` - Correção de bug
- `docs:` - Documentação
- `style:` - Formatação
- `refactor:` - Refatoração
- `test:` - Testes
- `chore:` - Manutenção

**Exemplos:**
```bash
feat(core): adiciona autenticação por CPF
fix(planilhas): corrige importação de dados
docs(api): atualiza documentação da API
```

#### 4. 🎯 Templates de Issues e PR
**Templates implementados:**
- ✅ **Bug Report** - Template para reportar bugs
- ✅ **Feature Request** - Template para solicitar features
- ✅ **Pull Request** - Template para PRs
- ✅ **Chore** - Template para tarefas técnicas

#### 5. 📊 Métricas e Monitoramento
**Ferramentas implementadas:**
- ✅ **Code Coverage** - Cobertura de testes
- ✅ **Code Quality** - Qualidade do código
- ✅ **Security Scanning** - Análise de segurança
- ✅ **Performance Monitoring** - Monitoramento de performance

### Estratégia de Testes

#### Testes por Módulo
```yaml
# Estratégia matricial de testes
strategy:
  matrix:
    module: [core, planilhas, relatorios, api]
    python-version: [3.13]
    django-version: [5.2]
```

#### Cobertura de Testes
- **Core**: 95% (crítico)
- **Planilhas**: 90% (importante)
- **Relatórios**: 85% (moderado)
- **API**: 90% (importante)

### Qualidade de Código

#### Ferramentas Implementadas
- **Black** - Formatação automática
- **Flake8** - Análise de estilo
- **isort** - Organização de imports
- **mypy** - Verificação de tipos
- **Bandit** - Análise de segurança
- **Safety** - Verificação de dependências

#### Configurações
```ini
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py313']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.13"
strict = true
```

---

## 🔄 WORKFLOWS E PROCESSOS

### Workflow de Desenvolvimento

#### 1. Início de Nova Feature
```bash
# 1. Atualizar develop
git checkout develop
git pull origin develop

# 2. Criar feature branch
git checkout -b feature/core-autenticacao

# 3. Desenvolver com commits pequenos
git add .
git commit -m "feat(core): adiciona validação de CPF"
```

#### 2. Pull Request
```bash
# 1. Push da feature branch
git push origin feature/core-autenticacao

# 2. Criar PR no GitHub
# 3. Aguardar code review
# 4. Corrigir feedback
# 5. Merge após aprovação
```

#### 3. Deploy
```bash
# 1. Deploy automático para homologação
# 2. Testes de aceitação
# 3. Deploy para produção
# 4. Monitoramento
```

### Processo de Code Review

#### Critérios de Aprovação
- ✅ **Funcionalidade**: Código funciona conforme especificado
- ✅ **Qualidade**: Código limpo e bem documentado
- ✅ **Testes**: Testes unitários e de integração
- ✅ **Performance**: Não degrada performance
- ✅ **Segurança**: Não introduz vulnerabilidades

#### Checklist do Reviewer
- [ ] Código segue padrões estabelecidos
- [ ] Testes cobrem funcionalidade
- [ ] Documentação atualizada
- [ ] Performance mantida
- [ ] Segurança verificada

### Processo de Deploy

#### Ambiente de Desenvolvimento
```bash
# Deploy automático via CI/CD
git push origin develop
# → Deploy automático para dev
```

#### Ambiente de Homologação
```bash
# Deploy via PR para main
git checkout main
git merge develop
git push origin main
# → Deploy automático para homologação
```

#### Ambiente de Produção
```bash
# Deploy manual após aprovação
git tag v1.2.0
git push origin v1.2.0
# → Deploy manual para produção
```

---

## 📝 CHANGELOG

### Versão 2.0.0 Unificada (30/09/2025)
- ✅ Unificação de 4 guias e estratégias
- ✅ Consolidação de workflows e processos
- ✅ Melhores práticas 2025 implementadas
- ✅ CI/CD pipeline completa

### Versão 1.0.0 (15/09/2025)
- ✅ Guias individuais criados
- ✅ Estratégias de branching definidas
- ✅ Melhores práticas identificadas

---

**📚 GUIAS E ESTRATÉGIAS COMPLETO - SISTEMA APRENDER**

*Documento unificado em: 2025-09-30*
*Status: ✅ GUIAS CONSOLIDADOS E ATUALIZADOS*
