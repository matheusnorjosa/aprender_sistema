# Backup

Estratégias de backup para o Aprender Sistema v2.

> **SSOT**: parâmetros canônicos (RPO/RTO/retenção/frequência) e procedimentos
> operacionais ficam em `v2/docs/BACKUP_OPERATIONS.md` (fora do escopo do
> MkDocs deste site). Este doc é um overview público; para detalhes de operação,
> sempre consulte o SSOT no repositório. Para procedimentos de recovery, ver
> `v2/docs/DISASTER_RECOVERY.md` (Docker) ou `v2/docs/GUIDE_DR.md` (VM).

## Componentes para Backup

| Componente | Frequência | Retenção |
|------------|------------|----------|
| PostgreSQL | Diário (ver SSOT) | 7 dias (configurável) |
| Redis | Não necessário | - |
| Uploads | Diário | 90 dias |
| Configurações | Por deploy | Indefinido |

## PostgreSQL

### Backup Manual

```bash
# Via Docker
docker compose exec db pg_dump -U aprender aprender_db > backup_$(date +%Y%m%d).sql

# Comprimido
docker compose exec db pg_dump -U aprender aprender_db | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Manual

```bash
# Restaurar
docker compose exec -T db psql -U aprender aprender_db < backup_20250115.sql

# Restaurar comprimido
gunzip -c backup_20250115.sql.gz | docker compose exec -T db psql -U aprender aprender_db
```

### Backup Automatizado

O AS v2 usa o script `v2/infra/scripts/backup_db.sh` orquestrado por Celery Beat
(Docker, 2:00 AM) ou cron (VM, 3:00 AM). Para configuração completa de env vars,
volume `backup_data`, S3 opcional e criptografia age opcional (SEC-017),
consultar a seção `Configuration` no SSOT `v2/docs/BACKUP_OPERATIONS.md`.

## Uploads

### Backup de Arquivos

```bash
# Copiar arquivos de mídia
tar -czvf uploads_$(date +%Y%m%d).tar.gz v2/backend/media/
```

### Sync com S3

```bash
# AWS CLI
aws s3 sync v2/backend/media/ s3://aprender-backups/media/
```

## Configurações

### .env

```bash
# Copiar arquivo de configuração (sem senhas reais)
cp .env .env.backup.$(date +%Y%m%d)
```

### Secrets

Armazenar secrets de forma segura:

- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

## Estratégia 3-2-1

- **3** cópias dos dados
- **2** tipos de mídia diferentes
- **1** cópia offsite

### Implementação

1. **Local**: Volume Docker (rápido restore)
2. **Cloud**: S3/GCS (redundância geográfica)
3. **Offsite**: Backup semanal em storage separado

## Verificação de Backups

### Teste de Restore

```bash
# Criar banco temporário
docker compose exec db createdb -U aprender test_restore

# Restaurar backup
docker compose exec -T db psql -U aprender test_restore < backup_latest.sql

# Verificar dados
docker compose exec db psql -U aprender test_restore -c "SELECT COUNT(*) FROM core_solicitacao;"

# Limpar
docker compose exec db dropdb -U aprender test_restore
```

## Monitoramento

```bash
# Verificar tamanho dos backups
du -sh backups/*

# Listar backups por data
ls -la backups/*.sql.gz | tail -10
```
