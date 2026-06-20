# Configuração

## Variáveis de Ambiente

O sistema utiliza variáveis de ambiente para configuração. Copie o arquivo de exemplo:

```bash
cp v2/backend/.env.example v2/backend/.env
```

### Variáveis Principais

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `ENVIRONMENT` | Ambiente de execução | `development`, `staging`, `production` |
| `SECRET_KEY` | Chave secreta Django | `sua-chave-secreta` |
| `DEBUG` | Modo debug | `1` ou `0` |
| `DB_HOST` | Host do PostgreSQL | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5433` |
| `DB_NAME` | Nome do banco | `aprender_v2` |
| `REDIS_HOST` | Host do Redis | `localhost` |
| `REDIS_PORT` | Porta do Redis | `6379` |

### Google Calendar

| Variável | Descrição |
|----------|-----------|
| `GCAL_CLIENT` | Cliente a usar: `fake` (in-memory, default) ou `google` (API real) |
| `GCAL_AUTH_MODE` | Modo de auth quando `google`: `service_account` (default) ou `oauth` |
| `GCAL_CALENDAR_ID` | ID do calendário Google |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Credenciais da service account (JSON) |

## Configuração do Docker

O arquivo `v2/infra/docker-compose.yml` contém toda a configuração de infraestrutura.

### Portas Padrão

| Serviço | Porta |
|---------|-------|
| PostgreSQL | 5433 |
| Redis | 6379 |
| Backend | 8002 |
| Frontend | 5173 |
