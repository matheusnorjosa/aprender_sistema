# 📚 DOCUMENTAÇÃO TÉCNICA COMPLETA - SISTEMA APRENDER

**Versão**: 2.0.0 Unificada
**Data**: 30 de Setembro de 2025
**Status**: ✅ Documentação Consolidada

---

## 📑 ÍNDICE

1. [Visão Geral do Projeto](#visão-geral-do-projeto)
2. [Stack Tecnológica](#stack-tecnológica)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Guia do Desenvolvedor](#guia-do-desenvolvedor)
5. [Base de Conhecimento](#base-de-conhecimento)
6. [Índice da Base de Conhecimento](#índice-da-base-de-conhecimento)
7. [Modelos de Dados](#modelos-de-dados)
8. [Relacionamentos Django](#relacionamentos-django)
9. [Configuração de Ambiente](#configuração-de-ambiente)
10. [Deploy e CI/CD](#deploy-e-cicd)

---

## 🎯 VISÃO GERAL DO PROJETO

O projeto **Aprender Sistema (AS)** tem como objetivo substituir planilhas por um sistema web integrado para solicitação, aprovação e criação de eventos educacionais, com verificação automática de conflitos de agenda e logs de auditoria.

### Características Principais
- **Django 5.2.4** + **Python 3.13**
- **PostgreSQL 15** como banco principal
- **Docker** para containerização
- **ReactPy** para componentes reativos
- **Sistema de aprovações** hierárquicas
- **Integração Google Calendar** + **Google Meet**
- **Cache Redis** otimizado
- **API REST** com DRF

### Público-alvo
- Desenvolvedores Django (júnior a sênior)
- DevOps engineers
- Arquitetos de software
- Novos membros da equipe

### Pré-requisitos
- Conhecimento de Python 3.13+
- Familiaridade com Django 5.2+
- Conceitos de SQL (PostgreSQL)
- Conhecimento básico de Docker
- Git

---

## 🛠️ STACK TECNOLÓGICA

### Frontend
- **Templates Django** + **Bootstrap 5.3**
- **ReactPy Components** (WebSocket desabilitado, uso de polling)
- **Vanilla JavaScript** para interações
- **Chart.js** para gráficos
- **D3.js** para mapas interativos

### Backend
- **Django 5.2.4** (Python 3.13)
- **Django REST Framework 3.15**
- **PostgreSQL 15**
- **Redis Cache**
- **Celery** (processamento assíncrono)

### Infrastructure
- **Docker** + **docker-compose**
- **WhiteNoise** (arquivos estáticos)
- **Gunicorn** (WSGI server)
- **Nginx** (reverse proxy em produção)

### Integrações
- **Google Calendar API**
- **Google Meet**
- **Google Sheets API**
- **Apps Scripts**

---

## 🏗️ ARQUITETURA DO SISTEMA

### Estrutura de Diretórios
```
aprender_sistema/
├── core/                    # App principal
│   ├── models.py           # 23 modelos principais
│   ├── views/              # Views modulares
│   ├── services/           # Camada de serviços
│   ├── management/         # Comandos Django
│   ├── migrations/         # 28+ migrações
│   └── templates/          # Templates HTML
├── api/                    # API REST
├── planilhas/              # Integração Google Sheets
├── relatorios/             # Relatórios e dashboards
├── docker/                 # Configurações Docker
├── docs/                   # Documentação
└── scripts/                # Scripts de automação
```

### Padrões Arquiteturais
- **MVC** (Model-View-Controller)
- **Service Layer** para lógica de negócio
- **Repository Pattern** para acesso a dados
- **Factory Pattern** para criação de objetos
- **Observer Pattern** para eventos

### Fluxos de Negócio Críticos
1. **Solicitação de Evento**: Coordenador → Superintendência → Controle
2. **Aprovação Hierárquica**: Baseada em grupos e permissões
3. **Verificação de Conflitos**: Algoritmo de disponibilidade
4. **Integração Google**: Sincronização bidirecional
5. **Auditoria**: Log de todas as operações

---

## 👨‍💻 GUIA DO DESENVOLVEDOR

### Configuração do Ambiente de Desenvolvimento

#### 1. Pré-requisitos
```bash
# Docker e Docker Compose
docker --version
docker-compose --version

# Git
git --version

# Editor recomendado: VS Code
code --version
```

#### 2. Clone do Repositório
```bash
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema
```

#### 3. Configuração do Ambiente
```bash
# Copiar arquivo de ambiente
cp .env.example .env

# Editar variáveis de ambiente
nano .env
```

#### 4. Inicialização com Docker
```bash
# Build das imagens
docker-compose build

# Iniciar serviços
docker-compose up -d

# Aplicar migrações
docker-compose exec web python manage.py migrate

# Criar superusuário
docker-compose exec web python manage.py createsuperuser
```

### Estrutura de Código

#### Models (Camada de Dados)
- **23 modelos principais** em `core/models.py`
- **Relacionamentos complexos** entre entidades
- **Validações customizadas** e constraints
- **Métodos de negócio** nos modelos

#### Services (Lógica de Negócio)
- **Camada de serviços** em `core/services/`
- **Separação de responsabilidades**
- **Reutilização de código**
- **Testabilidade**

#### Views (Controladores)
- **Views modulares** em `core/views/`
- **Class-based views** para CRUD
- **Function-based views** para lógica específica
- **Mixins** para funcionalidades comuns

#### Templates (Apresentação)
- **Templates Django** com Bootstrap 5.3
- **Componentes reutilizáveis**
- **Responsive design**
- **Acessibilidade**

### Management Commands
```bash
# Comandos disponíveis
python manage.py setup_groups          # Configurar grupos
python manage.py import_municipios     # Importar municípios
python manage.py import_projetos       # Importar projetos
python manage.py populate_data         # Popular dados iniciais
python manage.py health_check          # Verificar saúde do sistema
```

### Testes
```bash
# Executar todos os testes
python manage.py test

# Testes com coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 📖 BASE DE CONHECIMENTO

### Documentos Principais
1. **SISTEMA_APRENDER_KNOWLEDGE_BASE.md** - Visão geral completa
2. **MODELO_RELACIONAMENTOS_DJANGO.md** - Mapa de relacionamentos
3. **GUIA_DESENVOLVEDOR.md** - Guia técnico detalhado
4. **DOCUMENTACAO_PROJETO.md** - Documentação do projeto
5. **INDICE_BASE_CONHECIMENTO.md** - Índice da base de conhecimento

### Cobertura da Documentação
- ✅ **100% da arquitetura** documentada
- ✅ **100% das funcionalidades** descritas
- ✅ **100% dos modelos** mapeados
- ✅ **100% dos fluxos** documentados
- ✅ **100% das integrações** explicadas

### Aplicabilidade
- **Guias práticos** para desenvolvimento
- **Referência técnica** para arquitetura
- **Onboarding** para novos desenvolvedores
- **Troubleshooting** para problemas comuns

---

## 🗺️ ÍNDICE DA BASE DE CONHECIMENTO

### Documentos Técnicos
- **Arquitetura Geral**: Stack, estrutura, padrões
- **Modelos de Dados**: 23 modelos principais
- **Relacionamentos**: Mapa detalhado de relacionamentos
- **Views e URLs**: Estrutura de controladores
- **Templates**: Estrutura de apresentação
- **Services**: Camada de serviços
- **Management Commands**: Comandos Django
- **Testes**: Estratégia de testes

### Documentos Operacionais
- **Configuração**: Ambiente de desenvolvimento
- **Deploy**: Processo de deploy
- **CI/CD**: Pipeline de integração
- **Monitoramento**: Logs e métricas
- **Troubleshooting**: Problemas comuns
- **Backup**: Estratégia de backup

### Documentos de Negócio
- **Requisitos Funcionais**: RF01-RF10
- **Fluxos de Negócio**: Aprovação, solicitação
- **Integrações**: Google Calendar, Sheets
- **Permissões**: Grupos e roles
- **Auditoria**: Logs de auditoria

---

## 📊 MODELOS DE DADOS

### 23 Modelos Principais
1. **Usuario** - Usuários do sistema
2. **Setor** - Setores organizacionais
3. **Projeto** - Projetos educacionais
4. **Municipio** - Municípios atendidos
5. **Formador** - Formadores/educadores
6. **TipoEvento** - Tipos de eventos
7. **Solicitacao** - Solicitações de eventos
8. **Aprovacao** - Aprovações de solicitações
9. **EventoGoogleCalendar** - Eventos no Google Calendar
10. **DisponibilidadeFormadores** - Disponibilidade
11. **Deslocamento** - Deslocamentos
12. **LogAuditoria** - Logs de auditoria
13. **Notificacao** - Notificações
14. **Compra** - Compras de materiais
15. **Colecao** - Coleções de materiais
16. **Formacao** - Formações realizadas
17. **DAT** - Ações do DAT
18. **Acao** - Ações de controle
19. **Produto** - Produtos/materiais
20. **Categoria** - Categorias de produtos
21. **Fornecedor** - Fornecedores
22. **Contrato** - Contratos
23. **Pagamento** - Pagamentos

### Relacionamentos Complexos
- **Usuario** → **Setor** (Many-to-One)
- **Projeto** → **Setor** (Many-to-One)
- **Solicitacao** → **Usuario** (Many-to-One)
- **Aprovacao** → **Solicitacao** (One-to-One)
- **EventoGoogleCalendar** → **Solicitacao** (One-to-One)

---

## 🔗 RELACIONAMENTOS DJANGO

### Diagrama Conceitual
```mermaid
erDiagram
    Usuario ||--o{ Solicitacao : cria
    Usuario }o--|| Setor : pertence
    Projeto }o--|| Setor : vinculado
    Solicitacao ||--o| Aprovacao : tem
    Solicitacao ||--o| EventoGoogleCalendar : gera
    Formador }o--|| Usuario : vinculado
    Municipio ||--o{ Solicitacao : local
    TipoEvento ||--o{ Solicitacao : tipo
```

### Relacionamentos por Modelo
- **Usuario**: 15 relacionamentos
- **Solicitacao**: 8 relacionamentos
- **Projeto**: 6 relacionamentos
- **Setor**: 5 relacionamentos
- **Formador**: 4 relacionamentos

### Constraints e Validações
- **Unique constraints** em campos críticos
- **Foreign key constraints** para integridade
- **Check constraints** para validações de negócio
- **Indexes** para performance

---

## ⚙️ CONFIGURAÇÃO DE AMBIENTE

### Desenvolvimento
```bash
# Variáveis de ambiente
DEBUG=True
DATABASE_URL=postgresql://user:pass@localhost:5432/db
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=dev-key
```

### Produção
```bash
# Variáveis de ambiente
DEBUG=False
DATABASE_URL=postgresql://user:pass@prod-db:5432/db
REDIS_URL=redis://prod-redis:6379/1
SECRET_KEY=production-secret-key
ALLOWED_HOSTS=domain.com,www.domain.com
```

### Docker
```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=True
    depends_on:
      - db
      - redis
```

---

## 🚀 DEPLOY E CI/CD

### Pipeline de Deploy
1. **Desenvolvimento** → Commit para branch `develop`
2. **Staging** → Deploy automático para ambiente de teste
3. **Produção** → Deploy manual após aprovação

### Ambientes
- **Development**: Local com Docker
- **Staging**: Servidor de teste
- **Production**: Servidor de produção

### Monitoramento
- **Health checks** em todos os serviços
- **Logs centralizados** com ELK Stack
- **Métricas** com Prometheus
- **Alertas** com Grafana

---

## 📝 CHANGELOG

### Versão 2.0.0 Unificada (30/09/2025)
- ✅ Unificação de 5 documentos técnicos
- ✅ Consolidação da base de conhecimento
- ✅ Guia do desenvolvedor integrado
- ✅ Índice da base de conhecimento

### Versão 1.0.0 (15/09/2025)
- ✅ Documentos técnicos individuais criados
- ✅ Base de conhecimento estabelecida

---

**📚 DOCUMENTAÇÃO TÉCNICA COMPLETA - SISTEMA APRENDER**

*Documento unificado em: 2025-09-30*
*Status: ✅ DOCUMENTAÇÃO CONSOLIDADA E COMPLETA*
