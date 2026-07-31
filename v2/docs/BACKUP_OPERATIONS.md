# Backup Operations Guide — AS v2

**Status**: ⚠️ Backup grava; **restore pela ferramenta oficial está quebrado** (#1611)
**Refs**: Issue #169, PR #186, SEC-017 (criptografia), #1455, #1541
**Last Updated**: 2026-07-24 (revisão contra o código — auditoria M26)

> **SSOT de operações de backup do AS v2.** Outros docs (`DISASTER_RECOVERY.md`,
> `GUIDE_DR.md`, `SLO_DEFINITIONS.md`, `docs/operations/backup.md`) devem apontar
> para este arquivo em vez de duplicar parâmetros.

## Estado real do restore

⛔ **Leia esta seção antes de confiar neste pipeline.**

| Pergunta | Resposta honesta |
|---|---|
| O backup é gerado? | O wiring existe e é *fail-closed*: task Celery no `worker` às 02:00, bind-mount `/backups`, recipient `age` fixo no compose. **Se está rodando hoje em prod, não foi verificado neste documento.** |
| O backup é cifrado? | Sim, sempre. `backup_db.sh:44-48` **aborta** sem `BACKUP_AGE_RECIPIENT`. Produção grava só `.sql.gz.age`. |
| O backup é restaurável? | **Não sabemos.** Nenhum ensaio de restore com a chave privada foi registrado (ver [Último ensaio de restore](#último-ensaio-de-restore)). |
| `restore_db.sh` funciona? | **Não, para backups de produção.** `restore_db.sh:91` roda `gzip -t` incondicionalmente, antes do branch `.age` de `:113-119`, e aborta com `ERROR: Backup file is corrupted!` — mensagem **falsa**. Issue [#1611](https://github.com/matheusnorjosa/aprender_sistema/issues/1611). |

O restore que funciona hoje é manual e precisa da **chave privada `age`**, que por design
**não fica na VM** (`verify_backup.sh:41-43`) — está no gerenciador de senhas do mantenedor:

```bash
# 1) verificar SEM destruir
age -d -i /etc/backup-key.txt backup_full_<DATA>.sql.gz.age | gzip -t && echo OK
# 2) restaurar
age -d -i /etc/backup-key.txt backup_full_<DATA>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1
```

Passo a passo completo:
[GUIDE_DR.md → Restore Completo](./GUIDE_DR.md#restore-completo-desastre-total).

Precedente que justifica esse ceticismo: issue
[#1537](https://github.com/matheusnorjosa/aprender_sistema/issues/1537) — um backup que
nunca rodou, e ninguém percebeu porque o runbook dizia que rodava.

## Parâmetros canônicos (RPO / RTO / Retenção / Frequência)

| Métrica | Valor | Nota |
|---|---|---|
| **RPO** (Recovery Point Objective) | **5 minutos** | WAL archiving contínuo (`archive_timeout=300`) |
| **RTO** (Recovery Time Objective) | **1 hora** | Inclui restore + migrations + smoke; restore puro é tipicamente 10-30 min em base atual |
| **Retenção padrão** | **7 dias** | Configurável via `BACKUP_RETENTION_DAYS`; S3 pode ter lifecycle policy mais longa |
| **Frequência** | **1×/dia** | 2:00 AM em Docker (Celery beat) / 3:00 AM em VM (cron) — janela noturna |
| **Verificação** | Semanal (domingos) | `verify_backup_health` (Docker) ou `verify_backup.sh` (VM) |

## Overview

The AS v2 backup system provides automated PostgreSQL backups with:

- **Daily full backups** (parâmetros acima)
- **age encryption at rest** (SEC-017) — **obrigatória na prática**: sem
  `BACKUP_AGE_RECIPIENT` e sem `BACKUP_ALLOW_PLAINTEXT=1` o script **recusa gerar o dump**
  (`backup_db.sh:44-48`, fail-closed). Produção define o recipient em
  `docker-compose.prod.yml:197`.
- **S3/MinIO upload** (opt-in via `S3_BUCKET`) — ⚠️ **indisponível nas imagens atuais**:
  nenhum Dockerfile do projeto instala o `aws` CLI (`Dockerfile.prod:56`,
  `Dockerfile.dev:19-21`).
- **Health checks** semanais — ver a ressalva em [Health Monitoring](#health-monitoring):
  para artefatos `.age` eles conferem **presença/tamanho/frescor**, não restaurabilidade.
- **Failure alerting** via Sentry — **só se `SENTRY_DSN` estiver configurado**; estava
  ausente em produção na última verificação (ver [OBSERVABILITY.md](./OBSERVABILITY.md)).
- **Disaster recovery** — ⛔ procedimento de restore **não testado** e ferramenta oficial
  quebrada (#1611).

## Contextos suportados (mesmo script `backup_db.sh`)

| Contexto | Quem dispara | Storage | Doc complementar |
|---|---|---|---|
| **Produção (VM01, Docker/Portainer)** | Celery Beat 2:00 AM → task no serviço **`worker`** (`config/celery.py:38-40`, `tasks_backup.py:57`) | bind-mount **`/var/backups/aprender:/backups`** no `worker` (`docker-compose.prod.yml:235`) | `DISASTER_RECOVERY.md` (cenários de recovery) |
| **Dev/staging (Docker Compose)** | Celery Beat 2:00 AM | volume `backup_data` → `/backups` (`docker-compose.yml:16`) | `DISASTER_RECOVERY.md` |
| **VM02 (PostgreSQL nativo)** | Cron 3:00 AM (`/etc/cron.d/aprender-backup`) — **instalação não verificada** | `/var/backups/aprender` | `GUIDE_DR.md` (PITR via WAL) |

Em todos os contextos o script `v2/infra/scripts/backup_db.sh` é o **mesmo**; muda a
chamada (Celery vs cron) e os defaults das env vars (`BACKUP_DIR=/backups` no container
vs `/var/backups/aprender` na VM).

> **Atenção ao alvo do `docker compose exec`:** o `/backups` existe **apenas no serviço
> `worker`** em produção. `docker compose exec web ls /backups` e
> `docker compose exec db ls /backups` **falham** — e em produção nem existe serviço `db`
> (o PostgreSQL é externo, na VM02).

## Architecture

### Components

1. **Backup Script** (`v2/infra/scripts/backup_db.sh`)
   - `pg_dump | gzip | age -r $BACKUP_AGE_RECIPIENT` (`:69-72`) — **cifrado**, não só
     comprimido
   - `set -euo pipefail` (`:23`): falha do `pg_dump` no meio do pipe **aborta** em vez de
     gravar um dump truncado que se disfarça de sucesso (audit #1541)
   - Fail-closed sem recipient (`:44-48`)
   - S3 upload (opt-in via `S3_BUCKET`; hoje sem `aws` CLI na imagem)
   - Retention com glob que cobre `.sql.gz` **e** `.sql.gz.age` (`:103`)
   - Log em stdout (capturado pelo Docker; sem arquivo `.log` em Docker)

2. **Restore Script** (`v2/infra/scripts/restore_db.sh`) — ⛔ **quebrado para prod (#1611)**
   - Interactive restoration with confirmation
   - `:91` roda `gzip -t` **antes** do branch `.age` de `:113-119` → aborta em todo backup
     de produção com `ERROR: Backup file is corrupted!` (mensagem falsa)
   - `:17` hardcoda `BACKUP_DIR=/var/backups/aprender` e **ignora** a env var, então
     `--latest` não acha nada de dentro do container (onde o diretório é `/backups`)
   - `:128` declara `Restore completed successfully!` com exit 0 mesmo após restore
     incompleto — não há `ON_ERROR_STOP` no `psql` de `:116/:118`
     (issue [#1645](https://github.com/matheusnorjosa/aprender_sistema/issues/1645))
   - Zero cobertura: não existe `.bats` para este script

3. **Celery Tasks** (`v2/backend/apps/core/tasks_backup.py`)
   - `backup.perform_database_backup` - Main backup task
   - `backup.verify_backup_health` - Health monitoring

4. **Celery Beat Schedule** (`v2/backend/config/celery.py`)
   - Daily backup at 2:00 AM
   - Weekly health check on Sundays at 3:00 AM

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat (2:00 AM daily)                                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Celery Worker: backup.perform_database_backup              │
│ - Validates environment                                     │
│ - Executes backup_db.sh                                     │
│ - Monitors execution (1h timeout)                           │
│ - Retries on failure (3x, exponential backoff)             │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ backup_db.sh                                                │
│ 1. Exige BACKUP_AGE_RECIPIENT (senão ABORTA — fail-closed)  │
│ 2. pg_dump | gzip | age -r  -> backup_full_*.sql.gz.age     │
│ 3. Upload S3 (opt-in; sem `aws` na imagem hoje)             │
│ 4. Retenção (.sql.gz E .sql.gz.age)                         │
│ 5. Log em stdout + Sentry na falha (se SENTRY_DSN)          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Storage Destinations                                        │
│ - prod:  bind-mount host /var/backups/aprender  (worker)    │
│ - dev:   volume Docker `backup_data` -> /backups            │
│ - Remote: S3/MinIO (opt-in, hoje NÃO funcional)             │
└─────────────────────────────────────────────────────────────┘
```

> O `worker` é o **único** serviço com `/backups`. Se `docker compose exec web ls /backups`
> falhar, isso é o esperado — não é sintoma de backup quebrado.

## Configuration

### Environment Variables

Add to `v2/infra/.env`:

```bash
# Automated Backups (MP5)
BACKUP_DIR=/backups
BACKUP_RETENTION_DAYS=7
BACKUP_S3_BUCKET=  # Optional: s3://your-bucket-name

# Sentry (for failure alerts)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

### Docker Volumes

**Dev/staging** (`v2/infra/docker-compose.yml:16-17`) — volume nomeado, montado nos
serviços que compartilham o bloco comum:

```yaml
      - backup_data:/backups            # MP5: Database backups storage
      - ./scripts:/app/infra/scripts:ro # MP5: Backup scripts

volumes:
  backup_data:
```

**Produção** (`v2/infra/docker-compose.prod.yml:235`) — bind-mount do host, **só no
`worker`**, porque o root filesystem dos containers é `read_only`:

```yaml
  worker:
    volumes:
      - /var/backups/aprender:/backups
```

O diretório do host precisa existir **antes** do deploy (0755, dono = UID do `appuser`).
Sem esse mount, o job falha em silêncio — foi a causa raiz do
[#1455](https://github.com/matheusnorjosa/aprender_sistema/issues/1455). Os scripts vêm da
**imagem** (`Dockerfile.prod:67`), não de bind-mount, em prod.

### S3/MinIO Setup (opt-in, hoje não funcional)

`backup_db.sh:87-89` só tenta o upload se a env var **`S3_BUCKET`** estiver preenchida (a
task Celery mapeia a setting Django `BACKUP_S3_BUCKET` → `S3_BUCKET` em
`tasks_backup.py:78`). **Mas nenhuma imagem do projeto instala o `aws` CLI** — conferido em
`Dockerfile.prod:56` e `Dockerfile.dev:19-21`. Com `S3_BUCKET` preenchido hoje, o upload
falha e o script emite `WARNING: S3 upload FAILED (offsite copy missing)` no stderr
(`backup_db.sh:90-94`) sem abortar o backup local.

Para habilitar de verdade seria preciso, além do abaixo, **adicionar o `aws` CLI à imagem**:

1. **AWS Credentials** (no environment do serviço `worker`):
   ```bash
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_DEFAULT_REGION=us-east-1
   ```

2. **Configure Bucket** (`.env` / stack.env):
   ```bash
   BACKUP_S3_BUCKET=s3://aprender-backups/v2/
   ```

## Usage

### Manual Backup

Execute a partir do container **`worker`** (é ele que tem `/backups` e o
`BACKUP_AGE_RECIPIENT`):

```bash
cd v2/infra
docker compose exec -T worker /app/infra/scripts/backup_db.sh

# Conferir os arquivos gerados (nome real: backup_full_*.sql.gz.age)
docker compose exec -T worker ls -lh /backups/
```

> O script **não aceita argumentos**: `backup_db.sh` nunca lê `$1`. O `full` que a task
> Celery passa (`tasks_backup.py:85`) é inerte — o dump é sempre completo.
> Em dev, sem `BACKUP_AGE_RECIPIENT`, o script **aborta** (fail-closed); para um dump em
> texto claro local, use `BACKUP_ALLOW_PLAINTEXT=1` explicitamente
> (`backup_db.sh:43-48`).

### Manual Restore

⛔ **Não use `restore_db.sh` contra um backup de produção** — ver
[Estado real do restore](#estado-real-do-restore)
e issue #1611. Procedimento que funciona:

```bash
# 1. Listar backups reais
docker compose exec -T worker ls -lht /backups/

# 2. Verificar integridade SEM destruir nada (precisa da chave privada age)
docker compose exec -T worker sh -c \
  'age -d -i /etc/backup-key.txt /backups/backup_full_<DATA>.sql.gz.age | gzip -t' \
  && echo "INTEGRIDADE OK"

# 3. Restaurar (DESTRUTIVO — só após o passo 2 sair 0)
docker compose exec -T worker sh -c \
  'age -d -i /etc/backup-key.txt /backups/backup_full_<DATA>.sql.gz.age | gunzip \
   | psql -h "$DB_HOST" -U postgres -d "$DB_NAME" -v ON_ERROR_STOP=1'

# 4. Conferir explicitamente (não confie em exit 0 — ver #1645)
docker compose exec -T worker psql -h "$DB_HOST" -U postgres -d "$DB_NAME" \
  -c "SELECT count(*) FROM core_usuario;"
```

**Pré-requisitos**:
- Chave privada `age` — **não fica na VM por design** (`verify_backup.sh:41-43`); está no
  gerenciador de senhas do mantenedor. Copie para `/etc/backup-key.txt` com `chmod 600` e
  **apague ao final**.
- Binário `age` — presente na imagem de **produção** (`Dockerfile.prod:56`),
  **ausente** na imagem dev (`Dockerfile.dev:19-21`).

**Warning**: o restore sobrescreve todos os dados, e a aplicação precisa estar parada
(`web`, `worker`, `beat`) para não escrever durante a operação. Isso conflita com rodar os
comandos acima *dentro* do `worker`. Escolha um dos dois veículos:

- **Do host da VM** — precisa de `age` e `postgresql-client` instalados lá; o dump está em
  `/var/backups/aprender`. É o caminho descrito em
  [GUIDE_DR.md → Restore Completo](./GUIDE_DR.md#restore-completo-desastre-total).
- **Container efêmero** da mesma imagem de backend (tem `age` e `psql`), com os serviços da
  stack parados:
  ```bash
  docker run --rm -i \
    -v /var/backups/aprender:/backups:ro \
    -v /etc/backup-key.txt:/etc/backup-key.txt:ro \
    norjosamatheus/aprender-backend:<IMAGE_TAG> \
    sh -c 'age -d -i /etc/backup-key.txt /backups/backup_full_<DATA>.sql.gz.age | gunzip \
           | psql -h <DB_HOST> -U postgres -d aprender_db -v ON_ERROR_STOP=1'
  ```

### Trigger Backup Task via Celery

```bash
# Enter Django shell
docker compose exec web python manage.py shell

# Trigger backup task
from apps.core.tasks_backup import perform_database_backup
result = perform_database_backup.delay("full")
print(f"Task ID: {result.id}")
```

### Monitor Backup Status

```bash
# Logs do backup — saem no stdout do worker (o script não escreve arquivo .log
# em Docker; o redirecionamento para /var/log/aprender/backup.log só existe no
# cron da VM, v2/infra/cron/aprender-backup:14)
docker compose logs --tail=200 worker | grep -i backup

# Último backup (o /backups só existe no worker)
docker compose exec -T worker ls -lht /backups/ | head -5
```

## Scheduled Backups

### Celery Beat Schedule

Configured in `v2/backend/config/celery.py`:

| Task | Schedule | Description |
|------|----------|-------------|
| `daily-database-backup` | Daily at 2:00 AM | Full pg_dump backup |
| `weekly-backup-health-check` | Sundays at 3:00 AM | Verify backup system health |

### Verify Schedule

A SSOT do schedule é `v2/backend/config/celery.py:35-56` (`daily-database-backup` às 02:00,
`weekly-backup-health-check` domingos 03:00). Em produção o beat roda com o **scheduler
padrão** (`docker-compose.prod.yml:243`:
`celery -A config beat -l info --schedule /tmp/celerybeat-schedule`), que é quem lê esse
schedule do código — e **não** o `DatabaseScheduler` do `django_celery_beat`.

```bash
# O beat está disparando? (logs do próprio beat)
docker compose logs --tail=200 beat | grep -i "database-backup"

# O worker executou? (é ele que roda a task e grava o dump)
docker compose logs --tail=200 worker | grep -i "perform_database_backup"
```

> `celery -A config inspect scheduled` **não** mostra o `beat_schedule`: ele consulta os
> *workers* pelo broker e lista tarefas com ETA/countdown. Para saber se o beat está
> agendando, olhe os logs do `beat`; para saber se o worker executou, olhe os logs do
> `worker`.

## Health Monitoring

### Weekly Health Check

The `backup.verify_backup_health` task runs every Sunday at 3:00 AM and checks:

1. **Backup directory exists and is writable**
2. **Recent backup exists** (within last 25 hours)
3. **S3 connectivity** (if configured)

Results are logged and sent to Sentry **se `SENTRY_DSN` estiver configurado** — o que não
era o caso em produção na última verificação.

> ⚠️ **O que esses checks NÃO provam.** Nem esta task nem o `verify_backup.sh` abrem um
> artefato `.age`: `verify_backup.sh:44-48` pula explicitamente a checagem de conteúdo
> porque a chave privada não vive na VM. O mesmo vale para o gate de deploy
> `v2/infra/deployer/hooks/check_backup.sh`, que só faz `stat` (idade ≤ 28h, tamanho ≥
> 1024B). Ou seja: **"health check verde" significa "existe, é recente e não é minúsculo"**,
> não "é restaurável". A única evidência de restaurabilidade é um ensaio com a chave —
> ver [Último ensaio de restore](#último-ensaio-de-restore).

### Manual Health Check

```bash
# Run health check manually
docker compose exec web python manage.py shell

from apps.core.tasks_backup import verify_backup_health
result = verify_backup_health()
print(result)
```

Expected output:
```python
{
    'status': 'healthy',  # or 'degraded'
    'checks_passed': 3,
    'checks_total': 3,
    'warnings': []  # List of issues if degraded
}
```

## Failure Handling

### Retry Policy

Backup tasks automatically retry on failure:
- **Max retries**: 3
- **Delay**: 5 minutes (300s) with exponential backoff
- **Timeout**: 1 hour per backup attempt

### Sentry Alerts

Failures are sent to Sentry when `SENTRY_DSN` is configured:
- Backup script failures (exit code != 0)
- Task timeouts
- Task retries exhausted
- Health check warnings

### Common Failures

| Issue | Cause | Solution |
|-------|-------|----------|
| `ERROR: BACKUP_AGE_RECIPIENT ausente...` | Recipient sumiu do environment do `worker` | Fail-closed proposital (`backup_db.sh:44-48`). Repor o valor em `docker-compose.prod.yml:197` **e** no Portainer. Em dev, `BACKUP_ALLOW_PLAINTEXT=1` |
| `pg_dump: connection failed` | Banco inalcançável | Conferir `DB_HOST`/`DB_PORT`. **Em produção não existe serviço `db`** — o PostgreSQL é externo (VM02) |
| `Permission denied: /backups` | Bind-mount ausente ou dono errado | Criar `/var/backups/aprender` no host (0755, dono = UID do `appuser`); o root FS do container é `read_only`, só o mount é gravável |
| Nada em `/backups` e nenhum erro | `docker compose exec` no serviço errado | O `/backups` só existe no **`worker`** (`docker-compose.prod.yml:235`) |
| `S3 upload FAILED (offsite copy missing)` | `aws` CLI **não existe na imagem** | Ver [S3/MinIO Setup](#s3minio-setup-opt-in-hoje-não-funcional). O backup **local** segue válido — o script não re-roda o `pg_dump` (`backup_db.sh:90-94`) |
| `Backup timed out` | Banco grande (>1h) | Aumentar o `timeout` de `subprocess.run` em `tasks_backup.py:90` |

## Disaster Recovery

### Restore Procedure

**Scenario**: Production database corrupted, need to restore from backup.

O procedimento canônico está em
[GUIDE_DR.md → Restore Completo](./GUIDE_DR.md#restore-completo-desastre-total). Resumo:

1. **Obter a chave privada `age`** do gerenciador de senhas e colocá-la em
   `/etc/backup-key.txt` (`chmod 600`). Sem ela, nenhum backup de produção pode ser lido.

2. **Parar os serviços** (evitar escrita durante o restore):
   ```bash
   docker compose -f docker-compose.prod.yml stop web worker beat
   ```

3. **Listar backups** — no host da VM, onde o bind-mount aponta:
   ```bash
   ls -lht /var/backups/aprender/backup_full_*.sql.gz.age | head -5
   ```

4. **Verificar ANTES de destruir**:
   ```bash
   age -d -i /etc/backup-key.txt \
     /var/backups/aprender/backup_full_<DATA>.sql.gz.age | gzip -t && echo OK
   ```

5. **Restaurar** (pipeline manual — `restore_db.sh` está quebrado, #1611):
   ```bash
   age -d -i /etc/backup-key.txt \
     /var/backups/aprender/backup_full_<DATA>.sql.gz.age | gunzip \
     | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1
   ```

6. **Verificar a restauração explicitamente** (exit 0 não é prova — #1645):
   ```bash
   psql -h "$DB_HOST" -U postgres -d aprender_db \
     -c "SELECT COUNT(*) FROM core_solicitacao;"
   ```

7. **Subir a stack** (o one-shot `migrate` aplica migrations antes de web/worker/beat):
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

8. **Apagar a chave privada do host**: `shred -u /etc/backup-key.txt`

### Recovery Time Objective (RTO)

- **Expected RTO**: 10-30 minutos de restore puro (dentro do RTO canônico de 1h)
- **Bottlenecks**:
  - Obter a **chave privada `age`** do gerenciador de senhas (não está na VM) —
    contabilize esse tempo, é serial e depende de uma pessoa
  - Tamanho do banco (`age -d | gunzip | psql`)
  - Derrubar conexões ativas (mínimo)
- ⚠️ **Risco de estourar o RTO**: um operador que siga o runbook antigo roda
  `restore_db.sh`, recebe `ERROR: Backup file is corrupted!` (#1611) e pode concluir que a
  cadeia inteira de backups está corrompida. Esse desvio custa mais tempo do que o restore
  em si. Use o pipeline manual desde o início.

### Recovery Point Objective (RPO)

- **RPO alvo**: 5 minutos (WAL archiving + daily full dump)
- ⚠️ **RPO efetivo, hoje**: **até 24h** — o WAL archiving da VM02 **não foi verificado**
  (ver [GUIDE_DR.md → WAL Archiving](./GUIDE_DR.md#1-wal-archiving-point-in-time-recovery)).
  Sem WAL confirmado, a única linha de defesa é o dump diário das 02:00.
- **Daily dump**: `pg_dump` completo, cifrado, como baseline para PITR

## Testing

### Test Backup Script

```bash
# Sem upload offsite: a env var lida pelo SCRIPT é S3_BUCKET
# (a task Celery é que mapeia a setting Django BACKUP_S3_BUCKET → S3_BUCKET,
#  tasks_backup.py:78). Passar BACKUP_S3_BUCKET="" ao script direto NÃO tem efeito.
docker compose exec -T worker sh -c 'S3_BUCKET="" /app/infra/scripts/backup_db.sh'

# Verificar o arquivo gerado
docker compose exec -T worker ls -lh /backups/
```

### Test Restore Script

⛔ **`restore_db.sh` não pode ser usado como teste de DR hoje**: contra o formato de
produção (`.age`) ele sempre aborta com `ERROR: Backup file is corrupted!` (#1611); contra
um `.sql.gz` em texto claro ele passa, mas então o teste **não** exercita o formato real —
é a mesma cegueira do `test_dr.sh` (#1646).

O ensaio válido, com a chave privada e fora de produção, está em
[GUIDE_DR.md → Ensaio de DR](./GUIDE_DR.md#ensaio-de-dr-o-único-teste-que-vale).

Cobertura de teste automatizado do `restore_db.sh`: **zero**. Não existe `.bats` para ele
(os únicos bats do repositório cobrem `v2/infra/deployer/`).

### Test Celery Tasks

```bash
# Testes das tasks de backup (MP5)
docker compose exec -T web pytest apps/core/tests/test_tasks_mp5.py -v
```

## Metrics and Monitoring

### Key Metrics

Track these metrics in production:

1. **Backup Success Rate**: % of successful backups (target: >99%)
2. **Backup Duration**: Time to complete backup (monitor for increases)
3. **Backup Size**: Disk usage trend (capacity planning)
4. **S3 Upload Duration**: Network performance
5. **Restore Test Success**: Monthly restore drills

### Prometheus Metrics (Future)

Potential metrics to export (MP1 integration):

```python
# Example Prometheus metrics
backup_duration_seconds = Histogram('backup_duration_seconds', 'Backup execution time')
backup_size_bytes = Gauge('backup_size_bytes', 'Latest backup file size')
backup_success_total = Counter('backup_success_total', 'Successful backups')
backup_failure_total = Counter('backup_failure_total', 'Failed backups')
```

## Security

### Access Control

- **Backup files**: em produção ficam no host (`/var/backups/aprender`) e são visíveis
  apenas pelo container **`worker`** (único com o bind-mount) e por quem tem SSH na VM
- **S3 bucket**: Use IAM roles with minimal permissions (s3:PutObject, s3:GetObject)
- **Database credentials**: Never log `PGPASSWORD` in backup logs

### Data Encryption

- **Backup files**: **cifrados com `age`** (SEC-017). O dump é
  `pg_dump | gzip | age -r $BACKUP_AGE_RECIPIENT` (`backup_db.sh:69-72`). O recipient é a
  chave **pública** (só cifra) e está fixo em `docker-compose.prod.yml:197`; a chave
  **privada** nunca entra no repositório nem na VM — fica no gerenciador de senhas do
  mantenedor.
- **Consequência operacional**: quem tem acesso ao disco de backup **não** consegue ler PII;
  e quem restaura **precisa** buscar a chave privada antes. Sem a chave, o backup é
  inutilizável — o que faz da custódia dessa chave um ponto único de falha do DR.
- **Rotação**: trocar o valor em `docker-compose.prod.yml` **e** no `environment:` do
  `worker` no Portainer. Dumps antigos continuam exigindo a chave privada **antiga** —
  guarde as duas até a retenção expirar.
- **At rest (S3)**: S3 bucket encryption (AES-256 ou KMS), se o offsite for habilitado
- **In transit**: HTTPS for S3 uploads, TLS for database connections

**Recommendation**: Enable S3 server-side encryption (SSE-S3 or SSE-KMS):

```bash
aws s3api put-bucket-encryption \
  --bucket aprender-backups \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

## Maintenance

### Retention Policy

Default: 7 days (configurable via `BACKUP_RETENTION_DAYS`)

**Policy logic** — literal de `backup_db.sh:103`:
```bash
find "$BACKUP_DIR" \
  \( -name "backup_full_*.sql.gz" -o -name "backup_full_*.sql.gz.age" \) \
  -mtime +"$BACKUP_RETENTION_DAYS" -delete 2>/dev/null || true
```

> ⚠️ **Qualquer limpeza que use só `*.sql.gz` é cega aos arquivos reais.** É o caso da linha
> 17 de `v2/infra/cron/aprender-backup`
> (`find /var/backups/aprender -name "*.sql.gz" -mtime +7 -delete`), que nunca casa com
> `backup_full_*.sql.gz.age` — e é redundante, já que o script acima faz a retenção. Se
> escrever limpeza manual, use **os dois globs**.

**Manual cleanup**:
```bash
# Listar backups com mais de 30 dias
docker compose exec -T worker find /backups \
  \( -name "backup_full_*.sql.gz" -o -name "backup_full_*.sql.gz.age" \) -mtime +30

# Apagar
docker compose exec -T worker find /backups \
  \( -name "backup_full_*.sql.gz" -o -name "backup_full_*.sql.gz.age" \) -mtime +30 -delete
```

### Storage Capacity

Monitor disk usage (do host ou do `worker` — os demais serviços não montam `/backups`):

```bash
docker compose exec -T worker df -h /backups
docker compose exec -T worker du -h /backups/backup_full_* | sort -h
```

**Capacity planning**:
- Estimate daily backup size: ~10-50 MB per GB of database
- With 7-day retention: `7 × daily_backup_size`
- Add 20% buffer for growth

### Rotate S3 Buckets

S3 lifecycle policy example (delete backups >30 days):

```json
{
  "Rules": [
    {
      "Id": "Delete old backups",
      "Status": "Enabled",
      "Prefix": "v2/backups/",
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

Apply via AWS CLI:
```bash
aws s3api put-bucket-lifecycle-configuration \
  --bucket aprender-backups \
  --lifecycle-configuration file://lifecycle.json
```

## Troubleshooting

### Backup Not Running

**Symptoms**: No new backups in `/backups/` after 2:00 AM

**Diagnosis**:
```bash
# Check Celery Beat is running
docker compose ps beat

# Check Celery Beat logs
docker compose logs beat | grep "daily-database-backup"

# Check worker logs
docker compose logs worker | grep "backup.perform_database_backup"
```

**Common causes**:
- Beat container not running: `docker compose up -d beat`
- Wrong timezone: Verify `CELERY_TIMEZONE=America/Fortaleza` in settings
- Task queue full: `docker compose exec worker celery -A config purge`
- **Bind-mount `/backups` ausente/não gravável no `worker`** — causa raiz do #1455; o root
  FS é `read_only`, então sem o mount o job falha em silêncio
- **`BACKUP_AGE_RECIPIENT` sumiu** do environment do `worker` → o script aborta
  (fail-closed). Conferir:
  `docker compose exec -T worker printenv | grep BACKUP_AGE_RECIPIENT`

### Backup Fails with "pg_dump: connection failed"

**Symptoms**: Backup script exits with error, logs show connection refused

**Diagnosis**:
```bash
# Em PRODUÇÃO não existe serviço `db` — o PostgreSQL é externo (VM02, via DB_HOST).
# Testar a partir do worker, que é quem roda o backup:
docker compose exec -T worker sh -c 'psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;"'

# Em dev/staging (compose com serviço db):
docker compose ps db
```

**Solutions**:
- Em dev: banco parado → `docker compose up -d db`
- Em prod: conferir alcançabilidade da VM02 e a rede `backend-internal`
- Credenciais erradas: verificar `DB_USER`, `DB_PASSWORD` no `stack.env` (Portainer)

### S3 Upload Fails

**Symptoms**: Backup succeeds locally but S3 upload fails

**Diagnosis**:
```bash
# Primeiro: o binário existe? (Hoje a resposta é NÃO em ambas as imagens.)
docker compose exec -T worker sh -c 'command -v aws || echo "aws CLI AUSENTE"'

# Se estiver presente (imagem customizada):
docker compose exec -T worker aws s3 ls s3://aprender-backups/
docker compose exec -T worker env | grep AWS
```

**Solutions**:
- **`aws` ausente da imagem** (caso atual): o upload nunca vai funcionar sem adicionar o CLI
  ao `Dockerfile.prod`. Ver
  [S3/MinIO Setup](#s3minio-setup-opt-in-hoje-não-funcional)
- Missing credentials: Set `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Wrong bucket: Verify `BACKUP_S3_BUCKET` format (`s3://bucket-name/prefix/`)
- Permission denied: Check IAM policy allows `s3:PutObject`

### Restore "diz que o backup está corrompido"

**Symptoms**: `restore_db.sh` aborta com `ERROR: Backup file is corrupted!`

**Diagnosis**:
```bash
head -c 22 /var/backups/aprender/backup_full_<DATA>.sql.gz.age
# "age-encryption.org/v1" => o arquivo está CIFRADO e provavelmente íntegro
```

**Solution**: é o bug #1611, não corrupção. Use o pipeline manual
(`age -d | gunzip | psql`) descrito em
[Manual Restore](#manual-restore).

### Restore Hangs or Times Out

**Symptoms**: o restore roda por horas sem completar

**Diagnosis**:
```bash
# Em prod (PostgreSQL externo), a partir do worker:
docker compose exec -T worker sh -c \
  'psql -h "$DB_HOST" -U postgres -d postgres -c \
   "SELECT pid, state, query FROM pg_stat_activity WHERE datname = '"'"'aprender_db'"'"';"'
```

**Solutions**:
- Conexões ativas bloqueando: encerrar com `pg_terminate_backend` antes do restore
- Arquivo grande: espere ~5-10 minutos por GB
- Recursos insuficientes: aumentar limites de memória/CPU do container

## Performance Optimization

### Parallel Compression

Modify `backup_db.sh` to use `pigz` (parallel gzip):

```bash
# Install pigz in Dockerfile
RUN apt-get update && apt-get install -y pigz

# Update backup_db.sh (line ~120)
pg_dump --format=custom "$PGDATABASE" | pigz -9 > "$BACKUP_FILE"
```

### Incremental Backups (Future Enhancement)

Not yet implemented. Potential approach:

1. **Base backup**: Full pg_dump daily
2. **Incremental**: WAL archiving every hour
3. **Restore**: Apply base + WAL segments

See: [PostgreSQL WAL Archiving](https://www.postgresql.org/docs/current/continuous-archiving.html)

## References

- **Issue**: #169 (MP5 - Automated Backups)
- **PR**: #186 (feat/mp5-automated-backups)
- **Scripts**:
  - `v2/infra/scripts/backup_db.sh`
  - `v2/infra/scripts/restore_db.sh`
- **Tasks**: `v2/backend/apps/core/tasks_backup.py`
- **Schedule**: `v2/backend/config/celery.py` (beat_schedule)

## Estratégia 3-2-1 (recomendada / alvo)

> **Nota de realidade (2026-07-24):** o wiring que faltava no #1455 **existe hoje no
> compose** — bind-mount gravável `/var/backups/aprender:/backups` no `worker`
> (`docker-compose.prod.yml:227-235`), recipient `age` fixo (`:197`), script fail-closed
> (`backup_db.sh:44-48`) e gate de frescor no deploy (`deployer/hooks/check_backup.sh`).
> **O que continua NÃO verificado** é se o beat/worker estão de fato produzindo dumps em
> produção hoje, e se algum deles já foi restaurado com sucesso. Trate o 3-2-1 abaixo como
> **alvo**, não como estado.

- **3** cópias dos dados
- **2** tipos de mídia diferentes
- **1** cópia offsite

| Camada | Destino | Status |
|---|---|---|
| Local | Bind-mount do host `/var/backups/aprender` (prod) / volume `backup_data` (dev) | wiring ✅ presente; **execução em prod não verificada** |
| Cloud | S3/GCS via `S3_BUCKET` | ❌ **não funcional**: nenhuma imagem do projeto tem o `aws` CLI (`Dockerfile.prod:56`) |
| Offsite | Cópia semanal em storage separado | ❌ aspiracional — **hoje existe 1 cópia, no mesmo host da aplicação** |

> **Risco concreto:** perder a VM01 (ou o disco onde vive `/var/backups/aprender`) hoje
> significa perder o banco **e** os backups juntos. Não há segunda cópia.

## Último ensaio de restore

| Data | Origem do dump | Executado por | Resultado | Evidência |
|---|---|---|---|---|
| — | — | — | **NUNCA REGISTRADO** | — |

Preencha esta tabela após cada ensaio (procedimento:
[GUIDE_DR.md → Ensaio de DR](./GUIDE_DR.md#ensaio-de-dr-o-único-teste-que-vale)).
Enquanto a linha estiver vazia, a resposta correta para "temos backup restaurável?" é
**"não sabemos"** — e este documento não deve ser citado como prova do contrário.
Cadência recomendada: **trimestral**, e obrigatoriamente após qualquer mudança em
`backup_db.sh`, `restore_db.sh` ou na chave `age`.

## Cobertura além do PostgreSQL

O sistema de backup automatizado cobre **apenas o PostgreSQL** (`pg_dump`). As coberturas abaixo são **alvo
recomendado**, não automatizadas hoje.

### Uploads / media

Não há tarefa Celery/cron que faça backup da pasta de uploads. Para cobrir media manualmente:

```bash
# Snapshot local dos arquivos de mídia
tar -czvf uploads_$(date +%Y%m%d).tar.gz v2/backend/media/

# Sync incremental para S3 (opcional)
aws s3 sync v2/backend/media/ s3://aprender-backups/media/
```

Retenção alvo sugerida para uploads: ~90 dias (separada da retenção do DB, default 7 dias).

### Configurações e secrets

Os secrets reais de produção vivem no **Portainer** (env vars das Golden VMs), não no repo (os `.env.production`
versionados são templates de dev). Para snapshot de configuração sem expor segredos:

```bash
# Cópia local do arquivo de config (revisar: nunca commitar com senhas reais)
cp .env .env.backup.$(date +%Y%m%d)
```

Guardar segredos fora do repo em cofre dedicado (ex.: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).
A fonte de verdade dos secrets de prod permanece o Portainer.

## Next Steps (Post-MP5)

Em ordem de risco (o primeiro item é o que impede um restore hoje):

1. **Corrigir `restore_db.sh` (#1611)** — tornar a Step 1 ciente do formato `.age`,
   adicionar `set -o pipefail`, respeitar `BACKUP_DIR` (`:17`) e falhar cedo se `age` não
   estiver no PATH
2. **`ON_ERROR_STOP=1` + verificação real de sucesso no restore (#1645)** — hoje o script
   diz "successfully" com exit 0 mesmo perdendo objetos
3. **Cobrir `restore_db.sh` com `.bats`**, incluindo o round-trip cifrado (#1646)
4. **Ensaio de restore com a chave privada** e registro em
   [Último ensaio de restore](#último-ensaio-de-restore)
5. **Cópia offsite de verdade** (exige `aws` CLI na imagem, ou outro transporte)
6. **Prometheus metrics** integration (MP1) — nenhuma métrica de backup existe hoje
7. **Incremental backups** (WAL archiving) — confirmar antes se WAL archiving está ligado

---

**Document Owner**: DevOps/SRE Team
**Review Cycle**: Quarterly
**Last Reviewed**: 2026-07-24 (revisão contra o código — auditoria M26)
