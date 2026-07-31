# Contribuindo — Aprender Sistema v2

## Modelo de branches (trunk-based)

O projeto é **trunk-based**: `main` é a única branch de longa duração e a base de
integração. Feature branches curtas no padrão `type/nome` (ex.: `feat/gcal-sync`,
`fix/availability-buffer`) saem de `main` e voltam por **Pull Request com squash-merge**
(CP-05/CP-06). **Não há branch `develop`** nem fluxo gitflow. Como `main` é a única base de
PR, gatear `pull_request` → `main` cobre todo o fluxo de integração — não existe branch
intermediária ungated. **Merge na `main` NÃO deploya** (modelo pull-based,
[ADR-018](docs/architecture/project-decisions/ADR-018-pull-based-deploy.md)): ele dispara
build + scan + push + assinatura das imagens e a tag imutável `vYYYY.MM.DD-<sha7>`.
Produção só muda por **promoção deliberada** (`promote.yml`, gated no GitHub Environment
`production`), aplicada pelo agente `aprender-deployer` na VM01. Ainda assim cada PR passa
pela suíte completa de CI antes do merge: como **não há staging remoto**, os gates de PR
mais o staging gate local são a única rede de proteção antes de uma promoção.

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
