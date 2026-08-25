---
description: Pre-deployment checklist (local staging-full validation + merge-to-main deploy via Portainer)
argument-hint: [optional: deployment type - 'full' or 'hotfix']
---

# Deploy — Pre-Flight Checklist

Deployment type: ${ARGUMENTS:-full}

## 🎯 Overview

**There is NO dedicated staging environment** in AS v2. The flow is:

1. **Validate locally** with `make staging-full` (prod-like stack) — must finish **8/8 PASS**.
2. **Merge (squash) into `main`** → this triggers an **automatic deploy to production via Portainer**.
3. **Verify version/health** after the deploy lands.

"Staging" here means the **local prod-like validation gate**, not a remote server.
**NEVER skip the local gate** — merging to `main` deploys straight to prod (CP-07: never push
directly to `main`; merge a PR).

---

## 📋 Pre-Deployment Checklist

### Phase 1: Code Quality (Local, Docker — CP-01)

- [ ] **All backend tests passing** (Docker-only)
  ```bash
  docker exec aprender_dev-web-1 pytest apps/core/tests/ -v
  # Expected: All tests GREEN
  ```

- [ ] **Coverage threshold met** (gate = 85%)
  ```bash
  docker exec aprender_dev-web-1 pytest --cov=apps --cov-fail-under=85
  # Expected: Coverage >= 85%
  ```

- [ ] **Type check clean** (Pyright strict)
  ```bash
  cd v2/backend && pyright apps/core config
  # Expected: 0 errors
  ```

- [ ] **Linting clean** (flake8, black, isort)
  ```bash
  docker exec aprender_dev-web-1 flake8 apps/
  docker exec aprender_dev-web-1 black --check apps/
  docker exec aprender_dev-web-1 isort --check apps/
  # Expected: No errors
  ```

- [ ] **Migrations valid**
  ```bash
  docker exec aprender_dev-web-1 python manage.py makemigrations --check
  docker exec aprender_dev-web-1 python manage.py check
  # Expected: No issues detected
  ```

- [ ] **RBAC lint clean** (bans user.groups.filter(name=...))
  ```bash
  python v2/backend/scripts/rbac_lint.py
  # Expected: No violations (CI job: [required] backend rbac-lint)
  ```

### Phase 2: Local Staging-Full Gate (the real "staging")

- [ ] **Run the full prod-like validation** — must end **8/8 PASS**
  ```bash
  make staging-full
  # Expected: ALL 8 CHECKS PASSED
  ```
  > On GnuWin32/Windows, `$(MAKE)` recursion can break — run the staging-precheck/build/up/test/down
  > steps individually if `make staging-full` fails on the make-recursion (not on a real check).

- [ ] **Attach evidence + staging-gate markers to the PR body** (exact literals, no accents)
  - `make staging-full ... (8/8 PASS)`
  - `Evidencia anexada no PR`
  - `ALL 8 CHECKS PASSED`
  > The staging gate matches these literal strings (regex `Evidencia` — no accent). A `Evidência`
  > body fails the gate; fix via `gh pr edit --body`. Draft PRs skip the gate.

### Phase 3: Version Control & PR

- [ ] **Branch up-to-date with main**
  ```bash
  git fetch origin main
  gh pr update-branch   # if base moved; re-trigger required checks
  # Expected: branch in sync, CI re-runs
  ```

- [ ] **No uncommitted changes**
  ```bash
  git status
  # Expected: "nothing to commit, working tree clean"
  ```

- [ ] **PR green and ready**
  - All conversations resolved
  - At least 1 approval
  - All `[required]` checks passing (GitHub Actions)
  - Staging-gate markers present in body (Phase 2)
  - Conventional commit title (CP-06): `type(scope): message`

### Phase 4: Deploy Execution (merge → Portainer)

- [ ] **Squash-merge the PR into `main`**
  ```bash
  gh pr merge <PR> --squash
  # Merge to main = automatic deploy to PRODUCTION via Portainer. There is no manual ssh/deploy step.
  ```

- [ ] **Watch the deploy workflow**
  ```bash
  gh run watch          # or: gh run list --workflow=deploy
  # A burst of merges = N serial deploys; the deploy of HEAD is the one that must succeed.
  ```
  > Transient `curl 28` / HTTP 000 against Portainer (9443) during a merge burst is not an alarm
  > if the HEAD deploy succeeds and prod returns HTTP 200.

### Phase 5: Post-Deployment Validation

- [ ] **Version/health check**
  ```bash
  curl -s https://<prod-host>/api/health/
  # Expected: HTTP 200 + {"status": "ok", "version": "v2026.MM.DD-<sha>"}
  ```
  > **External health may return HTTP 000** (Kaspersky/KESL on the Golden VMs blocks the probe),
  > even when the site is up. In that case, fall back to the **Portainer API** to confirm the
  > container is healthy and serving — accept the deploy as good when Portainer shows the new
  > image running + an internal 200.

- [ ] **Confirm deployed image tag matches the merged commit**
  ```bash
  # via Portainer API: check the running container image tag == v2026.MM.DD-<sha>
  ```

- [ ] **Spot-check a critical endpoint** (with auth)
  - Frontend loads (homepage renders)
  - Login works → redirects to dashboard
  - `/api/solicitacoes/` returns data

### Phase 6: Rollback Plan (If Needed)

**If the deploy is bad**, roll back via Portainer (redeploy the previous image tag):

- [ ] **Redeploy previous known-good tag** through Portainer (stack/container update to
      `v2026.MM.DD-<previous-sha>`).
- [ ] **If a migration broke prod**, restore from the latest DB backup per
      `v2/docs/DISASTER_RECOVERY.md` / `BACKUP_OPERATIONS.md`.
- [ ] **Open a revert PR** if the fix is code-level (do NOT push to `main` directly — CP-07).
- [ ] **Never `systemctl restart docker`** on the VMs (Kaspersky race brings the site down).

---

## 🚨 Critical Checks (NEVER Skip)

1. ✅ **`make staging-full` 8/8 PASS** — merging to main deploys to PROD, so the local gate is the
   only pre-prod safety net.
2. ✅ **All required CI checks green** + staging-gate markers in the PR body.
3. ✅ **Migrations validated** locally before merge.
4. ✅ **Post-deploy health** — HTTP 200, or Portainer-API confirmation when external probe = 000.
5. ✅ **Rollback path known** — previous image tag in Portainer + latest DB backup.

---

## 🔧 Deployment Types

### Full Deployment

**Use when**: multiple PRs, major feature, breaking changes, or schema changes.
**Extra care**: full `make staging-full` run + full smoke of touched flows; confirm image tag post-deploy.

### Hotfix Deployment

**Use when**: critical bug fix, security patch, urgent prod issue.
**Streamlined**: still run `make staging-full` (the gate is non-negotiable), but smoke-test only the
fixed area. Merge → Portainer redeploys.

**Example**:
```bash
git checkout -b hotfix/critical-bug
# ... fix bug ...
git commit -m "fix(critical): resolve [issue]"
git push origin hotfix/critical-bug
# ... PR with staging-gate markers, approved, required checks green ...
gh pr merge <PR> --squash   # deploys to prod via Portainer
```

---

## 📊 Environment Reality

- **No remote staging server.** Validation is **local** (`make staging-full`, prod-like Docker stack).
- **Prod = 3 Golden VMs**: VM01_App (Nginx/Gunicorn/Celery/React), VM02_DB (PostgreSQL 15),
  VM03_Red (Redis 7). Deploys land via **Portainer**.
- **Secrets** live in **Portainer** (Golden VMs); `.env.production` in the repo are dev templates.
- **External health probe may be HTTP 000** (Kaspersky/KESL) — use the Portainer API as fallback.

---

## 🧪 Manual QA Checklist (RF Validation)

Run against the **local prod-like stack** before merge (and spot-check prod after):

- [ ] RF02: Create solicitação (wizard completes)
- [ ] RF03: Check conflicts (displays conflicts correctly)
- [ ] RF04: Approve/reject (superuser OR Gerente + Superintendência — PA-01)
- [ ] RF05: Google Calendar preview (payload generated)
- [ ] RF06: Meet link generation (field populated)
- [ ] RF07: Audit log (actions recorded)
- [ ] RF08: Monthly grid (data displays correctly)

> Data import is **not ETL** anymore. The import path is `import_export_contract` (mgmt command,
> dry-run by default; `--apply` requires an allowlist) + the DRF endpoints
> `POST /api/controle/import-compras/`, `/api/controle/import-acoes/`, `/api/dat/import-cadastros/`
> (helpers: `make import-compras-dry` / `import-acoes-dry` / `import-cadastros-dry`).
> See `v2/docs/specs/backend/imports.spec.md`.

**Cross-browser** (if UI changes): Chrome, Firefox, Safari, Edge, Mobile Chrome.

---

## 📚 Reference

- **Deploy flow / checklist**: `v2/docs/DEPLOY_CHECKLIST.md`
- **Imports spec**: `v2/docs/specs/backend/imports.spec.md`
- **Backup/DR**: `v2/docs/DISASTER_RECOVERY.md`, `v2/docs/BACKUP_OPERATIONS.md`
- **Migration command**: `.claude/commands/migrate.md`
- **Testing command**: `.claude/commands/test-coverage.md`
- **Project Context**: `.claude/CLAUDE.md`

---

## ✅ Output

**If all checks pass**:
```
✅ DEPLOY SUCCESSFUL (via Portainer)

Validation: make staging-full → ALL 8 CHECKS PASSED
CI: all [required] checks green
Merge: PR #<n> squash-merged to main

Prod:
- Image tag: v2026.MM.DD-<sha> running (confirmed via Portainer)
- Health: HTTP 200  (or Portainer-API confirmed if external probe = 000)
- Smoke: RF02 / RF03 / RF04 ✓

Status: Live in production
```

**If checks fail**:
```
❌ DEPLOY FAILED / ROLLED BACK

Failed: <staging-full check N> | <required CI check> | <post-deploy health>

Action: redeploy previous image tag via Portainer
- Previous tag restored ✓
- (DB restored from backup, if a migration broke prod)
- Revert PR opened (no direct push to main — CP-07)

Next: fix root cause, re-run make staging-full (8/8), re-merge
```

---

**Focus**: Local prod-like gate (`make staging-full` 8/8) → squash-merge to `main` → automatic
Portainer deploy → health verify (HTTP 200 or Portainer-API fallback) → Portainer rollback if bad.