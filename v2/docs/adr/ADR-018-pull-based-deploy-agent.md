# ADR-018 — Deploy pull-based com agente on-box + gate manual (repo público)

| Field        | Value                                                                 |
| ------------ | --------------------------------------------------------------------- |
| **Status**   | Proposed                                                              |
| **Date**     | 2026-07-07                                                            |
| **Deciders** | Infra/Backend (Aprender Sistema) — sessão pós-incidente 2026-07       |
| **Related**  | `.github/workflows/deploy.yaml`, `.github/workflows/slsa-provenance.yml`, `v2/infra/docker-compose.prod.yml`, `v2/infra/scripts/staging-gate.sh`, PR #1510 (band-aid do curl 28) |

## Sumário

Migrar a entrega de produção de um modelo **push** (o runner do GitHub Actions
chama a API do Portainer exposta na internet, `:9443`) para um modelo **pull**:
um **agente confiável** roda na VM01, lê um *ponteiro de release* íntegro do
GitHub (só egress) e aplica a mudança no Portainer via `127.0.0.1:9443`. Isso
(1) permite **fechar o `:9443`** público, (2) elimina a falha intermitente
`curl 28`, e (3) adiciona um **gate manual** (aprovação humana) antes de prod —
tudo **mantendo o repositório público**.

Este é um documento de **roadmap** (Status: Proposed). Não altera o deploy
atual; descreve a arquitetura-alvo, a segurança e um plano de implementação
faseado a ser priorizado.

## Contexto e análise do estado atual

O deploy atual (`.github/workflows/deploy.yaml`) é:

1. `prepare` calcula a versão imutável (`vAAAA.MM.DD-<sha>`).
2. `build_and_push` builda backend+frontend, roda **Trivy** (gate HIGH/CRITICAL)
   e faz push da imagem imutável ao Docker Hub.
3. `deploy` faz um **`PUT` na API do Portainer** (`:9443`) trocando o env
   `IMAGE_TAG` da stack de prod (`STACK_ID=7`) + `RepullImageAndRedeploy`.
4. O `compose.prod` referencia `image: ...:${IMAGE_TAG}` (tag imutável; **sem
   Watchtower** — removido de propósito; sem polling).

### O que já é bom (e deve ser preservado)

- **Tags imutáveis por-commit** — rastreabilidade exata (prod = qual commit),
  rollback limpo, sem ambiguidade de `:latest`. É boa prática; **remover o
  Watchtower em favor disto foi um acerto de maturidade**, não um erro.
- **Build + scan (Trivy) separados do deploy**; **assinatura de proveniência**
  já existe (`.github/workflows/slsa-provenance.yml`, cosign sign + attest).
- **`migrate` one-shot** no compose; **gates** (staging-gate local, security).

### Os dois pontos fracos reais

1. **Modelo de entrega push contra `:9443` público.** O runner do GitHub
   (cloud) alcança *para dentro* da rede, via NAT do Golden Firewall
   (`45.174.67.141:9443`). Dois problemas:
   - **Segurança:** o `:9443` é o **control-plane do Docker host** exposto à
     internet — o oposto da boa prática (nunca expor a API de orquestração).
   - **Fragilidade:** o Kaspersky/KESL no caminho derruba a conexão
     intermitentemente → **`curl (28)`** (os 3 deploys da Onda 4 falharam
     assim; re-rodar resolvia porque a conexão é *intermitente, não morta*).
2. **Não há degrau antes de prod: `merge = prod`, sem gate.** Hoje o
   `push→main` **auto-deploya em produção** — o alvo interno é rotulado
   `staging` mas, sem config de staging separada, cai no stack genérico
   `PORTAINER_STACK_ID=7 = aprender_prod` (ver `staging-gate.sh` e o `resolve`
   em `deploy.yaml`). Para um sistema **no ar servindo usuários**, cada merge
   chega direto ao usuário, sem aprovação nem ambiente intermediário.

### Restrição dura

O **repositório é público e permanecerá público**. Isso **elimina a opção de
self-hosted GitHub Actions runner**: em repo público, um fork pode abrir um PR
que executa **código arbitrário** no runner — e o runner estaria na VM01, o host
de produção. É a razão nº 1 pela qual o GitHub desaconselha self-hosted runner
em repo público. Ver *Alternativas consideradas*.

## Decisão

### Ideia central

**Inverter o fluxo.** Um **agente confiável** (código do próprio time) roda na
VM01, **lê um "ponteiro de release"** (uma string de tag validada) e chama o
Portainer em `127.0.0.1:9443`. A distinção que torna isto seguro em repo público
— onde o self-hosted runner não é — é que o agente **só lê um dado** (a tag) e o
trata como dado; **nunca executa código de PR/fork**.

O **gate manual** reusa o `GitHub Environment production` que o job de deploy
**já referencia** (`environment: production` em `deploy.yaml`) mas hoje está
**sem required reviewer** — ligar o botão é 0 linha de YAML, só habilitar
reviewers em *Settings → Environments*.

### Fluxo-alvo

```text
merge→main → build+scan(Trivy)+push (imagem IMUTÁVEL, GitHub-hosted, egress OK)
          → grava ponteiro de STAGING (automático)
   ┌─ [BOTÃO] Approve — Environment "production" (reviewer humano, auditável)
   ▼
   grava PONTEIRO DE PROD (tag imutável abençoada; inforjável: escrita atrás do gate)
   ───────────────── fronteira de rede (nada inbound) ─────────────────
   agente na VM01: poll (egress HTTPS) → valida regex do ponteiro
        → resolve tag→DIGEST → cosign/attestation verify (identidade = este repo)
        → PUT https://127.0.0.1:9443/api/stacks/7 (RepullImageAndRedeploy)
        → confirma em localhost:8000 (/api/version/ == tag && /api/readyz/ 200)
   → prod atualizado + notificação outbound (status-back)
```

### Componentes

1. **Build/scan/push — fica como está.** Roda em `push→main`/dispatch,
   GitHub-hosted, egress ao Docker Hub. Nenhum workflow disparável por fork
   referencia `DOCKER_HUB_TOKEN`/`PORTAINER_*` — forks não têm caminho aos
   secrets. Nunca introduzir `pull_request_target` com checkout+exec de head.

2. **Gate/botão — `GitHub Environment production` + required reviewers.**
   Environments/secrets nunca são expostos a `pull_request` de fork; aprovar
   exige write access; é per-deploy, auditável na aba Deployments. `staging`
   fica sem reviewers → continua automático. A run de `push→main` pausa no
   *Approve* (a tag é a mesma que foi para staging — zero digitação); ou
   `workflow_dispatch` (exige write → fork não dispara) para re-promover/rollback.

3. **Ponteiro — `production.json` num branch protegido `deploy-pointer`,
   leitura tokenless.** Lido pelo agente via `raw.githubusercontent.com` sem
   credencial. A integridade vem da **proteção de escrita**, não do sigilo do
   valor (ser público-legível não é fraqueza): o único escritor é o job de
   promoção atrás do gate `production`. Alternativa válida: repo Variable
   `PRODUCTION_IMAGE_TAG` (leitura autenticada não-pública, ao custo de um PAT
   read-only na VM). **Decisão aberta (§Pendências).**

   ```json
   { "image_tag": "v2026.07.07-abc1234", "digest": "sha256:...",
     "run_id": 456, "released_at": "2026-07-07T12:00:00Z" }
   ```

4. **Agente `aprender-deployer` na VM01 — systemd timer `Type=oneshot`.**
   Não-daemon (processo curto por tick, crash-safe, nada escuta). Usuário
   `aprender-deployer` (`/usr/sbin/nologin`, **fora do grupo docker, sem sudo,
   sem docker.sock**), sandbox systemd (`NoNewPrivileges`, `ProtectSystem=
   strict`, `CapabilityBoundingSet=`, `SystemCallFilter=@system-service`,
   `MemoryMax=128M`). Deps: `curl`, `jq`, `flock`, `cosign`/`gh`. Poder único:
   pedir ao Portainer para trocar `IMAGE_TAG` + repull — **não** roda contêiner
   arbitrário. Reconcile idempotente: **ponteiro válido AND imagem verificada
   AND desired≠running** antes de qualquer mutação; fail-closed. Token do
   Portainer fora de `argv` (`curl --config`).

5. **Firewall — fechar o `:9443`.** Remover o NAT do Golden + fechar no host.
   Admin do Portainer passa a **VPN / SSH tunnel** (`ssh -L 9443:127.0.0.1:9443`).
   Break-glass on-box documentado.

### Mudanças no `deploy.yaml`

- **Fica:** `prepare`, `build_and_push` (Trivy), `tag_and_release`,
  `validate_existing_tag`, o pré-gate "Verify staging is serving requested tag".
- **Muda:** o job `deploy` **deixa de chamar o Portainer** — o step do `PUT`
  sai e vira **"Publish production pointer"** (grava `production.json`, atrás do
  `environment: production`). Removem-se os secrets `PRODUCTION_PORTAINER_*` do
  GitHub após o corte (não deixar credencial inbound-capaz no CI). O poll
  público de health/version fica best-effort; a **confirmação autoritativa é a
  do agente on-box** (loopback), o que remove a dependência do caminho externo
  flaky.
- **Furo que o refactor DEVE corrigir (crítico):** enquanto `push→main` escrever
  o ponteiro de **prod**, o botão é **decorativo**. Correção obrigatória:
  `push→main` grava **só** o ponteiro de **staging**; o de **prod** é escrito
  **exclusivamente** pelo job atrás do gate. O agente de prod lê **só** o
  ponteiro de prod.

## Segurança

### O que impede um fork de forjar/enviar (garantia dura do GitHub)

Workflow disparado por `pull_request` de fork recebe `GITHUB_TOKEN` **read-only**
e **zero secrets** — não faz push em branch/tag protegido, não escreve Variable,
não aprova environment, não cria Release, não alcança `DOCKER_HUB_TOKEN`/
`PORTAINER_*`. Logo o **ponteiro** (branch protegido) e o **gate** (environment
reviewer) são **inforjáveis por fork**.

### Mínimo de proteções obrigatórias (TODAS ligadas, senão o design NÃO é seguro)

1. **Branch protection server-side em `main`**: PR obrigatório, ≥1 review,
   status checks, sem force-push/delete, **include administrators**. O hook
   CP-07 é client-side → **não conta** como controle de segurança.
2. **CODEOWNERS + review obrigatório** para `.github/workflows/**` e o diretório
   do agente.
3. **Ponteiro não-escrevível por fork** (branch protegido) + **regex estrita**
   no agente.
4. **Gate = Environment `production` required reviewers.**
5. **Deploy por DIGEST `@sha256:`** (immutable tags no Docker Hub ou digest
   pinado no `compose.prod`) — não por tag mutável.
6. **`cosign verify` + `gh attestation verify` no agente** antes de aplicar
   (identidade OIDC = este repo; o pipeline já existe em `slsa-provenance.yml`
   mas **não era verificado no deploy**).
7. **Agente = código confiável imutável** — **nunca `git pull` + exec** (senão
   um merge comprometido vira takeover da VM01 com o token do Portainer);
   token least-privilege, sem interpolação shell, TLS verificado.
8. **`:9443` fechado** (NAT + host); admin via SSH/VPN; break-glass documentado.
9. **`push→main` NÃO escreve ponteiro de prod**; anti-replay/downgrade com
   override autorizado; **audit log** de escrita de ponteiro + ações do agente.
10. **Cache poisoning**: escopar a chave `cache-from/to: type=gha` por ref
    confiável (não compartilhar PR↔main); a verificação por digest detecta a
    divergência resultante.

### Riscos residuais (honestos)

- **VM01 comprometida** → token = takeover. Já é game-over independente do
  design; com o `:9443` fechado, o token só é usável de dentro da VM/LAN.
  Mitigação: least-privilege + recusa de imagem sem proveniência do repo.
- **Merge de código malicioso em main** → build legítimo de imagem maliciosa.
  Trivy não defende (pega CVE, não backdoor). Defesa = branch protection +
  review (itens 1/2). É o vetor que sobra, fora do escopo do agente.
- **Ponteiro stale / agente parado** → prod fica na versão antiga =
  **disponibilidade**, não integridade. Detecção: heartbeat/dead-man's switch +
  comparar `/version` vs ponteiro; alertar divergência > N min.
- **Deploy parcial** (stack atualizou, contêineres unhealthy) → o agente **não
  reporta sucesso** até `version live && readyz 200`; alerta.

## Plano de implementação (faseado)

> Ordem obrigatória: o CI **hoje depende** do inbound `:9443` — **não fechar a
> porta antes** do agente estar validado (passos 1–5).

### Fase 0 — Pré-requisitos de segurança (bloqueantes, sem eles o resto é inseguro)

- [ ] Ligar **branch protection server-side** em `main` (PR + review + status
      checks + include admins).
- [ ] Adicionar **CODEOWNERS** cobrindo `.github/workflows/**` e o dir do agente.
- [ ] Habilitar **immutable tags** no Docker Hub **ou** decidir pinar
      `@sha256:` no `compose.prod` (pré-req do deploy-por-digest).

### Fase 1 — Agente na VM01 (contra staging/canário, porta ainda aberta)

- [ ] Escrever o agente (`aprender-deployer`): reconcile idempotente, resolve
      tag→digest, `cosign verify` + `gh attestation verify`, `PUT localhost:9443`,
      confirma em `localhost:8000`. Código **versionado e imutável** no host
      (imagem/config-mgmt), **sem `git pull`+exec**.
- [ ] Provisionar usuário não-root + unit systemd (`oneshot` timer, sandbox).
- [ ] Provisionar token do Portainer **least-privilege** (só update do stack) e
      a verificação cosign; egress allowlist (`raw.githubusercontent.com`,
      `registry-1.docker.io`, fulcio/rekor, host de notificação).
- [ ] Rodar end-to-end contra **staging ou um stack canário**.

### Fase 2 — Gate + ponteiro (lado GitHub)

- [ ] Criar o branch protegido `deploy-pointer` (ou a repo Variable, conforme
      §Pendências) — escrita só pelo job de promoção.
- [ ] **Corrigir o furo:** `push→main`/`staging-gate.sh` para de escrever o
      ponteiro de prod (passa a escrever só o de staging).
- [ ] Migrar o job de prod do `deploy.yaml`: PUT-Portainer → **gravar o
      ponteiro** (mantendo `environment: production` como botão).
- [ ] Ligar **required reviewers** no Environment `production`.

### Fase 3 — Validação de corte

- [ ] Aprovar o gate → agente vê ponteiro → resolve digest → verifica
      proveniência → PUT localhost → confirma. **Confirmar 2 promoções
      consecutivas** fluindo puramente pelo agente.

### Fase 4 — Fechar a porta

- [ ] **Fechar o `:9443`** (NAT Golden + host). Configurar SSH tunnel/VPN para
      admin. Documentar e **testar** o break-glass.
- [ ] **Remover** os secrets `PRODUCTION_PORTAINER_*` do GitHub.

### Fase 5 — Observabilidade e operação

- [ ] Status-back do agente (journald + webhook outbound recomendado; evitar PAT
      `deployments:write` na VM). Heartbeat/dead-man's switch. Alerta de
      divergência `/version` vs ponteiro e de deploy parcial.

## Rollback

- **De uma release ruim (operacional):** gravar o ponteiro de prod numa **tag
  imutável anterior**, **pelo mesmo gate** (`workflow_dispatch` rollback →
  Approve). O agente forward-aplica (o override autorizado libera a proteção
  anti-downgrade). **Auto-rollback OFF por default** (voltar por cima de
  migração forward corrompe dado; `migrate` one-shot é forward).
- **Do próprio cutover (Fases 1–3):** com o `:9443` ainda aberto, dá para
  reverter o `deploy.yaml` ao PUT direto enquanto se diagnostica. Após a Fase 4,
  o caminho é o break-glass (SSH → Portainer localhost).

## Alternativas consideradas

- **Self-hosted GitHub Actions runner na rede** — **rejeitado** enquanto o repo
  for público: um fork-PR executaria código arbitrário no runner (na VM01). O
  agente pull evita isso porque só lê dados, não executa código do repo.
- **Re-introduzir Watchtower** — **rejeitado**: exigiria uma **tag móvel**
  (`:prod`/`:latest`), revertendo a escolha (correta) de tags imutáveis, e
  perde o gate e a rastreabilidade.
- **Manter o push + só endurecer o retry** (PR #1510) — **band-aid aceito** para
  o curto prazo (para de sangrar o `curl 28`), mas **não** fecha o `:9443` nem
  adiciona gate. É complementar a este ADR, não substituto.

## Pendências / decisões abertas

1. **Ponteiro:** branch protegido `deploy-pointer` **tokenless** (recomendado —
   zero credencial GitHub na VM) vs. repo Variable `PRODUCTION_IMAGE_TAG`
   (leitura não-pública, custa um PAT read-only).
2. **Deploy por digest:** immutable tags no Docker Hub **ou** pinar `@sha256:`
   no `compose.prod`.
3. **Reviewers** do Environment `production` (mín. 1 com write; operação solo →
   "prevent self-review" desligado).
4. **Staging:** usa o mesmo `:9443`/VM? Se sim, staging também precisa do agente
   (mesmo mecanismo, sem reviewers) para não quebrar ao fechar a porta.
5. **Status-back:** journald + webhook outbound (recomendado) vs. Deployment
   status no GitHub (PAT `deployments:write` na VM — desaconselhado).

## Consequências

**Positivas:**
- Control-plane do Portainer **sai da internet** (só egress) — maior redução de
  risco.
- Token do Portainer **confinado à VM01** (não trafega pela internet).
- **Gate manual real** com reviewer humano auditável, fechando o furo do
  auto-deploy.
- Fim da flakiness do `curl 28/000` no caminho crítico (confirmação on-box).
- Supply-chain endurecida (proveniência por digest passa a ser verificada).

**Negativas (custo operacional):**
- **Peça nova** (agente): provisionar, versionar, monitorar heartbeat, rotacionar
  credenciais na VM.
- Admin do Portainer deixa de ser um clique no browser → SSH/VPN + break-glass.
- Fluxo dividido em dois lados (CI grava ponteiro / agente aplica) →
  observabilidade em dois lugares.
- Deploy por digest exige immutable tags ou pin no `compose.prod`.
