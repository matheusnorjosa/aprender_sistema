# Instalação

## Pré-requisitos

- Docker e Docker Compose
- Git
- Node.js 18+ (para desenvolvimento frontend)

## Clone do Repositório

```bash
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema
```

## Subindo o Ambiente

### Backend (Docker)

```bash
cd v2
docker compose -f infra/docker-compose.yml up -d
```

Isso irá subir:

- PostgreSQL (porta 5433)
- Redis (porta 6379)
- Backend Django (porta 8002)
- Celery Worker
- Celery Beat

### Frontend (Desenvolvimento)

```bash
cd v2/frontend
npm install
npm run dev
```

O frontend estará disponível em `http://localhost:5173`.

## Verificando a Instalação

```bash
# Verificar containers
docker compose -f v2/infra/docker-compose.yml ps

# Verificar logs
docker compose -f v2/infra/docker-compose.yml logs -f web

# Acessar shell Django
docker compose -f v2/infra/docker-compose.yml exec web python manage.py shell
```

## Próximos Passos

- [Configuração](configuration.md)
- [Quick Start](quickstart.md)
