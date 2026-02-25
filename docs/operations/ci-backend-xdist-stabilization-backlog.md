# CI Backend xdist Stabilization Backlog

Lista rastreavel de testes/assinaturas nao paralelizaveis identificados na trilha canary.

Ultima atualizacao: 2026-02-25

## Politica de backlog

- Qualquer teste ou assinatura recorrente (`>=2` ocorrencias no canary) precisa de issue vinculada ao epic `#677`.
- Cada item precisa ter owner e status explicitos.
- Item so pode ser marcado como `resolved` com evidencia de execucao (runner ou canary) apos a correcao.

## Itens de estabilizacao

| Issue | Escopo | Owner | Status | Evidencia | Observacoes |
|---|---|---|---|---|---|
| #681 | `test_config_validation` com `SessionInterrupted` em xdist | @matheusnorjosa | resolved | PR #685 (mergeado) | Troca para `APIClient` + `force_authenticate` no modulo de config API |
| #682 | Ruido de `duplicate key / unique constraint` intencional em testes de unicidade | @matheusnorjosa | resolved | PR #686 (mergeado) | Testes migrados para validacao por `full_clean()`/`ValidationError` |

## Proximo gatilho de acao

- Se o canary apontar nova recorrencia (`>=2`), abrir issue filha de `#677` com:
  - teste/assinatura
  - owner
  - plano de mitigacao
  - criterio de aceite
