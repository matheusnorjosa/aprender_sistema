# CI Security Checks

Este guia explica os checks de segurança adicionados para PRs em `main`.

## Dependency Review (bloqueante)

Check: `dependency review`

Objetivo:
- Bloquear introdução de dependências com vulnerabilidades **HIGH/CRITICAL** no momento do PR.

Comportamento:
- Se o PR introduzir vulnerabilidade alta/crítica em dependências, o check falha.
- O workflow publica um resumo no PR com o resultado da análise.

Ação esperada quando falhar:
- Atualizar/remover dependência vulnerável no próprio PR.
- Se for dependência transitiva, atualizar o pacote raiz que a introduz.

## OpenSSF Scorecard (informativo inicial)

Check: `openssf scorecard (informativo)`

Objetivo:
- Medir postura de segurança do repositório sem bloquear merge nesta fase inicial.

Comportamento:
- O check roda automaticamente em PRs internos.
- Está em modo **informativo** (`continue-on-error`), então não bloqueia merge.
- O resultado é publicado como artifact: `openssf-scorecard-results`.

Ação recomendada:
- Monitorar tendência do score ao longo do tempo.
- Priorizar melhorias com pior pontuação antes de tornar esse check bloqueante.
