# Plano: Simplificação do Pipeline de Deploy

**Data**: 2026-03-09
**Epic**: Simplificação do Pipeline CI/CD
**Status**: Planejado
**Estratégia de deploy**: Portainer Webhook (sem SSH)

---

## 1. Diagnóstico — Estado Atual

### 1.1 Fluxo atual (com problemas)

```
código → PR → merge main
                ↓
        [disparo MANUAL do workflow release.yaml]
                ↓
        build imagens → push Docker Hub
                ↓
        DEPLOY_COMMAND (secret não configurado)
                ↓
        Watchtower na VM01 (QUEBRADO — API v1.25 vs v1.44+ exigido)
                ↓
        ❌ Containers nunca atualizados automaticamente
```

**Resultado**: Deploy só funciona via Portainer manual (Pull and Redeploy).

### 1.2 Problemas identificados

| # | Problema | Impacto | Evidência |
|---|----------|---------|-----------|
| P1 | Watchtower usa imagem abandonada (`containrrr/watchtower`) | Deploy automático 100% quebrado | Logs: `client version 1.25 is too old` em loop infinito |
| P2 | `GITHUB_REF_NAME` colidia com built-in do GitHub Actions | Imagens nunca publicadas no Docker Hub | Run 22860845995: `non-main-ref` mesmo na main (corrigido PR #810) |
| P3 | Nenhum deploy automático no merge | Cada deploy requer disparo manual do `release.yaml` | workflow_dispatch obrigatório |
| P4 | `PRODUCTION_DEPLOY_COMMAND` não está configurado | Step `Execute deploy command` falharia se chegasse lá | Secret/var vazio |
| P5 | `dockerhub-rebuild.yml` duplica lógica do `release.yaml` | 2 workflows fazem build+push, com lógicas diferentes | Manutenção duplicada |
| P6 | Watchtower como modelo de deploy | Polling a cada 5min, requer Docker Hub token no compose, container extra | Arquitetura frágil |
| P7 | `stack.env` gerenciado manualmente no Portainer | Propenso a erros (ex: `#` truncando senha) | Incidente DB_PASSWORD |
| P8 | Sem rollback automatizado | Se deploy falhar, rollback é manual via Portainer | Sem safety net |

### 1.3 Workflows existentes

| Workflow | Trigger | Função | Problema |
|----------|---------|--------|----------|
| `ci.yaml` | push/PR | Testes, lint, coverage | ✅ Funciona bem |
| `release.yaml` | workflow_dispatch | Build + push + deploy | Deploy command não configurado |
| `dockerhub-rebuild.yml` | cron semanal + dispatch | Rebuild security + push | Duplica release.yaml |

### 1.4 Infraestrutura de produção

```
VM01_App (172.17.0.2)     VM02_Banco (172.17.0.3)     VM03_Redis (172.17.0.4)
┌─────────────────────┐   ┌──────────────────┐         ┌──────────────┐
│ Portainer (9443)     │   │ PostgreSQL 15    │         │ Redis 7      │
│ NPM (80/443/88)      │   │ (porta 5432)     │         │ (porta 6379) │
│ ┌─────────────────┐ │   └──────────────────┘         └──────────────┘
│ │ Stack Aprender  │ │
│ │ web (8000)      │ │   IP Externo compartilhado: 45.174.67.141
│ │ worker          │ │   NAT: 80,88,443,9443,9444
│ │ beat            │ │
│ │ frontend (81)   │ │
│ └─────────────────┘ │
└─────────────────────┘
```

---

## 2. Arquitetura Proposta

### 2.1 Novo fluxo

```
código → PR → CI (ci.yaml) → merge main
                                 ↓
                         [AUTOMÁTICO: deploy.yaml]
                                 ↓
                    build imagens → push Docker Hub
                                 ↓
                    POST Portainer Webhook → pull + redeploy
                                 ↓
                    health check (URL externa)
                                 ↓
                         ✅ Deploy concluído
```

### 2.2 Mudanças principais

| De | Para |
|----|------|
| Watchtower (polling 5min, quebrado) | Portainer Webhook (1 POST request) |
| Disparo manual (workflow_dispatch) | Automático no merge em main |
| 3 workflows (ci + release + rebuild) | 2 workflows (ci + deploy) |
| `DEPLOY_COMMAND` genérico (secret) | `PORTAINER_WEBHOOK_URL` (1 secret) |
| Sem rollback | Rollback por tag via Portainer |
| `containrrr/watchtower` abandonado | Removido do compose |
| SSH + usuário + chaves + NAT porta 22 | Zero setup na VM (Portainer já roda) |

### 2.3 Princípios

1. **Build once, deploy everywhere**: CI builda, prod só faz `docker pull`
2. **Deploy via Portainer**: Webhook trigger → pull + redeploy automático
3. **Zero setup na VM**: Portainer já está rodando, porta 9443 já aberta
4. **Verificação pós-deploy**: Health check via URL externa
5. **Rollback simples**: Re-deploy da tag anterior via workflow_dispatch
6. **Supply chain mantido**: SBOM + Trivy + provenance permanecem

### 2.4 Por que Portainer Webhook e não SSH

| Aspecto | SSH | Portainer Webhook |
|---------|-----|-------------------|
| Setup na VM | Criar usuário, chaves, NAT porta 22 | ✅ Nenhum (já roda) |
| GitHub Secrets | 4 (key, host, user, port) | ✅ 1 (webhook URL) |
| Portas NAT | Abrir porta 22 | ✅ Porta 9443 já aberta |
| Complexidade | Média | ✅ Mínima |
| Manutenção | Chaves SSH, usuário | ✅ Zero |

---

## 3. Plano de Execução (6 Issues)

### Issue 1: Configurar Portainer Webhook para o stack (#811)

**Objetivo**: Ativar o webhook no Portainer e configurar o GitHub Secret.

**Tarefas**:
1. No Portainer: Stacks → stack aprender → Automatic Updates → Webhook
2. Marcar "Re-pull image" e "Force redeployment"
3. Copiar URL do webhook gerado
4. Configurar GitHub Secret: `PORTAINER_WEBHOOK_URL`
5. Testar: `curl -X POST <webhook_url>` → stack redeploya

**Resultado esperado**:
- POST no webhook → Portainer faz pull das imagens + redeploy
- Containers recriados com imagens mais recentes do Docker Hub

---

### Issue 2: Criar workflow `deploy.yaml` unificado (#812)

**Objetivo**: Substituir `release.yaml` + `dockerhub-rebuild.yml` por um único workflow.

**Tarefas**:
1. Criar `.github/workflows/deploy.yaml` com triggers:
   - `push` em `main` → deploy automático
   - `workflow_dispatch` → deploy manual (rollback)
2. Steps:
   - Build + Trivy scan (security gate)
   - Push Docker Hub (tag + latest)
   - POST no Portainer Webhook
   - Health check via URL externa
   - Criar GitHub Release com SBOM + provenance
3. Manter supply chain (SBOM, Trivy, attestations)

**Resultado esperado**:
- Merge na main → deploy automático em ~10 min
- `workflow_dispatch` → rollback para versão anterior

---

### Issue 3: Remover Watchtower do compose de produção (#813)

**Objetivo**: Eliminar o serviço Watchtower quebrado.

**Tarefas**:
1. Remover serviço `watchtower` de `docker-compose.prod.yml`
2. Remover variáveis `WATCHTOWER_TOKEN` e `DOCKER_HUB_TOKEN` do compose
3. Remover labels `com.centurylinklabs.watchtower.enable`
4. Remover porta `8080` do NAT
5. Atualizar documentação

**Resultado esperado**:
- 4 containers (web, worker, beat, frontend) — sem watchtower
- Zero erros nos logs

---

### Issue 4: Deprecar `release.yaml` e `dockerhub-rebuild.yml` (#814)

**Objetivo**: Remover workflows duplicados.

**Tarefas**:
1. Desabilitar cron do `dockerhub-rebuild.yml`
2. Migrar security scan semanal para workflow dedicado
3. Remover `release.yaml`
4. Atualizar documentação

**Resultado esperado**:
- Apenas `ci.yaml` + `deploy.yaml` ativos

---

### Issue 5: Implementar rollback automatizado (#815)

**Objetivo**: Reverter para qualquer versão anterior com um clique.

**Tarefas**:
1. Input `rollback_tag` no `deploy.yaml` (workflow_dispatch)
2. Se rollback: pular build, retag no Docker Hub, POST webhook
3. Documentar procedimento no `RUNBOOK.md`

**Resultado esperado**:
- Rollback em ~3 min sem rebuild

---

### Issue 6: Health checks e verificação pós-deploy (#816)

**Objetivo**: Garantir deploy bem-sucedido automaticamente.

**Tarefas**:
1. Endpoint `/api/readyz/` com DB + Redis + migrations check
2. Endpoint `/api/version/` com tag + SHA
3. No `deploy.yaml`: aguardar + health check + version check via URL externa
4. Se falhar → rollback automático

**Resultado esperado**:
- Deploy OK: workflow verde, versão confirmada
- Deploy falho: rollback automático, workflow vermelho

---

## 4. Ordem de Execução

```
Issue 1 (Portainer Webhook)  ← Setup no Portainer + GitHub Secret
    ↓
Issue 2 (deploy.yaml)        ← Core do novo pipeline
    ↓
Issue 3 (remover Watchtower) ← Limpa compose
    ↓
Issue 4 (deprecar workflows) ← Limpa CI/CD
    ↓
Issue 5 (rollback)           ← Safety net  ⎫
    ↓                                       ⎬ Podem ser paralelas
Issue 6 (health checks)      ← Verificação ⎭
```

---

## 5. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Portainer webhook exposto | URL com token UUID no path, HTTPS via porta 9443 |
| Webhook falha silenciosamente | Verificação pós-deploy (health + version check) |
| Imagem corrompida no Docker Hub | Security gate (Trivy) impede push com HIGH/CRITICAL |
| Rollback perde migrations | Migrations são forward-only; rollback de DB é manual |
| Portainer fica offline | Fallback: Pull and Redeploy manual via UI |

---

## 6. Métricas de Sucesso

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tempo merge → deploy | ∞ (manual) | ~10 min |
| Steps manuais para deploy | 5+ (Portainer UI) | 0 (automático) |
| Workflows de deploy | 3 | 1 |
| Watchtower errors/dia | ~1440 | 0 |
| Rollback time | 15-30 min (manual) | ~3 min |
| Verificação pós-deploy | Nenhuma | Automática |
| Secrets necessários para deploy | 4+ (SSH) | 1 (webhook URL) |
| Setup necessário na VM | Usuário + chaves + NAT | Nenhum |

---

## Fontes

- [Portainer Webhooks Documentation](https://docs.portainer.io/user/docker/stacks/webhooks)
- [Automate Portainer deployment with GitHub workflows](https://medium.com/@aytronn18/automate-portainer-deployment-with-github-workflows-809e02e0650c)
- [Using Portainer and GitHub for Continuous Deployment](https://joshbuker.com/blog/using-portainer-and-github-for-continuous-deployment/)
- [Docker Docs — GitHub Actions](https://docs.docker.com/build/ci/github-actions/)
- [Best Practices CI/CD Docker & Kubernetes](https://github.com/orgs/community/discussions/184874)
