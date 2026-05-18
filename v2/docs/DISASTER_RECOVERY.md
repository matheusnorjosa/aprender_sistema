# Disaster Recovery Runbook

**Data**: 2026-05-17 (alinhamento SSOT)
**Status**: Ativo
**Referência**: PLAN_maturity_gaps.md (Gap 9)
**Ambiente**: Docker Compose (dev/staging). Para procedimentos em VM de produção, ver [GUIDE_DR.md](./GUIDE_DR.md).

> **Parâmetros de backup (RPO/RTO/retenção/frequência)** são definidos no SSOT
> [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md#parâmetros-canônicos-rpo--rto--retenção--frequência).
> Este documento foca em **cenários de recovery** (procedimentos operacionais).

---

## 1. Visão Geral

Este documento define os procedimentos de recuperação de desastres para o AS v2
em ambientes Docker Compose. Para a configuração do pipeline de backup (script,
agendamento, criptografia opcional, S3), consulte o SSOT
[`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md).

### 1.1 RTO/RPO (resumo — fonte: SSOT)

| Métrica | Valor |
|---------|-------|
| **RPO** | 5 minutos (WAL archiving) |
| **RTO** | 1 hora (restore + migrations + smoke) |

### 1.2 Backups (resumo — fonte: SSOT)

| Tipo | Frequência | Retenção | Storage |
|------|------------|----------|---------|
| Full dump | Diário (2:00 AM Docker / 3:00 AM VM) | 7 dias (configurável `BACKUP_RETENTION_DAYS`) | volume `backup_data` + S3 opcional |
| WAL archiving | Contínuo (`archive_timeout=300`) | 7 dias | `/var/lib/postgresql/wal_archive/` + S3 opcional |
| Redis snapshot | Não persistido | - | Memory only |

---

## 2. Cenários de Recuperação

### 2.1 Cenário 1: Database Corruption

**Sintomas**:
- Erros de leitura/escrita no PostgreSQL
- Inconsistências nos dados
- `pg_catalog` corrompido

**Procedimento**:

```bash
# 1. Parar a aplicação
docker compose down

# 2. Identificar último backup válido
ls -la /backups/

# 3. Restaurar do backup
./scripts/restore_db.sh /backups/latest.sql.gz

# 4. Se disponível, replay WAL para point-in-time recovery
# (Configurar archive_command no postgresql.conf)

# 5. Reiniciar aplicação
docker compose up -d

# 6. Validar integridade
curl http://localhost:8000/healthz/detailed/
```

### 2.2 Cenário 2: Perda Total do Servidor

**Sintomas**:
- Servidor inacessível
- Disco corrompido ou perdido
- VM destruída

**Procedimento**:

```bash
# 1. Provisionar novo servidor
# (Via terraform/ansible ou manualmente)

# 2. Clonar repositório e configurar ambiente
git clone https://github.com/org/aprender_sistema.git
cd aprender_sistema/v2

# 3. Baixar backup do S3
aws s3 cp s3://backups/as-v2/latest.sql.gz ./backups/

# 4. Subir containers
docker compose up -d db redis

# 5. Restaurar banco
./scripts/restore_db.sh ./backups/latest.sql.gz

# 6. Subir aplicação
docker compose up -d web celery

# 7. Validar
curl http://localhost:8000/healthz/detailed/
```

### 2.3 Cenário 3: Credenciais Comprometidas

**Sintomas**:
- Acesso não autorizado detectado
- Alertas de segurança
- Comportamento anômalo nos logs

**Procedimento**:

```bash
# 1. Revogar todas as sessões
docker compose exec web python manage.py clearsessions

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
curl http://localhost:8000/healthz/detailed/
# Esperado: "gcal_circuit": "open"

# 2. Verificar status do Google
# https://www.google.com/appsstatus/dashboard/

# 3. Se Google estiver OK, resetar circuit breaker
docker compose exec web python -c "
from apps.core.services.gcal.circuit_breaker import reset_circuit
reset_circuit()
"

# 4. Verificar fila de retry
docker compose exec celery celery -A config inspect active

# 5. Monitorar logs
docker compose logs -f web | grep gcal
```

---

## 3. Scripts de Backup/Restore

Scripts canônicos em `v2/infra/scripts/`:

- **`backup_db.sh`** — script unificado Docker+VM. Configurável via env vars
  (`DB_HOST/DB_PORT/DB_USER/DB_NAME/PGPASSWORD`, `BACKUP_DIR`,
  `BACKUP_RETENTION_DAYS`, `S3_BUCKET`, `BACKUP_AGE_RECIPIENT`). Nomenclatura
  `backup_full_YYYYMMDD_HHMMSS.sql.gz[.age]`. Retenção via
  `find -mtime +$BACKUP_RETENTION_DAYS -delete`. **Não duplicar lógica neste doc.**
- **`restore_db.sh`** — interativo (exige confirmação). Em modo não-interativo,
  invocar via `docker compose exec -T web /app/infra/scripts/restore_db.sh <file>`.

Para detalhes completos (variáveis, S3 setup, criptografia age opcional —
SEC-017), consultar [`BACKUP_OPERATIONS.md`](./BACKUP_OPERATIONS.md). Os exemplos
operacionais nas seções 2.1-2.4 acima referenciam esses scripts.

---

## 4. Testes de DR

### 4.1 Teste Mensal

Execute o script `test_dr.sh` mensalmente para validar backups:

```bash
./scripts/test_dr.sh
```

Este script:
1. Cria backup de teste
2. Restaura em database separado
3. Valida integridade (contagem de tabelas/registros)
4. Limpa database de teste

### 4.2 Checklist de Validação

- [ ] Backup foi criado com sucesso
- [ ] Backup tem tamanho razoável (> 1MB)
- [ ] Restore funciona sem erros
- [ ] Tabelas principais existem após restore
- [ ] Contagem de registros é consistente
- [ ] Aplicação inicia após restore
- [ ] Health check passa

---

## 5. Monitoramento

### 5.1 Alertas Recomendados

| Alerta | Condição | Severidade |
|--------|----------|------------|
| BackupFailed | Backup job falhou | Critical |
| BackupStale | Último backup > 24h | Warning |
| DiskSpaceLow | Disco backup < 20% | Warning |
| WALArchiveBehind | WAL archive atrasado > 1h | Warning |

### 5.2 Métricas

```promql
# Tamanho do último backup
as_backup_size_bytes{job="backup"}

# Idade do último backup
time() - as_backup_last_success_timestamp{job="backup"}

# Status do circuit breaker GCal
as_gcal_circuit_breaker_state{state="open"}
```

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

---

## 8. Referências

- [PostgreSQL Backup Guide](https://www.postgresql.org/docs/current/backup.html)
- [SCALING.md](./SCALING.md)
- [SLO_DEFINITIONS.md](./SLO_DEFINITIONS.md)
