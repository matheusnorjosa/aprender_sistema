# Deploy Checklist

> **Modelo atual: pull-based (ADR-018).** A decisão está em
> [ADR-018 — Pull-based deploy](../../docs/architecture/project-decisions/ADR-018-pull-based-deploy.md)
> (que **supersede** o ADR-010); a SSOT do mecanismo é
> [`specs/infra/deploy.spec.md`](specs/infra/deploy.spec.md) — este checklist só resume os passos operacionais.
> O modelo antigo (o CI fazia `PUT` no Portainer `:9443` **público**) foi desligado no cutover (#1515) e o job
> `deploy` removido na Fase 4 (#1516) — conferido em `.github/workflows/deploy.yaml`, que hoje só
> tem os jobs `prepare`, `build_and_push`, `sign` e `tag_and_release`. **Não** há mais secrets
> `PORTAINER_*` / `STAGING_*` / `PRODUCTION_*`.

Workflows canônicos:

- `.github/workflows/deploy.yaml` — **"Build, sign and release (main)"**
- `.github/workflows/promote.yml` — promoção/rollback (gated)

## 1. Pré-requisitos gerais

- [ ] GitHub Environment `production` criado com **required reviewer** (1 aprovação)
- [ ] Branch protegido `deploy-pointer` (o ponteiro de release assinado é publicado nele)
- [ ] Docker Hub token válido (`DOCKER_HUB_TOKEN`) para push das imagens
- [ ] Agente `aprender-deployer` ativo na VM01 (systemd) com o trusted-root do cosign pinado offline
- [ ] `cosign` disponível no pipeline (assinatura keyless + provenance SLSA)

## 2. Secrets/vars removidos (NÃO reconfigurar)

Após o cutover ADR-018 (#1515/#1516), estes secrets/vars foram **removidos do GitHub** e não têm mais uso:

- `PORTAINER_*` (URL / STACK_ID / ENDPOINT_ID / ACCESS_TOKEN / SKIP_TLS_VERIFY) e as variantes `STAGING_*` / `PRODUCTION_*`
- `STAGING_HEALTHCHECK_URL` / `PRODUCTION_HEALTHCHECK_URL`, `STAGING_VERSIONCHECK_URL` / `PRODUCTION_VERSIONCHECK_URL`
- `STAGING_DEPLOY_COMMAND` / `PRODUCTION_DEPLOY_COMMAND`

O único token de Portainer que ainda existe fica **dentro da VM01** (o `aprender-applier` o detém), nunca no GitHub.

## 3. Merge na `main` (build + sign + release)

- [ ] Merge na `main` dispara `deploy.yaml`: build → scan (Trivy) → push no Docker Hub → **assina** as imagens
      (cosign keyless + provenance SLSA) → cria a **tag imutável** `vYYYY.MM.DD-<sha7>` + GitHub Release
- [ ] **Merge NÃO deploya** — nenhum ambiente é atualizado neste passo
- [ ] Gate Trivy verde (bloqueia HIGH/CRITICAL); imagens assinadas verificáveis por digest

## 4. Promoção para produção (`promote.yml`)

Produção muda em **dois passos deliberados**:

```bash
# 1) Promoção — gated no GitHub Environment `production` (required reviewer)
gh workflow run promote.yml -f release=vYYYY.MM.DD-<sha7>
```

- [ ] `promote.yml` resolve tag→digest, exige imagens assinadas (step `Gate duro — imagens DEVEM estar assinadas (cosign)` em `promote.yml`) e publica o ponteiro **assinado** (`cosign sign-blob`, step `Assinar o ponteiro (cosign sign-blob keyless)` em `promote.yml`) no branch `deploy-pointer`
- [ ] O agente `aprender-deployer` (VM01) lê o ponteiro, verifica com cosign contra o trusted-root pinado, aplica **por digest** em `127.0.0.1:9443` e confirma de dentro da VM (`confirm_localhost` em `deployer/apply.sh` = `/api/readyz/` + `/api/version/`)
- [ ] **Gate de backup fresco**: o applier roda `deployer/hooks/check_backup.sh` e **recusa aplicar** se não houver dump com idade ≤ `BACKUP_MAX_AGE` (28h) e tamanho ≥ `BACKUP_MIN_SIZE` (1024B) em `/var/backups/aprender`. Ele só faz `stat` — **não** valida que o backup é restaurável (ver [BACKUP_OPERATIONS.md](BACKUP_OPERATIONS.md))
- [ ] **Rollback** = promover a tag anterior pelo mesmo caminho gated: `gh workflow run promote.yml -f release=<tag-anterior>`

> Rollback de **imagem** não desfaz **migration**. Se a release promovida aplicou migration
> destrutiva, o caminho de volta é restore de banco, com `restore_db.sh` — operante para
> `.age` desde `8f392636` (#1611) e com verificação real de sucesso desde `3bca74f3`
> (#1645). O que ainda **não** foi ensaiado é o drill de ponta a ponta
> ([#1646](https://github.com/matheusnorjosa/aprender_sistema/issues/1646), aberta):
> trate o RTO de restore como estimativa. Ver [DISASTER_RECOVERY.md](DISASTER_RECOVERY.md).

Observação:

- O pipeline rejeita `latest`; use apenas tag imutável `vYYYY.MM.DD-<sha7>`. Sem retag `latest`.
- Alterar o compose exige edição **manual** no Editor do Portainer + re-captura do pinado (senão o agente recusa por `compose_drift`).

## 5. Go-live local (v2)

Sequência mínima de validação pré-go-live (rodar em `v2/`):

- [ ] `make up` — sobe a stack dev
- [ ] `make readyz` — checa `/api/readyz/` (db + redis)
- [ ] `make healthz` — checa `/healthz/` (saúde da app)
- [ ] `make ban-v1` — roda `scripts/ban_v1.sh`: remove à força containers, redes e volumes legados do projeto v1 (`com.docker.compose.project=aprendersistema`), garantindo que nenhum resíduo v1 sobreviva ao corte (CP-05).

## 6. Gate de PR (staging local)

Não há staging remoto: a barreira prod-like é o `make staging-full` **local** do autor, evidenciado no corpo do PR.

- [ ] Check `[required] staging gate evidence` verde no PR
- [ ] PR contém `ALL 8 CHECKS PASSED` no corpo (evidência auditável)
- [ ] Checklist `make staging-full` marcado no PR
- [ ] PR com impacto em runtime (`v2/backend/**`, `v2/frontend/**`, `v2/infra/**`); se não houver impacto, o check pode ficar `skipped`

## 7. Critérios de aceite do deploy

- [ ] `deploy.yaml` conclui build+scan+push+sign+release sem erro
- [ ] Tag imutável `vYYYY.MM.DD-<sha7>` + Release publicados
- [ ] Promoção exige aprovação do Environment `production`
- [ ] Agente na VM01 aplica por digest e confirma `/api/version/` = release promovida
- [ ] Rollback por promoção de tag anterior executa pelo mesmo caminho gated

## 8. Poder de acesso depois do deploy (ADR-020)

O `promote.yml` só assina o ponteiro e não alcança o banco de produção: a conferência de poder é
manual, no container `web` novo. Os comandos são só leitura e não mostram dado pessoal.

- [ ] Antes do deploy: `rbac_diff --salvar /tmp/antes.json` e copiar o arquivo para o host da VM
      (passo a passo no docstring de `management/commands/rbac_diff.py`)
- [ ] Depois do deploy: devolver o arquivo ao `/tmp` do container novo e rodar
      `rbac_diff --comparar /tmp/antes.json`. Num PR que não muda poder, o esperado é literal:
      `rbac_diff: 0 ganhos, 0 perdas`. PR que soma chave a `PUBLIC_POLICY_KEYS` é a exceção: mostra
      `+ policies: <chaves novas>` para quem passa a tê-las, 0 perdas e nenhuma linha de `grupos`,
      `capacidades`, `gerencias_escopo` ou `vinculos`. As chaves esperadas estão na decisão do PR
      (ex.: D22 em `rbac_authorization_matrix.md`)
- [ ] `rbac_diff --auditar` termina com exit 0: matriz Grupo × Capability do banco igual à do seed
      (`functional_permissions_seed.py`) e nenhuma gerência com perfil fora de `PERFIL_PERMITIDO`
      (`services/rbac_pacotes.py`). Exit 1 lista a divergência (grupo / capacidade, ou gerência / perfil)
- [ ] `rbac_diff --diagnostico` mostra `fonte ativa: lotacao` no cabeçalho (PR 12, o corte). Se mostrar
      `uniao`, a volta de emergência da seção 9 está ligada no Environment da stack

## 9. Volta do corte (`RBAC_FONTE`, PR 12)

Desde o PR 12 o poder vem só do lugar onde a pessoa trabalha: superusuário, pacote do perfil da gerência
(vínculo EQUIPE ou GERENTE vigente) e direitos do papel vigente. O grupo Django (DAT, Controle, Diretoria) é
etiqueta. A variável `RBAC_FONTE` escolhe o modo: `lotacao` (padrão, também vazia ou ausente) ou `uniao`, que
volta a somar os grupos. Valor inválido derruba a subida (o `migrate` falha e nada sobe), de propósito.

**Uma pessoa sem acesso não pede a volta inteira.** O caminho depende da lotação dela:

- [ ] Sem outro vínculo ativo: o superusuário marca a gerência e "Equipe administrativa" na tela de Usuários.
      Vale na hora (o sinal limpa o cache no commit)
- [ ] Com vínculo ativo em outra gerência: **não usar a tela.** O formulário tem uma gerência só; trocar a
      gerência leva todos os papéis da pessoa para a nova e encerra os outros vínculos (`sync_user_lotacao`).
      Criar só o vínculo que falta por script (`upsert_vinculo`), com ensaio, OK do dono e releitura
      (skill `escrita-em-fonte-viva`), ou fazer a volta inteira abaixo
- [ ] Antes de salvar o formulário de alguém da gerência DAT ou CONTROLE, conferir que "Equipe administrativa"
      continua marcada: tirar ou trocar função refaz a lotação, e no corte o vínculo é a única porta

**Volta inteira (todo mundo de novo com a soma de grupos):**

- [ ] Passo 0, antes de virar: no container `web`, `rbac_diff --salvar /tmp/agora.json` e
      `rbac_diff --salvar /tmp/uniao.json --simular-fonte uniao`, depois
      `rbac_diff --comparar /tmp/agora.json --depois /tmp/uniao.json`. A volta soma os grupos **de hoje**: quem
      foi posto no grupo DAT, Controle ou Diretoria depois do corte ganha o poder do grupo na hora. Cada `+` da
      lista precisa do OK do dono, ou a pessoa sai do grupo antes da volta
- [ ] Portainer → stack de produção → Environment → `RBAC_FONTE=uniao` → **Update the stack**. Mexer só no
      Environment, nunca no editor do compose (compose diferente do pinado faz o agente recusar o deploy
      seguinte por `compose_drift`). O deployer preserva o Environment nos deploys seguintes: a volta vale até
      alguém apagar a variável. Registrar no arquivo de pós-deploy
- [ ] Se o site parar de responder de fora (HTTP 000): `systemctl restart kesl` na VM01, nunca restart do Docker
- [ ] Conferir: `rbac_diff --diagnostico` mostra `fonte ativa: uniao`. A chave do cache inclui a fonte: ninguém
      fica com o poder do modo anterior
- [ ] Para desfazer a volta: apagar a variável (ou deixá-la vazia) e "Update the stack". Vazio vale `lotacao`

**Antes do deploy do PR 12 e depois, a cada reativação de conta:** pessoa **inativa** com vínculo EQUIPE ou
GERENTE vigente na gerência DAT ou CONTROLE, ou GERENTE na Superintendência, volta com o poder ao ser reativada
(o retrato do `rbac_diff` só lê ativos, e desativar não encerra vínculo). A lista vai ao dono; o vínculo que não
deve voltar é encerrado por script com ensaio.
