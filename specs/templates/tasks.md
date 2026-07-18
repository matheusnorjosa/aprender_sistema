# Tasks — <título da mudança>

> **Em que ordem**. Checklist executável, granular, em ordem **TDD**.
> Cada passo de código vem **depois** do seu teste. Marque `[x]` ao concluir (com verde).

- **Spec ID**: NNNN-slug

## Pré-implementação

- [ ] `requirements.md` e `design.md` preenchidos e coerentes com a `CONSTITUTION.md`.
- [ ] Branch criada: `git checkout -b <tipo>/NNNN-slug` (a partir do `main` atual).
- [ ] Ambiente dev no ar (`cd v2/infra && docker compose --env-file .env.dev -f docker-compose.yml -f docker-compose.override.yml up -d --build`).

## Implementação (Red → Green → Refactor)

- [ ] **Red**: escrever teste que falha — `<arquivo::caso>`. Rodar e ver falhar.
- [ ] **Green**: código mínimo para passar. Rodar e ver verde.
- [ ] **Refactor**: limpar mantendo verde.
- [ ] (repetir por critério de aceite)

## Verificação (gate — ver CONSTITUTION § Verification gate)

- [ ] Arquivo de teste inteiro verde.
- [ ] Regressão relacionada verde.
- [ ] `black --check` / `isort --check` / `flake8` / `pyright` limpos (no container `web`).
- [ ] Cobertura ≥ 85% mantida.
- [ ] Diff contém **só** o necessário (sem arquivo a mais; segredos fora).

## Pré-PR (humano conduz)

- [ ] Rebase no `main` atual.
- [ ] Staging gate: `ALL 8 CHECKS PASSED` + evidência no corpo do PR.
- [ ] Commit convencional (`<tipo>(<escopo>): … (#issue)`); sem trailer "Claude Code".
- [ ] **Usuário** abre/mergeia o PR (CP-07). O agente para aqui e relata.

## Notas de execução

<o que foi descoberto durante a implementação; decisões; surpresas>
