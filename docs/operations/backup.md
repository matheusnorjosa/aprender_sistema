# Backup

Operações de backup do AS v2.

> **SSOT**: parâmetros canônicos (RPO/RTO/retenção/frequência), procedimentos operacionais, estratégia 3-2-1, backup de uploads/media e de secrets ficam em **[BACKUP_OPERATIONS.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/BACKUP_OPERATIONS.md)** (fora do MkDocs deste site). Contrato e invariantes em **[backup-dr.spec.md](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/backend/backup-dr.spec.md)**.
>
> Recovery: `DISASTER_RECOVERY.md` (Docker) / `GUIDE_DR.md` (VM).

## Estado real — leia antes de contar com o DR

> [!important] Este bloco listava defeitos que já foram fechados. Situação em 2026-08-25:
>
> | Defeito | Estado |
> |---|---|
> | #1611 / M26-01 — `restore_db.sh` rejeitava todo backup `.age` de produção com `ERROR: Backup file is corrupted!` | **Corrigido** — `8f392636`, 2026-08-10 |
> | #1645 / M26-02 — `restore_db.sh` declarava sucesso com exit 0 sobre banco vazio | **Corrigido** — `3bca74f3`, 2026-08-21 |
> | #1455 — `worker` de produção não montava `/backups`, então o job gravava no vazio | **Corrigido** — #1528; bind-mount `/var/backups/aprender:/backups` em `docker-compose.prod.yml:235` |
> | [#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646) / M26-03 — nenhum drill real de DR com artefato `.age` | **ABERTO** |

**O restore oficial funciona.** `restore_db.sh` é ciente do formato: decifra o `.age`
com `age -d` e só então testa o gzip (`:101-121`), respeita `BACKUP_DIR` via env var
(`:23`), tira safety dump antes do `DROP DATABASE` (`:132-148`), usa
`psql -v ON_ERROR_STOP=1` sob `pipefail` (`:162-178`) e verifica o resultado — piso de
tabelas e linhas > 0 nas tabelas-chave — antes de declarar sucesso (`:180-212`).

!!! danger "Em produção, `DB_HOST` por TCP não autentica — `M26-N1`, P1, aberto"
    `restore_db.sh` conecta sempre como superusuário `postgres` via `-h $DB_HOST` e
    **não tem tratamento de senha nenhum**:
    `grep -i PGPASSWORD v2/infra/scripts/restore_db.sh` retorna zero — para contraste,
    `backup_db.sh` exporta `PGPASSWORD`.

    A VM02 escuta em `10.0.0.2`, não em loopback
    (`v2/infra/configs/vm02/postgresql.conf:8`), e o `pg_hba.conf:18` termina com
    `host all all 0.0.0.0/0 reject`. A única regra que aceita `postgres` é
    `local … peer` (`:8`) — socket unix.

    **Na VM02, use o pipeline manual com peer auth** (`sudo -u postgres`), documentado
    em `v2/docs/GUIDE_DR.md`. O comando abaixo serve para **dev/staging**.

    `M26-N1` (P1, confirmado) —
    `v2/docs/audits/2026-07-17-system-module-audit.md:9438`.

```bash
BACKUP_DIR=/backups BACKUP_AGE_KEY=/etc/backup-key.txt \
  DB_HOST="$DB_HOST" DB_NAME="$DB_NAME" \
  /app/infra/scripts/restore_db.sh --latest
```

Rode onde o binário `age` exista: ele está na imagem de **produção**
(`Dockerfile.prod:56`), não na de dev (`Dockerfile.dev:19-21`).

**O que continua em aberto.** Não existe registro de restore drill bem-sucedido com
artefato `.age` — `test_dr.sh` não gera `.age` nem chama `age -d`, então não exercita o
caminho cifrado (issue
[#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646)). O código é
verificável linha a linha; **saber restaurar em produção ainda depende de executar o
drill.**
