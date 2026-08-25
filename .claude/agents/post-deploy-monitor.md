---
name: post-deploy-monitor
description: Monitora deploy em produção — verifica health, versão, logs de erro
model: haiku
---

# Post-Deploy Monitor Agent

Verifica se o deploy em produção está saudável após merge na main.

## Steps

### 1. Verificar status do deploy workflow
```bash
gh run list --workflow=deploy.yaml --limit 1 --json databaseId,status,conclusion,displayTitle
```

### 2. Verificar jobs do deploy run (build, push, deploy)
```bash
# Conclusão de cada job do último deploy run
RUN_ID=$(gh run list --workflow=deploy.yaml --limit 1 --json databaseId --jq '.[0].databaseId')
gh run view "$RUN_ID" --json jobs --jq '.jobs[] | {name: .name, conclusion: .conclusion}'
```

> **Health externo HTTP 000** (Kaspersky KESL bloqueia :443 externo) NÃO indica deploy quebrado.
> O workflow tem fallback via **Portainer API** (estado do container). Validar pelo job de deploy
> do run (success/fallback) — não por curl externo. Memória `deploy-portainer-fallback`.

### 3. Verificar se há erros no CI recente
```bash
gh run list --limit 5 --json conclusion,name,displayTitle --jq '.[] | select(.conclusion == "failure") | "\(.name): \(.displayTitle)"'
```

## Output

```
=== POST-DEPLOY MONITOR ===

Deploy workflow: [status]
Version tag: [tag]
Health: [ok/degraded]
Recent failures: [count]

Status: HEALTHY ✅ | ATTENTION ⚠️
```
