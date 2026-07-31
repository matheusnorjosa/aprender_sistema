# Instalação

## Pré-requisitos

- Docker e Docker Compose v2
- Git
- Node.js 20 (só se você for rodar o frontend fora do Docker) — o CI e as imagens
  usam `node:20` (`.github/actions/setup-node-deps/action.yml`, `v2/frontend/Dockerfile`)

## Clone do Repositório

```bash
git clone https://github.com/matheusnorjosa/aprender_sistema.git
cd aprender_sistema
```

## Subindo o Ambiente (DEV)

O compose **exige** `IMAGE_TAG` e as credenciais do Postgres; um `docker compose up`
sem `--env-file` falha logo no parsing. O caminho canônico é criar o `.env.dev` a
partir do template e usar os alvos do `Makefile`:

```bash
cd v2/infra
cp .env.dev.example .env.dev     # edite as senhas CHANGE_ME_*
make check-env-dev               # valida o compose sem subir nada
make up-dev                      # compose + override de dev
make health-dev                  # curl em /api/readyz/
```

`make up-dev` equivale a:

```bash
docker compose --env-file .env.dev \
  -f docker-compose.yml -f docker-compose.override.yml up -d
```

Isso sobe **6 serviços**:

| Serviço | O que é | Porta no host (default) |
|---|---|---|
| `db` | PostgreSQL 15 | `DB_HOST_PORT` = **5434** |
| `redis` | Redis 7 | `REDIS_HOST_PORT` = **6380** |
| `web` | Django + Gunicorn | `BACKEND_HOST_PORT` = **8002** |
| `worker` | Celery worker | — |
| `beat` | Celery beat | — |
| `frontend` | build Vite servido em container | `FRONTEND_HOST_PORT` = **5173** |

As portas do host são configuráveis em `.env.dev`; dentro da rede do compose os
serviços continuam em 5432/6379/8000.

### Frontend fora do Docker (opcional)

O `make up-dev` já sobe o frontend. Se preferir rodar o Vite no host:

```bash
cd v2/frontend
npm install
npm run dev
```

## Verificando a Instalação

```bash
cd v2/infra

make ps      # status dos containers
make logs    # logs do backend (serviço `web`)
make shell   # Django shell
```

## Próximos Passos

- [Configuração](configuration.md)
- [Quick Start](quickstart.md)
- Matriz completa dev/staging/prod-like/prod: `v2/infra/ENVIRONMENTS.md`
