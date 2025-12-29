# Infraestrutura

## Docker Compose

O sistema roda em containers Docker:

```yaml
services:
  db:        # PostgreSQL 15
  redis:     # Redis 7
  web:       # Django + Gunicorn
  worker:    # Celery Worker
  beat:      # Celery Beat (scheduler)
```

## Containers

### PostgreSQL

- **Imagem**: postgres:15
- **Porta**: 5433 (externa), 5432 (interna)
- **Volume**: `pgdata` para persistência

### Redis

- **Imagem**: redis:7
- **Porta**: 6379
- **Uso**: Cache de sessões, broker Celery

### Web (Django)

- **Porta**: 8002
- **Comando**: `gunicorn config.wsgi:application`
- **Variáveis**: Via `.env`

## Comandos Úteis

```bash
# Subir ambiente
docker compose -f v2/infra/docker-compose.yml up -d

# Ver logs
docker compose -f v2/infra/docker-compose.yml logs -f web

# Migrations
docker compose -f v2/infra/docker-compose.yml exec web python manage.py migrate

# Shell Django
docker compose -f v2/infra/docker-compose.yml exec web python manage.py shell

# Testes
docker compose -f v2/infra/docker-compose.yml exec web pytest
```

## CI/CD

O projeto usa GitHub Actions para CI:

- **Lint**: Black, isort, flake8, Pyright
- **Testes**: pytest com coverage (threshold 85%)
- **Deploy**: GitHub Pages (documentação)
