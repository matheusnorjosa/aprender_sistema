# Deploy Checklist

> **Modelo atual: pull-based (ADR-018).** A SSOT do mecanismo de deploy é
> [`specs/infra/deploy.spec.md`](specs/infra/deploy.spec.md) — este checklist só resume os passos operacionais.
> O modelo antigo (o CI fazia `PUT` no Portainer `:9443` **público**) foi desligado no cutover (#1515) e o job
> `deploy` removido na Fase 4 (#1516). **Não** há mais secrets `PORTAINER_*` / `STAGING_*` / `PRODUCTION_*`.

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

- [ ] `promote.yml` resolve tag→digest, exige imagens assinadas e publica o ponteiro **assinado** (`cosign sign-blob`) no branch `deploy-pointer`
- [ ] O agente `aprender-deployer` (VM01) lê o ponteiro, verifica com cosign contra o trusted-root pinado, aplica **por digest** em `127.0.0.1:9443` e confirma de dentro da VM (`/api/readyz/` + `/api/version/`)
- [ ] **Rollback** = promover a tag anterior pelo mesmo caminho gated: `gh workflow run promote.yml -f release=<tag-anterior>`

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
