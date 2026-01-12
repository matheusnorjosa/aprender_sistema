# Backup e Recovery - Aprender Sistema v2

## Visão Geral

| Métrica | Valor |
|---------|-------|
| **RPO** (Recovery Point Objective) | ~5 minutos |
| **RTO** (Recovery Time Objective) | ~30 minutos |
| **Retenção** | 7 dias |
| **Frequência** | Diário às 3h |

## Arquitetura de Backup

```
┌─────────────────────────────────────────────────────────────┐
│                      VM02_Banco                             │
│                                                             │
│  ┌─────────────┐    ┌──────────────────┐                   │
│  │ PostgreSQL  │───▶│ WAL Archiving    │                   │
│  │             │    │ (a cada 5 min)   │                   │
│  └─────────────┘    └────────┬─────────┘                   │
│         │                    │                              │
│         │                    ▼                              │
│         │           /var/lib/postgresql/wal_archive/        │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────┐                                           │
│  │ pg_dump     │    (diário às 3h)                         │
│  │ + gzip      │                                           │
│  └──────┬──────┘                                           │
│         │                                                   │
│         ▼                                                   │
│  /var/backups/aprender/                                    │
│  └── aprender_db_YYYYMMDD_HHMMSS.sql.gz                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Componentes

### 1. WAL Archiving (Point-in-Time Recovery)

**Configuração** (`postgresql.conf`):
```ini
archive_mode = on
archive_command = 'gzip < %p > /var/lib/postgresql/wal_archive/%f.gz'
archive_timeout = 300  # 5 minutos
```

**Benefício**: Permite recovery até qualquer ponto no tempo nos últimos 7 dias.

### 2. Backup Diário (pg_dump)

**Script**: `/opt/scripts/backup_db.sh`

**Cron** (`/etc/cron.d/aprender-backup`):
```cron
# Backup diário às 3h
0 3 * * * postgres /opt/scripts/backup_db.sh

# Limpeza de backups antigos (7 dias)
0 4 * * * postgres find /var/backups/aprender -name "*.sql.gz" -mtime +7 -delete

# Limpeza de WAL archives (7 dias)
30 4 * * * postgres find /var/lib/postgresql/wal_archive -name "*.gz" -mtime +7 -delete

# Verificação semanal (domingo 5h)
0 5 * * 0 postgres /opt/scripts/verify_backup.sh
```

### 3. Verificação de Integridade

**Script**: `/opt/scripts/verify_backup.sh`

Executa semanalmente e verifica:
- Integridade do arquivo gzip
- Estrutura SQL válida
- Contagem de tabelas
- Idade do backup

---

## Procedimentos

### Restore Completo (Desastre Total)

**Tempo estimado**: 20-30 minutos

```bash
# 1. Parar aplicação
sudo systemctl stop aprender-gunicorn aprender-celery

# 2. Executar restore
sudo -u postgres /opt/scripts/restore_db.sh --latest

# 3. Verificar dados
sudo -u postgres psql -d aprender_db -c "SELECT count(*) FROM core_solicitacao;"

# 4. Rodar migrations (se necessário)
cd /var/www/aprender/backend
source ../venv/bin/activate
python manage.py migrate

# 5. Reiniciar aplicação
sudo systemctl start aprender-gunicorn aprender-celery

# 6. Verificar health
curl -f http://localhost/healthz/
```

### Restore Point-in-Time (PITR)

Para recuperar até um momento específico (ex: antes de um DELETE acidental):

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
# Listar backups disponíveis
ls -lh /var/backups/aprender/

# Testar integridade
gzip -t /var/backups/aprender/aprender_db_*.sql.gz

# Verificar conteúdo
zcat /var/backups/aprender/aprender_db_*.sql.gz | head -100

# Executar verificação completa
/opt/scripts/verify_backup.sh
```

---

## Monitoramento

### Logs

```bash
# Log de backup
tail -f /var/log/aprender/backup.log

# Log do PostgreSQL
tail -f /var/log/postgresql/postgresql-15-main.log
```

### Alertas Recomendados

| Condição | Severidade | Ação |
|----------|------------|------|
| Backup não executado em 24h | Critical | Verificar cron e disco |
| Verificação semanal falhou | High | Investigar integridade |
| Disco > 80% | Warning | Limpar backups antigos |
| WAL archive > 10GB | Warning | Verificar replicação |

---

## Checklist de Setup

### VM02_Banco

- [ ] Criar diretório de backups: `mkdir -p /var/backups/aprender`
- [ ] Criar diretório WAL: `mkdir -p /var/lib/postgresql/wal_archive`
- [ ] Copiar scripts: `cp v2/infra/scripts/*.sh /opt/scripts/`
- [ ] Dar permissão: `chmod +x /opt/scripts/*.sh`
- [ ] Copiar cron: `cp v2/infra/cron/aprender-backup /etc/cron.d/`
- [ ] Verificar WAL archiving: `SELECT * FROM pg_stat_archiver;`
- [ ] Executar backup manual: `/opt/scripts/backup_db.sh`
- [ ] Verificar backup: `/opt/scripts/verify_backup.sh`

---

## Troubleshooting

### Backup falhou

```bash
# Verificar espaço em disco
df -h /var/backups

# Verificar logs
tail -50 /var/log/aprender/backup.log

# Executar manualmente para ver erros
/opt/scripts/backup_db.sh
```

### WAL archiving parado

```bash
# Verificar status
sudo -u postgres psql -c "SELECT * FROM pg_stat_archiver;"

# Verificar diretório
ls -la /var/lib/postgresql/wal_archive/

# Testar archive_command manualmente
sudo -u postgres pg_switch_wal  # Força novo WAL segment
```

### Restore falhou

```bash
# Verificar conexões ativas
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname = 'aprender_db';"

# Forçar desconexão
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'aprender_db';"
```
