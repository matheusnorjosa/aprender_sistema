# Verification Gate

Verificação obrigatória antes de qualquer claim de sucesso. **NUNCA** afirme que algo funciona sem evidência.

## Regra de Ferro

> "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"

Você DEVE executar comandos de verificação e confirmar output ANTES de afirmar sucesso.

## O Processo Gate (5 Passos)

Antes de afirmar status ou satisfação:

### 1. IDENTIFICAR
Qual comando prova sua claim?

```bash
# Exemplos por tipo de claim
Testes passam:     python manage.py test
Pyright passa:     npx pyright apps/core
Build funciona:    npm run build
Lint passa:        npm run lint
Migration OK:      python manage.py migrate --check
```

### 2. RODAR
Execute completamente e freshly (não use cache mental).

### 3. LER
Leia output COMPLETO e exit codes.

### 4. VERIFICAR
O output suporta sua claim?

| Claim | Evidência Necessária |
|-------|---------------------|
| "Testes passam" | `OK` ou `passed` + exit code 0 |
| "Sem erros pyright" | `0 errors` no output |
| "Build OK" | Exit code 0, sem erros |
| "Bug corrigido" | Teste que falhava agora passa |

### 5. CLAIM
Somente APÓS confirmação, afirme sucesso.

## Red Flags - Linguagem Proibida

**NUNCA use antes de verificar:**

- "should work" / "deve funcionar"
- "probably" / "provavelmente"
- "seems fine" / "parece ok"
- "I think" / "acho que"
- "Done!" / "Pronto!" (sem evidência)
- "Great!" / "Ótimo!" (sem rodar teste)

## Checklist por Tipo de Tarefa

### Após Implementar Feature
```bash
# 1. Testes passam
python manage.py test apps.core.tests.test_FEATURE

# 2. Type check passa
npx pyright apps/core/FILE.py

# 3. Lint passa (se frontend)
npm run lint
```

### Após Fix de Bug
```bash
# 1. Reproduzir bug (deve falhar)
python manage.py test apps.core.tests.test_BUG --failfast

# 2. Aplicar fix

# 3. Teste passa
python manage.py test apps.core.tests.test_BUG
```

### Após Criar PR
```bash
# 1. CI passou
gh pr checks PR_NUMBER

# 2. Sem conflitos
gh pr view PR_NUMBER --json mergeable
```

### Após ETL
```bash
# 1. Dry-run sem erros
python manage.py etl_COMMAND --dry-run

# 2. Contagens corretas
python manage.py etl_COMMAND --dry-run | grep -E "created|updated|skipped"
```

## Exemplos

### ❌ ERRADO
```
Implementei a feature de bloqueio parcial.
Os testes devem passar agora.
```

### ✅ CORRETO
```
Implementei a feature de bloqueio parcial.

Verificação:
$ python manage.py test apps.core.tests.test_availability
...
Ran 15 tests in 2.3s
OK

$ npx pyright apps/core/services/availability.py
0 errors, 0 warnings

Testes passam e type check OK.
```

## Integração com CI

O CI do projeto já implementa verification gate:
- Pyright deve passar
- Testes devem passar
- Build frontend deve passar

**Rodar localmente ANTES de push:**
```bash
# Backend
cd v2/backend && python manage.py test && npx pyright apps/core

# Frontend
cd v2/frontend && npm run lint && npm run build
```

## Consequências de Pular

Pular verificação já causou:
- PRs com testes falhando
- Deploys com bugs
- Features incompletas em produção
- Retrabalho e perda de confiança

**Esta regra não tem exceções.**
