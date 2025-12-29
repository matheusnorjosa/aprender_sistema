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
| `GCAL_CLIENT` | Cliente a usar: `fake` ou `google` |
| `GCAL_CALENDAR_ID` | ID do calendário Google |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Caminho para credenciais |

### ETL

| Variável | Descrição |
|----------|-----------|
| `ETL_OUTPUT_DIR` | Diretório para relatórios ETL |
| `ETL_DATA_DIR` | Diretório com arquivos CSV/Excel |

## Configuração do Docker

O arquivo `v2/infra/docker-compose.yml` contém toda a configuração de infraestrutura.

### Portas Padrão

| Serviço | Porta |
|---------|-------|
| PostgreSQL | 5433 |
| Redis | 6379 |
| Backend | 8002 |
| Frontend | 5173 |
