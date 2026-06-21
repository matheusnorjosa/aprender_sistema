# Dependency Guardrails (Backend + Frontend)

Este documento define os guardrails arquiteturais obrigatórios executados no CI para evitar regressão de acoplamento.

## Objetivo

- bloquear imports proibidos entre módulos de backend;
- bloquear ciclos e dependências inválidas no frontend;
- manter evidência auditável em artifact de CI.

## Backend (import-linter)

Configuração: `v2/backend/.importlinter`

Contratos ativos:
- `apps.core` não pode depender de `apps.dev_tools`;
- `config` não pode depender de `apps.dev_tools`.

> `apps.dat_ingest` foi removido (#967/#971); os guardrails restantes cobrem `apps.core` ↔ `apps.dev_tools`.

Execução local:

```bash
cd v2/backend
pip install import-linter==2.6
python scripts/run_import_linter.py
```

## Frontend (dependency-cruiser)

Configuração: `v2/frontend/.dependency-cruiser.cjs`

Regras ativas:
- sem ciclos de import no runtime (`src/**`);
- código de runtime não pode importar arquivos de teste;
- módulos internos não podem importar entrypoints (`src/App.tsx`, `src/main.tsx`).

Execução local:

```bash
cd v2/frontend
npm ci
npm run deps:check
```

Execução unificada via Make:

```bash
cd v2/infra
make architecture-guardrails
```

## CI

Workflow obrigatório:
- `.github/workflows/architecture-guardrails.yml`
- check name: `[required] architecture dependency guardrails`

Artifacts gerados:
- `architecture-backend.log`
- `architecture-frontend.log`

## Falha esperada (prova de efetividade)

O check deve falhar quando:
- um import proibido for adicionado no backend (ex.: `apps.core -> apps.dev_tools`);
- um ciclo de import for introduzido no frontend;
- um módulo de runtime importar arquivo de teste.
