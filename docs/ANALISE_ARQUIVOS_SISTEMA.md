# 📁 ANÁLISE COMPLETA DOS ARQUIVOS DO SISTEMA

## 🎯 SISTEMA PRINCIPAL (PARA DEPLOY)

### **Core Django** ✅
```
├── manage.py                    # Comando principal Django
├── aprender_sistema/            # Configurações principais
│   ├── settings.py             # Settings desenvolvimento
│   ├── settings_production.py  # Settings produção
│   ├── urls.py                 # URLs principais
│   └── wsgi.py                 # Interface web
├── core/                       # App principal do sistema
│   ├── models.py              # Modelos principais (Usuário, Formador, etc.)
│   ├── views.py               # Views do sistema
│   ├── admin.py               # Interface administrativa
│   ├── templates/             # Templates HTML
│   └── management/commands/   # Comandos de gerenciamento
├── planilhas/                  # App de planilhas/compras
│   ├── models.py              # Modelos de Compra, Produto, etc.
│   ├── views.py               # Views de planilhas
│   ├── services/              # Serviços Google Sheets
│   └── management/commands/   # Comandos de importação
├── api/                       # App de API REST
├── relatorios/                # App de relatórios
└── requirements.txt           # Dependências principais
```

### **Banco de Dados e Migrações** ✅
```
├── db.sqlite3                 # Banco de desenvolvimento
├── */migrations/             # Migrações Django (ESSENCIAL)
```

### **Configurações de Deploy** ✅
```
├── Dockerfile                 # Container Docker
├── docker-compose.yml        # Orquestração local
├── railway.json              # Config Railway
├── requirements_prod.txt     # Dependências produção
└── staticfiles/              # Arquivos estáticos (gerado)
```

---

## 🧪 ARQUIVOS DE TESTE/DESENVOLVIMENTO (PODEM SER REMOVIDOS)

### **Arquivos de Teste Individuais** ❌
```
├── test_login.py              # Teste de login específico
├── test_admin_formador_view.py # Teste de view admin
├── test_bloqueio_form.py      # Teste de formulário bloqueio  
├── test_business_flow.py      # Teste de fluxo de negócio
├── test_calendar_discovery.py # Teste de descoberta de calendário
├── test_end_to_end.py         # Teste end-to-end
├── test_formador_eventos.py   # Teste de eventos formador
├── test_formador_eventos_simple.py
├── test_formador_view_simple.py
├── test_formadores_display.py
├── test_menu_formador.py
├── test_modern_selects.py
├── test_permission_system.py
├── test_solicitacao_form.py
├── teste_menu_simulation.py
├── validate_dashboard_tests.py
└── create_groups.py          # Script de criação de grupos (temporário)
```

**❌ ESTES ARQUIVOS DEVEM SER MOVIDOS para `/tests/` ou removidos**

### **Arquivos de Documentação/Análise** ❓
```
├── DASHBOARD_TESTS.md
├── DOCUMENTACAO_PROJETO.md
├── FINAL_MIGRATION_REPORT.md
├── GRUPOS_ORGANIZACIONAIS.md
├── PERMISSION_SYSTEM_MIGRATION.md
├── RELATORIO_VARREDURA_PLANILHA_2025.md
├── SPRINT_GAPS_CRITICOS_RELATORIO.md
├── ajustes_permissoes.md
├── auditoria_*.md             # Múltiplos arquivos de auditoria
├── gap_analysis_workflow_real.md
├── checklist_*.md
├── matriz_*.csv
└── mini_commits_*.md
```

**❓ PODEM SER MANTIDOS EM `/docs/` mas não são necessários para deploy**

### **Arquivos de Extração/Scripts** ❌
```
├── extract_specific_tabs.py   # Script de extração temporário
├── manage_environments.py     # Script de ambiente
├── setup_local_settings.py   # Setup local
├── varredura_planilha.py     # Script de análise (temporário)
├── out/                      # Dados extraídos (temporário)
├── out_apps_script/          # Scripts Apps Script
└── credentials/              # Credenciais (MOVER para env vars)
```

### **Backups e Dados** ❌
```
├── backups/                   # Backups antigos (não necessário)
├── cookies.txt               # Arquivo temporário
└── static/                   # Pasta vazia
```

---

## 🚀 OPÇÕES DE DEPLOY GRATUITO RECOMENDADAS

### **1. Railway** 🎯 **MAIS RECOMENDADO**
- **Prós**: Especializado em Django, PostgreSQL grátis, CI/CD automático
- **Grátis**: $5 crédito mensal (suficiente para pequenos projetos)
- **Deploy**: Conecta direto ao GitHub
- **Banco**: PostgreSQL gratuito incluído

### **2. Render**
- **Prós**: Muito fácil de usar, PostgreSQL grátis
- **Grátis**: Web service gratuito (com limitações)
- **Deploy**: Conecta ao GitHub, deploy automático
- **Banco**: PostgreSQL gratuito separado

### **3. PythonAnywhere**
- **Prós**: Especializado em Python/Django
- **Grátis**: 1 web app gratuito (pythonanywhere.com)
- **Limitações**: Apenas bibliotecas pré-instaladas
- **Banco**: MySQL gratuito

### **4. Fly.io**
- **Prós**: Moderno, global
- **Grátis**: $5 crédito mensal
- **Deploy**: Docker-based
- **Banco**: PostgreSQL via extensões

---

## 🧹 PLANO DE LIMPEZA PARA DEPLOY

### **Ações Imediatas**
1. **Criar pasta `/tests/`** e mover todos os `test_*.py`
2. **Criar pasta `/docs/`** e mover todos os `.md`
3. **Remover pastas temporárias**: `out/`, `backups/`, `static/`
4. **Mover credenciais** para variáveis de ambiente
5. **Atualizar `.gitignore`** para ignorar arquivos temporários

### **Configurações de Produção**
1. **Configurar `settings_production.py`** com:
   - `DEBUG = False`
   - `ALLOWED_HOSTS` configurado
   - Banco PostgreSQL
   - Arquivos estáticos
2. **Criar `Procfile`** para Railway/Render
3. **Configurar variáveis de ambiente**

---

## 📊 RESUMO DO SISTEMA

### **Funcionalidades Principais** ✅
1. **Sistema de Usuários e Permissões** - Grupos organizacionais
2. **Gestão de Formadores** - Cadastro e disponibilidade  
3. **Gestão de Municípios e Projetos** - Dados mestres
4. **Sistema de Aprovações** - Workflow completo
5. **Integração Google Calendar** - Agendamento automático
6. **Sistema de Compras** - Importação de planilhas
7. **Relatórios e Dashboard** - Visão gerencial
8. **API REST** - Integração externa

### **Apps Django**
- `core` - Sistema principal (9.500+ linhas)
- `planilhas` - Gestão de compras e formações (3.200+ linhas)  
- `api` - Interface REST
- `relatorios` - Relatórios gerenciais

### **Tamanho do Sistema**
- **Total**: ~15.000 linhas de código Python
- **Templates**: 25+ arquivos HTML
- **Migrações**: 19 migrações Django
- **Comandos**: 15+ comandos de gerenciamento

---

## 🎯 RECOMENDAÇÃO FINAL

### **Para Deploy Imediato** (Railway)
```bash
# 1. Limpar repositório
mkdir tests && mv test_*.py tests/
mkdir docs && mv *.md docs/
rm -rf out/ backups/ static/

# 2. Configurar Railway
# 3. Push para GitHub
# 4. Deploy automático
```

### **Sistema Principal para Deploy**
O sistema que será colocado online é **robusto e completo**:
- Interface web moderna
- Sistema de permissões granular
- Integração com Google Workspace
- API REST documentada
- Dashboard executivo
- Relatórios automáticos

**É um sistema profissional de gestão educacional pronto para produção!**