# Phase 01 — Auth, RBAC, Sessions

Date: 2026-02-04
Scope: v2 only
Status: Completed

## Explored
- v2/docs/RBAC_COMPLETO.md
- v2/backend/apps/core/views_auth.py
- v2/backend/apps/core/views_basic.py
- v2/backend/apps/core/permissions.py
- v2/backend/apps/dev_tools/management/commands/seed_rbac.py
- v2/backend/apps/core/migrations/0042_rbac_setor_funcao_groups.py
- v2/backend/apps/core/migrations/0043_add_all_setor_groups.py
- v2/backend/apps/core/views_dashboard.py
- v2/backend/apps/core/views_solicitacao.py
- v2/backend/apps/core/views/availability.py
- v2/frontend/src/App.tsx
- v2/frontend/src/api/auth.ts
- v2/frontend/src/api/config.ts
- v2/frontend/src/pages/Auth/LoginPage.tsx
- v2/backend/config/settings.py

## What Was Implemented
- Login, logout, ping endpoints with audit logs and lockout behavior.
- CSRF HttpOnly support via /api/csrf/ with frontend retry and caching.
- Session storage in Redis with secure cookie settings for production.
- RBAC Setor + Função computed in /api/me/ with can_approve_super.
- DRF permission classes for core flows.

## Findings (Ordered by Severity)
High
- /api/dashboard/overview/ requires only IsAuthenticated, exposing aggregate metrics broadly. File: v2/backend/apps/core/views_dashboard.py
- Frontend allows dashboards for DAT/Diretoria, but backend metrics require Controle/Gerência. This causes 403s and mismatched access. Files: v2/frontend/src/App.tsx, v2/backend/apps/core/views/metrics/*.py

Medium
- Superintendência can access some backend Controle endpoints but is blocked in the frontend canControle flag. Files: v2/backend/apps/core/permissions.py, v2/frontend/src/App.tsx
- Approvals UI requires Gerente+Superintendência while API allows DAT via IsSuperintendencia. Files: v2/frontend/src/App.tsx, v2/backend/apps/core/views_solicitacao.py
- /bloqueios route has no frontend RBAC gate and backend uses IsAuthenticated only. If the policy is “Formador/Controle only,” this is a gap. File: v2/backend/apps/core/views/availability.py

Low
- Diretoria is referenced in RBAC lists and frontend but no migration/seed creates the group. Files: v2/backend/apps/core/views_basic.py, v2/backend/apps/core/migrations/0042_rbac_setor_funcao_groups.py, v2/backend/apps/core/migrations/0043_add_all_setor_groups.py
- Login audit IP uses REMOTE_ADDR without proxy headers. File: v2/backend/apps/core/views_auth.py
- Docs include outdated endpoint notes and RBAC statements. File: v2/docs/RBAC_COMPLETO.md

## Tests
- Attempted: pytest on auth + rbac tests.
- Result: failed due to missing pytest module.
- Suggestion: install v2/backend/requirements-dev.txt or run via Docker.

## Notes (Execution Thoughts)
- Focused on alignment between docs, frontend gating, and backend permissions.
- Paid special attention to any IsAuthenticated-only endpoints that present user-facing dashboards or aggregated data.
- Looked for RBAC group creation sources to ensure groups used in frontend are guaranteed to exist.

## Summary
- Auth and session handling are robust, but RBAC alignment is inconsistent across frontend and backend.
- Dashboard access is the most critical mismatch: UI and API use different roles and one endpoint is broadly authenticated.
- Minor inconsistencies and doc drift should be corrected after RBAC alignment.

## Next Phase
- Phase 02: Solicitações + Aprovações (PA)
