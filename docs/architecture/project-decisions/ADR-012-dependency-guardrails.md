# ADR-012: Guardrails Arquiteturais de Dependência

**Status:** Accepted
**Date:** 2026-01-15
**Decider:** Matheus Norjosa

## Context

À medida que o codebase cresce (3 apps backend, 45+ páginas frontend), imports cruzados entre módulos criam acoplamento oculto. Uma mudança em `dat_ingest` poderia quebrar `core` silenciosamente.

## Decision

Guardrails automatizados no CI que bloqueiam merge:

**Backend (import-linter)**:
- `apps.core` não pode depender de `apps.dat_ingest` nem `apps.dev_tools`
- `apps.dat_ingest` não pode depender de `apps.dev_tools`
- `config` não pode depender de `apps.dat_ingest` nem `apps.dev_tools`

**Frontend (dependency-cruiser)**:
- Sem ciclos de import no runtime (`src/**`)
- Runtime não pode importar arquivos de teste
- Módulos internos não podem importar entrypoints (`App.tsx`, `main.tsx`)

## Consequences

- CI falha se import proibido for introduzido
- Artifacts gerados: `architecture-backend.log`, `architecture-frontend.log`
- Check `[required] architecture dependency guardrails` bloqueia merge
- Módulos mantêm responsabilidade clara e isolada

## References

- `docs/architecture/dependency-guardrails.md`
- `v2/backend/.importlinter`
- `v2/frontend/.dependency-cruiser.cjs`
- `.github/workflows/architecture-guardrails.yml`
