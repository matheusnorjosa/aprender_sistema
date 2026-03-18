# Deploy Checklist

Checklist de configuração para o pipeline canônico de deploy:
- `.github/workflows/deploy.yaml`

## 1. Pré-requisitos gerais

- [ ] Environments GitHub criados: `staging` e `production`
- [ ] `production` com reviewers obrigatórios
- [ ] Docker Hub token válido (`DOCKER_HUB_TOKEN`)
- [ ] Portainer acessível pelo runner do GitHub Actions

## 2. Variáveis/secrets de Portainer

Defina por ambiente (ou fallback global):

| Nome | Escopo | Obrigatório |
|---|---|---|
| `STAGING_PORTAINER_URL` / `PRODUCTION_PORTAINER_URL` | per-env | Sim (ou `PORTAINER_URL`) |
| `STAGING_PORTAINER_STACK_ID` / `PRODUCTION_PORTAINER_STACK_ID` | per-env | Sim (ou `PORTAINER_STACK_ID`) |
| `STAGING_PORTAINER_ENDPOINT_ID` / `PRODUCTION_PORTAINER_ENDPOINT_ID` | per-env | Sim (ou `PORTAINER_ENDPOINT_ID`) |
| `STAGING_PORTAINER_ACCESS_TOKEN` / `PRODUCTION_PORTAINER_ACCESS_TOKEN` | per-env | Sim (ou `PORTAINER_ACCESS_TOKEN`) |
| `STAGING_PORTAINER_SKIP_TLS_VERIFY` / `PRODUCTION_PORTAINER_SKIP_TLS_VERIFY` | per-env | Não (default `true`) |

## 3. Verificação pós-deploy

| Nome | Escopo | Obrigatório |
|---|---|---|
| `STAGING_HEALTHCHECK_URL` / `PRODUCTION_HEALTHCHECK_URL` | per-env | Sim |
| `STAGING_VERSIONCHECK_URL` / `PRODUCTION_VERSIONCHECK_URL` | per-env | Sim |
| `POST_DEPLOY_SKIP_TLS_VERIFY` | global | Não (default `false`) |

Observação:
- em promoção para produção, `STAGING_VERSIONCHECK_URL` precisa existir para o gate de homologação da tag.

## 4. Comandos canônicos

### 4.1 Staging automático

- Trigger: `push` em `main`.
- Esperado: build + scan + push + deploy em `staging`.

### 4.2 Staging manual

```bash
gh workflow run deploy.yaml -f target_environment=staging
```

### 4.3 Promoção para produção

```bash
gh workflow run deploy.yaml -f target_environment=production -f promotion_tag=vYYYY.MM.DD-<sha>
```

### 4.4 Rollback de produção

```bash
gh workflow run deploy.yaml -f target_environment=production -f rollback_tag=vYYYY.MM.DD-<sha-anterior>
```

Observação:
- O workflow rejeita `latest` em produção. Use apenas tag imutável no formato `vYYYY.MM.DD-<sha-or-id>`.
- O build/publish do pipeline usa somente a tag imutável da release (sem retag `latest`).

## 5. Evidências obrigatórias

- [ ] Artifact `deploy-evidence-<run_id>` disponível
- [ ] `deploy-evidence.txt` presente
- [ ] `post-deploy-health-response.txt` presente
- [ ] `post-deploy-version-response.txt` presente
- [ ] Em caso de falha de update: `portainer-stack-update-attempts.txt`

## 6. Gate de PR (staging)

- [ ] Check `[required] staging gate evidence` verde no PR
- [ ] PR contém `ALL 8 CHECKS PASSED` no corpo (evidência auditável)
- [ ] Checklist `make staging-full` marcado no PR
- [ ] PR com impacto em runtime (`v2/backend/**`, `v2/frontend/**`, `v2/infra/**`); se não houver impacto, o check pode ficar `skipped`

## 7. Variáveis obsoletas (remover)

As variáveis abaixo não são mais usadas após a depreciação do `release.yaml`:

- `STAGING_DEPLOY_COMMAND`
- `PRODUCTION_DEPLOY_COMMAND`

## 8. Critérios de aceite do deploy

- [ ] Deploy de `staging` conclui sem erro opaco
- [ ] Deploy de `production` exige aprovação do environment
- [ ] `version` endpoint contém a tag esperada
- [ ] Rollback por tag imutável executa com sucesso
