# Plano: Simplificação do Pipeline de Deploy

**Data**: 2026-03-09 (rev.3 — ajustes pós-revisão)
**Epic**: Simplificação do Pipeline CI/CD
**Status**: Planejado
**Estratégia de deploy**: Portainer REST API (CE compatível, sem webhook BE)

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
| P2 | `GITHUB_REF_NAME` colidia com built-in do GitHub Actions | Imagens nunca publicadas no Docker Hub | Run 22860845995 (corrigido PR #810) |
| P3 | Nenhum deploy automático no merge | Cada deploy requer disparo manual do `release.yaml` | workflow_dispatch obrigatório |
| P4 | `PRODUCTION_DEPLOY_COMMAND` não está configurado | Step `Execute deploy command` falharia se chegasse lá | Secret/var vazio |
| P5 | `dockerhub-rebuild.yml` duplica lógica do `release.yaml` | 2 workflows fazem build+push, com lógicas diferentes | Manutenção duplicada |
| P6 | Watchtower como modelo de deploy | Polling a cada 5min, requer Docker Hub token no compose, container extra | Arquitetura frágil |
| P7 | `stack.env` gerenciado manualmente no Portainer | Propenso a erros (ex: `#` truncando senha) | Incidente DB_PASSWORD |
| P8 | Sem rollback automatizado | Se deploy falhar, rollback é manual via Portainer | Sem safety net |

### 1.3 Workflows existentes

| Workflow | Trigger | Função | Ação |
|----------|---------|--------|------|
| `ci.yaml` | push/PR | Testes, lint, coverage | ✅ Manter |
| `release.yaml` | workflow_dispatch | Build + push + deploy | ❌ Deprecar |
| `dockerhub-rebuild.yml` | cron semanal + dispatch | Rebuild security + push | ❌ Deprecar |
| `security-scan.yml` | push/PR/cron | Safety, Trivy, Bandit, Gitleaks, TruffleHog | ✅ Manter |
| `strict-security-headers.yml` | cron diário | Playwright headers check | ✅ Manter |
| `dependency-review-scorecard.yml` | PR | Dependency review + OpenSSF | ✅ Manter |
| `docs.yml` | - | Documentação | ✅ Manter |
| `frontend-ci.yml` | - | Frontend CI | ✅ Manter |

### 1.4 Infraestrutura de produção

```
VM01_App (172.17.0.2)     VM02_Banco (172.17.0.3)     VM03_Redis (172.17.0.4)
┌─────────────────────┐   ┌──────────────────┐         ┌──────────────┐
│ Portainer CE (9443)  │   │ PostgreSQL 15    │         │ Redis 7      │
│ NPM (80/443/88)      │   │ (porta 5432)     │         │ (porta 6379) │
│ ┌─────────────────┐ │   └──────────────────┘         └──────────────┘
│ │ Stack Aprender  │ │
│ │ web (8000)      │ │   IP Externo compartilhado: 45.174.67.141
│ │ worker          │ │   NAT: 80,88,443,9443,9444
│ │ beat            │ │
│ │ frontend (81)   │ │
│ │ watchtower ❌   │ │
│ └─────────────────┘ │
└─────────────────────┘
```

### 1.5 Restrição crítica: Portainer CE

Webhooks de stack são **exclusivos do Portainer Business Edition** (pago).
Fonte: [docs.portainer.io/user/docker/stacks/webhooks](https://docs.portainer.io/user/docker/stacks/webhooks)

**Solução**: Usar a API REST do Portainer CE (`PUT /api/stacks/{id}`) com
a GitHub Action [portainer-stack-redeploy-action](https://github.com/wirgen/portainer-stack-redeploy-action),
que é compatível com CE e faz pull + redeploy via API autenticada.

---

## 2. Arquitetura Proposta

### 2.1 Novo fluxo (com gate de promoção)

```
código → PR → CI (ci.yaml) → merge main
                                 ↓
                    [AUTOMÁTICO: deploy.yaml — modo staging]
                                 ↓
                    build imagens → push Docker Hub (tag imutável)
                                 ↓
                    Portainer API → pull tag + redeploy staging
                                 ↓
                    health check + version check
                                 ↓
                    ✅ Staging deployado
                                 ↓
                    [MANUAL: deploy.yaml — modo produção]
                    (workflow_dispatch com promotion_tag validado)
                                 ↓
                    Portainer API → pull tag imutável + redeploy produção
                                 ↓
                    health check + version check
                                 ↓
                    ✅ Produção deployada
```

### 2.2 Mudanças principais

| De | Para |
|----|------|
| Watchtower (polling 5min, quebrado) | Portainer REST API (CE compatível) |
| Disparo manual para tudo | Auto staging + promoção manual para prod |
| 3 workflows de deploy | 1 workflow (`deploy.yaml`) |
| `DEPLOY_COMMAND` genérico | Portainer API com token + stack ID |
| Rollback por retag `:latest` | Rollback por tag imutável |
| `containrrr/watchtower` | Removido do compose |
| Sem gate staging→prod | Gate de promoção obrigatório |

### 2.3 Princípios

1. **Build once, deploy everywhere**: CI builda, ambientes só fazem `docker pull`
2. **Tags imutáveis**: Cada deploy usa tag única (`v2026.03.09-abc1234`), nunca retag
3. **Gate de promoção**: Staging é automático, produção exige promoção manual com tag validada
4. **Deploy via Portainer API**: `PUT /api/stacks/{id}` com `pullImage=true` (CE compatível)
5. **Verificação pós-deploy**: Health check + version check automáticos
6. **Rollback por tag**: Re-deploy de tag anterior (imagem já existe no Docker Hub)
7. **Supply chain mantido**: SBOM + Trivy + provenance + workflows de segurança intactos
8. **Transição segura**: Watchtower removido somente após 2+ deploys bem-sucedidos via API

### 2.4 Por que Portainer API e não SSH

| Aspecto | SSH | Portainer API |
|---------|-----|---------------|
| Setup na VM | Criar usuário, chaves, NAT porta 22 | ✅ Nenhum (já roda) |
| GitHub Secrets | 4 (key, host, user, port) | ✅ 3 (URL, token, stack_id) |
| Portas NAT | Abrir porta 22 | ✅ Porta 9443 já aberta |
| Compatibilidade | Qualquer Linux | ✅ Portainer CE (free) |
| Complexidade | Média | ✅ Baixa |
| GitHub Action | appleboy/ssh-action | ✅ wirgen/portainer-stack-redeploy-action |

---

## 3. Plano de Execução (6 Issues)

### Issue 1: Configurar Portainer API e GitHub Secrets (#811)

**Objetivo**: Preparar acesso à API REST do Portainer CE para deploy automatizado.

**Tarefas**:

1. Gerar Access Token no Portainer (Account Settings → Access Tokens)
2. Identificar stack ID e endpoint ID no Portainer
3. Configurar GitHub Secrets: `PORTAINER_URL`, `PORTAINER_ACCESS_TOKEN`, `PORTAINER_STACK_ID`, `PORTAINER_ENDPOINT_ID`
4. Testar chamada API: `PUT /api/stacks/{id}?pullImage=true&endpointId={eid}`
5. Confirmar que redeploy funciona via API

**Critério de aceite**: Chamada API comprovadamente faz pull + redeploy do stack real.

---

### Issue 2: Criar workflow `deploy.yaml` unificado (#812)

**Objetivo**: Workflow único com dois modos — staging automático + produção por promoção.

**Tarefas**:

1. Criar `deploy.yaml` com triggers:
   - `push main` → deploy **staging** automático (build + push tag imutável + API redeploy)
   - `workflow_dispatch` com `promotion_tag` → deploy **produção** (sem rebuild, API redeploy com tag validada)
   - `workflow_dispatch` com `rollback_tag` → rollback (sem rebuild, API redeploy com tag anterior)
2. Steps staging: build → Trivy gate → push tag imutável → Portainer API → health check
3. Steps produção: validar tag existe → Portainer API com `IMAGE_TAG` → health check
4. Manter SBOM + provenance + GitHub Release
5. Concurrency group por environment

**Resultado esperado**: Merge → staging em ~10 min. Promoção → produção em ~3 min.

---

### Issue 3: Remover Watchtower do compose de produção (#813)

**Pré-condição**: Pelo menos 2 deploys bem-sucedidos via Portainer API (#812).

**Tarefas**:

1. Remover serviço `watchtower` de `docker-compose.prod.yml`
2. Remover labels `com.centurylinklabs.watchtower.enable` dos serviços
3. Remover variáveis `WATCHTOWER_TOKEN` do compose/stack.env
4. Remover porta 8080 do NAT
5. Atualizar documentação

**Critério de aceite**: Stack funciona com 4 containers, zero erros, deploy via API continua operacional.

---

### Issue 4: Deprecar `release.yaml` e `dockerhub-rebuild.yml` (#814)

**Escopo**: Deprecar **apenas** esses dois workflows. Manter intactos:

- `security-scan.yml` (Safety, Trivy, Bandit, Gitleaks, TruffleHog)
- `strict-security-headers.yml` (Playwright headers)
- `dependency-review-scorecard.yml` (Dependency review + OpenSSF)
- Todos os demais workflows existentes

**Tarefas**:

1. Remover cron do `dockerhub-rebuild.yml`, adicionar deprecation notice
2. Verificar se scan semanal de containers (Trivy) está coberto por `security-scan.yml`
3. Se não estiver → migrar o job de Trivy container scan para `security-scan.yml`
4. Remover `release.yaml` após confirmar cobertura total pelo `deploy.yaml`
5. Atualizar docs

---

### Issue 5: Rollback por tag imutável (#815)

**Mecanismo**: Rollback usa tag imutável existente — **nunca retag de `:latest`**.

**Tarefas**:

1. Input `rollback_tag` no `deploy.yaml` (workflow_dispatch)
2. Se rollback_tag fornecido:
   - Validar que tag existe no Docker Hub (`docker manifest inspect`)
   - Chamar Portainer API com `IMAGE_TAG=<rollback_tag>` como env var
   - Portainer faz pull da tag específica + redeploy
3. Manter histórico de deploys como artifact
4. Documentar procedimento no `RUNBOOK.md`

**Resultado esperado**: Rollback em ~3 min sem rebuild, sem perda de imutabilidade, sem corrida entre deploys.

---

### Issue 6: Health checks — alinhar contrato com implementação (#816)

**Estado atual** (`views_health.py`):

| Check | Implementação | Status HTTP |
|-------|---------------|-------------|
| DB connection | ✅ Verifica | 503 se falha (bloqueante) |
| Redis connection | ✅ Verifica | 200 com warning (não bloqueante) |
| Migrations | ❌ Não verifica | — |

**Tarefas**:

1. **Decidir contrato do readyz**:
   - DB: bloqueante (503) ✅ manter
   - Redis: decidir se deve ser bloqueante ou warning (documentar decisão)
   - Migrations: avaliar se adicionar check (custo vs benefício)
2. **Documentar contrato** no endpoint e no plano
3. **Endpoint `/api/version/`**: já existe como `versionz` — confirmar que retorna tag + SHA do `BUILD_INFO.json`
4. **No `deploy.yaml`**: health check via URL externa com retry (12x, 10s intervalo)
5. **Definir o que bloqueia deploy**: quais falhas do readyz impedem marcar deploy como sucesso
6. **Configurar GitHub Variables**: `PRODUCTION_HEALTHCHECK_URL`, `STAGING_HEALTHCHECK_URL`

---

## 4. Ordem de Execução

```
Issue 1 (Portainer API setup)    ← Pré-requisito para tudo
    ↓
Issue 6 (health check contrato) ← Definir antes de implementar deploy
    ↓
Issue 2 (deploy.yaml)           ← Core do novo pipeline
    ↓
Issue 3 (remover Watchtower)    ← Após 2+ deploys bem-sucedidos via API
    ↓
Issue 4 (deprecar workflows)    ← Após confirmar cobertura total
    ↓
Issue 5 (rollback)              ← Safety net (pode ser paralela com #3/#4)
```

**Nota**: Issue 6 foi antecipada — o contrato do health check precisa estar definido
antes de implementar a verificação pós-deploy no `deploy.yaml`.

---

## 5. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Portainer API indisponível | Fallback: Pull and Redeploy manual via UI |
| Token de API expira/revoga | Monitorar via falha do workflow; regenerar token |
| Corrida entre deploys | Concurrency group no workflow (um deploy por vez) |
| Imagem corrompida | Security gate (Trivy) impede push com HIGH/CRITICAL |
| Rollback perde migrations | Migrations forward-only; rollback de DB é manual |
| Perda de cobertura de segurança | Workflows de segurança mantidos intactos (#814) |
| Downtime na transição | Watchtower já está quebrado (zero risco); remoção após validação |

---

## 6. Métricas de Sucesso

| Métrica | Antes | Depois |
|---------|-------|--------|
| Tempo merge → staging | ∞ (manual) | ~10 min (automático) |
| Tempo staging → produção | ∞ (manual) | ~3 min (promoção manual) |
| Steps manuais para staging | 5+ | 0 |
| Steps manuais para produção | 5+ | 1 (workflow_dispatch) |
| Workflows de deploy | 3 | 1 |
| Watchtower errors/dia | ~1440 | 0 |
| Rollback time | 15-30 min | ~3 min |
| Verificação pós-deploy | Nenhuma | Automática |
| Imutabilidade de tags | Não garantida | Garantida |
| Gate staging→prod | Nenhum | Obrigatório |

---

## Fontes

- [Portainer Webhooks — Business Edition only](https://docs.portainer.io/user/docker/stacks/webhooks)
- [Portainer API examples (CE compatível)](https://docs.portainer.io/api/examples)
- [portainer-stack-redeploy-action (CE)](https://github.com/wirgen/portainer-stack-redeploy-action)
- [portainer-stack-webhook (free alternative)](https://github.com/aklinker1/portainer-stack-webhook)
- [Docker Docs — GitHub Actions](https://docs.docker.com/build/ci/github-actions/)
- [Best Practices CI/CD Docker & Kubernetes](https://github.com/orgs/community/discussions/184874)
