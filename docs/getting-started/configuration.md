# Configuração

## Variáveis de Ambiente

Os templates versionados ficam em `v2/infra/`, um por ambiente. Para desenvolvimento:

```bash
cd v2/infra
cp .env.dev.example .env.dev
```

Os demais (não use em dev):

| Template | Arquivo local | Usado por |
|---|---|---|
| `.env.dev.example` | `.env.dev` | `make up-dev` (compose + override) |
| `.env.staging.example` | `.env.staging` | `make up-staging` e o staging gate |
| `.env.prodlike.example` | `.env.prodlike.local` | `make up-prod-like` (validação local) |
| `.env.production.example` | `.env.production` | template; **produção real** lê o `stack.env` do Portainer |

`v2/.env.example` é um catálogo de variáveis do backend, **não** um arquivo que o
compose carregue (o compose vive em `v2/infra/` e resolve `--env-file`/`APP_ENV_FILE`
relativos a esse diretório). Ele também está defasado — cita `localhost:3000` como
origem CORS, porta que o frontend não usa desde a migração para Vite.

### Variáveis Principais

| Variável | Descrição | Exemplo (dev) |
|----------|-----------|---------|
| `IMAGE_TAG` | Tag da imagem; **obrigatória**, o compose falha sem ela | `latest` |
| `APP_ENV_FILE` | Arquivo lido pelo `env_file` de `web`/`worker`/`beat` | `.env.dev` |
| `ENVIRONMENT` | Ambiente de execução | `development`, `staging`, `production` |
| `SECRET_KEY` | Chave secreta Django | `sua-chave-secreta` |
| `DEBUG` | Modo debug | `1` ou `0` |
| `DB_HOST` / `DB_PORT` | Postgres **dentro** da rede do compose | `db` / `5432` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Credenciais da aplicação | `aprender_db` / `aprender_user` / … |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Credenciais do container `db` (devem casar com as de cima) | idem |
| `REDIS_HOST` / `REDIS_PORT` | Redis dentro da rede do compose | `redis` / `6379` |

### Google Calendar

| Variável | Descrição |
|----------|-----------|
| `GCAL_CLIENT` | Cliente a usar: `fake` (in-memory, default) ou `google` (API real) |
| `GCAL_AUTH_MODE` | Modo de auth quando `google`: `service_account` (default) ou `oauth` |
| `GCAL_CALENDAR_ID` | ID do calendário Google |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Credenciais da service account (JSON ou path) |

Produção roda `GCAL_CLIENT=google` com `GCAL_AUTH_MODE=oauth`. O detalhamento
(escopos, `GCAL_OAUTH_*`, `GCAL_ENCRYPTION_KEY`, `GCAL_ALLOWED_DOMAIN`) está no
SSOT: **[GUIDE_GCAL.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/GUIDE_GCAL.md)**.

## Configuração do Docker

`v2/infra/docker-compose.yml` é a base (dev + staging); `docker-compose.override.yml`
adiciona build local e bind-mounts de código para dev. Produção usa
`docker-compose.prod.yml` **sozinho** — ver `v2/docs/specs/infra/deploy.spec.md`.

### Portas publicadas no host (defaults de DEV)

| Serviço | Variável | Porta |
|---------|----------|-------|
| PostgreSQL | `DB_HOST_PORT` | 5434 |
| Redis | `REDIS_HOST_PORT` | 6380 |
| Backend | `BACKEND_HOST_PORT` | 8002 |
| Frontend | `FRONTEND_HOST_PORT` | 5173 |

As portas altas evitam colisão com outras stacks locais (staging usa 18002/15173,
prod-like usa 28000/18081 — ver `v2/infra/ENVIRONMENTS.md`).
