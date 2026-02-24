# CI Check Policy

Esta política define quais checks de CI bloqueiam merge em `main` e quais são apenas informativos.

## Convenção de nomes

- `"[required] ..."`: check bloqueante de merge.
- `"[info] ..."`: check informativo, não bloqueia merge.
- `"[ops] ..."`: rotina operacional (manual/schedule), fora do gate de PR.

## Checks bloqueantes (gate de PR)

Estes checks devem ficar obrigatórios no ruleset `Protect main`:

- `[required] tests`
- `[required] lint`
- `[required] build/lint do frontend`
- `[required] checklist tests (meta, a11y, security)`
- `[required] dependency review`
- `[required] Python Dependencies`
- `[required] Frontend Dependencies`
- `[required] Container Scan`
- `[required] Secret Detection`

## Checks informativos

Estes checks não bloqueiam merge:

- `[info] lighthouse CI`
- `[info] openssf scorecard`

## Checks operacionais

Executados por `schedule` ou `workflow_dispatch`:

- `[ops] strict security headers (staging/prod)`

## Regras de governança

- Todo novo check de PR deve ser classificado como `required` ou `info` no próprio nome.
- Só checks `required` entram no ruleset.
- Workflow que publica check `required` não deve usar `paths` no gatilho de `pull_request`.
- Checks `info` podem usar `continue-on-error`, com artifact/log para análise posterior.
- Não usar runners `self-hosted` nos gates de PR; manter `ubuntu-latest` hospedado pelo GitHub.
