# Deploy

> Conteúdo consolidado. Fonte única: **[Deploy & Produção (spec)](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/specs/infra/deploy.spec.md)** e o **[Deploy Checklist](https://github.com/matheusnorjosa/aprender_sistema/blob/main/v2/docs/DEPLOY_CHECKLIST.md)**.

## O modelo em três linhas (ADR-018)

**Merge na `main` NÃO deploya.** O `deploy.yaml` (hoje *"Build, sign and release"*) só
faz build → scan → push → assina (cosign + provenance SLSA) → cria a tag imutável
`vYYYY.MM.DD-<sha7>` e o Release. O job que fazia `PUT` no Portainer `:9443` público
foi **deletado** (Fase 4, #1516).

Produção muda em dois passos deliberados:

1. **`promote.yml`** (`workflow_dispatch`, gated no GitHub Environment `production` com
   *required reviewer*) resolve tag→digest, exige imagens assinadas, e assina o
   `production.json` no branch protegido `deploy-pointer`.
2. O agente **`aprender-deployer`** na VM01 lê o ponteiro, verifica assinatura e
   digests, e aplica em `127.0.0.1:9443` — confirmando de dentro da VM.

Rollback é o mesmo caminho: `promote.yml` com o input `rollback: true` (continua
exigindo `sequence` maior que o selo).

Detalhe completo (drift do compose, anti-rollback, fail-closed de cada degrau) na spec
e no ADR-018 (`docs/architecture/project-decisions/ADR-018-pull-based-deploy.md`).
