# Backup e Recovery — PostgreSQL nativo (VM02) + PITR

**Ambiente**: **VM02_Banco** — PostgreSQL nativo, operado por `systemd`/`cron` do próprio
Postgres. A **aplicação não roda aqui**: `web`, `worker`, `beat`, `frontend`, `redis` e o
one-shot `migrate` são uma stack **Docker/Portainer na VM01**
(`v2/infra/docker-compose.prod.yml`; o compose de produção **não tem serviço `db`** —
o Postgres é externo, ver `docker-compose.prod.yml:5-6`). Para os procedimentos do lado
Docker, ver [DISASTER_RECOVERY.md](./DISASTER_RECOVERY.md).

> **Parâmetros canônicos** (RPO/RTO/retenção/frequência) vêm do SSOT
> [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md#parâmetros-canônicos-rpo--rto--retenção--frequência).
> Este documento foca em **PITR via WAL archiving** e no restore do PostgreSQL nativo.

---

## Antes de restaurar: estado da ferramenta oficial

> [!important] O aviso que abria este guia foi revogado em 2026-08-25.
> Até essa data esta seção dizia que `v2/infra/scripts/restore_db.sh` **não conseguia
> restaurar o único formato que existe em produção** (`.age`) e mandava usar um pipeline
> manual. Os dois defeitos foram corrigidos:
>
> | Defeito | Sintoma antigo | Corrigido em |
> |---|---|---|
> | [#1611](https://github.com/matheusnorjosa/aprender_sistema/issues/1611) / M26-01 | `gzip -t` incondicional no `.age` → `ERROR: Backup file is corrupted!` (falso) | `8f392636`, 2026-08-10 |
> | [#1645](https://github.com/matheusnorjosa/aprender_sistema/issues/1645) / M26-02 | `Restore completed successfully!` com exit 0 sobre banco vazio | `3bca74f3`, 2026-08-21 |
>
> Sob incidente, um aviso obsoleto empurra o operador para o caminho pior — sem safety
> dump e sem verificação. **Use a ferramenta.**

O que o script faz hoje, contra um `.age` de produção:

| Etapa | Comportamento | Linha |
|---|---|---|
| Seleção | `--latest` e o modo interativo enxergam `*.sql.gz` **e** `*.sql.gz.age` | `:42, 62, 67` |
| `BACKUP_DIR` | Respeita a env var (`${BACKUP_DIR:-/var/backups/aprender}`); antes era hardcoded e `--latest` não achava nada de dentro do container | `:23` |
| Verificação prévia | Decifra com `age -d` e **só então** roda `gzip -t`; aborta se `age` não está no PATH ou a chave não é legível | `:101-121` |
| Rede de segurança | Safety dump do banco atual **antes** do `DROP DATABASE` | `:132-148` |
| Restore | `psql -v ON_ERROR_STOP=1` sob `pipefail`; erro aborta em vermelho e informa onde ficou o safety dump | `:162-178` |
| Verificação posterior | Piso de tabelas (`RESTORE_MIN_TABLES`, default 20) **e** linhas > 0 em `core_usuario`/`core_solicitacao` | `:180-212` |

> ⚠️ **O que continua não provado.** O código exercita o caminho `.age`, mas **nenhum
> drill real** foi executado: `test_dr.sh` não gera `.age` nem chama `age -d`. Issue
> [#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646) (M26-03, épico
> [#1662](https://github.com/matheusnorjosa/aprender_sistema/issues/1662)) segue
> **ABERTA**. Restaurabilidade aqui é *inferida do código*, não demonstrada — ver
> [Ensaio de DR](#ensaio-de-dr-o-único-teste-que-vale).

### 🔑 Credencial — o que decide se o script chega a rodar

O `restore_db.sh` conecta **sempre** como superusuário `postgres` via `-h $DB_HOST`
(`restore_db.sh:126, 152, 153, 166, 170, 183`) e **não tem tratamento de senha nenhum**:
`grep -i "PGPASSWORD\|PGPASS\|password" v2/infra/scripts/restore_db.sh` retorna **zero**
ocorrências, enquanto `backup_db.sh:57-60` exporta `PGPASSWORD`. O que a VM02 concede,
segundo os arquivos versionados:

| Regra | Efeito |
|---|---|
| `configs/vm02/pg_hba.conf:8` — `local all postgres peer` | socket Unix, **sem senha**, se o processo rodar como usuário de SO `postgres` |
| `configs/vm02/pg_hba.conf:12` — `host aprender_db aprender_user 10.0.0.1/32 scram-sha-256` | TCP só da VM01, só como `aprender_user`, **com senha** |
| `configs/vm02/pg_hba.conf:18` — `host all all 0.0.0.0/0 reject` | todo o resto por TCP |
| `configs/vm02/postgresql.conf:8` — `listen_addresses = '10.0.0.2'` | o Postgres **não escuta em 127.0.0.1** |

Logo `DB_HOST=localhost` **não autentica**: a conexão nem chega ao `pg_hba` (não há
listener em loopback) e, se chegasse, cairia no `reject` da linha 18 — e o script não teria
senha para oferecer. A única forma compatível com o `pg_hba` versionado é o socket local,
exatamente como o provisionamento já faz (`setup_vm02.sh:58`: `sudo -u postgres psql`):

```bash
# A chave precisa ser legível pelo usuário postgres — restore_db.sh:107-110 aborta se não for.
install -o postgres -g postgres -m 600 /dev/null /etc/backup-key.txt

sudo -u postgres env   BACKUP_DIR=/var/backups/aprender BACKUP_AGE_KEY=/etc/backup-key.txt   DB_HOST=/var/run/postgresql DB_NAME=aprender_db DB_USER=aprender_user   <checkout>/v2/infra/scripts/restore_db.sh backup_full_<DATA>.sql.gz.age
```

⚠️ Essa invocação **nunca foi exercitada contra a VM02**. O buraco de credencial é
`M26-N1` (P1, **ABERTO** — `v2/docs/audits/2026-07-17-system-module-audit.md:9438`), e o
drill que provaria o caminho é `M26-03`/[#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646),
também aberto. **Sob incidente, use o pipeline manual** de
[Restore Completo](#restore-completo-desastre-total): ele é o único caminho cujo modo de
autenticação (`sudo -u postgres psql`, peer) é o mesmo que o repositório já usa em
produção.

Procedimento passo a passo: [Restore Completo](#restore-completo-desastre-total).

---

## Visão Geral

| Métrica | Valor |
|---------|-------|
| **RPO** (Recovery Point Objective) | 5 minutos (WAL archiving) — **alvo de projeto, não medido em prod** |
| **RTO** (Recovery Time Objective) | 1 hora |
| **Retenção** | 7 dias (configurável via `BACKUP_RETENTION_DAYS`) |
| **Frequência** | Diário às 3h (cron VM); 2h em Docker — ver SSOT |

## Arquitetura de Backup

```
┌─────────────────────────────────────────────────────────────┐
│                      VM02_Banco                             │
│                                                             │
│  ┌─────────────┐    ┌──────────────────┐                   │
│  │ PostgreSQL  │───▶│ WAL Archiving    │  (NÃO VERIFICADO   │
│  │             │    │ (a cada 5 min)   │   em produção)     │
│  └─────────────┘    └────────┬─────────┘                   │
│         │                    │                              │
│         │                    ▼                              │
│         │           /var/lib/postgresql/wal_archive/        │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ pg_dump     │  ← quem chama isto hoje é o Celery worker  │
│  │ | gzip      │    da VM01 (2h), não o cron da VM02        │
│  │ | age -r    │                                           │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  /var/backups/aprender/                                    │
│  └── backup_full_YYYYMMDD_HHMMSS.sql.gz.age                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

O nome de arquivo acima é o **único** que os scripts do repositório produzem
(`backup_db.sh:50-55`). Não existe nenhum script neste repositório que gere
`aprender_db_*.sql.gz`.

---

## Componentes

### 1. WAL Archiving (Point-in-Time Recovery)

> **Status: NÃO VERIFICADO em produção.** A configuração abaixo é a recomendada; nada no
> repositório prova que ela está aplicada na VM02. Para confirmar, rode na VM02:
> `sudo -u postgres psql -c "SHOW archive_mode; SHOW archive_command; SHOW archive_timeout;"`
> e `sudo -u postgres psql -c "SELECT * FROM pg_stat_archiver;"` (`last_archived_time`
> recente = archiving vivo). Enquanto isso não for feito, **trate o RPO de 5 min como
> aspiracional** e o RPO efetivo como "até 24h" (o dump diário).

**Configuração** (`postgresql.conf`):
```ini
archive_mode = on
archive_command = 'gzip < %p > /var/lib/postgresql/wal_archive/%f.gz'
archive_timeout = 300  # 5 minutos
```

### 2. Backup Diário (pg_dump + gzip + age)

**Script**: `v2/infra/scripts/backup_db.sh` (copiado para `/opt/scripts/` na VM).

**Quem dispara em produção hoje**: a task Celery `backup.perform_database_backup`, que roda
no serviço **`worker`** da stack Docker da VM01 às 02:00
(`v2/backend/config/celery.py:38-40`; `tasks_backup.py:57` invoca
`/app/infra/scripts/backup_db.sh`). Os dumps caem no bind-mount
`/var/backups/aprender:/backups` — declarado **apenas no `worker`**
(`docker-compose.prod.yml:235`). `web` e `beat` **não** enxergam `/backups`.

**Cron da VM02** (`v2/infra/cron/aprender-backup`, se instalado em `/etc/cron.d/`):
```cron
# Backup diário às 3h
0 3 * * * postgres /opt/scripts/backup_db.sh >> /var/log/aprender/backup.log 2>&1

# Limpeza de WAL archives (7 dias)
30 4 * * * postgres find /var/lib/postgresql/wal_archive -name "*.gz" -mtime +7 -delete

# Verificação semanal (domingo 5h)
0 5 * * 0 postgres /opt/scripts/verify_backup.sh >> /var/log/aprender/backup.log 2>&1
```

> **Não use a linha de limpeza de dumps do arquivo de cron.**
> `v2/infra/cron/aprender-backup:17` roda
> `find /var/backups/aprender -name "*.sql.gz" -mtime +7 -delete`, que **nunca casa** com os
> arquivos reais `backup_full_*.sql.gz.age`. Ela é, além de ineficaz, **redundante**: o
> próprio `backup_db.sh:103` já aplica a retenção com o glob correto
> (`-name "backup_full_*.sql.gz" -o -name "backup_full_*.sql.gz.age"`). Se precisar de uma
> limpeza extra fora do script, use o mesmo par de globs.

### 3. Verificação de Integridade

**Script**: `v2/infra/scripts/verify_backup.sh`

O que ele realmente verifica (`verify_backup.sh:21-79`):

| Backup | Presença | Tamanho mínimo (`BACKUP_MIN_SIZE`, 1024B) | `gzip -t` + marcadores SQL | Frescor |
|---|---|---|---|---|
| `*.sql.gz` (plaintext) | ✅ | ✅ (falha dura) | ✅ | aviso |
| `*.sql.gz.age` (**o que prod grava**) | ✅ | ✅ (falha dura) | ❌ **pulado** | aviso |

O conteúdo de um `.age` **não é** verificado na VM porque a **chave privada não vive na VM
por design** (`verify_backup.sh:41-43`): ela fica no gerenciador de senhas do mantenedor.
Consequência operacional honesta: em produção, "verificação de backup" hoje significa
**"existe, tem tamanho plausível e é recente"** — não "é restaurável". A prova de
restaurabilidade só sai de um ensaio de restore com a chave (ver
[Ensaio de DR](#ensaio-de-dr-o-único-teste-que-vale)).

### 4. Gate de frescor no deploy

`v2/infra/deployer/hooks/check_backup.sh` bloqueia a aplicação de uma release se não houver
dump válido: idade ≤ `BACKUP_MAX_AGE` (default 28h) **e** tamanho ≥ `BACKUP_MIN_SIZE`
(default 1024B), em `BACKUP_DIR` (default `/var/backups/aprender`). Ele só faz `stat` —
nunca lê o conteúdo, justamente porque os dumps são cifrados.

---

## Procedimentos

### Restore Completo (Desastre Total)

**Tempo estimado**: 20-40 minutos.

**Pré-requisitos**:
1. A **chave privada `age`** (do gerenciador de senhas do mantenedor). Ela **não** está na
   VM. Sem ela, nenhum backup de produção pode ser lido.
2. Um host com o binário **`age`** no PATH. A imagem de backend de **produção** tem `age`
   (`v2/infra/Dockerfile.prod:56`); a imagem **dev não tem**
   (`v2/infra/Dockerfile.dev:19-21`). Se restaurar direto na VM02, instale `age` lá antes.

```bash
# 0. Colocar a chave privada em um arquivo de permissão restrita (apagar ao final)
umask 077
install -m 600 /dev/null /etc/backup-key.txt
# colar a chave privada (age1... / AGE-SECRET-KEY-1...) em /etc/backup-key.txt

# 1. Parar quem escreve no banco — a stack roda em Docker na VM01, NÃO em systemd.
#    Pelo Portainer: parar os serviços web, worker e beat da stack de produção.
#    (Equivalente por CLI, de dentro da VM01:)
docker compose -f docker-compose.prod.yml stop web worker beat

# 2. Escolher o backup (nome real: backup_full_*.sql.gz.age)
ls -lht /var/backups/aprender/backup_full_*.sql.gz.age | head -5

# 3. VERIFICAR ANTES DE DESTRUIR: decifrar e testar o gzip, sem tocar no banco.
#    Se este comando sair 0, o backup está íntegro.
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gzip -t && echo "INTEGRIDADE OK"

# 4. Conferir que é um dump PostgreSQL de verdade (não um arquivo truncado)
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gunzip | head -20

# 5. REDE DE SEGURANÇA: dump do estado atual ANTES do DROP. É a lição de #1645 — o
#    restore_db.sh passou a fazer isso em 3bca74f3 (restore_db.sh:132-148); no
#    pipeline manual ela é sua responsabilidade.
sudo -u postgres pg_dump aprender_db \
  | gzip > /var/backups/aprender/pre-restore-safety-$(date +%Y%m%d_%H%M%S).sql.gz

# 6. Recriar o banco (DESTRUTIVO — só depois dos passos 3 e 5 saírem OK)
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
  WHERE datname = 'aprender_db' AND pid <> pg_backend_pid();"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS aprender_db;"
sudo -u postgres psql -c "CREATE DATABASE aprender_db OWNER aprender_user;"

# 7. Restaurar
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gunzip \
  | sudo -u postgres psql -d aprender_db -v ON_ERROR_STOP=1

# 8. Conferir o resultado — NÃO confie em "sucesso" implícito (ver #1645)
sudo -u postgres psql -d aprender_db -t -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
sudo -u postgres psql -d aprender_db -c "SELECT count(*) FROM core_usuario;"
sudo -u postgres psql -d aprender_db -c "SELECT count(*) FROM core_solicitacao;"
# Compare com os números esperados ANTES de liberar a aplicação. Pisos que o
# restore_db.sh aplica e valem aqui também (restore_db.sh:188-203): >= 20 tabelas
# e linhas > 0 em core_usuario e core_solicitacao.

# 9. Subir a stack (o serviço one-shot `migrate` aplica migrations pendentes
#    automaticamente antes de web/worker/beat — docker-compose.prod.yml:47-51)
docker compose -f docker-compose.prod.yml up -d

# 10. Health de dentro da VM01
curl -f http://127.0.0.1:8000/api/readyz/
curl -f http://127.0.0.1:8000/api/version/

# 11. Apagar a chave privada do host
shred -u /etc/backup-key.txt 2>/dev/null || rm -f /etc/backup-key.txt
```

> **Por que `sudo -u postgres` e não `restore_db.sh` aqui.** O pipeline acima autentica por
> **peer auth no socket local** — o único método que o `pg_hba.conf` versionado da VM02
> concede ao superusuário (`configs/vm02/pg_hba.conf:8`), e o mesmo que o provisionamento
> usa (`setup_vm02.sh:58`). O `restore_db.sh` está **correto no que faz** (#1611 e #1645
> fechados), mas não trata senha e não escolhe o socket sozinho: o default de `DB_HOST` é
> `localhost` (`restore_db.sh:26`) e a VM02 não escuta em loopback
> (`configs/vm02/postgresql.conf:8`). Para usá-lo aqui é preciso a invocação por socket de
> [Credencial](#-credencial--o-que-decide-se-o-script-chega-a-rodar), que **ainda não foi
> exercitada** (`M26-N1`, aberto). Sob incidente, o caminho acima é o que tem histórico.

> ~~**Passo 3 alternativo: `BACKUP_DIR=… BACKUP_AGE_KEY=… DB_HOST=localhost … restore_db.sh <arquivo>`**~~
> — **introduzido e revogado em 2026-08-25**. Substituía os passos manuais 3 a 8, mas
> `DB_HOST=localhost` faz o script abrir conexão **TCP** como `postgres` sem senha contra
> um Postgres que não escuta em 127.0.0.1 (`configs/vm02/postgresql.conf:8`) e que
> rejeitaria a conexão de qualquer forma (`configs/vm02/pg_hba.conf:18`). Falharia na
> primeira conexão, sob incidente. **Decisão (2026-08-25):** o procedimento canônico volta
> a ser o pipeline manual com peer auth; o `restore_db.sh` continua documentado, com a
> invocação por socket local e o carimbo de "não exercitado".

> **`ON_ERROR_STOP=1` não é opcional.** Sem ela o `psql` engole erros linha a linha e
> termina com exit 0 mesmo tendo perdido objetos — era exatamente o buraco de
> [#1645](https://github.com/matheusnorjosa/aprender_sistema/issues/1645), fechado em
> `3bca74f3`. O `restore_db.sh` passa a flag nos dois branches, cifrado e plaintext
> (`restore_db.sh:166, 170`); no pipeline manual ela vai na mão, como no passo 7.

### Restore Point-in-Time (PITR)

> **Depende de WAL archiving estar ligado** — ver a ressalva em
> [WAL Archiving](#1-wal-archiving-point-in-time-recovery). Confirme
> `pg_stat_archiver.last_archived_time` **antes** de contar com este procedimento num
> incidente. Requer também um `base_backup` (`pg_basebackup`), que é diferente do dump
> lógico do `backup_db.sh` — **não existe automação para ele neste repositório**.

```bash
# 1. Parar PostgreSQL
sudo systemctl stop postgresql

# 2. Limpar data directory (CUIDADO!)
sudo -u postgres rm -rf /var/lib/postgresql/15/main/*

# 3. Restaurar base backup
sudo -u postgres pg_restore -d postgres /var/backups/aprender/base_backup.tar

# 4. Criar recovery.signal
touch /var/lib/postgresql/15/main/recovery.signal

# 5. Adicionar ao postgresql.auto.conf:
#    restore_command = 'gunzip -c /var/lib/postgresql/wal_archive/%f.gz > %p'
#    recovery_target_time = '2026-01-12 14:30:00'
#    recovery_target_action = 'promote'

# 6. Iniciar PostgreSQL (replay automático)
sudo systemctl start postgresql

# 7. Verificar recovery
sudo -u postgres psql -c "SELECT pg_is_in_recovery();"
# Deve retornar 'f' (false) após recovery completo
```

### Verificação Manual de Backup

```bash
# Listar backups reais (o padrão é backup_full_*, NÃO aprender_db_*)
ls -lh /var/backups/aprender/backup_full_*.sql.gz.age

# Integridade de um backup CIFRADO (precisa da chave privada)
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age | gzip -t
echo "exit=$?"   # 0 = íntegro

# Espiar o conteúdo (primeiras linhas do dump SQL)
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gunzip | head -100

# Verificação automatizada (presença + tamanho + frescor; NÃO abre .age)
/opt/scripts/verify_backup.sh
```

> `gzip -t` e `zcat` aplicados **diretamente** a um `.sql.gz.age` sempre falham com
> `not in gzip format`. Isso **não** indica corrupção — indica que o arquivo está cifrado.
> Decifre primeiro.

### Ensaio de DR (o único teste que vale)

O `test_dr.sh` do repositório **não** exercita o caminho cifrado: ele gera o dump com
`pg_dump | gzip` direto (`test_dr.sh:76`) e restaura com `gunzip -c | psql`
(`test_dr.sh:103`) — nunca chama `restore_db.sh` nem `age`. Ou seja, ele passa verde num
cenário que **não é** o de produção (issue
[#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646)). Também depende de
um serviço `db` no compose, que **existe só em dev/staging**.

Um ensaio que realmente prova o DR, feito **fora de produção**, com a chave privada:

1. Gerar um dump cifrado real: `BACKUP_AGE_RECIPIENT=<recipient> backup_db.sh`.
2. Restaurar num banco descartável com **`restore_db.sh`** — é justamente o caminho de
   produção que precisa ser exercitado, e o que `test_dr.sh` não cobre. O ensaio precisa
   incluir a **credencial**: aponte `DB_HOST` para o socket local e rode como usuário
   `postgres` (ver [Credencial](#-credencial--o-que-decide-se-o-script-chega-a-rodar)) —
   o script não trata senha, e é esse pedaço que nunca foi exercitado (`M26-N1`). Comparar
   com o pipeline manual de [Restore Completo](#restore-completo-desastre-total).
3. Comparar contagens de `core_usuario`, `core_solicitacao`, `core_municipio`,
   `core_projeto`, `core_gerencia` contra a origem.
4. **Registrar a data do ensaio** em [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md).

Enquanto o passo 4 estiver vazio, a resposta honesta à pergunta "temos backup restaurável?"
é **"não sabemos"**. Precedente: issue
[#1537](https://github.com/matheusnorjosa/aprender_sistema/issues/1537) — um backup que
nunca rodou.

---

## Monitoramento

### Logs

```bash
# Backup em produção: o job roda no worker da stack Docker (VM01), não no cron da VM02
docker compose -f docker-compose.prod.yml logs --tail=200 worker | grep -i backup

# Se o cron da VM02 estiver instalado
tail -f /var/log/aprender/backup.log

# Log do PostgreSQL (VM02)
tail -f /var/log/postgresql/postgresql-15-main.log
```

### Alertas Recomendados

> **Parcialmente implementado.** Não existe regra de alerta **versionada** (Prometheus)
> neste repositório e o Grafana não roda em produção — ver
> [OBSERVABILITY.md](./OBSERVABILITY.md). O que existe hoje, em código:
>
> - **Dead-man diário de frescor** — `backup.check_backup_freshness` roda às 06:00
>   (`config/celery.py:50-59`) e alarma quando o backup mais novo passa de
>   `BACKUP_DEADMAN_MAX_AGE_HOURS` (default 24h, `settings.py:868`) ou quando não há backup
>   nenhum (`tasks_backup.py:322-342`). O alarme é `logger.error` **mais** Sentry quando há
>   DSN (`tasks_backup.py:191-201`) — ou seja, **não depende do Sentry** para existir.
>   Criado em `2bbcf60b` ([#1733](https://github.com/matheusnorjosa/aprender_sistema/issues/1733),
>   2026-08-17) depois de o backup morrer 10 dias em silêncio (`tasks_backup.py:304-307`).
> - **Gate de deploy** — `check_backup.sh` continua sendo a única checagem que **bloqueia**
>   algo (idade + tamanho), e é o backstop se o próprio beat/worker estiver morto
>   (`tasks_backup.py:309-311`).
>
> O que **falta**: destino de alerta. Sem `SENTRY_DSN` e sem agregador de logs
> (`OBSERVABILITY.md:49`), o `ERROR` do dead-man só existe no stdout do container.

| Condição | Severidade | Ação |
|----------|------------|------|
| Backup não executado em 24h | Critical | **Já detectado** pelo dead-man diário (`backup.check_backup_freshness`). Verificar o worker (Celery beat/worker), disco e o bind-mount `/backups` |
| Ensaio de restore não feito no trimestre | High | Agendar ensaio com a chave privada |
| Disco > 80% | Warning | Conferir retenção (`BACKUP_RETENTION_DAYS`) |
| WAL archive > 10GB | Warning | Verificar `pg_stat_archiver` |

---

## Checklist de Setup (VM02_Banco)

> **Estado não verificado.** Este checklist descreve o que o repositório prevê para a VM02.
> Nada aqui foi confirmado como instalado em produção — em produção quem gera os dumps hoje
> é a task Celery da VM01. Antes de marcar qualquer item, confirme na própria VM.

- [ ] Criar diretório de backups: `mkdir -p /var/backups/aprender` (0755, dono = UID do `appuser` do container worker)
- [ ] Criar diretório WAL: `mkdir -p /var/lib/postgresql/wal_archive`
- [ ] Copiar scripts: `cp v2/infra/scripts/*.sh /opt/scripts/`
- [ ] Dar permissão: `chmod +x /opt/scripts/*.sh`
- [ ] Instalar `age` na VM (necessário para qualquer restore): `apt-get install -y age`
- [ ] Copiar cron: `cp v2/infra/cron/aprender-backup /etc/cron.d/` — **e corrigir a linha 17**, cujo glob `*.sql.gz` não casa com os arquivos `.age` reais
- [ ] Verificar WAL archiving: `SELECT * FROM pg_stat_archiver;`
- [ ] Executar backup manual: `BACKUP_AGE_RECIPIENT=<recipient> /opt/scripts/backup_db.sh`
- [ ] Verificar backup: `/opt/scripts/verify_backup.sh`
- [ ] **Ensaio de restore com a chave privada** e registro da data

---

## Troubleshooting

### "ERROR: Backup file is corrupted!" ao rodar `restore_db.sh`

Esse era o sintoma do **#1611**, corrigido em `8f392636` (2026-08-10): o script rodava
`gzip -t` no `.age` sem decifrar. **Hoje essa mensagem só sai no branch plaintext**
(`restore_db.sh:117`) — num `.sql.gz` de verdade corrompido. Para um `.age` inválido a
mensagem é outra: `ERROR: backup cifrado invalido (falha ao decifrar ou gzip
corrompido)!` (`:113`).

```bash
head -c 22 /var/backups/aprender/backup_full_<DATA>.sql.gz.age
# "age-encryption.org/v1"  => arquivo cifrado

# O script no host/imagem está atualizado? O fix é 8f392636:
grep -n "age -d -i" /app/infra/scripts/restore_db.sh   # deve casar em :112 e :166
```

- **Sai `Backup file is corrupted!` num arquivo `.age`** → o script é anterior a
  `8f392636`. Atualize a imagem/checkout; não contorne.
- **Sai `backup cifrado invalido`** → decifragem ou gzip falharam de verdade. Confira
  `BACKUP_AGE_KEY` (chave certa? legível?) e teste outro artefato.

### `restore_db.sh --latest` não acha nada

`BACKUP_DIR` **passou a ser respeitado** em `8f392636` (`restore_db.sh:23`) — antes era
hardcoded em `/var/backups/aprender`, e de dentro do container (onde o diretório é
`/backups`) o `--latest` não achava nada. Exporte a variável:

```bash
BACKUP_DIR=/backups /app/infra/scripts/restore_db.sh --latest
```

Se ainda assim não achar, confirme que há artefato no diretório: a seleção cobre
`*.sql.gz` **e** `*.sql.gz.age` (`:42, 62, 67`).

### Backup falhou

```bash
# Espaço em disco no host da VM01 (onde o bind-mount aponta)
df -h /var/backups/aprender

# Logs do worker (é ele quem roda o backup)
docker compose -f docker-compose.prod.yml logs --tail=200 worker | grep -i backup

# Causa clássica: BACKUP_AGE_RECIPIENT ausente => backup_db.sh:44-48 ABORTA (fail-closed).
docker compose -f docker-compose.prod.yml exec worker printenv | grep BACKUP_AGE_RECIPIENT
```

### WAL archiving parado

```bash
sudo -u postgres psql -c "SELECT * FROM pg_stat_archiver;"
ls -la /var/lib/postgresql/wal_archive/
sudo -u postgres psql -c "SELECT pg_switch_wal();"  # força novo WAL segment
```

### Restore travou / conexões presas

```bash
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname = 'aprender_db';"
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
  WHERE datname = 'aprender_db' AND pid <> pg_backend_pid();"
```
