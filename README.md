# Aprender Sistema

[![CI](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml/badge.svg)](https://github.com/matheusnorjosa/aprender_sistema/actions/workflows/ci.yaml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)

Plataforma web para gerenciamento interno empresarial e gestão automatizada de eventos com integração direta à API do Google Calendar.

---

## Stack

- **Backend**: Python 3.12 + Django 5.2 + DRF + Celery
- **Frontend**: React 18 + Vite + Ant Design
- **Database**: PostgreSQL 15 + Redis 7
- **Infra**: Docker + Docker Compose

---

## Quick Start

```bash
# Clone
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema/v2

# Configure
cp infra/.env.example infra/.env

# Start
cd infra && docker compose up -d

# Access
# Frontend: http://localhost:5173
# API: http://localhost:8002/api
```

---

## Comandos

```bash
# Containers
docker compose up -d      # Start
docker compose down       # Stop
docker compose logs -f    # Logs

# Backend
docker compose exec web pytest              # Tests
docker compose exec web python manage.py migrate   # Migrations

# Frontend
cd frontend && npm test   # Tests
cd frontend && npm run build   # Build
```

---

## Estrutura

```
v2/
├── backend/      # Django API
├── frontend/     # React App
├── infra/        # Docker configs
└── docs/         # Documentation
```

---

## Licenca

Proprietario - Todos os direitos reservados.

---

**Autor**: Matheus Norjosa