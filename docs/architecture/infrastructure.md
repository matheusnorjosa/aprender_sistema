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

O projeto usa GitHub Actions para CI/CD:

- **Lint**: Black, isort, flake8, Pyright
- **Testes**: pytest com coverage (threshold 85%)
- **Deploy** (pull-based, ADR-018): merge na `main` **não** deploya. Ele dispara `.github/workflows/deploy.yaml` ("Build, sign and release"), que faz build + scan + push da imagem com tag imutável `vYYYY.MM.DD-<sha>` e **assina** as imagens (cosign keyless + provenance SLSA). Levar a produção são dois passos deliberados: o `promote.yml` (atrás do GitHub Environment `production`, com *required reviewer*) assina um ponteiro de release no branch protegido `deploy-pointer`; e o agente `aprender-deployer`, na própria VM01, lê esse ponteiro, verifica as assinaturas e aplica **por digest** em `127.0.0.1:9443`, confirmando de dentro da VM. Isso substituiu o `PUT` do CI ao `:9443` público — o [ADR-010](project-decisions/ADR-010-deploy-portainer-direct-to-prod.md) foi superado nesse ponto. Não há ambiente de staging remoto; a validação pré-merge é o staging gate local (`v2/infra/scripts/staging-gate.sh`).
