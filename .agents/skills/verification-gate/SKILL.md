---
name: verification-gate
description: Verify before claiming success. Use when about to say something works/is done, after implementing a feature, after a bugfix, or before pushing — run the proof command and confirm output first.
---

# Verification Gate

Verificação obrigatória antes de qualquer claim de sucesso. **NUNCA** afirme que algo funciona sem evidência fresca.

> "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE"

## O Processo Gate (5 Passos)

Antes de afirmar status, "pronto" ou satisfação:

1. **IDENTIFICAR** — qual comando prova sua claim? (tabela abaixo)
2. **RODAR** — execute completamente e freshly (não use cache mental).
3. **LER** — leia o output COMPLETO e os exit codes.
4. **VERIFICAR** — o output suporta a claim? (tabela de evidência abaixo)
5. **CLAIM** — só APÓS confirmação, afirme sucesso.

### Comando por tipo de claim (v2 = Docker-only, CP-01)

| Claim | Comando | Evidência necessária |
|-------|---------|----------------------|
| "Testes passam" | `docker exec aprender_dev-web-1 pytest apps/core/tests/ -v` | `passed` + exit code 0 |
| "Sem erros pyright" | `cd v2/backend && pyright apps/core config` | `0 errors` no output |
| "Build frontend OK" | `cd v2/frontend && npm run build` | exit code 0, sem erros |
| "Lint passa" | `cd v2/frontend && npm run lint` | exit code 0 |
| "Migration OK" | `docker exec aprender_dev-web-1 python manage.py migrate --check` | exit code 0 |
| "Bug corrigido" | o teste que falhava agora passa | `passed` no teste-alvo |
| "CI passou" | `gh pr checks PR_NUMBER` | todos os checks verdes |

## Red Flags — Linguagem Proibida antes de verificar

"should work" / "deve funcionar" · "probably" / "provavelmente" ·
"seems fine" / "parece ok" · "I think" / "acho que" ·
"Done!" / "Pronto!" (sem evidência) · "Great!" / "Ótimo!" (sem rodar teste).

## Checklist por tipo de tarefa

**Após implementar feature:**
```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/test_FEATURE.py -v
cd v2/backend && pyright apps/core config
cd v2/frontend && npm run lint   # se tocou frontend
```

**Após fix de bug** (reproduzir → corrigir → confirmar):
```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/test_BUG.py -x   # deve FALHAR antes do fix
docker exec aprender_dev-web-1 pytest apps/core/tests/test_BUG.py -v   # deve PASSAR depois
```

**Antes de push** (o CI roda os mesmos gates — rode local primeiro):
```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/ -v
cd v2/backend && pyright apps/core config
cd v2/frontend && npm run lint && npm run build
```

**Após import (export-contract / DRF):** ver `reference/import-verification.md`.

## Exemplo: errado vs. certo

❌ ERRADO:
```
Implementei a feature de bloqueio parcial. Os testes devem passar agora.
```

✅ CORRETO:
```
Implementei a feature de bloqueio parcial.

$ docker exec aprender_dev-web-1 pytest apps/core/tests/test_availability_service.py -v
15 passed in 2.3s
$ cd v2/backend && pyright apps/core config
0 errors, 0 warnings

Testes passam e type check OK.
```
