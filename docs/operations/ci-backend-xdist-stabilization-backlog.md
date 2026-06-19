# CI Backend xdist Stabilization Backlog

Lista rastreavel de testes/assinaturas nao paralelizaveis identificados na trilha canary.

Ultima atualizacao: 2026-06-19

## Politica de backlog

- Qualquer teste ou assinatura recorrente (`>=2` ocorrencias no canary) precisa de issue vinculada ao epic `#677`.
- Cada item precisa ter owner e status explicitos.
- Item so pode ser marcado como `resolved` com evidencia de execucao (runner ou canary) apos a correcao.

## Itens de estabilizacao

| Issue | Escopo | Owner | Status | Evidencia | Observacoes |
|---|---|---|---|---|---|
| #681 | `test_config_validation` com `SessionInterrupted` em xdist | @matheusnorjosa | resolved | PR #685 (mergeado) | Troca para `APIClient` + `force_authenticate` no modulo de config API |
| #682 | Ruido de `duplicate key / unique constraint` intencional em testes de unicidade | @matheusnorjosa | resolved | PR #686 (mergeado) | Testes migrados para validacao por `full_clean()`/`ValidationError` |
| #1402 | ~537 testes falhando sob xdist (403 PERMISSION_DENIED em cascata) | @matheusnorjosa | resolved | PR #1450 (`64dfeb4`); canary 0/4 em 2 runs consecutivos | Causa: testes `@pytest.mark.django_db(transaction=True)` TRUNCAM o DB no teardown, apagando o seed de RBAC (grupos x capability); Django reordena `TransactionTestCase` pro fim (serial ok), pytest-xdist NAO -> truncate no meio do worker envenena os seguintes. Fix: fixture autouse `ensure_rbac_seed` (conftest raiz) re-semeia idempotente pos-truncate + isolamento de cache/sessao Redis por worker. |

## Promocao ao gate (#1403)

`-n auto --dist loadscope` promovido aos jobs `backend-tests-core`/`backend-tests-ingest-devtools`
(`ci.yaml`) em 2026-06-19 apos #1402 estabilizar a suite. Decisao de **fast-track** (em vez dos 14 dias de
canary do criterio formal): o fix e **deterministico** (re-seed garante o seed presente, nao e reducao
probabilistica de flaky) e a canary deu **0/4 celulas em 2 runs consecutivos**. Repo single-dev. Regressao
futura (teste novo xdist-inseguro) passa a ser barrada pelo proprio gate. Ganho: ~15min -> ~5min.

## Proximo gatilho de acao

- Se o canary apontar nova recorrencia (`>=2`), abrir issue filha de `#677` com:
  - teste/assinatura
  - owner
  - plano de mitigacao
  - criterio de aceite
