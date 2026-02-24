# Deploy

Guia de deploy do Aprender Sistema v2.

## Requisitos

- Docker Engine 24+
- Docker Compose v2
- Git
- 4GB RAM mínimo
- 20GB disco

## Release via GitHub Actions

Workflow: `.github/workflows/release.yaml`

Comportamento atual:
- Publica imagens Docker e executa deploy real por comando configurado para o ambiente selecionado.
- Se não houver comando configurado, o workflow falha explicitamente (não há falso sinal de deploy concluído).
- Gera artefato `deploy-evidence-<run_id>` com evidências da execução.

Configuração obrigatória por ambiente:
- `STAGING_DEPLOY_COMMAND` (secret ou variável de repositório)
- `PRODUCTION_DEPLOY_COMMAND` (secret ou variável de repositório)

Variáveis disponíveis para o comando:
- `TARGET_ENV`
- `RELEASE_VERSION`
- `IMAGE_TAG`
- `BACKEND_IMAGE`
- `FRONTEND_IMAGE`

## Deploy Local (Development)

```bash
# Clonar repositório
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema

# Subir ambiente
cd v2/infra
make up

# Verificar status
make healthz
```

## Deploy Staging

```bash
# Usar o slash command
/deploy-staging full

# Ou manualmente
cd v2/infra
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Variáveis de Ambiente (Staging)

```bash
# .env.staging
ENVIRONMENT=staging
DEBUG=False
SECRET_KEY=<generate-random-key>
ALLOWED_HOSTS=staging.aprender.com.br

# Database
DB_HOST=db
DB_PORT=5432
DB_NAME=aprender_staging
DB_USER=aprender
DB_PASSWORD=<secure-password>

# Redis
REDIS_URL=redis://redis:6379/0

# Google Calendar
GCAL_CLIENT=google
GCAL_CALENDAR_ID=<calendar-id>
GOOGLE_SERVICE_ACCOUNT_FILE=/secrets/sa-key.json

# Sentry
SENTRY_DSN=<sentry-dsn>
SENTRY_TRACES_SAMPLE_RATE=0.5
```

## Deploy Produção

### Checklist Pré-Deploy

- [ ] Testes passando (`make test`)
- [ ] Migrations aplicadas
- [ ] Variáveis de ambiente configuradas
- [ ] Secrets armazenados de forma segura
- [ ] Backup do banco realizado

### Comandos

```bash
# Build e push das imagens
docker build -t aprender-web:latest v2/backend
docker push registry.example.com/aprender-web:latest

# Deploy
docker compose -f docker-compose.prod.yml up -d

# Aplicar migrations
docker compose exec web python manage.py migrate

# Coletar static files
docker compose exec web python manage.py collectstatic --no-input
```

## Makefile

```bash
# Comandos disponíveis
make up          # Subir ambiente
make down        # Parar ambiente
make logs        # Ver logs
make shell       # Django shell
make test        # Rodar testes
make migrate     # Aplicar migrations
make healthz     # Health check
make readyz      # Ready check
```

## Rollback

```bash
# Ver histórico de deploys
docker compose ps --all

# Voltar para versão anterior
docker compose up -d --force-recreate web

# Ou restaurar backup do banco
docker compose exec db pg_restore -U aprender -d aprender_db backup.dump
```

## Monitoramento Pós-Deploy

1. Verificar logs: `docker compose logs -f web`
2. Verificar métricas: http://localhost:9090 (Prometheus)
3. Verificar Sentry para erros
4. Testar endpoints críticos
