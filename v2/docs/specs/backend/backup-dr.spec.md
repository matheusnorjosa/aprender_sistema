---
title: Backup & Disaster Recovery
status: canonical
last_verified: 2026-07-24
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

> **AVISO DE REALIDADE (revisto em 2026-07-24).** Duas coisas diferentes:
>
> 1. **Backup (escrita)** — as tres causas de codigo do #1455 **ja estao corrigidas** e presentes tanto na `main` (`d08acfa5`) quanto no SHA de producao (`94f27651`): registro da task (`config/celery.py:73`, segundo `autodiscover_tasks(related_name="tasks_backup")`), mount gravavel de `/backups` no `worker` (`docker-compose.prod.yml:234-235`) e glob do health check ciente de `.age` (`tasks_backup.py:202-205`). Ver §Pontos de atencao para o detalhe do que era falso na versao anterior desta spec.
> 2. **Restore (leitura)** — **quebrado**. `v2/infra/scripts/restore_db.sh:91` roda `gzip -t` incondicionalmente e rejeita **todo** backup `.age` — que e o unico formato que producao grava. Achado `M26-01` (**P0**, issue #1611), epico #1662. Detalhe abaixo.
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
- **Script de restore** — [`v2/infra/scripts/restore_db.sh`](../../../infra/scripts/restore_db.sh) — interativo (exige `yes`, `:80-84`), verifica integridade com `gzip -t` (`:91`), termina conexoes (`:99`), drop+create do DB (`:107-108`), restaura com branch `.age` (`:113-119`), imprime contagem de tabelas (`:123`). **⚠️ Ver §Pontos de atencao: a ordem esta invertida e o script rejeita o formato de producao.**
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
# restore (DESTRUTIVO) — ver AVISO: hoje ABORTA em artefato .age (M26-01/#1611)
docker compose exec web /app/infra/scripts/restore_db.sh /backups/backup_full_<ts>.sql.gz.age
```

**Contorno manual enquanto `M26-01` estiver aberto** (o unico caminho que funciona hoje para um artefato de producao):

```bash
age -d -i /etc/backup-key.txt backup_full_<ts>.sql.gz.age | gunzip | psql -h <host> -U postgres -d <db>
```

**Env vars (contrato `tasks_backup.py:69-81` -> `backup_db.sh`):** `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME`, `BACKUP_DIR` (default `/backups`), `BACKUP_RETENTION_DAYS` (7), `S3_BUCKET` (opcional; a task exporta `settings.BACKUP_S3_BUCKET` com o **nome `S3_BUCKET`**), `BACKUP_AGE_RECIPIENT`, `SENTRY_DSN`. ⚠️ `restore_db.sh` **nao** honra `BACKUP_DIR`: o valor esta hardcoded em `:17` (`/var/backups/aprender`), enquanto `backup_db.sh:31` usa `${BACKUP_DIR:-/backups}` — dentro do container (mount `/var/backups/aprender:/backups`) o `--latest` do restore procura no diretorio errado. Tabela completa de variaveis e setup S3 em [`BACKUP_OPERATIONS.md`](../../BACKUP_OPERATIONS.md#configuration).

## Fluxos principais

**Backup (caminho feliz):** Beat dispara 02:00 -> `perform_database_backup("full")` valida que `/app/infra/scripts/backup_db.sh` existe -> monta env do `settings.DATABASES` -> `subprocess.run` (timeout 1h) -> script faz `pg_dump | gzip [| age]` em `$BACKUP_DIR` -> verifica arquivo nao-vazio -> upload S3 (se `BACKUP_S3_BUCKET`) -> retencao -> task parseia o path do stdout e retorna `{status: success, ...}`.

**Erros:** timeout -> `self.retry` (countdown 300); `CalledProcessError` -> log + Sentry + retry com backoff exponencial; retries esgotados -> excecao propaga (deveria alertar via Sentry).

**Restore (cenario 1 — corrupcao de DB), contrato-alvo:** parar `web/worker/beat` -> listar backups -> `restore_db.sh <file>` (verifica integridade, termina conexoes, drop/create, restaura, valida contagem) -> reiniciar -> validar `/healthz/detailed/`. Cenarios completos (perda total do servidor, credenciais comprometidas, GCal indisponivel) em [`DISASTER_RECOVERY.md` §2](../../DISASTER_RECOVERY.md).

**Restore — o que o script FAZ hoje** (`M26-01`, P0, issue #1611):

1. A selecao ja e ciente de `.age` nos tres caminhos de entrada — arquivo explicito (`:42-50`), `--latest` (`:36`) e interativo (`:56,:61`).
2. **Step 1 nao e**: `if ! gzip -t "$BACKUP_FILE"` roda **incondicionalmente** em `:91`. Um artefato `age` comeca com o cabecalho de texto `age-encryption.org/v1`, que nao e gzip -> `gzip -t` retorna 1.
3. O script aborta em `:92-93` com a mensagem literal **`ERROR: Backup file is corrupted!`** — factualmente falsa e ativamente enganosa sob pressao de incidente.
4. O branch que sabe decifrar (`:113-119`) fica **inalcancavel** para o unico formato que producao grava.

Atenuante: a falha e **fail-closed** — para em `:91`, antes do `DROP DATABASE` de `:107`. Nao ha destruicao de dados; o dano e RTO estourado e perda de confianca no DR. Use o contorno manual da secao anterior.

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
- **Restore tem cobertura ZERO** (`M26-03`, issue #1646). Nao existe `.bats` para `restore_db.sh` — os 5 arquivos `.bats` do repo vivem em `v2/infra/deployer/tests/` e nenhum menciona restore. E [`test_dr.sh`](../../../infra/scripts/test_dr.sh) **nao exercita o caminho cifrado nem chama `restore_db.sh`**: ele gera o dump em texto claro (`:76`) e restaura a mao com `gunzip -c | psql` (`:103`). E exatamente por isso que `M26-01` sobreviveu. (O comentario de `verify_backup.sh:43`, que afirma que a verificacao de conteudo cifrado "e exercitada no test_dr.sh", esta errado.)

## Pontos de atencao / dividas conhecidas

- **P0 ABERTO — o restore oficial rejeita todo backup de producao** (`M26-01`, issue #1611, epico #1662). Ver §Fluxos. Correcao: espelhar na Step 1 o branch `.age` que ja existe na Step 4, e adicionar `set -o pipefail` (hoje so `set -e` em `:15`) para que uma falha do `age` no pipe de `:116` nao seja mascarada pelo exit 0 do proximo estagio — mesma classe de bug ja corrigida em `backup_db.sh` pelo #1543. Corrigir junto o `BACKUP_DIR` hardcoded (`:17`). Nota operacional: o binario `age` precisa existir no host/imagem onde o restore roda — verificar antes do incidente, nao durante.
- **P1 ABERTO — "Restore completed successfully!" com exit 0 apos restore parcial** (`M26-02`, issue #1645). `restore_db.sh:123-124` calcula `TABLE_COUNT` e **so imprime** — nao compara com piso algum (contraste: `test_dr.sh:116-119` tem `-lt 10 -> exit 1`). E o `psql` de restore (`:116`/`:118`) roda **sem `-v ON_ERROR_STOP=1`**, entao erros de SQL individuais nao mudam o exit code: `set -e` nao dispara e `:128` declara sucesso.
- **P1 ABERTO — DR nunca exercitado no formato real** (`M26-03`, issue #1646). Ver §Testes.
- **CORRIGIDO (nao repetir o diagnostico antigo do #1455).** Versoes anteriores desta spec afirmavam que `worker`/`beat` de producao nao montavam `/backups` nem `/app/infra/scripts`, e que `script_path.exists()` falhava com `FileNotFoundError`. Isso **nao corresponde ao codigo atual**: o `worker` monta `/var/backups/aprender:/backups` (`docker-compose.prod.yml:234-235`, com comentario `#1455 / ADR-018 B2`) e os scripts vem assados na imagem (`Dockerfile.prod:67-68`), logo nao dependem de mount. A causa raiz real era outra: `autodiscover_tasks()` importa apenas o modulo `tasks` de cada app, e as tasks de backup vivem em `tasks_backup.py` — o beat despachava e o worker respondia `NotRegistered` em silencio. Fechado por `config/celery.py:73` (`app.autodiscover_tasks(related_name="tasks_backup")`). O `beat` continua sem mount de `/backups`, e isso e correto: quem executa o script e o `worker`.
- **Sem alerta de "backup ausente"**: o health check semanal so emite warning ao Sentry; se `SENTRY_DSN` nao estiver configurado, `degraded` nao chega a ninguem. Se o Sentry esta ou nao ativo em producao **depende de verificacao humana** (conteudo do env no Portainer — item F5 de `ACHADOS_REAIS.md`).
- **RPO 5 min depende do WAL na VM02**, nao do `pg_dump` (diario). Em ambiente Docker sem `archive_mode`, o RPO efetivo regride para ~24h (ultimo dump).
- **Sem backup de media/uploads e secrets** automatizado — so procedimento manual. Estrategia 3-2-1 e aspiracional (sem copia offsite ativa).
- **Restore drill nao automatizado em CI** — `test_dr.sh` existe mas a execucao recorrente nao esta garantida, e no formato atual ele nao provaria o caminho de producao (ver §Testes).
