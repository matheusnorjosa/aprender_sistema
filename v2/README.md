# Aprender Sistema v2

**Status**: Produção
**Versão**: 2.0
**Atualizado**: Janeiro 2026

---

## Visão Geral

Sistema de gestão de eventos e disponibilidade de formadores, substituindo planilhas Google/Excel por plataforma web automatizada.

**Stack**:
- Backend: Python 3.12 + Django 5.2 + DRF + Celery
- Frontend: React 18 + Vite + Ant Design + Tailwind
- Database: PostgreSQL 15 + Redis 7
- Infra: Docker + Docker Compose

---

## Quick Start

### 1. Pré-requisitos

- Docker 24+ & Docker Compose 2+
- Git

### 2. Iniciar Serviços

```bash
cd v2/infra
docker compose up -d
```

### 3. Acessar

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8002/api/ |
| Admin | http://localhost:8002/admin/ |
| Health | http://localhost:8002/api/health/ |

---

## Estrutura

```
v2/
├── backend/              # Django + DRF
│   ├── apps/
│   │   ├── core/         # Domínio principal (28 models)
│   │   └── dat_ingest/   # ETL (21 comandos)
│   └── config/           # Settings, URLs, Celery
│
├── frontend/             # React + Vite
│   ├── src/
│   │   ├── pages/        # 45+ páginas
│   │   ├── components/   # Componentes reutilizáveis
│   │   └── api/          # Clients API
│   └── e2e/              # Testes Playwright (46 testes)
│
├── infra/                # Docker
│   ├── docker-compose.yml
│   └── Dockerfile
│
└── docs/                 # Documentação (99 arquivos)
```

---

## Testes

```bash
# Backend (pytest)
docker compose exec web pytest apps/core -v

# Frontend (Vitest)
cd frontend && npm test

# E2E (Playwright) - parar frontend Docker primeiro
docker compose stop frontend
cd frontend && npx playwright test
```

**Cobertura**:
- Backend: 100+ testes
- E2E: 46 testes passando

---

## ETL

```bash
# Dry-run (simulação)
docker compose exec web python manage.py import_usuarios --dry-run

# Executar
docker compose exec web python manage.py import_usuarios --apply
```

**Comandos disponíveis**: 21 (import_usuarios, import_municipios, import_dat_acoes, etc.)

---

## Portas

| Serviço | Porta Host | Porta Container |
|---------|------------|-----------------|
| Frontend | 5173 | 5173 |
| Backend | 8002 | 8000 |
| PostgreSQL | 5434 | 5432 |
| Redis | 6380 | 6379 |

---

## Documentação

| Documento | Descrição |
|-----------|-----------|
| [PROJETO_ORIGEM.md](docs/PROJETO_ORIGEM.md) | Origem, modelos, regras |
| [GUIDE_GCAL.md](docs/GUIDE_GCAL.md) | Integração Google Calendar |
| [RBAC_COMPLETO.md](docs/RBAC_COMPLETO.md) | Sistema de permissões |
| [OBSERVABILITY.md](docs/OBSERVABILITY.md) | Prometheus/Grafana/Logs |
| [TESTING_POLICY.md](docs/TESTING_POLICY.md) | Políticas de teste |

---

## Variáveis de Ambiente

```bash
# Obrigatórias
SECRET_KEY=sua-chave-secreta
DB_PASSWORD=senha-banco

# Google Calendar (opcional)
GCAL_CLIENT=fake|google
GCAL_CALENDAR_ID=seu-calendar-id
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/key.json
```

---

## Comandos Úteis

```bash
# Logs
docker compose logs -f web

# Shell Django
docker compose exec web python manage.py shell

# Migrations
docker compose exec web python manage.py migrate

# Criar superuser
docker compose exec web python manage.py createsuperuser
```

---

## Contribuindo

1. Branch: `git checkout -b feat/minha-feature`
2. Commit: `git commit -m "feat: descrição"`
3. Push: `git push origin feat/minha-feature`
4. Pull Request

**Padrões**: feat, fix, refactor, test, docs, chore
