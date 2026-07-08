# `aprender-deployer` — agente de deploy pull-based (ADR-018 Fase 1)

Agente **on-box** (VM01) que substitui o deploy *push* (runner → Portainer `:9443`
exposto na internet) por *pull*: lê um **ponteiro de release assinado** do GitHub
(tokenless) e chama o Portainer em `127.0.0.1:9443`. Seguro em repo público porque
**só lê dados verificados, nunca executa código de PR**.

> **Escopo desta fase (Fase 1):** este diretório é **código + testes**. Nada roda
> no host ainda — a instalação/cutover (bootstrap contra canário, fechar o `:9443`)
> é Fase 3/4. Pré-requisito **não** presente ainda: `promote.yml` (assina o ponteiro,
> Fase 2). Ver issues #1513/#1514/#1516 e o blueprint em #1513.

## Modelo de confiança (fail-closed)

Cada elo verifica o anterior; **qualquer falha = recusa, nunca deploy**:

1. Gate humano (GitHub Environment `production` + reviewer) autoriza `promote.yml`.
2. `promote.yml` **assina** `production.json` (cosign) e o commita no branch protegido `deploy-pointer` (com `sequence` monotônico + `expires_at`).
3. O **deployer** lê tokenless, **verifica a assinatura do ponteiro** → **cosign verify + attestation de cada digest**.
4. O **applier** re-verifica tudo, checa **anti-rollback selado**, confere o **compose pinado**, exige **backup fresco**, faz o **PUT por digest** e **confirma em localhost**.

## Separação de privilégio (por que 2 usuários)

O token do Portainer é **root-equivalente** (um PUT com compose arbitrário = container
arbitrário = takeover da VM01). Por isso:

| Usuário | Tem o token? | Papel |
|---|---|---|
| `aprender-deployer` | **não** | busca + verifica dados hostis; escreve o handoff |
| `aprender-applier` | **sim** (`curlrc` 0400) | re-verifica; faz o PUT com o **seu** compose pinado; sela |

Comprometer o parser de dados (deployer) não entrega o token nem injeta compose →
"RCE no agente" vira, no máximo, DoS.

## Estrutura

```
reconcile.sh  apply.sh  break-glass.sh  VERSION
lib/       # funções puras (sourced): log, notify, state, seal, fetch, pointer,
           # verify_image, portainer, compose, confirm, backup, common
trust/     # ÂNCORAS (código imutável): identity.env, compose.pinned.yml,
           # sigstore-root.json, bin.sha256
systemd/   # aprender-deployer.{service,timer} + aprender-applier.{service,path}
bootstrap/ # install.sh, migrate-stack.sh (cutover), egress.md
tests/     # *.bats
config.env.example  portainer.curlrc.example
```

## Instalação (host, resumo — ver `bootstrap/`)

1. `sudo bootstrap/install.sh --src <arvore> --record-bins` (1ª vez, pina hashes dos binários).
2. Preencher `/etc/aprender-deployer/config.env` (`STACK_ID`, `ENDPOINT_ID`) e o token em `/etc/aprender-deployer/portainer.curlrc` (0400 applier).
3. Gerar `trust/sigstore-root.json` (`cosign trusted-root create`) e re-`install`.
4. **Canário primeiro** (Fase 3): `migrate-stack.sh` → capturar `compose.pinned.yml` normalizado + semear o selo.
5. `systemctl start aprender-deployer.timer`.

## Operação

- **Rollback:** promover a **tag imutável anterior** pelo mesmo gate (nova `sequence`, `rollback:true` assinado). **Não há auto-rollback** (migrate é forward-only). Ref do Env anterior fica em `/var/lib/aprender-applier/rollback_ref.json`.
- **Rotação do token:** substituir `portainer.curlrc` (0400) — nenhum outro lugar tem o token.
- **Confirmação:** `journalctl -u aprender-applier` (logs JSON, token redigido). Verdade do que subiu = digest verificado no PUT, não a cor de nenhum job.
- **Dead-man switch:** o deployer toca `heartbeat` a cada tick; um observador **externo** alerta na **ausência** de heartbeat (>15min). "Quem observa o observador" = decisão aberta #9.

## Testes

```bash
bats tests/          # unit dos guards + integração com mocks de cosign/gh/curl
shellcheck *.sh lib/*.sh bootstrap/*.sh
```

## Riscos residuais aceitos

- **Solo + self-review** (decisão travada): a corrente humana é *single-account*. A defesa técnica permanece, mas 1 conta comprometida ⇒ deploy verificado arbitrário. É o **risco nº1** do ADR-018.
- Comprometer o **applier** (que detém o token) ainda = takeover; superfície mínima.
