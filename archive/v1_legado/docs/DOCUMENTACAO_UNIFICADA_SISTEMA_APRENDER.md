# 📚 **DOCUMENTAÇÃO UNIFICADA - SISTEMA APRENDER**

**Versão:** 2.0  
**Data:** 29 de Setembro de 2025  
**Status:** Sistema em Produção  

---

## 🎯 **VISÃO GERAL**

### **O que é o Sistema Aprender?**
O **Sistema Aprender** é uma plataforma web Django que substitui planilhas manuais por um sistema automatizado de gestão de eventos educacionais. O sistema centraliza solicitações, aprovações e criação de eventos com integração Google Calendar.

### **Objetivos Principais**
- ✅ **Centralizar** gestão de eventos educacionais
- ✅ **Automatizar** fluxo de aprovações
- ✅ **Integrar** com Google Calendar
- ✅ **Controlar** disponibilidade de formadores
- ✅ **Auditar** todas as operações
- ✅ **Relatórios** executivos e operacionais

---

## 🚀 **INÍCIO RÁPIDO**

### **Pré-requisitos**
- Python 3.13+
- PostgreSQL 15+ (ou Docker)
- Git
- Node.js 18+ (opcional, para ferramentas de desenvolvimento)

### **🐳 Setup com Docker (Recomendado)**

```bash
# 1. Clone o repositório
git clone https://github.com/[USUARIO]/aprender_sistema.git
cd aprender_sistema

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Execute com Docker Compose
docker-compose up -d

# 4. Execute as migrações
docker-compose exec web python manage.py migrate

# 5. Crie um superusuário
docker-compose exec web python manage.py createsuperuser

# 6. Acesse o sistema
# http://localhost:8000 - Sistema principal
# http://localhost:8000/admin - Painel administrativo
```

### **💻 Setup Local (Desenvolvimento)**

```bash
# 1. Clone e entre no diretório
git clone https://github.com/[USUARIO]/aprender_sistema.git
cd aprender_sistema

# 2. Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 3. Instale dependências
pip install -r requirements-dev.txt

# 4. Configure ambiente
cp .env.example .env
# Edite .env com suas configurações locais

# 5. Execute migrações
python manage.py migrate

# 6. Carregue dados iniciais
python manage.py loaddata fixtures/initial_data.json

# 7. Execute o servidor
python manage.py runserver
```

---

## 🏗️ **ARQUITETURA DO SISTEMA**

### **Stack Tecnológica**

```
Frontend:
├── Django Templates + Bootstrap 5.3
├── Vanilla JavaScript + Chart.js + D3.js
├── ReactPy Components (em desenvolvimento)
└── Mapas interativos com GeoJSON

Backend:
├── Django 5.2.4 (Python 3.13)
├── Django REST Framework 3.15
├── PostgreSQL 15 (banco principal)
├── Redis (cache e sessões)
└── Celery (processamento assíncrono)

Infraestrutura:
├── Docker + Docker Compose
├── Nginx (proxy reverso)
├── Gunicorn (WSGI server)
└── WhiteNoise (arquivos estáticos)
```

### **Estrutura do Projeto**

```
aprender_sistema/
├── 🐍 Python Django Apps
│   ├── core/                 # App principal (models, views, templates)
│   ├── api/                  # API REST endpoints
│   ├── relatorios/          # Relatórios e dashboards
│   └── aprender_sistema/    # Configurações Django
├── 🐳 Docker & Deploy
│   ├── docker/              # Dockerfiles por ambiente
│   ├── docker-compose.yml   # Orquestração de containers
│   └── scripts/             # Scripts de automação
├── 📖 Documentação
│   ├── docs/                # Documentação técnica
│   └── README.md           # Este arquivo
└── 🔧 Configuração
    ├── .env.example        # Template de variáveis de ambiente
    ├── requirements*.txt   # Dependências Python
    └── pyproject.toml     # Configurações de lint/format
```

---

## 🛠️ **FLUXO DE TRABALHO - DESENVOLVIMENTO CENTRALIZADO**

### **🎯 FILOSOFIA DE TRABALHO**

**TUDO deve ser desenvolvido e testado no ambiente de desenvolvimento antes de ir para produção.**

### **📋 FLUXO ESTABELECIDO**

#### **1. 🛠️ DESENVOLVIMENTO (SEMPRE PRIMEIRO)**
- ✅ **Todas as mudanças** começam no `docker-compose.dev.yml`
- ✅ **Todos os testes** são feitos no ambiente de desenvolvimento
- ✅ **Todas as funcionalidades** são validadas no dev primeiro
- ✅ **Claude e Cursor** sempre trabalham no ambiente de desenvolvimento

#### **2. ✅ VALIDAÇÃO**
- ✅ **Usuário testa** e confirma que está funcionando
- ✅ **Usuário aprova** a implementação
- ✅ **Só então** migra para produção

#### **3. 🚀 PRODUÇÃO (APENAS APÓS APROVAÇÃO)**
- ✅ **Implementação** no `docker-compose.prod.yml`
- ✅ **Deploy** para ambiente de produção
- ✅ **Monitoramento** e validação final

### **🐳 AMBIENTE DE DESENVOLVIMENTO**

#### **Comando Padrão:**
```bash
# SEMPRE usar este comando para desenvolvimento
docker-compose -f docker-compose.dev.yml up -d
```

#### **Serviços Disponíveis:**
- 🗄️ **PostgreSQL** (porta 5432)
- 🌐 **Django Web** (porta 8000)
- ⚡ **Redis** (porta 6379)
- 🗃️ **pgAdmin** (porta 8080)
- 📧 **MailHog** (porta 8025)
- 🗄️ **Adminer** (porta 8081)

#### **Acessos de Desenvolvimento:**
- **Aplicação**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **pgAdmin**: http://localhost:8080
- **MailHog**: http://localhost:8025
- **Adminer**: http://localhost:8081

### **🔧 COMANDOS DE DESENVOLVIMENTO**

#### **Iniciar Ambiente:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

#### **Parar Ambiente:**
```bash
docker-compose -f docker-compose.dev.yml down
```

#### **Rebuild (após mudanças):**
```bash
docker-compose -f docker-compose.dev.yml up -d --build
```

#### **Ver Logs:**
```bash
docker-compose -f docker-compose.dev.yml logs -f
```

#### **Comandos Django:**
```bash
# Migrações
docker-compose -f docker-compose.dev.yml exec web python manage.py migrate

# Criar superusuário
docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser

# Shell Django
docker-compose -f docker-compose.dev.yml exec web python manage.py shell

# Comandos customizados
docker-compose -f docker-compose.dev.yml exec web python manage.py [comando]
```

#### **Acessar Container:**
```bash
docker-compose -f docker-compose.dev.yml exec web bash
```

---

## 🔐 **CONFIGURAÇÃO DE AMBIENTE**

### **Variáveis de Ambiente Essenciais**

Copie `.env.example` para `.env` e configure:

```bash
# === AMBIENTE ===
ENVIRONMENT=development  # development | staging | production
DEBUG=True
SECRET_KEY=your-secret-key-here

# === DATABASE ===
DATABASE_URL=postgresql://user:pass@localhost:5432/aprender_sistema
# OU para desenvolvimento local:
# DATABASE_URL=sqlite:///db.sqlite3

# === GOOGLE INTEGRATIONS ===
GOOGLE_CALENDAR_ID=seu-calendar-id@group.calendar.google.com
GOOGLE_CREDENTIALS_JSON='{...}'  # Service Account JSON
GOOGLE_CALENDAR_TIME_ZONE=America/Fortaleza

# === EMAIL (Opcional) ===
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True

# === SECURITY ===
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,http://localhost:8000
```

### **🔑 Configuração Google Calendar**

1. **Criar Service Account**:
   - Acesse [Google Cloud Console](https://console.cloud.google.com/)
   - Crie projeto ou selecione existente
   - Habilite Google Calendar API
   - Crie Service Account e baixe JSON

2. **Configurar Calendar**:
   ```bash
   # Copie o JSON para a variável de ambiente
   export GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'

   # Configure o ID do calendário
   export GOOGLE_CALENDAR_ID='seu-calendar@group.calendar.google.com'
   ```

3. **Testar Integração**:
   ```bash
   python manage.py shell -c "from core.services.integrations.google_calendar import GoogleCalendarService; GoogleCalendarService().test_connection()"
   ```

---

## 🔄 **FLUXO DE TRABALHO**

### **Processo de Solicitação → Aprovação → Agenda**

```mermaid
graph LR
    A[Coordenador] --> B[Solicita Evento]
    B --> C[Verificação Automática]
    C --> D{Conflitos?}
    D -->|Não| E[Superintendência]
    D -->|Sim| F[Retorna para Ajustes]
    E --> G{Aprovado?}
    G -->|Sim| H[Pré-Agenda]
    G -->|Não| I[Rejeitado]
    H --> J[Controle]
    J --> K[Google Calendar]
    K --> L[Evento Criado]
```

### **Perfis de Usuário**

| Perfil | Funcionalidades |
|--------|----------------|
| 👨‍🏫 **Formador** | Bloquear agenda, visualizar eventos |
| 👨‍💼 **Coordenador** | Solicitar eventos, acompanhar status |
| 👨‍💻 **Controle** | Pré-agenda, sincronização Calendar |
| 🏢 **Superintendência** | Aprovar/reprovar solicitações |
| 📊 **Diretoria** | Dashboards, relatórios executivos |
| ⚙️ **Admin** | Gestão completa do sistema |

---

## 📊 **MODELOS DE DADOS**

### **Estrutura Organizacional**

#### **Setor**
```python
class Setor(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    sigla = models.CharField(max_length=20, unique=True)
    vinculado_superintendencia = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
```
**Função:** Representa setores organizacionais (Superintendência, Vidas, etc.)

#### **Usuario (Customizado)**
```python
class Usuario(AbstractUser):
    cpf = models.CharField(max_length=11, unique=True)
    cargo = models.CharField(max_length=50, choices=CARGO_CHOICES)
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT)
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)
    area_especializacao = models.CharField(max_length=100)
    formador_ativo = models.BooleanField(default=False)
    coordenador_ativo = models.BooleanField(default=False)
```
**Função:** Usuário customizado com campos específicos do negócio

### **Entidades de Negócio**

#### **Municipio**
```python
class Municipio(models.Model):
    nome = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    regiao = models.CharField(max_length=50)
    ativo = models.BooleanField(default=True)
```
**Função:** Municípios onde ocorrem as formações

#### **Projeto**
```python
class Projeto(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)
    setor = models.ForeignKey(Setor, on_delete=models.PROTECT)
    codigo_produto = models.CharField(max_length=50, blank=True)
    ativo = models.BooleanField(default=True)
```
**Função:** Projetos educacionais (Super, ACerta, Vidas, etc.)

#### **TipoEvento**
```python
class TipoEvento(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)
    duracao_horas = models.PositiveIntegerField(default=8)
    ativo = models.BooleanField(default=True)
```
**Função:** Tipos de eventos/formações

### **Fluxo Principal**

#### **Solicitacao**
```python
class Solicitacao(models.Model):
    titulo_evento = models.CharField(max_length=200)
    descricao = models.TextField()
    data_evento = models.DateField()
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    municipio = models.ForeignKey(Municipio, on_delete=models.PROTECT)
    projeto = models.ForeignKey(Projeto, on_delete=models.PROTECT)
    tipo_evento = models.ForeignKey(TipoEvento, on_delete=models.PROTECT)
    solicitante = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    formadores = models.ManyToManyField(Usuario, through='FormadoresSolicitacao')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    observacoes = models.TextField(blank=True)
```
**Função:** Solicitações de eventos/formações

#### **Aprovacao**
```python
class Aprovacao(models.Model):
    solicitacao = models.OneToOneField(Solicitacao, on_delete=models.CASCADE)
    aprovador = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=APROVACAO_STATUS)
    data_aprovacao = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)
```
**Função:** Sistema de aprovações hierárquicas

#### **EventoGoogleCalendar**
```python
class EventoGoogleCalendar(models.Model):
    solicitacao = models.OneToOneField(Solicitacao, on_delete=models.CASCADE)
    event_id = models.CharField(max_length=200, unique=True)
    calendar_id = models.CharField(max_length=200)
    status_sync = models.CharField(max_length=20, choices=SYNC_STATUS)
    data_sync = models.DateTimeField(auto_now=True)
```
**Função:** Sincronização com Google Calendar

### **Controle de Disponibilidade**

#### **DisponibilidadeFormadores**
```python
class DisponibilidadeFormadores(models.Model):
    formador = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    data = models.DateField()
    periodo = models.CharField(max_length=20, choices=PERIODO_CHOICES)
    disponivel = models.BooleanField(default=True)
    observacoes = models.TextField(blank=True)
```
**Função:** Controle de disponibilidade de formadores

#### **LogAuditoria**
```python
class LogAuditoria(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    acao = models.CharField(max_length=100)
    modelo = models.CharField(max_length=50)
    objeto_id = models.CharField(max_length=50)
    dados_anteriores = models.JSONField(blank=True, null=True)
    dados_novos = models.JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
```
**Função:** Auditoria completa de todas as operações

---

## 🎨 **INTERFACES E DASHBOARDS**

### **Dashboard Executivo**
- **URL:** `/diretoria/dashboard/`
- **Funcionalidades:**
  - Mapa interativo do Brasil
  - Estatísticas em tempo real
  - Gráficos de distribuição
  - Lista de coordenadores por município

### **Dashboard de Gestão**
- **URL:** `/gestao/dashboard/`
- **Funcionalidades:**
  - CRUD de formadores
  - CRUD de municípios
  - CRUD de projetos
  - CRUD de tipos de evento

### **Sistema de Solicitações**
- **URL:** `/solicitar/`
- **Funcionalidades:**
  - Formulário de solicitação
  - Seleção de formadores
  - Verificação de conflitos
  - Histórico de solicitações

### **Sistema de Aprovações**
- **URL:** `/aprovacoes/`
- **Funcionalidades:**
  - Lista de pendências
  - Aprovação em lote
  - Histórico de aprovações
  - Filtros avançados

---

## 🔌 **APIs REST**

### **APIs do Mapa**
- **`/api/mapa/estatisticas/`** - Estatísticas gerais
- **`/api/mapa/dados/`** - Dados geográficos
- **`/api/mapa/realtime/`** - Dados em tempo real

### **APIs de Aprovação**
- **`/api/approval/pendentes/`** - Solicitações pendentes
- **`/api/approval/bulk/`** - Aprovação em lote
- **`/api/approval/conflicts/`** - Verificação de conflitos

### **APIs de Disponibilidade**
- **`/api/availability/formadores/`** - Disponibilidade de formadores
- **`/api/availability/municipios/`** - Disponibilidade por município

---

## 🧪 **TESTES**

### **Executar Testes**

```bash
# Todos os testes
python manage.py test

# Testes específicos
python manage.py test core.tests.test_models
python manage.py test core.tests.test_views

# Com coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Relatório HTML em htmlcov/
```

### **Testes E2E (Playwright)**

```bash
# Instalar Playwright
pip install playwright
playwright install

# Executar testes E2E
python -m pytest tests/e2e/ -v
```

---

## 🚀 **DEPLOY**

### **Ambientes**

| Branch | Ambiente | URL | Auto-Deploy |
|--------|----------|-----|-------------|
| `dev` | Desenvolvimento | http://localhost:8000 | ❌ Manual |
| `homolog` | Staging | https://staging.aprender.com | ✅ Auto |
| `main` | Produção | https://aprender.com | ⚠️ Manual + Review |

### **Deploy Staging (Render)**

1. **Configure secrets no GitHub**:
   ```
   RENDER_API_KEY=your-render-api-key
   DATABASE_URL=postgresql://...
   GOOGLE_CREDENTIALS_JSON={"type": "service_account"...}
   ```

2. **Push para branch `homolog`**:
   ```bash
   git push origin homolog
   # Deploy automático via GitHub Actions
   ```

### **Deploy Produção**

1. **Criar Release**:
   ```bash
   # Atualizar CHANGELOG.md
   git tag v1.2.3
   git push origin v1.2.3
   ```

2. **GitHub Actions executará**:
   - ✅ Testes completos
   - ✅ Build da imagem Docker
   - ✅ Deploy para produção
   - ✅ Migrações automáticas
   - ✅ Coleta de arquivos estáticos

---

## 🛠️ **DESENVOLVIMENTO**

### **Comandos Úteis**

```bash
# Executar servidor de desenvolvimento
make dev
# ou: python manage.py runserver

# Executar testes
make test
# ou: python manage.py test

# Lint e formatação
make lint
# ou: black . && flake8 . && isort .

# Migrações
make migrate
# ou: python manage.py makemigrations && python manage.py migrate

# Coleta de estáticos
make collectstatic
# ou: python manage.py collectstatic --noinput
```

### **Pre-commit Hooks**

```bash
# Instalar hooks
pre-commit install

# Executar manualmente
pre-commit run --all-files
```

### **Estrutura de Branches**

```
main (produção)
├── homolog (staging)
│   ├── dev (desenvolvimento)
│   │   ├── feat/nova-funcionalidade
│   │   ├── fix/correcao-bug
│   │   └── chore/atualizacao-dependencias
```

### **Convenção de Commits**

```bash
feat: adicionar sistema de notificações por email
fix: corrigir erro na validação de datas
docs: atualizar README com instruções de deploy
chore: atualizar dependências do Django para 5.2.4
test: adicionar testes para módulo de calendário
```

---

## 📊 **MONITORAMENTO**

### **Health Checks**

- 🟢 **Sistema**: http://localhost:8000/health/
- 🟢 **Database**: http://localhost:8000/health/db/
- 🟢 **Google Calendar**: http://localhost:8000/health/calendar/

### **Métricas (Produção)**

- **Performance**: Tempo de resposta < 500ms
- **Disponibilidade**: 99.9% uptime
- **Integrações**: Sync Google Calendar < 30s

---

## 🐛 **TROUBLESHOOTING**

### **Problemas Comuns**

**❌ Erro: `django.db.utils.OperationalError`**
```bash
# Verifique se PostgreSQL está rodando
docker-compose up db -d

# Execute migrações
python manage.py migrate
```

**❌ Google Calendar API Error**
```bash
# Verifique credenciais
python manage.py shell -c "import os; print(os.getenv('GOOGLE_CREDENTIALS_JSON'))"

# Teste conexão
python manage.py test_google_calendar
```

**❌ CSS/JS não carregando**
```bash
# Colete arquivos estáticos
python manage.py collectstatic

# Verifique DEBUG=True em desenvolvimento
```

### **Logs**

```bash
# Docker Compose
docker-compose logs -f web

# Local
tail -f logs/django.log

# Specific service
docker-compose logs -f db
```

---

## 🤝 **CONTRIBUIÇÃO**

Ver [CONTRIBUTING.md](./CONTRIBUTING.md) para guidelines detalhados.

### **Quick Start para Contribuição**

1. Fork o repositório
2. Crie branch: `git checkout -b feat/minha-feature`
3. Implemente com testes
4. Execute lint: `make lint`
5. Commit: `git commit -m "feat: minha nova feature"`
6. Push: `git push origin feat/minha-feature`
7. Abra Pull Request

---

## 📄 **LICENÇA**

Este projeto está licenciado sob a **MIT License** - veja [LICENSE](./LICENSE) para detalhes.

---

## 🆘 **SUPORTE**

- 📧 **Email**: dev@aprender.com
- 💬 **Issues**: [GitHub Issues](https://github.com/[USUARIO]/aprender_sistema/issues)
- 📚 **Docs**: [Wiki do Projeto](https://github.com/[USUARIO]/aprender_sistema/wiki)

---

## 📈 **STATUS DO PROJETO**

- ✅ **v1.0**: Sistema base de solicitações (Q3 2024)
- ✅ **v1.1**: Integração Google Calendar (Q4 2024)  
- ✅ **v1.2**: Sistema de pré-agenda (Q1 2025)
- ✅ **v1.3**: Dashboards executivos (Q2 2025)

---

## 📝 **HISTÓRICO DE LIMPEZAS E OTIMIZAÇÕES**

### **🧹 Limpeza Completa do Sistema (29/09/2025)**

**📈 Estatísticas Gerais:**
- **Espaço recuperado:** 33.04GB+ (Docker + arquivos)
- **Containers removidos:** Todos os containers do sistema
- **Volumes removidos:** 8+ volumes Docker
- **Imagens removidas:** 20+ imagens Docker
- **Arquivos removidos:** Milhares de arquivos temporários
- **Status:** Sistema completamente limpo

**✅ CONTAINERS REMOVIDOS:**
- `aprender_db_development` - Container do PostgreSQL
- Todos os containers parados (docker container prune)

**✅ VOLUMES REMOVIDOS:**
- `aprender_postgres_dev` - Dados do PostgreSQL
- `aprender_redis_dev` - Cache Redis
- `aprender_static_dev` - Arquivos estáticos
- `aprender_media_dev` - Arquivos de mídia
- `aprender_logs_dev` - Logs da aplicação
- `aprender_pgadmin_dev` - Configurações PgAdmin
- `aprender_mcp_logs_dev` - Logs MCP
- `aprender_postgres_development` - Volume adicional PostgreSQL
- 6 volumes não utilizados adicionais

**✅ IMAGENS REMOVIDAS:**
- `aprendersistema-web:latest` (2.58GB)
- `aprendersistema-ragflow-adapter:latest` (207MB)
- `aprendersistema-playwright-mcp:latest` (1.77GB)
- `aprendersistema-github-mcp:latest` (339MB)
- `aprendersistema-sentry-mcp:latest` (354MB)
- `aprendersistema-mcp:latest` (1.17GB)
- `aprendersistema-streamlit:latest` (1.91GB)
- **20+ imagens adicionais** (Elasticsearch, Kibana, Grafana, Prometheus, etc.)

### **🐳 Otimização de Containers (29/09/2025)**

**📈 Estatísticas:**
- **Integrações MCP removidas:** 8 diretórios
- **Arquivos removidos:** ~2000+ arquivos (principalmente RAGFlow)
- **Containers eliminados:** 8+ containers MCP
- **Dockerfiles removidos:** 1 (Dockerfile.mcp)
- **Volumes removidos:** 1 (mcp_logs)
- **Redução de complexidade:** ~70%

**✅ Diretórios Completos Removidos:**
1. **`context7_integration/`** - Integração Context7
2. **`fastmcp_integration/`** - Integração FastMCP  
3. **`github_mcp_integration/`** - Integração GitHub MCP
4. **`markitdown_integration/`** - Integração MarkItDown
5. **`playwright_mcp_integration/`** - Integração Playwright MCP
6. **`ragflow_integration/`** - Integração RAGFlow (**1761 arquivos!**)
7. **`sentry_mcp_integration/`** - Integração Sentry MCP
8. **`serena_integration/`** - Integração Serena

### **📊 Limpeza de Contexto Supremo (29/09/2025)**

**✅ Dados Removidos:**
- **Arquivos JSON**: Não encontrados (já removidos na limpeza anterior)
- **Arquivos CSV**: Não encontrados 
- **Arquivos Excel**: Não encontrados
- **Diretórios de dados**: Não encontrados
- **Tokens OAuth**: Não encontrados
- **Credenciais**: Não encontrados
- **Relatórios de extração**: Não encontrados

**🔒 Permissões de Acesso Preservadas:**
- ✅ **Código de integração com Google Sheets** está preservado
- ✅ **Configurações de API** estão preservadas  
- ✅ **Estrutura para autenticação** está preservada
- ✅ **Scripts de acesso** estão preservados

---

<div align="center">
  <strong>Desenvolvido com ❤️ pela equipe DAT</strong><br>
  <em>Transformando educação através da tecnologia</em>
</div>
