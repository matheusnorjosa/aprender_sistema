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

## Validacoes

- [ ] Checks `[required]` verdes (somente gates bloqueantes)
- [ ] Checks `[info]` revisados quando falharem (sem bloquear merge)
- [ ] Sem alteracoes fora do escopo combinado
