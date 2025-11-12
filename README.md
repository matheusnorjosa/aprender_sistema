# Aprender Sistema

[![CI](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml/badge.svg)](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/matheusnorjosa/aprender_sistema/branch/main/graph/badge.svg)](https://codecov.io/gh/matheusnorjosa/aprender_sistema)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.1](https://img.shields.io/badge/django-5.1-green.svg)](https://www.djangoproject.com/)
[![Type Hints: 100%](https://img.shields.io/badge/type%20hints-100%25-brightgreen.svg)](https://github.com/microsoft/pyright)
[![Branch Protection](https://img.shields.io/badge/branch%20protection-enabled-success.svg)](https://github.com/matheusnorjosa/aprender_sistema/settings/rules)

Sistema de gestão de eventos e agendamento com integração Google Calendar, verificação automática de conflitos e workflow de aprovações.

---

## 🚀 Sobre o Projeto

**Aprender Sistema v2** é uma plataforma web completa para gerenciamento de solicitações de eventos, aprovações e sincronização com Google Calendar. O sistema substitui processos manuais baseados em planilhas por uma solução automatizada, escalável e auditável.

### Principais Funcionalidades

- 📅 **Gestão de Eventos**: Criação, aprovação e publicação de eventos
- ✅ **Workflow de Aprovações**: Fluxo configurable (manual/automático) baseado em perfis
- 🔍 **Verificação de Conflitos**: Detecção automática de sobreposições, bloqueios e restrições de disponibilidade
- 🔗 **Integração Google Calendar**: Sincronização bidirecional com criação automática de Meet links
- 📊 **Dashboard de Monitoramento**: Métricas em tempo real de sincronização e erros
- 🔐 **RBAC**: Controle de acesso baseado em grupos (Superintendência, Controle, Coordenador, Formador, DAT)
- 📝 **Auditoria Completa**: Log de todas as operações críticas

---

## 🛠️ Stack Técnico

### Backend
- **Python 3.12.12** com Type Hints completos ([Pyright strict mode](https://github.com/microsoft/pyright))
- **Django 5.1.x** + **Django REST Framework 3.14.x**
- **Celery** (worker + beat) para tarefas assíncronas
- **PostgreSQL 15** como banco de dados principal
- **Redis 7** para cache e broker Celery

### Frontend
- **React 18** com **Vite**
- **Ant Design** + **Tailwind CSS**
- **Axios** para comunicação com API

### Infraestrutura
- **Docker** + **Docker Compose** (desenvolvimento e produção)
- **GitHub Actions** para CI/CD
- **Codecov** para cobertura de testes (target: 90%+)

### Qualidade de Código
- ✅ **Type Hints 100%** em código crítico (42 arquivos, ~18,000 linhas)
- ✅ **Pyright** strict mode (0 erros)
- ✅ **855+ testes** unitários e de integração
- ✅ **Coverage 90%+** em módulos críticos

---

## 📂 Estrutura do Projeto

```
.
└── v2/                      # Versão atual
    ├── backend/             # Django + DRF + Celery
    │   ├── apps/
    │   │   ├── core/        # Domínio principal
    │   │   └── dat_ingest/  # ETL e importação de dados
    │   ├── config/          # Settings Django
    │   └── manage.py
    ├── frontend/            # React + Vite
    │   ├── src/
    │   │   ├── pages/       # Páginas principais
    │   │   ├── components/  # Componentes reutilizáveis
    │   │   └── api/         # Cliente API
    │   └── package.json
    ├── infra/               # Docker + CI/CD
    │   ├── docker-compose.yml
    │   └── Dockerfile.backend
    └── docs/                # Documentação técnica
        ├── RUNBOOK.md       # Guia operacional
        ├── TESTING_POLICY.md
        └── TYPE_HINTS_GUIDE.md
```

---

## 🚀 Quick Start

### Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Make (opcional, para atalhos)

### Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema/v2

# Suba o stack completo (PostgreSQL, Redis, backend, frontend)
make up

# Verifique se tudo está rodando
make readyz

# Acesse:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8002/api
# - Django Admin: http://localhost:8002/admin
```

### Comandos Úteis

```bash
# Parar containers
make down

# Ver logs
docker compose logs -f web

# Rodar testes
docker compose exec web pytest -v

# Criar migrations
docker compose exec web python manage.py makemigrations

# Aplicar migrations
docker compose exec web python manage.py migrate

# Acessar shell Django
docker compose exec web python manage.py shell
```

---

## 📚 Documentação

### Guias Principais

- 📖 **[RUNBOOK.md](v2/docs/RUNBOOK.md)** - Guia operacional completo (Docker, Celery, troubleshooting)
- 🧪 **[TESTING_POLICY.md](v2/docs/TESTING_POLICY.md)** - Políticas e práticas de testes
- 🐍 **[TYPE_HINTS_GUIDE.md](v2/docs/TYPE_HINTS_GUIDE.md)** - Como usar type hints no projeto
- 🔐 **[OAUTH_ENV_VARIABLES.md](v2/OAUTH_ENV_VARIABLES.md)** - Configuração OAuth Google Calendar

### APIs e Endpoints

**Principais endpoints REST**:
- `GET/POST /api/solicitacoes/` - Gestão de solicitações
- `GET /api/availability/monthly/` - Disponibilidade mensal
- `GET /api/gcal/dashboard/metrics/` - Métricas de sincronização
- `POST /api/oauth/google/start/` - Iniciar conexão OAuth

**Documentação completa**: Acesse `/api/docs` (Swagger) quando o servidor estiver rodando.

---

## 🎯 Highlights Técnicos

### Type Hints 100% ✅

Implementação completa de type hints em código crítico (concluída em janeiro/2025):

- ✅ **42 arquivos tipados** (~18,000 linhas)
- ✅ **Pyright strict mode** (0 erros)
- ✅ **8 PRs incrementais** (#108-#116)
- ✅ **PEP 695** (Python 3.12+)

**Benefícios**:
- Detecção de erros em tempo de desenvolvimento
- Autocomplete 3x mais preciso
- Refactoring seguro
- CI como gate de qualidade

### Integração Google Calendar

Dois modos de autenticação suportados:

**Service Account Mode** (padrão):
- Autenticação servidor-a-servidor
- Ideal para desenvolvimento/staging

**OAuth Mode** (produção):
- Autenticação individual por usuário
- Grupos "Controle" e "Superintendência"
- Tokens criptografados no banco
- Rotação de chave de criptografia

**Features**:
- Criação/atualização/cancelamento de eventos
- Geração automática de Meet links
- Retry com exponential backoff
- Dashboard de monitoramento

### GCal Dashboard

**Rota**: `/dashboard/gcal`
**Permissões**: Controle/Superintendência

Dashboard completo de monitoramento:
- 📊 Cards de contagem por status (NONE/PENDING/PUBLISHED/ERROR)
- 🔍 Filtros por período e status
- 📋 Tabela paginada com ordenação
- ⚠️ Alertas de erros recentes (top 5)

**Testes**: 12/12 passando (veja [Testing Policy](v2/docs/TESTING_POLICY.md))

### Testes e Qualidade

**Baseline CI**: 855 passed, 14 skipped

**Cobertura**:
- Target geral: 90%+
- Módulos críticos: 100%

**Tipos de testes**:
- Unitários (models, services, serializers)
- Integração (API endpoints, workflows)
- RBAC (permissions)
- Celery (tasks assíncronas)
- OAuth (fixtures e mocks)

---

## 🔧 Configuração de Ambiente

### Variáveis de Ambiente Essenciais

Crie um arquivo `.env` em `v2/backend/`:

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=aprender_v2
DB_USER=postgres
DB_PASSWORD=postgres

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Google Calendar (opcional, para desenvolvimento)
GCAL_CLIENT=fake  # ou 'google' para modo real
GCAL_CLIENT_MODE=service_account  # ou 'oauth'
# GCAL_CALENDAR_ID=your-calendar-id@group.calendar.google.com
# GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/service-account.json
```

**Nota**: Para produção, consulte [OAUTH_ENV_VARIABLES.md](v2/OAUTH_ENV_VARIABLES.md)

---

## 🧪 Rodando Testes

```bash
# Todos os testes
docker compose exec web pytest -v

# Com coverage
docker compose exec web pytest --cov=apps.core --cov-report=html

# Testes específicos
docker compose exec web pytest apps/core/tests/test_availability_service.py -v

# Módulo específico com coverage mínima
docker compose exec web pytest --cov=apps.core.services.availability_service --cov-fail-under=90
```

---

## 🤝 Contribuindo

### Workflow de Desenvolvimento

1. **Crie uma branch** a partir de `main`:
   ```bash
   git checkout -b feat/minha-feature
   ```

2. **Faça suas mudanças** seguindo os padrões:
   - Conventional commits (`feat:`, `fix:`, `chore:`)
   - Type hints em código novo
   - Testes para novas funcionalidades (coverage 90%+)

3. **Rode os testes**:
   ```bash
   docker compose exec web pytest -v
   docker compose exec web pyright apps/core
   ```

4. **Crie um Pull Request** para `main`:
   - Título descritivo
   - Descrição clara das mudanças
   - Testes passando no CI
   - Coverage mantido/melhorado

### Padrões de Código

- **Python**: PEP 8, type hints obrigatórios
- **Django**: Models SSOT, views thin, lógica em services
- **Testes**: Behavior-driven, fixtures reutilizáveis
- **Commits**: Conventional Commits

---

## 📊 CI/CD

GitHub Actions workflows:

- ✅ **CI** (.github/workflows/ci.yaml): Testes + Pyright + Coverage
- ✅ **Codecov**: Upload automático de coverage
- ✅ **Pre-commit hooks**: Linting e formatação

**Status**:
[![CI](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml/badge.svg)](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml)

---

## 🐳 Docker

### Serviços

```yaml
services:
  db:        # PostgreSQL 15 (porta 5433 no host)
  redis:     # Redis 7 (porta 6379)
  web:       # Django + DRF (porta 8002 no host)
  celery:    # Celery worker
  beat:      # Celery beat (scheduler)
  frontend:  # React dev server (porta 3000)
```

### Comandos Docker

```bash
# Rebuild após mudanças no Dockerfile
docker compose build web

# Ver logs de um serviço específico
docker compose logs -f celery

# Restart de um serviço
docker compose restart web

# Parar e remover tudo (limpar volumes)
docker compose down -v
```

---

## 📝 Licença

Proprietário - Todos os direitos reservados.

---

## 👤 Autor

**Matheus Norjosa**

- GitHub: [@matheusnorjosa](https://github.com/matheusnorjosa)

---

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte a [documentação](v2/docs/)
2. Verifique [issues abertas](https://github.com/matheusnorjosa/aprender_sistema/issues)
3. Crie uma nova issue se necessário

---

<p align="center">
  Desenvolvido com ❤️ por <a href="https://github.com/matheusnorjosa">Matheus Norjosa</a>
</p>
