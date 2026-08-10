---
title: Criptografia de dados em repouso (at-rest) — CPF/PII
status: draft
last_verified: 2026-08-10
sources_of_truth:
  - v2/infra/docker-compose.prod.yml
  - v2/infra/scripts/backup_db.sh
  - v2/backend/apps/core/models/usuario.py
  - v2/backend/apps/core/models/integracao.py
  - v2/backend/config/settings.py
owner: infra
supersedes: []
related:
  - ./deploy.spec.md
  - ./environments.spec.md
  - ../../BACKUP_OPERATIONS.md
  - ../../DISASTER_RECOVERY.md
  - ../INDEX_SDD.md
---

# Criptografia de dados em repouso (at-rest) — CPF/PII

> **Decisão de arquitetura** (auditoria de risco jurídico, 2026-08-10). Define **como** o
> CPF e a PII operacional são protegidos **em repouso** e **por que** a cifra é feita no
> **disco/volume da VM02**, não campo-a-campo no aplicativo. A verificação/ativação na VM02
> é ação de infra (runbook abaixo) — por isso `status: draft` até a evidência ser registrada.

## Contexto / risco

`core_usuario.cpf` é **texto puro** no PostgreSQL: `CharField(max_length=11, unique=True)`, **NOT
NULL**, e é a **chave de login** (autenticação por CPF). Nome, e-mail e telefone idem
([`usuario.py`](../../../backend/apps/core/models/usuario.py)). O `DATCoordenador` mantém um
dossiê paralelo de PII. O risco é a exposição desse dado **em repouso** — um cenário de **roubo
de disco, snapshot ou dump não-autorizado** do volume do banco.

O que **já** protege (por isso o risco é "em repouso", não vazamento iminente):

| Camada | Estado | Onde |
|---|---|---|
| TLS em trânsito (app↔DB `sslmode=require`, HSTS, cookies seguros) | ✅ | [`settings.py`](../../../backend/config/settings.py) (SEC-016) |
| Backups cifrados com `age` (fail-closed, chave fora do repo) | ✅ | [`backup_db.sh`](../../../infra/scripts/backup_db.sh) |
| Tokens OAuth cifrados com Fernet | ✅ | [`integracao.py`](../../../backend/apps/core/models/integracao.py) |
| Controle de acesso (RBAC + admin superuser-only) | ✅ | `apps/core/rbac/` |
| **Cifra do volume do PostgreSQL (VM02)** | ⚠️ **não evidenciado** | infra/provedor |

A última linha é o furo: o PGDATA na **VM02** (Postgres externo — [`docker-compose.prod.yml`](../../../infra/docker-compose.prod.yml)
**não** tem serviço de DB; o app conecta na VM02) precisa de cifra em repouso.

## Decisão

**O controle de at-rest é a criptografia de disco/volume da VM02** (LUKS no host **ou** cifra de
volume gerenciada pelo provedor). É transparente para o app e para o PostgreSQL, protege **toda**
a PII (não só o CPF), e não exige mudança de código.

### Rejeitado: cifra de campo (Fernet) do CPF

Considerada e **descartada como over-engineering** para este *threat model*:

1. **Quebra o login-por-CPF.** A autenticação faz `WHERE cpf = X`; um valor cifrado não é
   buscável. Exigiria cifra **determinística** ou um **HMAC/hash paralelo** só para a busca, mais
   **migração de dados** e mudanças em `auth_backends`, serializers, importadores e na busca do
   admin — superfície grande e sensível (auth).
2. **Ganho marginal sobre a cifra de disco.** Um adversário com acesso ao processo Django tem a
   chave Fernet de qualquer forma; a cifra de campo só ajuda contra **dump de disco frio** — que a
   **cifra de disco já cobre**, para toda a PII e sem código.
3. **Custo de gestão + rotação de chave** para esse ganho marginal.

> **Por que os tokens OAuth *são* cifrados com Fernet e o CPF não deve ser:** o token é **segredo de
> altíssimo valor e NÃO é chave de busca** — cifra de campo é adequada. O CPF é **identificador de
> busca** (login) — categoria diferente; para ele o controle certo é a cifra de disco.

## Runbook — verificar / ativar (VM02)

1. **Verificar** se o volume do PGDATA já é cifrado:
   - LUKS: `lsblk -o NAME,FSTYPE,MOUNTPOINT` e `cryptsetup status <device>` (esperar `crypto_LUKS`
     no device que monta o PGDATA).
   - Provedor (cloud): confirmar "**encryption at rest**" habilitado no disco/volume no console.
2. **Se não cifrado**, planejar a migração: cifrar exige recriar o volume ou migrar o PGDATA para um
   volume cifrado — **janela de manutenção** + restore a partir do backup `age`
   ([`restore_db.sh`](../../../infra/scripts/restore_db.sh); ver [`DISASTER_RECOVERY.md`](../../DISASTER_RECOVERY.md)).
3. **Confirmar** que os **snapshots do volume** (se o provedor os faz) também são cifrados.
4. **Registrar** a evidência e atualizar o `last_verified` + `status` desta spec.

## Critério de aceite

- Volume do PGDATA na VM02 **cifrado em repouso** (LUKS ou gerenciado pelo provedor), com evidência.
- Snapshots do volume cifrados.
- Esta spec atualizada (`status: canonical`, `last_verified` com a data da verificação, evidência).

## Estado atual

⚠️ **Pendente de verificação de infra.** A cifra de disco da VM02 é configuração de infra/provedor,
**fora do código** — não é observável neste repositório. Achado da auditoria de risco jurídico
(2026-08-10): *"o at-rest do CPF/PII depende da cifra de disco da VM02, não evidenciada no repo"*.
**Ação do dono/infra:** rodar o runbook acima e registrar a evidência aqui. Enquanto isso, os
controles compensatórios da tabela de contexto (TLS, backups `age`, RBAC) permanecem ativos.
