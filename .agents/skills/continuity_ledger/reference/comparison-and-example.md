# Continuity Ledger — comparison and worked example

## Comparison with other state-preservation tools

| Tool | Scope | Fidelity |
|------|-------|----------|
| CLAUDE.md | Project | Always fresh, stable patterns |
| TodoWrite | Turn | Survives compaction, but understanding degrades |
| CONTINUITY_CLAUDE-*.md | Session | External file — never compressed, full fidelity |
| Handoffs (`create_handoff`/`resume_handoff`) | Cross-session | External file — detailed context for new session |

## Worked example

```markdown
# Session: rbac-capability-rename
Updated: 2026-06-20T14:30:00Z

## Goal
Migrate views to canonical `permission_classes = [HasPerm("codename")]`. Done when all tests pass, pyright clean, and no legacy permission classes remain in scope.

## Constraints
- v2 Docker-only (CP-01): tests via `docker exec aprender_dev-web-1 pytest`
- Import only `from apps.core.rbac import HasPerm` (apps/core/permissions.py is a shim)
- `scripts/rbac_lint.py` bans `user.groups.filter(name=...)` — keep CI green
- Coverage gate = 85%

## Key Decisions
- Composition: `HasPerm("a") | HasPerm("b")` for OR (≤2 caps); Policy class for ≥3
- Non-DRF checks: `user_has_any_perm(user, *codenames)`
- Codemod: regex + line-context guards (1→1 rename only)

## State
- Done: rbac module layout, HasPerm parametrization, lint guard
- Now: migrate remaining viewsets in apps/core/views/
- Next: drop legacy IsSuperintendencia/IsControleOrSuper, update tests

## Open Questions
- UNCONFIRMED: any @action with permission_classes hidden by get_permissions override?

## Working Set
- Branch: `feat/rbac-capability-rename`
- Key files: `v2/backend/apps/core/rbac/`, `v2/backend/apps/core/views/`
- Test cmd: `docker exec aprender_dev-web-1 pytest apps/core/tests/ -v`
```
