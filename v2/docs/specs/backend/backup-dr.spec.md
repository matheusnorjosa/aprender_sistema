---
title: Backup & Disaster Recovery
status: canonical
last_verified: 2026-08-26
sources_of_truth:
  - v2/backend/apps/core/tasks_backup.py
  - v2/backend/config/celery.py
  - v2/infra/Dockerfile.prod
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

Garantir que o estado do AS v2 (banco PostgreSQL, fonte de verdade de ~82k formulas migradas) seja recuperavel apos corrupcao, perda de servidor ou comprometimento de credenciais. O modulo cobre dois eixos: (1) **backup automatizado** do PostgreSQL via `pg_dump` agendado pelo Celery Beat (Docker) ou cron (VM), com retencao, upload S3 opcional e criptografia `age` (SEC-017 — opcional no script, mas **efetivamente obrigatoria** em producao, ver §Contratos); e (2) **recovery** — procedimentos operacionais de restore para cada cenario de desastre.

Esta spec e o **indice canonico** do tema. Os parametros e procedimentos detalhados vivem em [`BACKUP_OPERATIONS.md`](../../BACKUP_OPERATIONS.md) (SSOT de operacoes/parametros) e [`DISASTER_RECOVERY.md`](../../DISASTER_RECOVERY.md) (cenarios de recovery em Docker); para VM de producao, [`GUIDE_DR.md`](../../GUIDE_DR.md). Aqui ficam o **contrato** e os **invariantes** — nao se duplica o passo-a-passo dos guias.

> **AVISO DE REALIDADE (revisto em 2026-08-26).** Duas coisas diferentes:
>
> 1. **Backup (escrita)** — as tres causas de codigo do #1455 **ja estao corrigidas** e presentes tanto na `main` (`d08acfa5`) quanto no SHA de producao (`94f27651`): registro da task (`config/celery.py:73`, segundo `autodiscover_tasks(related_name="tasks_backup")`), mount gravavel de `/backups` no `worker` (`docker-compose.prod.yml:234-235`) e glob do health check ciente de `.age` (`tasks_backup.py:202-205`). Ver §Pontos de atencao para o detalhe do que era falso na versao anterior desta spec.
> 2. **Restore (leitura)** — **corrigido no codigo**. `M26-01` (P0, #1611, `8f392636`) e `M26-02` (P1, #1645, `3bca74f3`/#1793) estao **fechados**: `restore_db.sh` agora e ciente do formato (decifra `.age` com `age -d` **antes** do `gzip -t`), roda o restore com `psql -v ON_ERROR_STOP=1` + piso de contagem de tabelas, faz dump de seguranca antes do `DROP` e honra `BACKUP_DIR`. Cobertura `.bats` criada (`restore_db.bats`, 7 casos). O que **continua aberto** e o drill real de ponta-a-ponta (`M26-03`, #1646, epico #1662): os testes exercitam o script, mas nenhum `.age` foi restaurado num banco real. Detalhe abaixo.
>
> O que continua **NAO verificado** e nao pode ser afirmado por leitura de codigo: se o beat realmente executa em producao e se existe hoje um artefato restauravel. E o item **F7** de `v2/docs/audits/ACHADOS_REAIS.md` — depende de verificacao humana na VM. Precedente: #1537, backup que nunca rodou.

## Fonte de verdade no codigo

- **Tasks Celery** — [`v2/backend/apps/core/tasks_backup.py`](../../../backend/apps/core/tasks_backup.py)
  - `backup.perform_database_backup(backup_type="full")` — invoca o script, `max_retries=3`, `default_retry_delay=300`, `timeout=3600`, backoff exponencial; alerta Sentry se `SENTRY_DSN` setado.
  - `backup.verify_backup_health()` — health check semanal (3 checks: dir gravavel, backup recente < 25h, conectividade S3 se configurado).
- **Schedule (beat)** — [`v2/backend/config/celery.py`](../../../backend/config/celery.py)
  - `daily-database-backup` — `crontab(hour=2, minute=0)`, args `("full",)`, `expires=3600`.
  - `weekly-backup-health-check` — `crontab(hour=3, minute=0, day_of_week=0)` (domingos).
- **Script de backup** — [`v2/infra/scripts/backup_db.sh`](../../../infra/scripts/backup_db.sh) — `set -euo pipefail` (`:23`), `pg_dump | gzip [| age]`, nomenclatura `backup_full_YYYYMMDD_HHMMSS.sql.gz[.age]` (`:51-55`), `BACKUP_DIR="${BACKUP_DIR:-/backups}"` (`:31`), retencao que cobre **os dois sufixos** (`:103`), upload S3 opcional. Mesmo script para Docker e VM (muda so a chamada e os defaults das env vars).
- **Script de restore** — [`v2/infra/scripts/restore_db.sh`](../../../infra/scripts/restore_db.sh) — interativo (exige `yes`), verificacao de integridade **ciente do formato** (`.age` -> `age -d | gzip -t` com pipefail local, `:100-113`; branch plaintext usa `gzip -t` direto), dump de seguranca antes do `DROP` (`SAFETY_DUMP`, `:135`), termina conexoes, drop+create do DB, restaura com `psql -v ON_ERROR_STOP=1` (`:166`/`:170`) e **valida piso de contagem de tabelas** (`:184-191`). Honra `BACKUP_DIR` (`:21-23`).
- **Onde os scripts vivem no container** — [`v2/infra/Dockerfile.prod:67-68`](../../../infra/Dockerfile.prod): `COPY infra/scripts /app/infra/scripts` + `chmod +x`. Sao **assados na imagem**, nao montados. Por isso `Path("/app/infra/scripts/backup_db.sh").exists()` (`tasks_backup.py:57,62`) e verdadeiro em producao sem mount algum.
- **Scripts auxiliares** — [`verify_backup.sh`](../../../infra/scripts/verify_backup.sh) (health check da VM; sabe distinguir `.age` **antes** de chamar `gzip -t`, `:44-71`, e pula a inspecao de conteudo cifrado por design, `:45-48`), [`test_dr.sh`](../../../infra/scripts/test_dr.sh) (drill).
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

- **Nomenclatura fixa**: `backup_full_*.sql.gz[.age]`. O health check faz **dois** globs — `backup_full_*.sql.gz` **e** `backup_full_*.sql.gz.age` (`tasks_backup.py:202-205`, correcao do #1455 com teste sentinela em `test_celery_backup.py:144-166`). Artefatos cifrados **sao visiveis**. O que continua invisivel e qualquer nome fora do prefixo `backup_full_` (provado em `test_celery_backup.py:113-142`): mudar o prefixo quebra a deteccao de "backup recente".
- **Restore e destrutivo e irreversivel**: dropa o DB alvo (`restore_db.sh:107`). Em modo interativo exige confirmacao literal `yes`. Producao deve parar `web`/`worker`/`beat` antes (prevenir escrita concorrente).
- **Idempotencia de retencao**: a limpeza so apaga `backup_full_*` (`.sql.gz` e `.sql.gz.age`) mais velhos que a janela; nunca toca arquivos fora do padrao (`backup_db.sh:103`).
- **Credencial nunca logada**: `PGPASSWORD` e exportado para o `pg_dump`, jamais ecoado. Secrets reais de prod vivem no Portainer, nao no repo.
- **Cobertura = somente PostgreSQL**: uploads/media e secrets NAO tem backup automatizado (apenas procedimento manual documentado). Redis nao e persistido (cache/sessions/broker efemero).
- **`age` NAO e opcional na pratica (SEC-017)**: o script e **fail-closed** — sem `BACKUP_AGE_RECIPIENT` e sem `BACKUP_ALLOW_PLAINTEXT=1` o backup **aborta** (`backup_db.sh:42-48`); com recipient o nome vira `.sql.gz.age` (`:51-55`). E `docker-compose.prod.yml:197` define `BACKUP_AGE_RECIPIENT` no servico `worker`. Consequencia: **producao grava exclusivamente `.age`**, e todo restore de producao exige `BACKUP_AGE_KEY` (default `/etc/backup-key.txt`, `restore_db.sh:114`) e o binario `age` disponivel no host/imagem onde o restore roda.

## API / Interface

Nao expoe endpoints HTTP. Interface = tasks Celery + scripts CLI + env vars.

**Disparo manual (Docker):**

```bash
# backup full
docker compose exec web /app/infra/scripts/backup_db.sh full
# via Celery
docker compose exec web python manage.py shell -c \
  "from apps.core.tasks_backup import perform_database_backup; perform_database_backup.delay('full')"
# restore (DESTRUTIVO) — ciente do formato desde #1611/#1645 (decifra .age antes do gzip -t)
docker compose exec web /app/infra/scripts/restore_db.sh /backups/backup_full_<ts>.sql.gz.age
```

**Restore manual direto** (alternativa ao script — util para inspecao ou pipe custom; o `restore_db.sh` ja cobre o `.age` de producao):

```bash
age -d -i /etc/backup-key.txt backup_full_<ts>.sql.gz.age | gunzip | psql -h <host> -U postgres -d <db>
```

**Env vars (contrato `tasks_backup.py:69-81` -> `backup_db.sh`):** `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME`, `BACKUP_DIR` (default `/backups`), `BACKUP_RETENTION_DAYS` (7), `S3_BUCKET` (opcional; a task exporta `settings.BACKUP_S3_BUCKET` com o **nome `S3_BUCKET`**), `BACKUP_AGE_RECIPIENT`, `SENTRY_DSN`. ⚠️ `restore_db.sh` **nao** honra `BACKUP_DIR`: o valor esta hardcoded em `:17` (`/var/backups/aprender`), enquanto `backup_db.sh:31` usa `${BACKUP_DIR:-/backups}` — dentro do container (mount `/var/backups/aprender:/backups`) o `--latest` do restore procura no diretorio errado. Tabela completa de variaveis e setup S3 em [`BACKUP_OPERATIONS.md`](../../BACKUP_OPERATIONS.md#configuration).

## Fluxos principais

**Backup (caminho feliz):** Beat dispara 02:00 -> `perform_database_backup("full")` valida que `/app/infra/scripts/backup_db.sh` existe -> monta env do `settings.DATABASES` -> `subprocess.run` (timeout 1h) -> script faz `pg_dump | gzip [| age]` em `$BACKUP_DIR` -> verifica arquivo nao-vazio -> upload S3 (se `BACKUP_S3_BUCKET`) -> retencao -> task parseia o path do stdout e retorna `{status: success, ...}`.

**Erros:** timeout -> `self.retry` (countdown 300); `CalledProcessError` -> log + Sentry + retry com backoff exponencial; retries esgotados -> excecao propaga (deveria alertar via Sentry).

**Restore (cenario 1 — corrupcao de DB), contrato-alvo:** parar `web/worker/beat` -> listar backups -> `restore_db.sh <file>` (verifica integridade, termina conexoes, drop/create, restaura, valida contagem) -> reiniciar -> validar `/healthz/detailed/`. Cenarios completos (perda total do servidor, credenciais comprometidas, GCal indisponivel) em [`DISASTER_RECOVERY.md` §2](../../DISASTER_RECOVERY.md).

**Restore — comportamento atual** (`M26-01`/#1611 e `M26-02`/#1645 corrigidos):

1. A selecao e ciente de `.age` nos tres caminhos de entrada — arquivo explicito (`:42-50`), `--latest` e interativo (`:56,:67`).
2. **Verificacao de integridade ciente do formato**: para `.age`, `age -d -i $BACKUP_AGE_KEY | gzip -t` num subshell com `set -o pipefail` (`:100-113`); para `.sql.gz` legitimo, `gzip -t` direto. Falha de decifragem ou gzip **aborta antes de qualquer escrita**.
3. **Dump de seguranca antes do `DROP`** (`SAFETY_DUMP`, `:135`), depois drop+create.
4. **Restore com `psql -v ON_ERROR_STOP=1`** (`:166` `.age` / `:170` plaintext) — um erro de SQL aborta em vez de mascarar; o **piso de contagem de tabelas** (`:184-191`) rejeita restore incompleto em vez de declarar sucesso falso.

O unico gap restante e o **drill real** (`M26-03`, #1646): a suite `.bats` exercita o script, mas nenhum `.age` foi restaurado ponta-a-ponta num banco real.

## Decisoes relacionadas (ADRs)

- MP5 — Automated Backup System (issue #169, PR #186) — origem do sistema.
- SEC-017 — criptografia `age` opcional em repouso para backups.
- Issue #562 (C-05) / #563 (C-06) — script unificado Docker+VM e testes.
- Spec de deploy/infra relacionada: [`deploy.spec.md`](../infra/deploy.spec.md).

## Testes que cobrem

- [`v2/backend/apps/core/tests/test_celery_backup.py`](../../../backend/apps/core/tests/test_celery_backup.py)
  - `TestVerifyBackupHealth` (`:22`) — degraded sem backups; healthy com backup recente; warning com backup > 25h; warning com dir inexistente; **prefixo `backup_full_` e obrigatorio** (nome divergente = invisivel, `:113-142`); **`backup_full_*.sql.gz.age` conta como healthy** (`:144-166`, sentinela do #1455).
  - `TestPerformDatabaseBackupScriptPath` (`:169`) — task registrada com nome `backup.perform_database_backup`; `max_retries=3`, `default_retry_delay=300`.
- `apps/core/tests/test_celery_beat_registration.py` — sentinela do registro da task num interpretador novo (um `import` direto de `tasks_backup` no pytest mascararia o `NotRegistered` do #1455; ver comentario em `config/celery.py:60-71`).
- **Restore agora tem cobertura `.bats`** ([`v2/infra/scripts/tests/restore_db.bats`](../../../infra/scripts/tests/restore_db.bats), 7 casos: `.age` valido, corrupcao, formato simples, diretorio customizado, `--latest`, e os 2 do piso de tabelas). Criada por `8f392636` (#1691, o fix do `M26-01`) e ampliada por `3bca74f3` (#1793, `M26-02`). **O que continua faltando e o drill real** (`M26-03`, issue #1646): os `.bats` exercitam o script, mas [`test_dr.sh`](../../../infra/scripts/test_dr.sh) ainda gera o dump em texto claro (`:76`) e restaura a mao com `gunzip -c | psql` (`:103`) — nunca um `.age` restaurado num banco real. (O comentario de `verify_backup.sh:43`, que afirma que a verificacao de conteudo cifrado "e exercitada no test_dr.sh", segue errado.)

## Pontos de atencao / dividas conhecidas

- **CORRIGIDO — `M26-01` (P0, #1611), fechado por `8f392636`.** `restore_db.sh` espelhou na verificacao de integridade o branch `.age` que ja existia no restore (decifra antes do `gzip -t`) e adicionou `set -o pipefail` **local** nos pipes do `age` (o global e so `set -e` por design — ver comentario `:14-19` sobre `ls A B | head`). `BACKUP_DIR` deixou de ser hardcoded (`:21-23`). Nota operacional (ainda valida): o binario `age` precisa existir no host/imagem onde o restore roda, e a chave privada (`BACKUP_AGE_KEY`) precisa ser provisionada — verificar antes do incidente, nao durante (`M26-N2`).
- **CORRIGIDO — `M26-02` (P1, #1645), fechado por `3bca74f3` (#1793).** `restore_db.sh` agora roda o `psql` de restore com `-v ON_ERROR_STOP=1` (`:166`/`:170`), compara `TABLE_COUNT` com um piso e aborta se `< MIN_TABLES` (`:184-191`), alem do dump de seguranca antes do `DROP`. O "Restore completed successfully!" (`:216`) so e impresso apos passar o piso.
- **P1 ABERTO — DR nunca exercitado no formato real** (`M26-03`, issue #1646, epico #1662). Os `.bats` exercitam o script, mas nenhum round-trip real de um `.age` num banco de verdade ocorreu. Ver §Testes.
- **CORRIGIDO (nao repetir o diagnostico antigo do #1455).** Versoes anteriores desta spec afirmavam que `worker`/`beat` de producao nao montavam `/backups` nem `/app/infra/scripts`, e que `script_path.exists()` falhava com `FileNotFoundError`. Isso **nao corresponde ao codigo atual**: o `worker` monta `/var/backups/aprender:/backups` (`docker-compose.prod.yml:234-235`, com comentario `#1455 / ADR-018 B2`) e os scripts vem assados na imagem (`Dockerfile.prod:67-68`), logo nao dependem de mount. A causa raiz real era outra: `autodiscover_tasks()` importa apenas o modulo `tasks` de cada app, e as tasks de backup vivem em `tasks_backup.py` — o beat despachava e o worker respondia `NotRegistered` em silencio. Fechado por `config/celery.py:73` (`app.autodiscover_tasks(related_name="tasks_backup")`). O `beat` continua sem mount de `/backups`, e isso e correto: quem executa o script e o `worker`.
- **Sem alerta de "backup ausente"**: o health check semanal so emite warning ao Sentry; se `SENTRY_DSN` nao estiver configurado, `degraded` nao chega a ninguem. Se o Sentry esta ou nao ativo em producao **depende de verificacao humana** (conteudo do env no Portainer — item F5 de `ACHADOS_REAIS.md`).
- **RPO 5 min depende do WAL na VM02**, nao do `pg_dump` (diario). Em ambiente Docker sem `archive_mode`, o RPO efetivo regride para ~24h (ultimo dump).
- **Sem backup de media/uploads e secrets** automatizado — so procedimento manual. Estrategia 3-2-1 e aspiracional (sem copia offsite ativa).
- **Restore drill nao automatizado em CI** — `test_dr.sh` existe mas a execucao recorrente nao esta garantida, e no formato atual ele nao provaria o caminho de producao (ver §Testes).
