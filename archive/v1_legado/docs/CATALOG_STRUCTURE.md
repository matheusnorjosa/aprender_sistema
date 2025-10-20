# 📁 CATÁLOGO DE ARQUIVOS POR CATEGORIA

**Objetivo**: Organizar arquivos por funcionalidade para commits semânticos estruturados

---

## 🏗️ **CATEGORIA 1: PROJECT SETUP & INFRASTRUCTURE**

### **Docker & Environment**
```
docker-compose.yml
Dockerfile
entrypoint.sh
init_sistema_neural.bat
init_sistema_neural.ps1
.dockerignore
.env.example (a criar)
```

### **Configuration Files**
```
aprender_sistema/settings.py
aprender_sistema/urls.py
aprender_sistema/wsgi.py
aprender_sistema/__init__.py
manage.py
requirements.txt
```

### **Development Tools**
```
.pre-commit-config.yaml
.flake8
.python-version
pytest.ini
.gitignore
.gitmessage
```

---

## 🔐 **CATEGORIA 2: AUTHENTICATION & AUTHORIZATION (RF01)**

### **Core Authentication**
```
core/backends.py                    # CPFAuthenticationBackend
core/middleware/security.py         # SecurityHeadersMiddleware, RateLimit, Audit
```

### **Models & Forms**
```
core/models.py                      # Usuario model (seções auth)
core/forms.py                       # LoginForm, UsuarioForm, ChangePasswordForm
```

### **Views & Templates**
```
core/views/base.py                  # LoginView, LogoutView
core/templates/core/login.html      # Interface de login
core/templates/base.html            # Template base com auth checks
```

### **Tests**
```
core/tests/test_authentication.py  # Testes de autenticação
core/tests/test_security_middleware.py
```

---

## 📋 **CATEGORIA 3: REQUEST MANAGEMENT (RF02)**

### **Models & Services**
```
core/models.py                      # Solicitacao, SolicitacaoStatus, FormadoresSolicitacao
core/services/data_services.py     # SolicitacaoService
core/serializers.py                # SolicitacaoSerializer
```

### **Forms & Validation**
```
core/forms.py                       # SolicitacaoForm com validações
```

### **Views & Templates**
```
core/views/coordenador_views.py     # SolicitarEventoView
core/templates/core/solicitacao_form.html
core/templates/core/solicitacao_ok.html
```

### **APIs**
```
core/views/api_health.py           # APIs de solicitações
```

---

## ⚡ **CATEGORIA 4: CONFLICT DETECTION & AVAILABILITY (RF03)**

### **Conflict Engine**
```
core/services/availability_engine.py    # Engine principal de conflitos
check_conflicts.py                       # Funções de verificação (deprecated)
```

### **Models & Data**
```
core/models.py                          # DisponibilidadeFormador, Bloqueio, Deslocamento
```

### **Real-time Views**
```
core/views/mapa_realtime_views.py       # APIs de disponibilidade em tempo real
core/views/deslocamento_views.py        # CRUD de deslocamentos
```

### **Interactive Map**
```
core/templates/core/diretoria/dashboard_working_original.html  # Mapa D3.js
static/js/dashboard.js                                        # JavaScript do mapa
static/css/dashboard.css                                      # Estilos do mapa
```

### **Tests**
```
core/tests/test_availability_engine.py  # Testes do engine de conflitos
```

---

## ✅ **CATEGORIA 5: APPROVAL WORKFLOW (RF04)**

### **Models & Services**
```
core/models.py                      # Aprovacao, LogAuditoria
core/services/notification_service.py  # Notificações
```

### **Approval Views**
```
core/views/controle_views.py        # AprovacaoViews, workflow
core/views/controle_pre_agenda_views.py  # Sistema de pré-agenda
```

### **Templates**
```
core/templates/core/controle/aprovacoes_pendentes.html
core/templates/core/controle/aprovacao_detail.html
core/templates/core/controle/pre_agenda.html
```

---

## 📅 **CATEGORIA 6: GOOGLE CALENDAR INTEGRATION (RF05)**

### **Google Services**
```
core/services/google_calendar_service.py  # GoogleCalendarService
autorizar_google_sheets.py               # OAuth2 setup
processar_codigo_oauth.py               # OAuth processing
gerar_url_oauth.py                       # OAuth URL generation
```

### **Credentials & Config**
```
credentials.json                         # Google OAuth credentials
google_oauth_token.json                  # Token storage
```

### **Views & Integration**
```
core/views/controle_views.py            # CriarEventoGoogleCalendarView
```

---

## 📊 **CATEGORIA 7: DASHBOARD & ANALYTICS (RF06)**

### **Dashboard Backend**
```
core/views/diretoria_views.py           # DiretoriaExecutiveDashboardView
core/services/dashboard_service.py      # DashboardService
core/services/data_master_service.py    # Master data service
```

### **APIs & Data**
```
core/views/diretoria_views.py           # DashboardStatsAPIView, DashboardCursosAPIView
core/views/gestao_views.py              # Gestão dashboard
core/views/formador_views.py            # Formador dashboard
```

### **Frontend**
```
core/templates/core/diretoria/dashboard_working_original.html  # Dashboard principal
core/templates/core/gestao/dashboard.html                     # Dashboard gestão
static/js/dashboard.js                                        # JavaScript avançado
static/css/dashboard.css                                      # Estilos modernos
```

---

## 🔄 **CATEGORIA 8: DATA IMPORT & MIGRATION (RF07)**

### **Import Commands**
```
core/management/commands/import_extracted_events.py      # Importador principal
core/management/commands/import_agenda_completa.py       # Google Sheets importer
core/management/commands/extract_google_sheets_master.py # Extrator master
```

### **Neural Processors**
```
neural_postgresql_importer_robust.py    # Importador neural robusto
neural_data_processor.py                # Processador de dados
neural_robust_processor.py              # Processador robusto
```

### **Data Files**
```
mapeamento_completo_google_sheets_*.json    # Dados extraídos
neural_robust_processed_*.json              # Dados processados
estrutura_planilhas_mapeada.json           # Estrutura mapeada
```

### **Utilities**
```
check_imported_data.py                   # Verificação de dados
fix_dashboard_data.py                    # Correção de dados
create_missing_services.py               # Criação de serviços
```

---

## 🎨 **CATEGORIA 9: UI/UX & FRONTEND**

### **Base Templates**
```
core/templates/base.html                 # Template base
core/templates/core/home.html            # Página inicial
```

### **Component Templates**
```
core/templates/core/bloqueio_form.html   # Formulário de bloqueios
core/templates/core/components/          # Componentes reutilizáveis
```

### **Static Assets**
```
static/css/                              # Estilos CSS
static/js/                               # JavaScript
static/images/                           # Imagens e ícones
```

---

## 🧪 **CATEGORIA 10: TESTING & QUALITY**

### **Test Files**
```
core/tests/test_availability_engine.py
core/tests/test_security_middleware.py
core/tests/__init__.py
```

### **Quality Config**
```
.pre-commit-config.yaml
.flake8
pytest.ini
```

---

## 📚 **CATEGORIA 11: DOCUMENTATION**

### **Project Documentation**
```
README.md
CHANGELOG.md
CONTRIBUTING.md
SECURITY.md
CODE_OF_CONDUCT.md (a criar)
```

### **Technical Docs**
```
ARQUITETURA_REFERENCIA.md
docs/DEPLOYMENT.md (a criar)
docs/API.md (a criar)
docs/ENVIRONMENT_UNIFICATION.md
```

### **Context & Reports**
```
CLAUDE.md
.claude/CLAUDE.md
INVENTORY_COMPLETE.md
CATALOG_STRUCTURE.md (este arquivo)
RELATORIO_*.md (múltiplos relatórios)
```

---

## 🤖 **CATEGORIA 12: CI/CD & AUTOMATION**

### **GitHub Workflows**
```
.github/workflows/ci.yml
.github/workflows/branch-protection.yml
.github/ISSUE_TEMPLATE/ (a criar)
.github/PULL_REQUEST_TEMPLATE.md (a criar)
.github/CODEOWNERS (a criar)
```

### **MCP & Automation**
```
mcp_bridge.py
.mcp.json
```

---

## 🗃️ **CATEGORIA 13: LEGACY & TEMPORARY**

### **Temporary Files**
```
temp_*.py                                # Scripts temporários
test_*.py                                # Testes temporários
backup_*.txt                             # Backups temporários
```

### **Analysis Files**
```
analisador_completo_planilhas.py
audit_*.py
investigate_*.py
fix_*.py
```

---

## 🎯 **ESTRUTURA DE COMMITS PROPOSTA**

Com base neste catálogo, os commits serão organizados assim:

1. **chore: project setup and infrastructure** (Categoria 1)
2. **feat: implement authentication and authorization system** (Categoria 2)
3. **feat: implement request management system** (Categoria 3)
4. **feat: implement conflict detection and availability engine** (Categoria 4)
5. **feat: implement approval workflow system** (Categoria 5)
6. **feat: implement google calendar integration** (Categoria 6)
7. **feat: implement dashboard and analytics** (Categoria 7)
8. **feat: implement data import and migration tools** (Categoria 8)
9. **feat: implement modern UI/UX interface** (Categoria 9)
10. **test: implement comprehensive testing suite** (Categoria 10)
11. **docs: add comprehensive project documentation** (Categoria 11)
12. **chore: implement CI/CD and automation** (Categoria 12)

Arquivos da Categoria 13 (legacy) serão excluídos do novo repositório.