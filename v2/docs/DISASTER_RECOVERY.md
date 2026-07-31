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

## 0. ⛔ A ferramenta oficial de restore está quebrada (#1611)

**Não use `restore_db.sh` contra um backup de produção.** Ele roda
`gzip -t "$BACKUP_FILE"` incondicionalmente (`restore_db.sh:91`) **antes** do branch que
decifra `.age` (`restore_db.sh:113-119`). Produção grava **exclusivamente**
`backup_full_*.sql.gz.age` (`backup_db.sh:44-55` fail-closed +
`docker-compose.prod.yml:197`), e um artefato `age` começa com o texto
`age-encryption.org/v1` — que não é gzip. O script aborta com

```
ERROR: Backup file is corrupted!
```

**A mensagem é falsa** e atinge os três caminhos de entrada (arquivo explícito, `--latest`,
interativo). Nada é destruído: a parada é na linha 91, antes do `DROP DATABASE` da linha
107. Issue [#1611](https://github.com/matheusnorjosa/aprender_sistema/issues/1611).

**O que funciona hoje** (precisa da chave privada `age`, que **não** fica na VM — está no
gerenciador de senhas do mantenedor):

```bash
age -d -i /etc/backup-key.txt <arquivo>.sql.gz.age | gzip -t   # verificar ANTES
age -d -i /etc/backup-key.txt <arquivo>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1
```

O binário `age` existe na imagem de backend **de produção**
(`v2/infra/Dockerfile.prod:56`) e **não** existe na imagem dev
(`v2/infra/Dockerfile.dev:19-21`). Procedimento passo a passo:
[GUIDE_DR.md → Restore Completo](./GUIDE_DR.md#restore-completo-desastre-total).

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

# 3. Verificar integridade ANTES de destruir (precisa da chave privada age)
age -d -i /etc/backup-key.txt \
  /var/backups/aprender/backup_full_<DATA>.sql.gz.age | gzip -t && echo "OK"

# 4. Restaurar — pipeline manual (restore_db.sh está quebrado, ver seção 0 / #1611)
age -d -i /etc/backup-key.txt \
  /var/backups/aprender/backup_full_<DATA>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1

# 5. Conferir explicitamente o resultado (não confie em exit 0 — ver #1645)
psql -h "$DB_HOST" -U postgres -d aprender_db -c "SELECT count(*) FROM core_usuario;"
psql -h "$DB_HOST" -U postgres -d aprender_db -c "SELECT count(*) FROM core_solicitacao;"

# 6. Reiniciar a stack (o one-shot `migrate` aplica migrations antes de web/worker/beat)
docker compose -f docker-compose.prod.yml up -d

# 7. Validar de dentro da VM01
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

# 5. Restaurar (pipeline manual — ver seção 0)
age -d -i /etc/backup-key.txt backup_full_<DATA>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d aprender_db -v ON_ERROR_STOP=1

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
- **`restore_db.sh`** — ⛔ **quebrado para backups de produção** (ver seção 0 / #1611).
  Além disso, `restore_db.sh:17` hardcoda `BACKUP_DIR=/var/backups/aprender` e ignora a
  env var, então `--latest` não funciona de dentro do container (onde o diretório é
  `/backups`). Use o pipeline manual até a correção.
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
  chama `restore_db.sh`. O bug #1611 passaria despercebido por ele indefinidamente.
  Issue [#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646).
- ❌ Depende de um serviço `db` no compose (`docker compose exec -T db …`), que só existe
  em **dev/staging**. Em produção o PostgreSQL é externo.
- ❌ Não existe nenhum teste `.bats` para `restore_db.sh` (os únicos bats do repositório
  cobrem `v2/infra/deployer/`).

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

---

## 8. Referências

- [PostgreSQL Backup Guide](https://www.postgresql.org/docs/current/backup.html)
- [SCALING.md](./SCALING.md)
- [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md)
