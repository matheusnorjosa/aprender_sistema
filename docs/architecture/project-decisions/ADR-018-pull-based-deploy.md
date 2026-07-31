# ADR-018: Deploy Pull-Based com Ponteiro de Release Assinado

**Status:** Accepted
**Date:** 2026-07-10
**Decider:** Matheus Norjosa
**Supersedes:** [ADR-010](ADR-010-deploy-portainer-direct-to-prod.md)

> **Nota de registro.** A decisão foi tomada e implementada entre 2026-07-09 e 2026-07-10
> (issues #1513, #1514, #1515, #1516, #1524, #1530), mas o ADR só foi **escrito em
> 2026-07-24**. Até então o modelo era referenciado como "ADR-018" por 13 artefatos vivos
> (workflows, specs, runbooks, compose) sem que o documento existisse, enquanto o ADR-010
> permanecia `Accepted` ensinando o fluxo oposto. Este arquivo fecha essa lacuna; ele
> **descreve** o que já está em produção, não propõe algo novo.

## Context

O [ADR-010](ADR-010-deploy-portainer-direct-to-prod.md) estabeleceu que **merge na `main`
dispara deploy automático em produção**: o job `deploy` do `deploy.yaml` fazia um `PUT` na
API do Portainer da VM01, exposta na internet em `:9443`. Três problemas tornaram esse
modelo insustentável:

1. **A porta `:9443` precisava ser pública.** O runner do GitHub Actions tem faixa de IP
   ampla e mutável, então não havia allowlist estreita possível. O token do Portainer é
   *root-equivalente* — um `PUT` com um compose arbitrário cria um container arbitrário, o
   que é takeover da VM01. O repositório é público (ADR-009), o que amplia a superfície.
2. **Deploy não era um ato deliberado.** Todo merge ia para produção. A única rede de
   proteção era o staging gate **local** do autor, porque não existe ambiente de staging
   remoto. Não havia ponto no fluxo em que um humano dissesse "agora, esta versão, em
   produção".
3. **Não havia prova criptográfica do que subia.** O deploy aplicava uma *tag*, que é um
   ponteiro mutável no Docker Hub. A "verdade" do que rodava em produção era a cor de um
   job de CI, não um digest verificado.

O modelo *push* também sofria de "false-red": timeouts do `:9443` marcavam o job como
falho depois de o deploy já ter sido aplicado (#1396/#1394).

## Decision

Inverter o sentido do deploy: **produção puxa, o CI não empurra**. Merge na `main` **não
deploya**.

**1. O CI só constrói, assina e libera.** O `deploy.yaml` (renomeado para *"Build, sign and
release"*) faz build → scan → push no Docker Hub → assina as imagens (cosign keyless +
provenance SLSA, `slsa-provenance.yml`, #1524) → cria a tag imutável `vYYYY.MM.DD-<sha7>` e
o GitHub Release. Os jobs `deploy` e `validate_existing_tag` foram **deletados** (#1516).

**2. Promoção é um ato humano gated.** O `promote.yml` (`workflow_dispatch`, atrás do
GitHub Environment `production` com *required reviewer*) resolve tag→digest, **exige** que
as imagens já estejam assinadas, monta o `production.json` (release, digests, `sequence`
monotônica, `expires_at`), assina o blob com `cosign sign-blob` (identidade OIDC do próprio
workflow) e publica no branch protegido **`deploy-pointer`**. O `promote.yml` **não**
deploya — ele é a *autoridade de assinatura* do ponteiro.

**3. A VM01 aplica sozinha, por digest.** O agente `aprender-deployer` (systemd timer,
~60s) lê o ponteiro *tokenless* por `raw.githubusercontent.com`, verifica a assinatura
contra um trusted-root **pinado offline** e verifica cada imagem **por digest**
(`cosign verify` + attestation). Entrega o handoff ao `aprender-applier`, que re-verifica
tudo a partir dos bytes, confere anti-rollback (selo monotônico), confere drift do compose
contra a cópia **pinada** que ele mesmo detém, exige **backup de DB fresco**, faz o `PUT` em
**`127.0.0.1:9443`**, confirma em `localhost` (`/api/readyz/` + `/api/version/`) e só então
sela a nova `sequence`. Cada degrau é **fail-closed**.

**4. Separação de privilégio entre dois usuários de sistema.** Só o `aprender-applier`
detém o token do Portainer (`curlrc` 0400); o `aprender-deployer`, que faz o parsing de
dados vindos da internet, **não** o detém. Comprometer o parser vira, no máximo, DoS.

**5. Migrations são automáticas e bloqueantes.** O serviço one-shot `migrate` do
`docker-compose.prod.yml` roda `python manage.py migrate --noinput`; `web`, `worker` e
`beat` só sobem após ele terminar com êxito (`depends_on: service_completed_successfully`).
Uma migration quebrada **bloqueia** o deploy em vez de servir um schema meio-migrado
(#1456).

**6. A `:9443` deixa de ser pública.** O único consumidor legítimo passa a ser local.

## Consequences

- **Merge na `main` não é mais deploy.** Ele produz um artefato assinado e liberável. Levar
  a produção exige `promote.yml` + aprovação no Environment `production`.
- **Rollback é uma promoção para trás**, pelo mesmo gate: promover a tag imutável anterior
  com `rollback: true` (ainda exige `sequence` maior que o selo). **Não há auto-rollback** —
  migrations são forward-only.
- **A verdade do que roda em produção é o digest verificado no `PUT`**, não a cor de um job.
  Conferir por `/api/version/`.
- **Migrations manuais em produção deixaram de ser necessárias.** A instrução do ADR-010
  ("rodar `python manage.py migrate` manualmente no container prod") está **revogada**.
- **Continua não havendo staging remoto.** A validação pré-merge segue sendo o staging gate
  local (`v2/infra/scripts/staging-gate.sh`) mais os gates `[required]` de CI. O ADR-018 não
  resolve isso.
- **Risco residual nº 1 aceito: a corrente humana é *single-account*.** O autor do PR, o
  aprovador do Environment e o dono da VM são a mesma pessoa. A defesa técnica (assinatura,
  digest, anti-rollback, compose pinado) permanece, mas **uma conta comprometida ⇒ deploy
  verificado arbitrário**. Registrado em `v2/infra/deployer/README.md`.
- **Dead-man switch é dívida aberta.** O deployer emite heartbeat a cada tick, mas quem
  observa a *ausência* do heartbeat é decisão em aberto (decisão #9 do blueprint #1513).
- **Novo custo operacional:** o agente na VM01 é software que precisa ser instalado,
  atualizado e monitorado (`bootstrap/install.sh`, hashes de binário pinados). Falha do
  agente = produção congela na versão atual (fail-closed, não fail-open).

## References

- Issues: **#1513** (Fase 1, agente + blueprint), **#1514** (Fase 2, `promote.yml`),
  **#1515** (cutover), **#1516** (Fase 4, remoção do job `deploy` e fechamento do `:9443`),
  **#1524** (assinatura cosign + SLSA), **#1530** (staging gate deixa de implicar deploy),
  **#1455** (mount `/backups` como gate de backup fresco), **#1456** (serviço `migrate`).
- SSOT do mecanismo: `v2/docs/specs/infra/deploy.spec.md`
- CI: `v2/docs/specs/infra/ci.spec.md`
- Agente: `v2/infra/deployer/README.md`

> Os caminhos acima estão como código, não como link: `v2/docs/` fica **fora** do `docs_dir`
> do site MkDocs, então um link relativo daqui quebraria na publicação.
- Workflows: `.github/workflows/deploy.yaml`, `.github/workflows/promote.yml`,
  `.github/workflows/slsa-provenance.yml`, `.github/workflows/deployer-bats.yml`
- Compose: `v2/infra/docker-compose.prod.yml`
- Supersede: [ADR-010](ADR-010-deploy-portainer-direct-to-prod.md)
</content>
</invoke>
