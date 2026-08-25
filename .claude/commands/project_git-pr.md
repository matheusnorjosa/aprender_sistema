---
allowed-tools: Bash(git add:*), Bash(git commit:*), Bash(git status:*)
description: Prepare a clean commit and PR description
---

Componha uma mensagem de **conventional commit** (CP-06: `type(scope): mensagem`) resumindo a mudança e prepare a descrição da PR com: **contexto, abordagem, riscos e evidência de teste**.

Regras obrigatórias (AS v2):
- **NUNCA** incluir "Generated with Claude Code" nem co-author do Claude no commit ou na PR.
- Base `main`; **nunca** push direto na main (CP-07, enforced por hook) — abrir PR + squash merge.
- Se a mudança toca backend (`v2/backend/`, `v2/infra/`, `.github/workflows/ci.yaml`, `_backend-test.yml`),
  o corpo da PR PRECISA dos 3 marcadores **literais** do staging gate (sem acento):
  - `make staging-full executado com sucesso (8/8 PASS)`
  - `Evidencia anexada no PR`
  - `ALL 8 CHECKS PASSED`
- Docs-only / `.claude` / `scripts/` não disparam o staging gate (pular os marcadores).

(think)
