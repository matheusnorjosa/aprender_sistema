# Deploy

Guia operacional de deploy do Aprender Sistema v2.

## Workflow canônico

Workflow único de deploy:
- `.github/workflows/deploy.yaml`

Comportamento:
- `push` na `main`: deploy automático em `staging`.
- `workflow_dispatch`:
  - `target_environment=staging`: novo build/deploy de staging.
  - `target_environment=production` + `promotion_tag`: promoção de tag imutável.
  - `target_environment=production` + `rollback_tag`: rollback para tag imutável.

Regra de tag em produção:
- `promotion_tag` e `rollback_tag` devem seguir `vYYYY.MM.DD-<sha-or-id>`.
- `latest` é rejeitada explicitamente no workflow.
- O publish de imagens no CI gera somente a tag imutável da release (sem retag `latest`).

## Governança por environment

O job de deploy usa GitHub Environments:
- `staging`
- `production`

Recomendação:
- `staging`: sem aprovação obrigatória.
- `production`: reviewers obrigatórios (+ wait timer opcional).

## Variáveis/secrets obrigatórios

O `deploy.yaml` resolve valores por ambiente com fallback global.

Exemplos:
- `STAGING_PORTAINER_URL` / `PRODUCTION_PORTAINER_URL` ou `PORTAINER_URL`
- `STAGING_PORTAINER_STACK_ID` / `PRODUCTION_PORTAINER_STACK_ID` ou `PORTAINER_STACK_ID`
- `STAGING_PORTAINER_ENDPOINT_ID` / `PRODUCTION_PORTAINER_ENDPOINT_ID` ou `PORTAINER_ENDPOINT_ID`
- `STAGING_PORTAINER_ACCESS_TOKEN` / `PRODUCTION_PORTAINER_ACCESS_TOKEN` ou `PORTAINER_ACCESS_TOKEN`
- `STAGING_HEALTHCHECK_URL` / `PRODUCTION_HEALTHCHECK_URL`
- `STAGING_VERSIONCHECK_URL` / `PRODUCTION_VERSIONCHECK_URL`

Consulte checklist completo em:
- `v2/docs/DEPLOY_CHECKLIST.md`

## Evidências do deploy

Cada execução gera artifact `deploy-evidence-<run_id>` com:
- `deploy-evidence.txt`
- `post-deploy-health-response.txt`
- `post-deploy-version-response.txt`
- `post-deploy-debug.txt`
- `portainer-stack-update-attempts.txt` (quando aplicável)

## Deprecação (issue #814)

Workflows removidos:
- `.github/workflows/release.yaml`
- `.github/workflows/dockerhub-rebuild.yml`

Variáveis obsoletas:
- `STAGING_DEPLOY_COMMAND`
- `PRODUCTION_DEPLOY_COMMAND`

Essas variáveis não são mais usadas pelo pipeline canônico.
