# CI Backend xdist Canary (non-blocking)

Este fluxo cria uma trilha de experimento para `pytest-xdist` sem alterar os gates obrigatorios de PR.

## Workflow

Arquivo: `.github/workflows/backend-xdist-canary.yml`

Gatilhos:
- `schedule` diario
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

## Criterio formal para promocao ao caminho obrigatorio

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
