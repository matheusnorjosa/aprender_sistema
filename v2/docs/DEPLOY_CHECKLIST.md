# Deploy Checklist — Produção

Checklist de variáveis de ambiente para deploy em produção.

---

## Variáveis Obrigatórias

### Segurança

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `SECRET_KEY` | Chave forte (50+ chars) | Gerar com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `0` | Nunca `1` em produção |
| `ALLOWED_HOSTS` | `dominio.com.br` | Domínio(s) real(is), separados por vírgula |
| `CORS_ALLOWED_ORIGINS` | `https://dominio.com.br` | Origem(ns) HTTPS |
| `CSRF_TRUSTED_ORIGINS` | `https://dominio.com.br` | Origem(ns) HTTPS |

### Módulos Opcionais

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `INCLUDE_ETL` | `false` | Exclui módulo ETL (dat_ingest) |
| `INCLUDE_DEV_TOOLS` | `false` | Exclui comandos de seed/dev |

### Google Calendar

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `GCAL_CLIENT` | `google` | Usa API real (não `fake`) |
| `GCAL_CALENDAR_ID` | `<calendar-id>` | ID do calendário Google |
| `GCAL_ENCRYPTION_KEY` | `<fernet-key>` | Chave para criptografar tokens OAuth |

### Entrypoint

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `CREATE_SUPERUSER` | `0` | Não criar superuser automático |
| `RUN_MIGRATIONS` | `1` | Rodar migrations no startup |
| `COLLECT_STATIC` | `1` | Coletar arquivos estáticos |

### Banco de Dados

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `DB_HOST` | `<host>` | Host do PostgreSQL |
| `DB_PORT` | `5432` | Porta do PostgreSQL |
| `DB_NAME` | `<database>` | Nome do banco |
| `DB_USER` | `<user>` | Usuário do banco |
| `DB_PASSWORD` | `<password>` | Senha do banco |

### Redis/Celery

| Variável | Valor Prod | Descrição |
|----------|------------|-----------|
| `REDIS_HOST` | `<host>` | Host do Redis |
| `REDIS_PORT` | `6379` | Porta do Redis |
| `CELERY_BROKER_URL` | `redis://<host>:6379/0` | URL do broker Celery |

### GitHub Release Workflow (Deploy + Verificação)

Use **secrets** ou **variables** com os mesmos nomes (secrets têm prioridade):

| Variável | Escopo | Obrigatória | Descrição |
|----------|--------|-------------|-----------|
| `STAGING_DEPLOY_COMMAND` | staging | Sim (staging) | Comando real de deploy executado no workflow `Release` |
| `PRODUCTION_DEPLOY_COMMAND` | production | Sim (production) | Comando real de deploy executado no workflow `Release` |
| `STAGING_HEALTHCHECK_URL` | staging | Sim (staging) | Endpoint HTTP 200 para validar saúde pós-deploy |
| `PRODUCTION_HEALTHCHECK_URL` | production | Sim (production) | Endpoint HTTP 200 para validar saúde pós-deploy |
| `STAGING_VERSIONCHECK_URL` | staging | Sim (staging) | Endpoint que retorna a versão release implantada |
| `PRODUCTION_VERSIONCHECK_URL` | production | Sim (production) | Endpoint que retorna a versão release implantada |

---

## Exemplo de .env para Produção

```bash
# Segurança
SECRET_KEY=<gerar-chave-forte>
DEBUG=0
ENVIRONMENT=production
ALLOWED_HOSTS=aprender.com.br
CORS_ALLOWED_ORIGINS=https://aprender.com.br
CSRF_TRUSTED_ORIGINS=https://aprender.com.br

# Módulos
INCLUDE_ETL=false
INCLUDE_DEV_TOOLS=false

# Google Calendar
GCAL_CLIENT=google
GCAL_CALENDAR_ID=<calendar-id>@group.calendar.google.com
GCAL_ENCRYPTION_KEY=<fernet-key>

# Entrypoint
CREATE_SUPERUSER=0
RUN_MIGRATIONS=1
COLLECT_STATIC=1

# Banco de Dados
DB_HOST=db.exemplo.com
DB_PORT=5432
DB_NAME=aprender_prod
DB_USER=aprender_user
DB_PASSWORD=<senha-forte>

# Redis
REDIS_HOST=redis.exemplo.com
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis.exemplo.com:6379/0
```

---

## Validações Automáticas

O sistema valida automaticamente em produção (`ENVIRONMENT=production`):

| Validação | Ação |
|-----------|------|
| `DEBUG=1` | ❌ Erro fatal, não inicia |
| `ALLOWED_HOSTS=['*']` | ❌ Erro fatal, não inicia |
| `SECRET_KEY` < 50 chars | ⚠️ Warning no log |
| `GCAL_CLIENT=fake` | ⚠️ Warning no log |

---

## Comandos de Deploy

```bash
# Build da imagem
docker build -t aprender:prod -f infra/Dockerfile .

# Deploy com variáveis de produção
docker compose -f docker-compose.yml up -d

# Verificar logs
docker compose logs -f web

# Verificar health
curl https://aprender.com.br/healthz/
```

---

## Pós-Deploy

- [ ] Verificar `/healthz/` retorna `{"status": "ok"}`
- [ ] Verificar endpoint de versão contém a release atual (`vYYYY.MM.DD-<sha>`)
- [ ] Verificar logs sem erros
- [ ] Testar login de usuário
- [ ] Verificar integração Google Calendar (se `GCAL_CLIENT=google`)
- [ ] Verificar Prometheus metrics (`/metrics/`)
- [ ] Confirmar artifacts de supply chain na release:
  - [ ] `backend-sbom.spdx.json`
  - [ ] `frontend-sbom.spdx.json`
  - [ ] bundles de provenance (`*.bundle.jsonl`)
  - [ ] `deploy-evidence.txt`
