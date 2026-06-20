---
title: Backup & Disaster Recovery
status: canonical
last_verified: 2026-06-19
sources_of_truth:
  - v2/backend/apps/core/tasks_backup.py
  - v2/backend/config/celery.py
  - v2/infra/scripts/backup_db.sh
  - v2/infra/scripts/restore_db.sh
  - v2/infra/scripts/verify_backup.sh
  - v2/infra/scripts/test_dr.sh
  - v2/infra/configs/vm02/postgresql.conf
  - v2/infra/docker-compose.prod.yml
  - v2/backend/apps/core/tests/test_celery_backup.py
  - v2/docs/BACKUP_OPERATIONS.md
  - v2/docs/DISASTER_RECOVERY.md
  - v2/docs/GUIDE_DR.md
owner: backend
supersedes:
  - v2/docs/BACKUP_OPERATIONS.md
  - v2/docs/DISASTER_RECOVERY.md
related:
  - v2/docs/specs/infra/deploy.spec.md
  - v2/docs/GUIDE_DR.md
  - v2/docs/SLO_DEFINITIONS.md
---

# Backup & Disaster Recovery

## Proposito

Garantir que o estado do AS v2 (banco PostgreSQL, fonte de verdade de ~82k formulas migradas) seja recuperavel apos corrupcao, perda de servidor ou comprometimento de credenciais. O modulo cobre dois eixos: (1) **backup automatizado** do PostgreSQL via `pg_dump` agendado pelo Celery Beat (Docker) ou cron (VM), com retencao, upload S3 opcional e criptografia `age` opcional (SEC-017); e (2) **recovery** — procedimentos operacionais de restore para cada cenario de desastre.

Esta spec e o **indice canonico** do tema. Os parametros e procedimentos detalhados vivem em [`BACKUP_OPERATIONS.md`](../../BACKUP_OPERATIONS.md) (SSOT de operacoes/parametros) e [`DISASTER_RECOVERY.md`](../../DISASTER_RECOVERY.md) (cenarios de recovery em Docker); para VM de producao, [`GUIDE_DR.md`](../../GUIDE_DR.md). Aqui ficam o **contrato** e os **invariantes** — nao se duplica o passo-a-passo dos guias.

> **AVISO DE REALIDADE (2026-06):** o backup automatizado esta **morto/silencioso em producao** (issue #1455). As secoes abaixo descrevem o **contrato-alvo**; onde o estado real diverge, esta sinalizado. Trate a cobertura como aspiracional ate o job ser ressuscitado e validado por um restore drill real.

## Fonte de verdade no codigo

- **Tasks Celery** — [`v2/backend/apps/core/tasks_backup.py`](../../../backend/apps/core/tasks_backup.py)
  - `backup.perform_database_backup(backup_type="full")` — invoca o script, `max_retries=3`, `default_retry_delay=300`, `timeout=3600`, backoff exponencial; alerta Sentry se `SENTRY_DSN` setado.
  - `backup.verify_backup_health()` — health check semanal (3 checks: dir gravavel, backup recente < 25h, conectividade S3 se configurado).
- **Schedule (beat)** — [`v2/backend/config/celery.py`](../../../backend/config/celery.py)
  - `daily-database-backup` — `crontab(hour=2, minute=0)`, args `("full",)`, `expires=3600`.
  - `weekly-backup-health-check` — `crontab(hour=3, minute=0, day_of_week=0)` (domingos).
- **Script de backup** — [`v2/infra/scripts/backup_db.sh`](../../../infra/scripts/backup_db.sh) — `pg_dump | gzip [| age]`, nomenclatura `backup_full_YYYYMMDD_HHMMSS.sql.gz[.age]`, retencao `find -mtime +$BACKUP_RETENTION_DAYS -delete`, upload S3 opcional. Mesmo script para Docker e VM (muda so a chamada e os defaults das env vars).
- **Script de restore** — [`v2/infra/scripts/restore_db.sh`](../../../infra/scripts/restore_db.sh) — interativo (exige `yes`), verifica integridade (`gzip -t`), termina conexoes, drop+create do DB, restaura (suporta `.age`), valida contagem de tabelas.
- **Scripts auxiliares** — [`verify_backup.sh`](../../../infra/scripts/verify_backup.sh) (health check VM), [`test_dr.sh`](../../../infra/scripts/test_dr.sh) (drill mensal).
- **WAL archiving (RPO)** — [`v2/infra/configs/vm02/postgresql.conf`](../../../infra/configs/vm02/postgresql.conf): `archive_mode=on`, `archive_timeout=300`, `archive_command` para `/var/lib/postgresql/wal_archive/`.

## Contratos e invariantes

| Parametro | Valor | Fonte |
|---|---|---|
| **RPO** | 5 min | `archive_timeout=300` (WAL contínuo na VM02) |
| **RTO** | 1 h (restore + migrations + smoke) | SSOT `BACKUP_OPERATIONS.md` |
| **Retencao** | 7 dias (`BACKUP_RETENTION_DAYS`) | `backup_db.sh` |
| **Frequencia** | 1x/dia (02:00 Docker / 03:00 VM, `America/Fortaleza`) | `celery.py` / cron |
| **Health check** | semanal (domingos 03:00) | `verify_backup_health` |

Invariantes que NAO podem ser violados:

- **Nomenclatura fixa**: `backup_full_*.sql.gz[.age]`. O health check faz glob exatamente por `backup_full_*.sql.gz`; arquivos com outro nome sao **invisiveis** (provado em teste). Mudar o prefixo quebra a deteccao de "backup recente".
- **Restore e destrutivo e irreversivel**: dropa o DB alvo. Em modo interativo exige confirmacao literal `yes`. Producao deve parar `web`/`worker`/`beat` antes (prevenir escrita concorrente).
- **Idempotencia de retencao**: a limpeza so apaga `backup_full_*` mais velhos que a janela; nunca toca arquivos fora do padrao.
- **Credencial nunca logada**: `PGPASSWORD` e exportado para o `pg_dump`, jamais ecoado. Secrets reais de prod vivem no Portainer, nao no repo.
- **Cobertura = somente PostgreSQL**: uploads/media e secrets NAO tem backup automatizado (apenas procedimento manual documentado). Redis nao e persistido (cache/sessions/broker efemero).
- **`age` opcional (SEC-017)**: se `BACKUP_AGE_RECIPIENT` setado, o dump e criptografado em repouso; restore exige `BACKUP_AGE_KEY`.

## API / Interface

Nao expoe endpoints HTTP. Interface = tasks Celery + scripts CLI + env vars.

**Disparo manual (Docker):**

```bash
# backup full
docker compose exec web /app/infra/scripts/backup_db.sh full
# via Celery
docker compose exec web python manage.py shell -c \
  "from apps.core.tasks_backup import perform_database_backup; perform_database_backup.delay('full')"
# restore (DESTRUTIVO)
docker compose exec web /app/infra/scripts/restore_db.sh /backups/backup_full_<ts>.sql.gz
```

**Env vars (contrato `tasks_backup.py` -> `backup_db.sh`):** `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME`, `BACKUP_DIR` (default `/backups`), `BACKUP_RETENTION_DAYS` (7), `BACKUP_S3_BUCKET` (opcional), `BACKUP_AGE_RECIPIENT` (opcional), `SENTRY_DSN`. Tabela completa de variaveis e setup S3 em [`BACKUP_OPERATIONS.md`](../../BACKUP_OPERATIONS.md#configuration).

## Fluxos principais

**Backup (caminho feliz):** Beat dispara 02:00 -> `perform_database_backup("full")` valida que `/app/infra/scripts/backup_db.sh` existe -> monta env do `settings.DATABASES` -> `subprocess.run` (timeout 1h) -> script faz `pg_dump | gzip [| age]` em `$BACKUP_DIR` -> verifica arquivo nao-vazio -> upload S3 (se `BACKUP_S3_BUCKET`) -> retencao -> task parseia o path do stdout e retorna `{status: success, ...}`.

**Erros:** timeout -> `self.retry` (countdown 300); `CalledProcessError` -> log + Sentry + retry com backoff exponencial; retries esgotados -> excecao propaga (deveria alertar via Sentry).

**Restore (cenario 1 — corrupcao de DB):** parar `web/worker/beat` -> listar backups -> `restore_db.sh <file>` (verifica integridade, termina conexoes, drop/create, restaura, valida contagem) -> reiniciar -> validar `/healthz/detailed/`. Cenarios completos (perda total do servidor, credenciais comprometidas, GCal indisponivel) em [`DISASTER_RECOVERY.md` §2](../../DISASTER_RECOVERY.md).

## Decisoes relacionadas (ADRs)

- MP5 — Automated Backup System (issue #169, PR #186) — origem do sistema.
- SEC-017 — criptografia `age` opcional em repouso para backups.
- Issue #562 (C-05) / #563 (C-06) — script unificado Docker+VM e testes.
- Spec de deploy/infra relacionada: [`deploy.spec.md`](../infra/deploy.spec.md).

## Testes que cobrem

- [`v2/backend/apps/core/tests/test_celery_backup.py`](../../../backend/apps/core/tests/test_celery_backup.py)
  - `TestVerifyBackupHealth` — degraded sem backups; healthy com backup recente; warning com backup > 25h; warning com dir inexistente; **glob so casa `backup_full_*.sql.gz`** (nome divergente = invisivel).
  - `TestPerformDatabaseBackupScriptPath` — task registrada com nome `backup.perform_database_backup`; `max_retries=3`, `default_retry_delay=300`.
- Sem cobertura de integracao real do `pg_dump`/restore (exige Docker); drill via [`test_dr.sh`](../../../infra/scripts/test_dr.sh) e manual/mensal.

## Pontos de atencao / dividas conhecidas

- **CRITICO — job morto/silencioso em prod (issue #1455).** O Beat esta agendado, mas a execucao em producao nao produz backups verificaveis. Causa estrutural confirmada no codigo: [`docker-compose.prod.yml`](../../../infra/docker-compose.prod.yml) define `worker`/`beat` mas **nao monta o volume `backup_data` (`/backups`) nem o diretorio `infra/scripts` (`/app/infra/scripts`)** — ao contrario do compose de dev/staging. A task hardcoda `Path("/app/infra/scripts/backup_db.sh")`; sem o mount, `script_path.exists()` falha (`FileNotFoundError`) ou, na melhor hipotese, escreve em path efemero perdido no restart. Sem `SENTRY_DSN` ativo em prod, a falha e **silenciosa**. Acao: montar volume + scripts no `worker`/`beat` de prod, garantir `SENTRY_DSN`/alerta, e validar com restore drill.
- **Sem alerta de "backup ausente"**: o health check semanal so emite warning ao Sentry; se Sentry estiver OFF (estado prod atual), `degraded` nao chega a ninguem.
- **RPO 5 min depende do WAL na VM02**, nao do `pg_dump` (diario). Em ambiente Docker sem `archive_mode`, o RPO efetivo regride para ~24h (ultimo dump).
- **Sem backup de media/uploads e secrets** automatizado — so procedimento manual. Estrategia 3-2-1 e aspiracional (sem copia offsite ativa).
- **Restore drill mensal nao automatizado em CI** — `test_dr.sh` existe mas a execucao recorrente nao esta garantida.
