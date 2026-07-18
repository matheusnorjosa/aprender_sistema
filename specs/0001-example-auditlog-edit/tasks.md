# Tasks — reabilitar AuditLog de edição de Solicitação

- **Spec ID**: 0001-example-auditlog-edit

## Pré-implementação

- [x] `requirements.md` e `design.md` coerentes com a `CONSTITUTION.md`.
- [x] Branch `test/1382-auditlog-edicao-solicitacao` a partir do `main`.
- [x] Ambiente dev no ar (Docker). **Nota**: usar `up -d --build` — a imagem `latest` de
      prod não traz `pytest`; só o build do `Dockerfile.dev` instala `requirements-dev`.

## Implementação (Red → Green → Refactor)

- [x] Investigar o skip → confirmar que `perform_update` já gera AuditLog (PR #332).
- [x] Remover `@pytest.mark.skip` e o TODO do docstring.
- [x] Reforçar asserts: `observacoes` em `changed_fields`; old/new de `local`.
- [x] Rodar o teste alvo → **2 passed**.

## Verificação

- [x] Arquivo inteiro `test_solicitacao_edit.py` → **32 passed**.
- [x] Regressão `-k "audit or Audit"` → **93 passed** (ignorando coleção pré-existente
      quebrada em `test_pr_security_url_substring.py`, não relacionada).
- [x] `black`/`isort`/`flake8` limpos no arquivo.
- [x] Diff test-only (6+/6−); sem segredos.

## Pré-PR (humano conduz)

- [x] Rebase no `main` atual (0 atrás / 1 à frente; verde reconfirmado).
- [x] Staging gate: `ALL 8 CHECKS PASSED` (rodado localmente).
- [ ] **Usuário** abre/mergeia o PR (CP-07) — pendente de decisão.

## Notas de execução

- Lição de ambiente: sem `make` no git-bash → rodar `docker compose` direto; `up` sem
  `--build` reusa imagem prod sem `pytest`.
- O skip era órfão: nenhuma mudança de produção foi necessária — a aposta do design se
  confirmou no primeiro run verde.
