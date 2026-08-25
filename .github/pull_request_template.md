## Resumo

<!-- Descreva objetivamente o que mudou e por que -->

## Checklist Tecnico (Code Review Expert - Slim)

- [ ] Arquitetura e SOLID: mudancas mantiveram coesao e responsabilidade clara
- [ ] Seguranca: sem vazamento de segredo, sem novos vetores obvios de injecao/XSS/SSRF
- [ ] Performance: sem regressao relevante (render, queries, loops, payload, N+1)
- [ ] Tratamento de erros: falhas tratadas com mensagem/fluxo previsivel
- [ ] Condicoes de fronteira: nulos, lista vazia e limites numericos cobertos

## Workflow (Superpowers - Parcial)

- [ ] Escopo definido em ate 5 passos objetivos antes da implementacao
- [ ] Testes criados/ajustados para comportamento novo ou corrigido
- [ ] Evidencias anexadas (logs, screenshots, outputs de teste) quando aplicavel

## Staging Gate

<!-- Obrigatorio para PRs com impacto em runtime (v2/backend, v2/frontend, v2/infra). -->
- [ ] `make staging-full` executado com sucesso (8/8 PASS)
- [ ] Evidencia anexada no PR (trecho de log contendo "ALL 8 CHECKS PASSED")

### Evidencia Staging Gate (obrigatorio para merge)

```text
ALL 8 CHECKS PASSED
```

## Documentacao viva

<!-- Auditoria de 2026-08-24: 92,9% dos commits `fix(...)` nao tocam nenhum .md,
     e 39 issues fechadas seguem descritas como abertas na doc. O job
     [required] docs quality aponta o que este PR afeta. -->

- [ ] Se o PR resolve uma issue, a doc que a descreve foi atualizada
- [ ] Se o PR toca arquivo listado em `sources_of_truth` de uma spec, a spec foi
      revisada (ou o `last_verified` dela renovado)

Quando um documento apontado pelo gate **nao** for afetado, declare aqui — a
justificativa fica registrada e revisavel, em vez de tacita:

<!-- doc-nao-afetada: caminho/do/doc.md — por que nao afeta -->

## Validacoes

- [ ] Checks `[required]` verdes (somente gates bloqueantes)
- [ ] Checks `[info]` revisados quando falharem (sem bloquear merge)
- [ ] Sem alteracoes fora do escopo combinado
