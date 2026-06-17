# Contribuindo — Aprender Sistema v2

## Modelo de branches (trunk-based)

O projeto é **trunk-based**: `main` é a única branch de longa duração e a base de
integração. Feature branches curtas no padrão `type/nome` (ex.: `feat/gcal-sync`,
`fix/availability-buffer`) saem de `main` e voltam por **Pull Request com squash-merge**
(CP-05/CP-06). **Não há branch `develop`** nem fluxo gitflow. Como `main` é a única base de
PR, gatear `pull_request` → `main` cobre todo o fluxo de integração — não existe branch
intermediária ungated. **Merge na `main` dispara deploy de produção**, então cada PR passa
pela suíte completa de CI antes do merge.

## Convenções

- **Commits**: Conventional Commits — `type(scope): mensagem` (`feat`, `fix`, `chore`,
  `docs`, `test`, `refactor`, `perf`, `ci`, `security`).
- **PRs**: base `main`, CI verde, squash-and-merge. Mudanças com impacto em runtime exigem
  evidência do staging gate no corpo do PR (ver `v2/infra` `make staging-full`).

## Gating de CI

Os workflows disparam em `push` para `main` e `pull_request` → `main`. O prefixo no nome do
job indica a criticidade:

- `[required]` — check obrigatório no ruleset; **bloqueia o merge** se falhar.
- `[info]` — informativo (ex.: build de documentação, e2e journeys, lighthouse); roda e
  reporta, mas não bloqueia.
