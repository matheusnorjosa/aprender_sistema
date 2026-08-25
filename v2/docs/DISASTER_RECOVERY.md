# Disaster Recovery Runbook

**Data**: 2026-07-24 (revisão contra o código)
**Status**: Ativo
**Referência**: PLAN_maturity_gaps.md (Gap 9)
**Ambiente**: stack Docker Compose. Em **produção** ela roda na VM01 sob Portainer
(`v2/infra/docker-compose.prod.yml`: `migrate`, `web`, `redis`, `worker`, `beat`,
`frontend` — **não há serviço `db`**, o PostgreSQL é externo na VM02). Para os
procedimentos do lado PostgreSQL nativo e PITR, ver [GUIDE_DR.md](./GUIDE_DR.md).

> **Parâmetros de backup (RPO/RTO/retenção/frequência)** são definidos no SSOT
> [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md#parâmetros-canônicos-rpo--rto--retenção--frequência).
> Este documento foca em **cenários de recovery** (procedimentos operacionais).

---

## 0. Antes de restaurar: use `restore_db.sh`

> [!important] O aviso que abria este runbook foi revogado em 2026-08-25.
> Até essa data a seção 0 dizia **"não use `restore_db.sh` contra um backup de produção"**
> e mandava o operador para um pipeline manual. Os dois defeitos que justificavam o aviso
> foram corrigidos:
>
> | Defeito | Corrigido em |
> |---|---|
> | #1611 / M26-01 — `gzip -t` incondicional rejeitava todo `.age` com `Backup file is corrupted!` (mensagem falsa) | `8f392636`, 2026-08-10 |
> | #1645 / M26-02 — declarava `Restore completed successfully!` com exit 0 sobre banco vazio | `3bca74f3`, 2026-08-21 |
>
> Numa emergência, um aviso obsoleto empurra o operador para o caminho pior — sem safety
> dump e sem verificação. **Use a ferramenta.**

O `restore_db.sh` hoje, contra um `.age` de produção:

1. Verifica a integridade **antes de destruir qualquer coisa**, decifrando com `age -d` e
   só então rodando `gzip -t` (`restore_db.sh:101-121`). Falha cedo se o binário `age` não
   estiver no PATH ou a chave não for legível (`:103-110`).
2. Tira um **safety dump** do banco atual antes do `DROP DATABASE` (`:132-148`).
3. Restaura com `psql -v ON_ERROR_STOP=1` sob `pipefail`; qualquer erro de SQL,
   decifragem ou descompressão aborta em vermelho e informa onde o safety dump ficou
   (`:162-178`).
4. **Verifica o resultado**: piso de tabelas (`RESTORE_MIN_TABLES`, default 20) e linhas
   > 0 em `core_usuario` e `core_solicitacao`. Só então imprime o banner verde
   (`:180-212`).

> [!caution] Em produção, `DB_HOST` por TCP **não autentica** — `M26-N1`, P1, aberto
> `restore_db.sh` conecta **sempre** como superusuário `postgres` via `-h $DB_HOST` e
> **não tem tratamento de senha nenhum**: `grep -i PGPASSWORD v2/infra/scripts/restore_db.sh`
> retorna zero (para contraste, `backup_db.sh` exporta `PGPASSWORD`).
>
> A VM02 escuta em `10.0.0.2`, não em loopback
> (`v2/infra/configs/vm02/postgresql.conf:8`), e o `pg_hba.conf:18` termina com
> `host all all 0.0.0.0/0 reject`. A única regra que aceita `postgres` é `local … peer`
> (`:8`) — socket unix.
>
> **Na VM02, use o pipeline manual com peer auth** (`sudo -u postgres`), que é o
> procedimento canônico e está em [GUIDE_DR.md](./GUIDE_DR.md). O comando abaixo serve
> para **dev/staging**, onde o banco aceita a conexão.
>
> `M26-N1` (P1, confirmado) —
> `v2/docs/audits/2026-07-17-system-module-audit.md:9438`.

```bash
# dev/staging — em produção, veja o aviso acima
BACKUP_DIR=/var/backups/aprender BACKUP_AGE_KEY=/etc/backup-key.txt \
DB_HOST="$DB_HOST" DB_NAME=aprender_db \
  /app/infra/scripts/restore_db.sh --latest
```

Pré-requisitos: a **chave privada `age`** não fica na VM por design — está no gerenciador
de senhas do mantenedor. O binário `age` existe na imagem de backend **de produção**
(`v2/infra/Dockerfile.prod:56`) e **não** existe na imagem dev
(`v2/infra/Dockerfile.dev:19-21`).

> ⚠️ **O que ainda não foi provado.** O código está correto e o caminho `.age` é
> exercitado por ele, mas **nenhum drill real** foi executado: `test_dr.sh` não gera
> `.age` nem chama `age -d`. Issue
> [#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646) (M26-03) segue
> **ABERTA**. Trate a restaurabilidade como *inferida do código*, não demonstrada.

Passo a passo completo:
[GUIDE_DR.md → Restore Completo](./GUIDE_DR.md#restore-completo-desastre-total).

<details>
<summary>Pipeline manual (contorno histórico de #1611 — só para host sem o repositório)</summary>

Não faz safety dump nem verificação pós-restore; foi por isso que #1645 existiu.

```bash
age -d -i /etc/backup-key.txt <arquivo>.sql.gz.age | gzip -t   # verificar ANTES
age -d -i /etc/backup-key.txt <arquivo>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1
```

</details>

---


## 1. Visão Geral

Este documento define os procedimentos de recuperação de desastres para o AS v2
em ambientes Docker Compose. Para a configuração do pipeline de backup (script,
agendamento, criptografia, S3), consulte o SSOT
[`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md).

### 1.1 RTO/RPO (resumo — fonte: SSOT)

| Métrica | Valor |
|---------|-------|
| **RPO** | 5 minutos (WAL archiving) — **alvo; WAL archiving não verificado em prod** |
| **RTO** | 1 hora (restore + migrations + smoke) |

### 1.2 Backups (resumo — fonte: SSOT)

| Tipo | Frequência | Retenção | Storage |
|------|------------|----------|---------|
| Full dump (cifrado `.age`) | Diário 2:00 AM, task Celery no serviço **`worker`** | 7 dias (`BACKUP_RETENTION_DAYS`) | **prod**: bind-mount `/var/backups/aprender:/backups` (`docker-compose.prod.yml:235`); **dev**: volume `backup_data` |
| WAL archiving | Contínuo (`archive_timeout=300`) — **não verificado em prod** | 7 dias | `/var/lib/postgresql/wal_archive/` na VM02 |
| Redis snapshot | Não persistido | - | Memory only |

> O bind-mount `/backups` existe **apenas no serviço `worker`**. `web`, `beat` e
> `frontend` não enxergam o diretório — comandos do tipo
> `docker compose exec web ls /backups` falham em produção.

---

## 2. Cenários de Recuperação

### 2.1 Cenário 1: Database Corruption

**Sintomas**:
- Erros de leitura/escrita no PostgreSQL
- Inconsistências nos dados
- `pg_catalog` corrompido

**Procedimento**:

```bash
# 1. Parar quem escreve no banco (em prod: pelo Portainer, ou de dentro da VM01)
docker compose -f docker-compose.prod.yml stop web worker beat

# 2. Identificar último backup válido — o nome real é backup_full_*.sql.gz.age.
#    NÃO existe "latest.sql.gz".
ls -lht /var/backups/aprender/backup_full_*.sql.gz.age | head -5

# 3. Restaurar com a ferramenta oficial (ver secao 0). Ela verifica a integridade do
#    .age ANTES de destruir, tira safety dump do banco atual, aborta em erro de SQL
#    e confere tabelas + linhas antes de declarar sucesso. Pede confirmacao 'yes'.
BACKUP_DIR=/var/backups/aprender BACKUP_AGE_KEY=/etc/backup-key.txt \
DB_HOST="$DB_HOST" DB_NAME=aprender_db \
  /app/infra/scripts/restore_db.sh backup_full_<DATA>.sql.gz.age

# 4. Ler a saida. Exit 0 ja significa "tabelas restauradas E tabelas-chave nao-vazias"
#    (restore_db.sh:180-212); exit 1 imprime onde ficou o safety dump do estado
#    anterior. Conferencia independente, se quiser:
psql -h "$DB_HOST" -U postgres -d aprender_db -c "SELECT count(*) FROM core_usuario;"
psql -h "$DB_HOST" -U postgres -d aprender_db -c "SELECT count(*) FROM core_solicitacao;"

# 5. Reiniciar a stack (o one-shot `migrate` aplica migrations antes de web/worker/beat)
docker compose -f docker-compose.prod.yml up -d

# 6. Validar de dentro da VM01
curl -f http://127.0.0.1:8000/api/readyz/
curl -f http://127.0.0.1:8000/api/version/
```

> Em **dev/staging** (compose com serviço `db`) o equivalente é
> `docker compose exec -T db psql -U postgres -d aprender_db`. Em **produção** não existe
> serviço `db`: o PostgreSQL é externo (VM02), acessado por `DB_HOST`.

### 2.2 Cenário 2: Perda Total do Servidor

**Sintomas**:
- Servidor inacessível
- Disco corrompido ou perdido
- VM destruída

**Procedimento**:

> **Cópia offsite não existe hoje.** O upload para S3 é opt-in via `S3_BUCKET`
> (`backup_db.sh:34,87-89`) e **nenhuma imagem do projeto instala o `aws` CLI**
> (`Dockerfile.prod:56`, `Dockerfile.dev:19-21`). Se o host que guarda
> `/var/backups/aprender` for perdido junto com a VM, **não há de onde restaurar**.
> Ver [BACKUP_OPERATIONS.md → Estratégia 3-2-1](./BACKUP_OPERATIONS.md#estratégia-3-2-1-recomendada--alvo).

```bash
# 1. Provisionar novo servidor
# (Golden VM / Portainer — ver docs de infra)

# 2. Recriar a stack de produção no Portainer a partir de
#    v2/infra/docker-compose.prod.yml, com o IMAGE_TAG da release desejada.
#    Deploy é PULL-BASED (ADR-018): produção só muda por `promote.yml`.

# 3. Obter o dump. Se houver cópia offsite (S3_BUCKET configurado):
aws s3 cp s3://<bucket>/backups/backup_full_<DATA>.sql.gz.age ./
#    Sem cópia offsite, a única fonte é /var/backups/aprender do host original.

# 4. Subir só o necessário para restaurar
docker compose -f docker-compose.prod.yml up -d redis

# 5. Restaurar com restore_db.sh (ver secao 0). Rode a partir de um container da
#    imagem de backend, que traz `age`, `psql` e o script em /app/infra/scripts.
BACKUP_DIR=$(pwd) BACKUP_AGE_KEY=/etc/backup-key.txt \
DB_HOST="$DB_HOST" DB_NAME=aprender_db \
  /app/infra/scripts/restore_db.sh backup_full_<DATA>.sql.gz.age

# 6. Subir a aplicação (serviços reais: migrate, web, worker, beat, frontend)
docker compose -f docker-compose.prod.yml up -d

# 7. Validar de dentro da VM
curl -f http://127.0.0.1:8000/api/readyz/
curl -f http://127.0.0.1:8000/api/version/
```

### 2.3 Cenário 3: Credenciais Comprometidas

**Sintomas**:
- Acesso não autorizado detectado
- Alertas de segurança
- Comportamento anômalo nos logs

**Procedimento**:

```bash
# 1. Revogar todas as sessões
#    ATENÇÃO: as sessões vivem no Redis, não no banco
#    (settings.py:328-329 — SESSION_ENGINE=cache, SESSION_CACHE_ALIAS=default).
#    `manage.py clearsessions` opera sobre a tabela de sessões do Django e NÃO
#    derruba ninguém neste setup. O que derruba é limpar o cache:
docker compose exec -T web python -c "from django.core.cache import cache; cache.clear()"
#    Efeito colateral aceito num incidente de credencial: isso também limpa o
#    cache de capabilities/options (o app repopula sob demanda).

# 2. Rotacionar chave de criptografia GCal
docker compose exec web python manage.py rotate_gcal_encryption_key

# 3. Regenerar SECRET_KEY
# Atualizar SECRET_KEY no .env ou secrets manager

# 4. Forçar re-login de todos usuários
docker compose restart web

# 5. Auditar logs
docker compose exec web python manage.py compliance_audit --days=7

# 6. Notificar stakeholders
```

### 2.4 Cenário 4: Google Calendar API Indisponível

**Sintomas**:
- Circuit breaker em estado OPEN
- Erros 5xx do GCal API
- Eventos não sincronizando

**Procedimento**:

```bash
# 1. Verificar status do circuit breaker
#    /healthz/detailed/ é GATEADO (superuser ou IP interno — config/urls.py:46-54):
#    de fora da rede responde 403. Rode de dentro da VM.
curl http://127.0.0.1:8000/healthz/detailed/
# Esperado: "gcal_circuit": "open"
#    Alternativa autenticada: GET /api/gcal/circuit-breaker/ (apps/core/urls.py:315)

# 2. Verificar status do Google
# https://www.google.com/appsstatus/dashboard/

# 3. Se Google estiver OK, resetar circuit breaker
docker compose exec -T web python -c "
from apps.core.services.gcal.circuit_breaker import reset_circuit
reset_circuit()
"

# 4. Verificar fila de retry — o serviço se chama `worker` (não `celery`)
docker compose exec -T worker celery -A config inspect active

# 5. Monitorar logs
docker compose logs -f web | grep gcal
```

---

## 3. Scripts de Backup/Restore

Scripts canônicos em `v2/infra/scripts/`:

- **`backup_db.sh`** — script unificado Docker+VM. Configurável via env vars
  (`DB_HOST/DB_PORT/DB_USER/DB_NAME/DB_PASSWORD`, `BACKUP_DIR`,
  `BACKUP_RETENTION_DAYS`, `S3_BUCKET`, `BACKUP_AGE_RECIPIENT`). Nomenclatura
  `backup_full_YYYYMMDD_HHMMSS.sql.gz[.age]` (`backup_db.sh:50-55`). Em produção o
  sufixo é **sempre** `.age`. Retenção no próprio script (`backup_db.sh:103`), com glob
  que cobre `.sql.gz` **e** `.sql.gz.age`. **Não duplicar lógica neste doc.**
- **`restore_db.sh`** — **operante para `.age` e plaintext** (ver seção 0). Verificação de
  integridade ciente do formato (`:101-121`), `BACKUP_DIR` respeitando a env var (`:23`,
  então `--latest` funciona de dentro do container), safety dump pré-DROP (`:132-148`),
  `ON_ERROR_STOP=1` + `pipefail` (`:162-178`) e verificação pós-restore de tabelas e
  linhas (`:180-212`). Corrigido em `8f392636` (#1611) e `3bca74f3` (#1645); o aviso
  anterior de "quebrado" foi revogado em 2026-08-25.
- **`verify_backup.sh`** — para `.age`, verifica **presença + tamanho + frescor** e
  **pula a checagem de conteúdo** (`verify_backup.sh:44-48`), porque a chave privada não
  fica na VM. "Verificado" aqui não significa "restaurável".

Para detalhes completos (variáveis, S3 setup, criptografia age — SEC-017),
consultar [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md). Os exemplos
operacionais nas seções 2.1-2.4 acima referenciam esses scripts.

---

## 4. Testes de DR

### 4.1 O que `test_dr.sh` realmente cobre (e o que não cobre)

```bash
./scripts/test_dr.sh
```

Este script:
1. Cria um dump com `pg_dump | gzip` **em texto claro** (`test_dr.sh:76`)
2. Restaura em database separado com `gunzip -c | psql` (`test_dr.sh:103`)
3. Valida contagem de tabelas e presença das tabelas-chave
4. Limpa o database de teste

**Limites conhecidos — leia antes de tratar um verde como garantia de DR:**

- ❌ **Nunca exercita o formato de produção.** Não gera `.age`, não chama `age -d` e não
  chama `restore_db.sh`. Foi essa cegueira que deixou #1611 e #1645 vivos até 2026-08;
  ambos já foram corrigidos, mas o teste que os teria pego **continua não existindo**.
  Issue [#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646) —
  **ABERTA**.
- ❌ Depende de um serviço `db` no compose (`docker compose exec -T db …`), que só existe
  em **dev/staging**. Em produção o PostgreSQL é externo.
- ✅ **Corrigido.** Existe `v2/infra/scripts/tests/restore_db.bats`, com 7 testes:
  **criado por `8f392636`** (2026-08-10, #1691 — o fix do #1611) com 5 casos, e
  **ampliado por `3bca74f3`** (2026-08-21, #1793) com os 2 do #1645. Cobre `.age` válido,
  corrupção, formato simples, diretório customizado, `--latest`, erro no meio do restore
  e banco com tabela-chave vazia. Até 2026-08-25 esta linha dizia que a cobertura era zero.

  > O que os `.bats` **não** cobrem — e é a razão de o #1646 seguir aberto: eles exercitam
  > o script, nunca um artefato `.age` real restaurado num banco real. Cobertura de unidade
  > não é ensaio de recuperação.

O ensaio que de fato prova o DR está em
[GUIDE_DR.md → Ensaio de DR](./GUIDE_DR.md#ensaio-de-dr-o-único-teste-que-vale).

### 4.2 Checklist de Validação

- [ ] Backup foi criado com sucesso e tem sufixo `.age`
- [ ] Backup tem tamanho razoável (piso duro de `check_backup.sh`/`verify_backup.sh`: 1024B)
- [ ] **Decifrou** com a chave privada e passou no `gzip -t`
- [ ] Restore rodou com `ON_ERROR_STOP=1` e sem erro
- [ ] Tabelas principais existem após restore
- [ ] Contagem de registros bate com a origem (conferida explicitamente)
- [ ] Aplicação inicia após restore
- [ ] `/api/readyz/` e `/api/version/` respondem de dentro da VM
- [ ] **Data do ensaio registrada** em `BACKUP_OPERATIONS.md`

---

## 5. Monitoramento

### 5.1 Alertas — alvo, não implementado

> Não existe regra de alerta versionada neste repositório. Prometheus/Grafana **não rodam
> em produção** (ver [OBSERVABILITY.md](./OBSERVABILITY.md)); em prod só existe `/metrics`
> gated + Sentry condicional (e `SENTRY_DSN` estava ausente em prod na última verificação).
> A **única** checagem automática que hoje bloqueia algo relacionado a backup é
> `v2/infra/deployer/hooks/check_backup.sh`, que barra a aplicação de uma release quando
> não há dump com idade ≤ `BACKUP_MAX_AGE` (28h) e tamanho ≥ `BACKUP_MIN_SIZE` (1024B).

| Alerta | Condição | Severidade |
|--------|----------|------------|
| BackupFailed | Backup job falhou | Critical |
| BackupStale | Último backup > 24h | Warning |
| DiskSpaceLow | Disco backup < 20% | Warning |
| WALArchiveBehind | WAL archive atrasado > 1h | Warning |

### 5.2 Métricas

> ⚠️ **As métricas `as_backup_size_bytes`, `as_backup_last_success_timestamp` e
> `as_gcal_circuit_breaker_state` NÃO existem** — não há nenhuma definição delas no
> backend. Não escreva alerta nem painel em cima delas. A única métrica customizada com
> prefixo `as_` que existe hoje é `as_db_transaction_retries_total`
> (`apps/core/services/db_retry.py:64`), usada em
> [RUNBOOK_concurrency.md](./RUNBOOK_concurrency.md). As demais métricas disponíveis são as
> geradas por `django-prometheus` em `/metrics`.

Instrumentar backup em Prometheus continua como item de backlog — ver
[BACKUP_OPERATIONS.md](./BACKUP_OPERATIONS.md#prometheus-metrics-future).

---

## 6. Contatos de Emergência

| Papel | Nome | Contato |
|-------|------|---------|
| DBA | - | - |
| DevOps | - | - |
| Líder Técnico | - | - |
| Stakeholder | - | - |

---

## 7. Revisões

| Data | Versão | Mudanças |
|------|--------|----------|
| 2026-01-12 | 1.0 | Versão inicial |
| 2026-07-24 | 1.1 | Revisão contra o código (auditoria M26). Adicionada seção 0 (#1611: `restore_db.sh` rejeita todo backup `.age` de produção). Corrigidos: nomes de arquivo (`latest.sql.gz` → `backup_full_*.sql.gz.age`), serviço `celery` → `worker`, ausência do serviço `db` em produção, `clearsessions` vs sessões no Redis, métricas Prometheus inexistentes, limites reais do `test_dr.sh`. |
| 2026-08-25 | 1.2 | **Seção 0 revogada**: #1611 corrigido em `8f392636` (2026-08-10) e #1645 em `3bca74f3` (2026-08-21). O runbook voltou a mandar usar `restore_db.sh`; o pipeline manual virou contorno histórico. **#1646 (drill real de DR) permanece ABERTA** e continua sinalizada. |

---

## 8. Referências

- [PostgreSQL Backup Guide](https://www.postgresql.org/docs/current/backup.html)
- [SCALING.md](./SCALING.md)
- [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md)
