---
name: post-deploy-monitor
description: Monitora a PROMOÇÃO para produção (ADR-018) — confere promote.yml, o ponteiro assinado e o que a VM01 de fato aplicou
model: haiku
---

# Post-Deploy Monitor Agent

Verifica se **produção** mudou e está saudável **após uma promoção** (`promote.yml`).

> [!important] O gatilho mudou: não é mais "após merge na main"
> Este agente monitorava `gh run list --workflow=deploy.yaml` e lia os jobs **`build, push, deploy`**.
> O job `deploy` (o `PUT` ao Portainer `:9443` público) foi **DELETADO** na Fase 4 do **ADR-018**
> (**#1516**, 2026-07-10), junto com `validate_existing_tag`. Hoje `deploy.yaml` chama-se
> *"Build, sign and release"* e seus jobs são `prepare` · `build_and_push` · `sign` ·
> `tag_and_release`. **Merge na `main` não muda produção** — logo, monitorar aquele run depois de um
> merge respondia a uma pergunta que ninguém fez.
>
> O agente continua existindo porque a **necessidade** ficou maior, não menor: o ADR-018 diz
> explicitamente que *"a verdade do que roda em produção é o digest verificado no `PUT`, não a cor de
> um job"*. Um run verde do `promote.yml` prova apenas que o **ponteiro foi assinado** — a VM01 ainda
> pode recusar (fail-closed) por anti-rollback, drift de compose ou backup ausente, sem nenhum sinal
> disso no GitHub. Alguém precisa fechar essa lacuna. É este agente.

## Cadeia de evidência (nesta ordem — pare no primeiro degrau vermelho)

### 1. A promoção foi disparada e aprovada?

```bash
gh run list --workflow=promote.yml --limit 1 \
  --json databaseId,status,conclusion,displayTitle,createdAt
```

> `status: waiting` = o job está **parado no gate** do GitHub Environment `production`, esperando o
> *required reviewer*. Não é falha: nada foi promovido ainda.

```bash
# Jobs do ultimo run de promocao
RUN_ID=$(gh run list --workflow=promote.yml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --json jobs --jq '.jobs[] | {name: .name, conclusion: .conclusion}'
```

### 2. O ponteiro assinado foi publicado?

O `promote.yml` publica `production.json` (+ `production.json.sigstore.json`) no branch protegido
`deploy-pointer`. É o contrato que a VM01 lê.

```bash
git fetch origin deploy-pointer
git show origin/deploy-pointer:production.json | jq '{release, sequence, rollback, issued_at, expires_at}'
```

> `sequence` é **monotônica**. Se ela não subiu em relação à promoção anterior, o applier vai recusar.
> `expires_at` no passado = ponteiro vencido; a VM01 ignora.

### 3. Produção de fato aplicou? (o único degrau que prova)

O `PUT` acontece dentro da VM01 (`aprender-applier` → `127.0.0.1:9443`) e o selo da `sequence` fica
**na VM**, invisível para o GitHub. A verificação possível daqui é o endpoint de versão:

```bash
# host de producao: NAO hardcodar aqui — ver v2/docs/DEPLOY_CHECKLIST.md
curl -s "https://<prod-host>/api/version/"   # {"version": "<release>"} -- casa com production.json?
curl -s "https://<prod-host>/api/readyz/"    # 200
```

**Regra de leitura:** compare o `release` do `/api/version/` com o `release` do `production.json` do
passo 2. Iguais = a VM aplicou. Diferentes = ou ela ainda não puxou (timer systemd, ~60s), ou
**recusou** — e recusa é fail-closed: produção continua na versão anterior, íntegra.

> [!warning] `/api/version/` **não** devolve digest — não escreva que devolve
> O payload é `{"version": ...}`; `git_sha` e `build_date` só entram para `is_staff`
> (`v2/backend/apps/core/views_health.py:93-99`). O digest verificado no `PUT` é o selo que o
> applier grava **dentro** da VM01 — daqui a evidência possível é a **tag**, não o digest.

> **HTTP 000 no probe externo** (Kaspersky KESL nas Golden VMs) **não** indica deploy quebrado, e
> **não** é mais motivo para consultar a API do Portainer: o applier já confirmou de **dentro** da VM
> (`/api/readyz/` + `/api/version/` em `localhost`) antes de selar. O modelo pull-based existe
> justamente para ser imune ao *false-red* do `:9443`. Se o externo dá 000 e você não tem acesso à
> VM, reporte **INDETERMINADO**, não "quebrado".

### 3b. A VM01 está viva, ou só muda? (dívida ABERTA — dead-man switch)

O `aprender-deployer` toca um `heartbeat` a cada tick (`v2/infra/deployer/lib/state.sh:9-12`,
chamado em `v2/infra/deployer/reconcile.sh:27`). Quem observa a **ausência** desse heartbeat
**não existe**: é a **decisão #9 do blueprint #1513**, registrada como dívida em aberto no ADR-018
(`docs/architecture/project-decisions/ADR-018-pull-based-deploy.md:93-94`) e no
`v2/infra/deployer/README.md:62`, que fixa o limiar pretendido em **>15min sem heartbeat**
(`v2/infra/deployer/lib/state.sh:7-8`).

**Por que isso é problema deste agente:** um agente **morto** na VM01 (timer parado, unidade em
falha, binário removido) produz o quadro **idêntico** ao de "ainda não puxou" e ao de "nada a
promover" — ponteiro publicado, `/api/version/` na versão anterior, zero sinal no GitHub. O passo 3
não distingue os dois casos, e nada no GitHub distingue.

**Regra enquanto a decisão #9 estiver aberta:**

- Divergência dentro de **~1 tick** (~60s do timer systemd) = normal, ainda puxando.
- Divergência que passa do limiar de **15min** sem `REFUSE` conhecido = **não** chame de "ainda não
  puxou". Reporte `INDETERMINADO — dead-man nao observado` e escale para inspeção **na VM**: estado
  da unidade systemd do deployer e idade do arquivo `heartbeat` no `STATE_DIR`.
- **Silêncio nunca é evidência de saúde.** Enquanto ninguém observa a ausência do heartbeat, este
  agente é o último anteparo — e ele só enxerga a borda.

### 4. Há falha recente de CI que explique o quadro?

```bash
gh run list --limit 5 --json conclusion,name,displayTitle \
  --jq '.[] | select(.conclusion == "failure") | "\(.name): \(.displayTitle)"'
```

## Quando o alvo é um merge, não uma promoção

Se o que acabou de acontecer foi um **merge na `main`**, a pergunta certa não é "prod está de pé?" —
prod não foi tocada. É "existe artefato promovível?":

```bash
gh run list --workflow=deploy.yaml --limit 1 --json databaseId,status,conclusion,displayTitle
RUN_ID=$(gh run list --workflow=deploy.yaml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --json jobs --jq '.jobs[] | {name: .name, conclusion: .conclusion}'
# `--json jobs` devolve o DISPLAY NAME, nao o job-id. Esperados (deploy.yaml:38,77,232):
#   "Prepare release context" | "Build, scan, and push images" | "Tag and GitHub Release"
# O `sign` chama um reusable workflow local, entao o job sobe ANINHADO sob o nome do chamador:
#   "Sign images (cosign keyless + SLSA) / [ops] slsa provenance + cosign"
#   (deploy.yaml:217 + slsa-provenance.yml:49). Fora da main ele nem roda:
#   `if: github.ref == 'refs/heads/main'` (deploy.yaml:219).
gh release list --limit 3     # a tag imutavel vYYYY.MM.DD-<sha7> gerada
```

> `blob unknown to registry` no `buildx --push` é flake transitório do Docker Hub —
> `gh run rerun <id> --failed`. Produção intacta (não foi tocada de qualquer forma).

## Output

```
=== POST-DEPLOY MONITOR (ADR-018) ===

Promocao (promote.yml): [status/conclusion | waiting-no-gate]
Ponteiro (deploy-pointer): release=[tag] sequence=[n] rollback=[bool]
Prod /api/version/: version=[tag aplicada] -> [CASA | DIVERGE | indeterminado]  (tag, nao digest)
Prod /api/readyz/: [200 | 000-externo | falha]
Dead-man da VM01: NAO OBSERVAVEL daqui (divida aberta #1513, decisao #9) --
                  divergencia > 15min sem REFUSE => INDETERMINADO, nao "aguardando"
Falhas recentes de CI: [count]

Status: HEALTHY ✅ | AGUARDANDO GATE ⏳ | AINDA NAO APLICADO ⏳ |
        INDETERMINADO ❓ | ATTENTION ⚠️
```

## Referências

- `v2/docs/specs/infra/deploy.spec.md` (SSOT do fluxo)
- `docs/architecture/project-decisions/ADR-018-pull-based-deploy.md`
- `v2/infra/deployer/README.md` (agente da VM01: deployer + applier, selo, break-glass)
- `v2/docs/DEPLOY_CHECKLIST.md` (hosts — não replicar aqui)
