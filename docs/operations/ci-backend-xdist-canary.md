# CI Backend xdist Canary (non-blocking)

Este fluxo cria uma trilha de experimento para `pytest-xdist` sem alterar os gates obrigatorios de PR.

> **Estado atual: a promocao ja aconteceu.** Desde 2026-06-19 (#1403) o gate obrigatorio
> roda `-n auto --dist loadscope` (`ci.yaml:231` e `ci.yaml:253`). A canary deixou de ser
> um experimento pre-promocao e passou a ser **tripwire de regressao**: pega teste novo
> xdist-inseguro em combinacoes que o gate nao exercita. Os criterios formais abaixo ficam
> como registro do processo que autorizou a promocao (que foi por fast-track — ver o
> [backlog de estabilizacao](ci-backend-xdist-stabilization-backlog.md)).

## Workflow

Arquivo: `.github/workflows/backend-xdist-canary.yml`

Gatilhos:
- `schedule` **semanal** (segunda, 10:20 UTC) — era diario ate a estabilizacao consolidar
- `workflow_dispatch` (manual)
- `push` em `main` para mudancas no proprio workflow/script/doc da trilha

Importante:
- Nao roda em `pull_request`.
- Nao publica checks `[required]`.
- Nao bloqueia merge em `main`.

## Matriz de experimento

Cada execucao roda a combinacao:
- workers: `2`, `auto`
- dist: `loadscope`, `loadfile`

## Evidencias publicadas

Artifacts por combinacao:
- `xdist-canary-<workers>w-<dist>`
- Conteudo: log pytest, junit xml, metadata da execucao

Artifact consolidado:
- `xdist-canary-report`
- Conteudo: `xdist-canary-report.json` e `xdist-canary-report.md`

O relatorio consolidado inclui:
- testes que falharam
- assinaturas de erro
- frequencia de reincidencia por teste/assinatura

## Backlog de estabilizacao

Regra de triagem:
- teste/assinatura com reincidencia em `2+` execucoes precisa ter issue de estabilizacao vinculada ao epic da fase (`#677`).
- backlog com owner/status: [CI Backend xdist Stabilization Backlog](ci-backend-xdist-stabilization-backlog.md)

## Trilha de evidencia (14 dias) — historico

> Registro do processo original. O criterio de 14 dias **nao** foi o caminho usado: a
> promocao de 2026-06-19 foi por fast-track (fix deterministico + canary 0/4 em 2 runs).



- O job `[ops] backend xdist canary summary` publica:
  - artifact consolidado (`xdist-canary-report`)
  - resumo no `GITHUB_STEP_SUMMARY`
  - snapshot em comentario na issue `#677`
- Esses snapshots formam a trilha objetiva para o criterio de 14 dias antes de qualquer promocao para gate obrigatorio.

## Criterio formal para promocao ao caminho obrigatorio — historico

> Ja cumprido/dispensado em 2026-06-19. Mantido como referencia para uma eventual
> proxima mudanca de modo do gate (ex.: trocar `loadscope` por `loadfile`).

Promover `xdist` para gate obrigatorio so quando TODOS os criterios abaixo forem atendidos:

1. Evidencia minima de 14 dias corridos de canary (schedule diario) com dados validos.
2. Taxa de sucesso >= 95% considerando todas as combinacoes da matriz no periodo.
3. Nenhuma assinatura de erro recorrente (`>= 2` ocorrencias) sem issue de mitigacao aberta e com status atualizado.
4. Nenhum teste recorrente nao paralelizavel (`>= 2` ocorrencias) sem owner definido no backlog.
5. Dois dry-runs consecutivos em branch de experimento, reproduzindo o modo candidato do gate obrigatorio, sem falhas.
6. Decisao registrada em issue/PR especifico antes de alterar `.github/workflows/ci.yaml`.

## Rollback

Se a trilha canary gerar ruido operacional, desabilitar o workflow `backend-xdist-canary.yml`.

Rollback da trilha canary nao afeta os checks obrigatorios atuais.
