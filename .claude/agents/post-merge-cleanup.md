---
name: post-merge-cleanup
description: Limpeza pós-merge — atualiza main, deleta branches locais/remotas, verifica deploy, prune
model: haiku
---

# Post-Merge Cleanup Agent

Executa limpeza completa após merge de um PR.

## Steps

### 1. Atualizar main
```bash
git checkout main
git pull origin main
```

### 2. Deletar branch local do PR mergeado
```bash
# Listar branches locais (exceto main)
git branch | grep -v "* main"

# Branches mergeadas via merge-commit (fast-forward/non-squash)
git branch --merged main | grep -v "main" | xargs -r git branch -d
```

> **Squash-merge NÃO aparece em `git branch --merged`** (a ancestry não bate; sinal
> autoritativo de stale = `PR=MERGED`, não git ancestry — memória `squash-merge-branch-cleanup`).
> Complementar checando o estado do PR de cada branch local e forçando o delete:
```bash
# Para cada branch local, ver se seu PR já foi mergeado e deletar (-D = force)
git branch --format='%(refname:short)' | grep -v "^main$" | while read br; do
  state=$(gh pr view "$br" --json state --jq '.state' 2>/dev/null)
  if [ "$state" = "MERGED" ]; then
    echo "PR de '$br' = MERGED → git branch -D $br"
    git branch -D "$br"
  fi
done

# Alternativa: listar PRs já mergeados e cruzar com branches locais
gh pr list --state merged --limit 30 --json headRefName --jq '.[].headRefName'
```

### 3. Prune branches remotas deletadas
```bash
git fetch --prune
```

### 4. Deletar branches stale não mergeadas (se existirem)
```bash
# Listar branches não mergeadas
git branch --no-merged main | grep -v "main"
# Se houver, perguntar ao usuário antes de deletar
```

### 5. Verificar graph limpo
```bash
git branch
# Esperado: apenas "* main"
```

### 6. Verificar deploy (se runtime change)
```bash
# Último deploy run
gh run list --workflow=deploy.yaml --limit 1 --json databaseId,status,conclusion,displayTitle
```

### 7. Verificar issues fechadas
```bash
# Confirmar que issues do PR foram fechadas automaticamente
# (extrair do commit message "Closes #NNN")
git log --oneline -1 | grep -oP "Closes #\d+" | while read close; do
  num=$(echo "$close" | grep -oP "\d+")
  state=$(gh issue view $num --json state --jq '.state')
  echo "#$num: $state"
done
```

## Output

```
=== POST-MERGE CLEANUP ===

Main updated: ✅
Branches deleted: N local, M remote pruned
Graph: clean (main only)
Deploy: [status]
Issues closed: #X, #Y, #Z

Done ✅
```
