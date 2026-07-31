# Backup

Operações de backup do AS v2.

> **SSOT**: parâmetros canônicos (RPO/RTO/retenção/frequência), procedimentos operacionais, estratégia 3-2-1, backup de uploads/media e de secrets ficam em **[BACKUP_OPERATIONS.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/BACKUP_OPERATIONS.md)** (fora do MkDocs deste site). Contrato e invariantes em **[backup-dr.spec.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/backend/backup-dr.spec.md)**.
>
> Recovery: `DISASTER_RECOVERY.md` (Docker) / `GUIDE_DR.md` (VM).

## Estado real — leia antes de contar com o DR

Dois defeitos abertos, ambos confirmados por execução contra `main`:

**1. O restore oficial rejeita todo backup de produção (P0, issue #1611).**
`v2/infra/scripts/restore_db.sh:91` roda `gzip -t "$BACKUP_FILE"` **incondicionalmente**,
antes do branch que sabe decifrar `age` (linhas 113-119). Produção grava
**exclusivamente** `.age`: `backup_db.sh:44-52` é fail-closed (sem
`BACKUP_AGE_RECIPIENT` o backup aborta; com recipient o nome vira `.sql.gz.age`) e
`docker-compose.prod.yml:197` define o recipient. Um artefato `age` começa com o
cabeçalho de texto `age-encryption.org/v1`, que não é gzip — então o script aborta com

```
ERROR: Backup file is corrupted!
```

que é **factualmente falso**. Atinge os três caminhos de entrada (arquivo explícito,
`--latest`, modo interativo). A falha é *fail-closed*: para na linha 91, antes do
`DROP DATABASE` da linha 107, então não há destruição de dados — o dano é RTO
estourado sob incidente.

**Contorno manual enquanto #1611 não é corrigida** (rodar onde o binário `age` exista;
a imagem `web` não o tem):

```bash
age -d -i /etc/backup-key.txt backup_full_<ts>.sql.gz.age | gunzip \
  | psql -h "$DB_HOST" -U postgres -d "$DB_NAME"
```

Atenção adicional: `restore_db.sh:17` hardcoda `BACKUP_DIR=/var/backups/aprender` e
ignora a env var (`backup_db.sh:31` respeita), então `--latest` dentro do container não
acha nada.

**2. O job automatizado está silencioso/morto em produção (issue #1455).** `worker` e
`beat` de prod não montam `/backups`; sem `SENTRY_DSN`, a falha não alerta ninguém.

Consequência: a estratégia documentada nos SSOTs é o **alvo recomendado**, não o estado
operante. Não existe registro de restore drill bem-sucedido com artefato `.age`
(`test_dr.sh` não exercita o caminho cifrado — issue #1646). **Se existe backup
restaurável hoje em produção é uma pergunta em aberto que só um drill real responde.**
