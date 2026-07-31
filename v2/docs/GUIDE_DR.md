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

## ⛔ LEIA ANTES DE RESTAURAR — a ferramenta oficial está quebrada (#1611)

`v2/infra/scripts/restore_db.sh` **não consegue restaurar o único formato de backup que
existe em produção.**

- Produção grava **exclusivamente** `backup_full_YYYYMMDD_HHMMSS.sql.gz.age` (cifrado com
  `age`). Prova: `backup_db.sh:44-48` é *fail-closed* — sem `BACKUP_AGE_RECIPIENT` e sem
  `BACKUP_ALLOW_PLAINTEXT=1` o backup **aborta**; `backup_db.sh:50-55` acrescenta o sufixo
  `.age` quando há recipient; `docker-compose.prod.yml:197` define o recipient no serviço
  `worker`.
- `restore_db.sh:91` executa `gzip -t "$BACKUP_FILE"` **incondicionalmente**, antes do
  branch que decifra `.age` (`restore_db.sh:113-119`). Um artefato `age` começa com o
  cabeçalho de texto `age-encryption.org/v1`, que não é gzip.
- Resultado (reproduzido nos **três** caminhos de entrada: arquivo explícito, `--latest` e
  modo interativo): o script aborta com

  ```
  gzip: .../backup_full_20260720_010000.sql.gz.age: not in gzip format
  ERROR: Backup file is corrupted!
  ```

  **A mensagem é falsa.** O backup pode estar perfeitamente íntegro; o que está errado é a
  verificação.

**Atenuante — não há destruição de dados.** A execução para na linha 91, **antes** do
`DROP DATABASE` da linha 107. O custo é RTO estourado e perda de confiança no DR, não perda
de dados.

Rastreio: issue [#1611](https://github.com/matheusnorjosa/aprender_sistema/issues/1611)
(épico [#1662](https://github.com/matheusnorjosa/aprender_sistema/issues/1662)).
Enquanto não estiver corrigida, **use o procedimento manual da seção
[Restore Completo](#restore-completo-desastre-total)** — ele funciona.

### Bug adjacente: `BACKUP_DIR` ignorado no restore

`restore_db.sh:17` **hardcoda** `BACKUP_DIR="/var/backups/aprender"` e ignora a variável de
ambiente, enquanto `backup_db.sh:31` usa `BACKUP_DIR="${BACKUP_DIR:-/backups}"`. Dentro de
um container (onde `/var/backups/aprender` do host é montado como `/backups`), o `--latest`
do restore não acha nada. Sempre passe o **caminho absoluto** do arquivo.

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
#    Se este comando sair 0, o backup está íntegro — independente do que o
#    restore_db.sh disser.
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gzip -t && echo "INTEGRIDADE OK"

# 4. Conferir que é um dump PostgreSQL de verdade (não um arquivo truncado)
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gunzip | head -20

# 5. Recriar o banco (DESTRUTIVO — só depois do passo 3 sair OK)
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity \
  WHERE datname = 'aprender_db' AND pid <> pg_backend_pid();"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS aprender_db;"
sudo -u postgres psql -c "CREATE DATABASE aprender_db OWNER aprender_user;"

# 6. Restaurar — este é o pipeline que funciona (contorno de #1611)
age -d -i /etc/backup-key.txt /var/backups/aprender/backup_full_<DATA>.sql.gz.age \
  | gunzip \
  | sudo -u postgres psql -d aprender_db -v ON_ERROR_STOP=1

# 7. Conferir o resultado — NÃO confie em "sucesso" implícito (ver #1645)
sudo -u postgres psql -d aprender_db -t -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
sudo -u postgres psql -d aprender_db -c "SELECT count(*) FROM core_usuario;"
sudo -u postgres psql -d aprender_db -c "SELECT count(*) FROM core_solicitacao;"
# Compare com os números esperados ANTES de liberar a aplicação.

# 8. Subir a stack (o serviço one-shot `migrate` aplica migrations pendentes
#    automaticamente antes de web/worker/beat — docker-compose.prod.yml:47-51)
docker compose -f docker-compose.prod.yml up -d

# 9. Health de dentro da VM01
curl -f http://127.0.0.1:8000/api/readyz/
curl -f http://127.0.0.1:8000/api/version/

# 10. Apagar a chave privada do host
shred -u /etc/backup-key.txt 2>/dev/null || rm -f /etc/backup-key.txt
```

> **`ON_ERROR_STOP=1` não é opcional.** Sem ele, o `psql` engole erros linha a linha e
> termina com exit 0 mesmo tendo perdido objetos. É exatamente o buraco de
> `restore_db.sh`, que declara `Restore completed successfully!` com exit 0 depois de um
> restore incompleto (issue
> [#1645](https://github.com/matheusnorjosa/aprender_sistema/issues/1645)).

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
2. Restaurar num banco descartável pelo pipeline manual da seção
   [Restore Completo](#restore-completo-desastre-total), com `ON_ERROR_STOP=1`.
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

> **Alvo, não implementado.** Não existe regra de alerta versionada neste repositório; a
> única checagem automática que hoje **bloqueia** algo é o `check_backup.sh` no caminho de
> deploy (idade + tamanho). Ver [OBSERVABILITY.md](./OBSERVABILITY.md) — Prometheus/Grafana
> não rodam em produção.

| Condição | Severidade | Ação |
|----------|------------|------|
| Backup não executado em 24h | Critical | Verificar o worker (Celery beat/worker), disco e o bind-mount `/backups` |
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

**Quase certamente NÃO é corrupção.** É o bug #1611: `restore_db.sh:91` roda `gzip -t` num
arquivo `.age`. Confirme em 10 segundos:

```bash
head -c 22 /var/backups/aprender/backup_full_<DATA>.sql.gz.age
# "age-encryption.org/v1"  => arquivo cifrado, íntegro; a verificação é que está errada
```

Siga o [Restore Completo](#restore-completo-desastre-total) manual.

### `restore_db.sh --latest` não acha nada

`restore_db.sh:17` ignora a env var `BACKUP_DIR` e procura sempre em
`/var/backups/aprender`. Dentro de um container o diretório é `/backups`. Passe o caminho
absoluto do arquivo, ou use o pipeline manual.

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
