# Aprender Sistema

[![CI](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml/badge.svg)](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/matheusnorjosa/aprender_sistema/branch/main/graph/badge.svg)](https://codecov.io/gh/matheusnorjosa/aprender_sistema)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)
[![Type Hints: 100%](https://img.shields.io/badge/type%20hints-100%25-brightgreen.svg)](https://github.com/microsoft/pyright)
[![Coverage 85%+](https://img.shields.io/badge/coverage-85%25+-success.svg)](https://codecov.io/gh/matheusnorjosa/aprender_sistema)
[![Tests: 900+](https://img.shields.io/badge/tests-900%2B-blue.svg)](v2/docs/TESTING_POLICY.md)

Sistema de gestao de eventos, agendamento e formacoes com integracao Google Calendar, verificacao automatica de conflitos, workflow de aprovacoes e modulo DAT completo.

---

## Sobre o Projeto

**Aprender Sistema v2** e uma plataforma web completa para gerenciamento de solicitacoes de eventos, aprovacoes, formacoes e operacoes DAT (Departamento de Apoio Tecnico). O sistema substitui processos manuais baseados em planilhas por uma solucao automatizada, escalavel e auditavel.

### Principais Funcionalidades

| Modulo | Descricao |
|--------|-----------|
| **Gestao de Eventos** | Criacao, aprovacao e publicacao de eventos com suporte a eventos presenciais e online |
| **Workflow de Aprovacoes** | Fluxo configuravel (SUPER/NAO_SUPER) baseado em perfis RBAC |
| **Verificacao de Conflitos** | Deteccao automatica de sobreposicoes, bloqueios, buffers de deslocamento e limites diarios (RD-01 a RD-08) |
| **Integracao Google Calendar** | Sincronizacao com criacao automatica de Meet links (OAuth e Service Account) |
| **Modulo DAT** | Gestao completa de acoes, registros, cadastros, coordenadores, formacoes e compras |
| **Plano de Formacoes** | Acompanhamento de formacoes, provas e resultados |
| **Dashboard de Monitoramento** | Metricas em tempo real, sincronizacao GCal, equipe e mapa Brasil |
| **RBAC Completo** | Controle de acesso por Setor (9 grupos) + Funcao (4 grupos) |
| **Pipeline ETL** | 21 comandos de importacao de dados com dry-run, idempotencia e relatorios |
| **Auditoria** | Log completo de todas as operacoes criticas |

---

## Stack Tecnico

### Backend
- **Python 3.12.12** com Type Hints 100% ([Pyright strict mode](https://github.com/microsoft/pyright))
- **Django 5.2.x** + **Django REST Framework 3.14.x**
- **Celery** (worker + beat) para tarefas assincronas
- **PostgreSQL 15** como banco de dados principal
- **Redis 7** para cache, sessoes e broker Celery

### Frontend
- **React 18** com **Vite** (35+ paginas)
- **Ant Design** + **Tailwind CSS**
- **Axios** para comunicacao com API
- **Playwright** para testes E2E
- **Lighthouse CI** para metricas de performance
- **axe-core** para testes de acessibilidade (WCAG 2.1)

### Infraestrutura
- **Docker** + **Docker Compose** (6 servicos: web, worker, beat, db, redis, frontend)
- **Gunicorn** com configuracao otimizada (workers, threads, max-requests)
- **GitHub Actions** para CI/CD (Pyright, testes, coverage)
- **Prometheus + Grafana** para observabilidade (opcional)

### Qualidade de Codigo
- **Type Hints 100%** em codigo critico (42 arquivos, ~18,000 linhas)
- **Pyright** strict mode (0 erros)
- **103 arquivos de teste** (~32,600 linhas)
- **5 suites E2E** com Playwright (46 testes)
- **Coverage 85%+** enforced no CI

---

## Arquitetura do Sistema

```
.
├── v2/                           # Versao atual
│   ├── backend/                  # Django + DRF + Celery
│   │   ├── apps/
│   │   │   ├── core/             # Dominio principal (modular)
│   │   │   │   ├── models/       # 20 models organizados por dominio
│   │   │   │   ├── serializers/  # Serializers DRF modulares
│   │   │   │   ├── views/        # ViewSets organizados por feature
│   │   │   │   ├── services/     # Logica de negocio (gcal/, availability)
│   │   │   │   └── tests/        # 103 arquivos de teste
│   │   │   ├── dat_ingest/       # Pipeline ETL (21 comandos)
│   │   │   └── dev_tools/        # Seeds e ferramentas de desenvolvimento
│   │   └── config/               # Settings Django + Celery
│   ├── frontend/                 # React + Vite
│   │   ├── src/
│   │   │   ├── pages/            # 35+ paginas organizadas por modulo
│   │   │   ├── components/       # Componentes reutilizaveis
│   │   │   └── api/              # Cliente API (Axios)
│   │   └── e2e/                  # Testes Playwright
│   │       ├── checklist/        # Testes de qualidade (a11y, performance, SEO)
│   │       └── *.spec.ts         # 5 suites funcionais
│   ├── infra/                    # Docker + Scripts
│   │   ├── docker-compose.yml    # Stack principal (6 servicos)
│   │   └── docker-compose.observability.yml
│   └── docs/                     # 60+ documentos tecnicos
└── .claude/                      # Configuracao Claude Code
    ├── commands/                 # 20 slash commands
    └── skills/                   # 3 skills especializadas
```

### Models Principais

| Dominio | Models |
|---------|--------|
| **Usuario** | Usuario (custom user), Grupos RBAC |
| **Organizacao** | Projeto, Gerencia, Municipio, Deslocamento |
| **Solicitacao** | Solicitacao, Participation, AvailabilityBlock |
| **DAT** | DATAcao, DATRegistro, DATCadastro, DATCompra, DATCoordenador, DATFormacao |
| **Formacoes** | PlanoFormacoes, Formacao, Acompanhamento, Prova |
| **Compras** | Compra, Produto |
| **Auditoria** | AuditLog, SystemConfig |
| **Integracao** | GoogleOAuthCredential |

---

## Quick Start

### Pre-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Make (opcional, para atalhos)

### Desenvolvimento

```bash
# Clone o repositorio
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema/v2

# Configure variaveis de ambiente
cp infra/.env.example infra/.env

# Suba o stack completo
make up

# Verifique se tudo esta rodando
make readyz

# Acesse:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8002/api
# - Django Admin: http://localhost:8002/admin
```

### Comandos Uteis

```bash
# Gerenciamento de containers
make up              # Sobe todos os servicos
make down            # Para containers
make logs            # Ver logs (todos)
make logs-web        # Ver logs do backend

# Desenvolvimento
make shell           # Acessar shell Django
make migrate         # Aplicar migrations
make test            # Rodar testes
make test-cov        # Testes com coverage

# ETL e Dados
make etl-dry         # Pipeline ETL em modo dry-run
make etl-apply       # Pipeline ETL (aplica mudancas)

# Observabilidade (opcional)
make up-obs          # Sobe stack com Prometheus + Grafana
```

---

## Sistema RBAC

O sistema usa **duas dimensoes** de controle de acesso:

### Grupos de Setor (9 grupos)
| Setor | Descricao |
|-------|-----------|
| Superintendencia | Setor estrategico (fluxo SUPER) |
| Vidas | Gerencia 2 - Projetos Vida |
| Fluir | Gerencia 3 - Projeto Fluir |
| ACerta | Gerencia 4 - Projetos ACerta |
| Brincando | Gerencia 5 - Brincando e Aprendendo |
| Sou da Paz | Gerencia 6 - Projeto Sou da Paz |
| DAT | Departamento de Apoio Tecnico |
| Controle | Setor de Controle (operacoes) |
| Gerencia | Gerencia generica |

### Grupos de Funcao (4 grupos)
| Funcao | Permissoes |
|--------|------------|
| Formador | Visualiza grade, gerencia bloqueios pessoais |
| Coordenador | Cria solicitacoes de eventos |
| Apoio de Coordenacao | Auxilia coordenacao, visualiza solicitacoes |
| Gerente | Aprova/reprova, acessa dashboards e relatorios |

### API /api/me/
```json
{
  "id": 1,
  "username": "maria",
  "groups": ["Superintendencia", "Gerente"],
  "setores": ["Superintendencia"],
  "funcoes": ["Gerente"],
  "is_superuser": false,
  "is_superintendencia": true,
  "can_approve_super": true
}
```

---

## Regras de Disponibilidade (RD-01 a RD-08)

| Regra | Descricao |
|-------|-----------|
| RD-01 | Nao-sobreposicao (overlap >= 1 min = conflito; borda fim==inicio = OK) |
| RD-02 | Bloqueio total (T) impede quaisquer eventos |
| RD-03 | Bloqueio parcial (P) impede dentro do subintervalo |
| RD-04 | Buffer de deslocamento (D) entre municipios distintos (60-120 min) |
| RD-05 | Capacidade diaria (M) - limite de horas por dia por formador |
| RD-06 | Timezone America/Fortaleza (aware), armazenar UTC |
| RD-07 | Prioridade: Bloqueios -> Conflitos -> Buffer -> Limite diario |
| RD-08 | Mensagens listam formador(es), data/intervalo, tipo (E/M/D/P/T/X) |

---

## Politica de Aprovacao Manual (PA-01 a PA-07)

| Regra | Descricao |
|-------|-----------|
| PA-01 | Sem auto-aprovacao para fluxo SUPER |
| PA-02 | Usuarios com Superintendencia, DAT ou superuser podem aprovar |
| PA-03 | Integracoes externas (GCal) so executam apos aprovacao |
| PA-04 | Toda solicitacao nasce com status=pendente |
| PA-05 | Registrar usuario, data/hora e justificativa em AuditLog |
| PA-06 | UI esconde botoes para perfis sem permissao |
| PA-07 | 5 testes obrigatorios de conformidade |

---

## Integracao Google Calendar

### Modos de Autenticacao

**Service Account Mode** (desenvolvimento/staging):
```bash
GCAL_CLIENT=google
GCAL_CLIENT_MODE=service_account
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/service-account.json
```

**OAuth Mode** (producao):
```bash
GCAL_CLIENT=google
GCAL_CLIENT_MODE=oauth
# Tokens criptografados no banco por usuario
```

### Features
- Criacao/atualizacao/cancelamento de eventos
- Geracao automatica de Meet links
- Retry com exponential backoff
- Dashboard de monitoramento (`/dashboard/gcal`)
- Fake client para testes

---

## Pipeline ETL

21 comandos de importacao de dados:

```bash
# Pipeline completo
python manage.py load_full_pipeline --dry-run

# Comandos individuais
python manage.py etl_upsert_core --apply
python manage.py etl_upsert_acompanhamento --dry-run
python manage.py etl_import_dat_cadastros --apply
python manage.py import_usuarios_from_csv --dry-run
```

Features:
- Modo `--dry-run` (preview) e `--apply` (persiste)
- Relatorios JSON estruturados
- Idempotencia (re-execucao segura)
- Rollback em caso de erro
- Logging detalhado

---

## Testes

### Backend (103 arquivos, ~32,600 linhas)

```bash
# Todos os testes
docker compose exec web pytest -v

# Com coverage
docker compose exec web pytest --cov=apps.core --cov-report=html

# Testes especificos
docker compose exec web pytest apps/core/tests/test_availability_service.py -v

# Type checking
docker compose exec web pyright apps/core
```

### Frontend E2E (Playwright)

```bash
# Instalar browsers
npx playwright install chromium

# Rodar todos os testes
npx playwright test

# Testes de qualidade (checklist)
npm run test:checklist

# Lighthouse CI
npm run lighthouse

# Modo interativo
npx playwright test --ui
```

**Suites Funcionais:**
- `z-auth.spec.ts` - Autenticacao
- `navigation.spec.ts` - Navegacao
- `solicitacoes.spec.ts` - Fluxo de solicitacoes
- `dashboards.spec.ts` - Dashboards
- `dat-module.spec.ts` - Modulo DAT

**Suites de Qualidade (checklist/):**
- `meta-tags.spec.ts` - Charset, viewport, title, favicon
- `console-errors.spec.ts` - Zero erros JS
- `security-headers.spec.ts` - X-Frame-Options, CSP, HSTS
- `broken-links.spec.ts` - Links e recursos 404
- `accessibility.spec.ts` - WCAG 2.1 (axe-core)
- `performance.spec.ts` - Core Web Vitals (LCP, CLS, FCP)

---

## Documentacao

### Guias Principais
| Documento | Descricao |
|-----------|-----------|
| [RUNBOOK.md](v2/docs/RUNBOOK.md) | Guia operacional completo |
| [TESTING_POLICY.md](v2/docs/TESTING_POLICY.md) | Politicas de testes |
| [TYPE_HINTS_GUIDE.md](v2/docs/TYPE_HINTS_GUIDE.md) | Guia de type hints |
| [OBSERVABILITY.md](v2/docs/OBSERVABILITY.md) | Prometheus + Grafana + Logging |
| [GUIDE_GCAL.md](v2/docs/GUIDE_GCAL.md) | Integracao Google Calendar |
| [RBAC_COMPLETO.md](v2/docs/RBAC_COMPLETO.md) | Sistema de permissoes |

### Documentacao Adicional
- 60+ documentos tecnicos em `v2/docs/`
- [INDEX_DOCUMENTACAO.md](v2/docs/INDEX_DOCUMENTACAO.md) - Indice completo

---

## CI/CD

### GitHub Actions

| Workflow | Descricao |
|----------|-----------|
| **CI** | Testes + Pyright + Coverage (85%+ enforced) |
| **frontend-ci** | Build + Lint + Checklist Tests + Lighthouse CI |
| **Codecov** | Upload automatico de coverage |

### Metricas Atuais
- **134 arquivos de teste** (backend + frontend)
- **900+ testes** passando
- **Coverage 85%+** (enforced)
- **Pyright 0 erros** (strict mode)
- **11 suites E2E** (5 funcionais + 6 qualidade)

---

## Docker

### Servicos

```yaml
services:
  db:        # PostgreSQL 15 (porta 5434)
  redis:     # Redis 7 (porta 6380)
  web:       # Django + Gunicorn (porta 8002)
  worker:    # Celery worker
  beat:      # Celery beat (scheduler)
  frontend:  # React + Vite (porta 5173)
```

### Observabilidade (opcional)

```yaml
# docker-compose.observability.yml
services:
  prometheus:    # Metricas (porta 9090)
  grafana:       # Dashboards (porta 3001)
  postgres_exp:  # PostgreSQL exporter
  redis_exp:     # Redis exporter
```

---

## Variaveis de Ambiente

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
ENVIRONMENT=staging  # development|staging|production

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

# Google Calendar (opcional)
GCAL_CLIENT=fake  # fake|google
GCAL_CLIENT_MODE=service_account  # service_account|oauth
```

---

## Contribuindo

### Workflow

1. Crie uma branch: `git checkout -b feat/minha-feature`
2. Faca commits convencionais: `feat:`, `fix:`, `chore:`, `test:`
3. Mantenha type hints e coverage
4. Rode testes: `make test && make pyright`
5. Crie PR para `main`

### Padroes
- **Python**: PEP 8, type hints obrigatorios
- **Django**: Models SSOT, views thin, logica em services
- **Testes**: Behavior-driven, fixtures reutilizaveis
- **Commits**: Conventional Commits

---

## Licenca

Proprietario - Todos os direitos reservados.

---

## Autor

**Matheus Norjosa**
- GitHub: [@matheusnorjosa](https://github.com/matheusnorjosa)

---

## Suporte

1. Consulte a [documentacao](v2/docs/)
2. Verifique [issues abertas](https://github.com/matheusnorjosa/aprender_sistema/issues)
3. Crie uma nova issue se necessario

---

<p align="center">
  <strong>Aprender Sistema v2</strong><br>
  Python 3.12 | Django 5.2 | React 18 | PostgreSQL 15 | Redis 7
</p>
