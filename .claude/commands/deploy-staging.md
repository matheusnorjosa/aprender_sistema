---
description: Pre-deployment checklist for staging environment with validation steps
argument-hint: [optional: deployment type - 'full' or 'hotfix']
---

# Deploy to Staging — Pre-Flight Checklist

Deployment type: ${ARGUMENTS:-full}

## 🎯 Overview

This checklist ensures safe deployment to staging environment. **NEVER skip steps** - each validates critical aspects of the deployment.

---

## 📋 Pre-Deployment Checklist

### Phase 1: Code Quality (Local)

- [ ] **All tests passing**
  ```bash
  docker compose exec web pytest -v
  # Expected: All tests GREEN (56+ passing)
  ```

- [ ] **Coverage threshold met** (90%+)
  ```bash
  docker compose exec web pytest --cov=apps --cov-fail-under=90
  # Expected: Coverage >= 90%
  ```

- [ ] **Linting clean** (flake8, black)
  ```bash
  docker compose exec web flake8 apps/
  docker compose exec web black --check apps/
  # Expected: No errors
  ```

- [ ] **Migrations valid**
  ```bash
  docker compose exec web python manage.py makemigrations --check
  docker compose exec web python manage.py check
  # Expected: No issues detected
  ```

- [ ] **Security checks**
  ```bash
  docker compose exec web python manage.py check --deploy
  # Expected: No warnings
  ```

### Phase 2: Version Control

- [ ] **Branch up-to-date with main**
  ```bash
  git fetch origin main
  git status
  # Expected: "Your branch is up to date with 'origin/main'"
  ```

- [ ] **No uncommitted changes**
  ```bash
  git status
  # Expected: "nothing to commit, working tree clean"
  ```

- [ ] **PR approved and merged**
  - All conversations resolved
  - At least 1 approval
  - CI checks passing (GitHub Actions)

- [ ] **Tag created** (for full deployments)
  ```bash
  git tag -a v2.1.0 -m "Release v2.1.0: [Brief description]"
  git push origin v2.1.0
  ```

### Phase 3: Docker & Infrastructure

- [ ] **Docker images built successfully**
  ```bash
  docker compose build web
  # Expected: Successfully built
  ```

- [ ] **Image tagged correctly**
  ```bash
  docker tag aprender_v2_web:latest registry.example.com/aprender_v2_web:staging-latest
  docker push registry.example.com/aprender_v2_web:staging-latest
  ```

- [ ] **Environment variables validated**
  ```bash
  # Check .env.staging has all required vars
  cat .env.staging | grep -E "DB_HOST|DB_PORT|REDIS_HOST|SECRET_KEY|GCAL_CLIENT"
  # Expected: All variables present
  ```

### Phase 4: Database (Staging)

- [ ] **Database backup created**
  ```bash
  ssh staging "docker compose exec db pg_dump -U postgres aprender_v2 > /backups/backup_pre_deploy_$(date +%Y%m%d_%H%M%S).sql"
  # Verify backup exists and has content
  ssh staging "ls -lh /backups/backup_pre_deploy_*.sql"
  ```

- [ ] **Migrations tested in dry-run**
  ```bash
  ssh staging "docker compose exec web python manage.py migrate --plan"
  # Review migration plan, ensure expected
  ```

- [ ] **Database connection verified**
  ```bash
  ssh staging "docker compose exec web python manage.py dbshell -c '\dt'"
  # Expected: List of tables
  ```

### Phase 5: Deployment Execution

- [ ] **Enable maintenance mode** (optional, for large migrations)
  ```bash
  ssh staging "touch /app/MAINTENANCE_MODE"
  ```

- [ ] **Pull latest code**
  ```bash
  ssh staging "cd /app && git pull origin main"
  ```

- [ ] **Pull/rebuild Docker images**
  ```bash
  ssh staging "cd /app && docker compose pull"
  # or
  ssh staging "cd /app && docker compose build"
  ```

- [ ] **Apply migrations**
  ```bash
  ssh staging "cd /app && docker compose exec web python manage.py migrate"
  # Watch output for errors
  ```

- [ ] **Collect static files** (if frontend changes)
  ```bash
  ssh staging "cd /app && docker compose exec web python manage.py collectstatic --no-input"
  ```

- [ ] **Restart services**
  ```bash
  ssh staging "cd /app && docker compose restart web worker beat"
  ```

- [ ] **Disable maintenance mode**
  ```bash
  ssh staging "rm /app/MAINTENANCE_MODE"
  ```

### Phase 6: Post-Deployment Validation

- [ ] **Health check endpoint**
  ```bash
  curl https://staging.aprender.example.com/api/health/
  # Expected: {"status": "ok", "version": "v2.1.0"}
  ```

- [ ] **Database connection (from app)**
  ```bash
  ssh staging "docker compose exec web python manage.py shell -c 'from apps.core.models import Usuario; print(Usuario.objects.count())'"
  # Expected: Count matches pre-deployment
  ```

- [ ] **Redis connection**
  ```bash
  ssh staging "docker compose exec web python manage.py shell -c 'from django.core.cache import cache; cache.set(\"test\", \"ok\"); print(cache.get(\"test\"))'"
  # Expected: "ok"
  ```

- [ ] **Celery workers running**
  ```bash
  ssh staging "docker compose exec worker celery -A config inspect active"
  # Expected: Worker(s) active
  ```

- [ ] **Critical tests in production-like env**
  ```bash
  ssh staging "docker compose exec web pytest apps/core/tests/test_critical.py -v"
  # Expected: All passing
  ```

### Phase 7: Smoke Testing (Manual)

- [ ] **Frontend loads**
  - Visit: https://staging.aprender.example.com/
  - Expected: Homepage renders without errors

- [ ] **Authentication works**
  - Login with test user
  - Expected: Redirects to dashboard

- [ ] **API endpoints respond**
  - Visit: https://staging.aprender.example.com/api/solicitacoes/
  - Expected: Returns data (with auth)

- [ ] **Critical flows work**
  - Create solicitação (RF02)
  - Check conflicts (RF03)
  - Approve solicitação (RF04)
  - Expected: No errors, data persists

### Phase 8: Monitoring & Logs

- [ ] **Check logs for errors**
  ```bash
  ssh staging "docker compose logs web --tail=100 | grep ERROR"
  # Expected: No critical errors
  ```

- [ ] **Check Celery logs**
  ```bash
  ssh staging "docker compose logs worker --tail=50"
  # Expected: Tasks processing normally
  ```

- [ ] **Monitor resource usage**
  ```bash
  ssh staging "docker stats --no-stream"
  # Expected: CPU < 80%, Memory < 80%
  ```

- [ ] **Database query performance**
  ```bash
  ssh staging "docker compose exec db psql -U postgres aprender_v2 -c 'SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;'"
  # Review slow queries
  ```

### Phase 9: Rollback Plan (If Needed)

**If deployment fails, execute rollback**:

- [ ] **Restore database**
  ```bash
  ssh staging "cd /app && docker compose down"
  ssh staging "docker compose exec db psql -U postgres aprender_v2 < /backups/backup_pre_deploy_20250115_103000.sql"
  ssh staging "cd /app && docker compose up -d"
  ```

- [ ] **Revert code**
  ```bash
  ssh staging "cd /app && git checkout [previous-commit-hash]"
  ssh staging "cd /app && docker compose restart"
  ```

- [ ] **Notify team**
  - Post in Slack/Discord: "Staging deployment rolled back due to [reason]"
  - Create incident ticket

### Phase 10: Documentation

- [ ] **Update CHANGELOG.md**
  ```markdown
  ## [v2.1.0] - 2025-01-15

  ### Added
  - Feature X (PR#45)
  - Feature Y (PR#46)

  ### Fixed
  - Bug Z (PR#47)

  ### Changed
  - Improved performance of availability service (PR#48)
  ```

- [ ] **Update deployment log**
  - Date: 2025-01-15 10:30 BRT
  - Version: v2.1.0
  - Deployed by: [Your name]
  - Status: Success
  - Rollback needed: No

- [ ] **Notify stakeholders**
  - Email: "Staging updated to v2.1.0. Ready for QA testing."
  - Include: Release notes, testing checklist, known issues

---

## 🚨 Critical Checks (NEVER Skip)

These checks are **absolutely mandatory**:

1. ✅ **Database backup** - Always backup before migrations
2. ✅ **All tests passing** - No deployment with failing tests
3. ✅ **Migrations validated** - Review migration plan
4. ✅ **Health check** - Verify app responds after deployment
5. ✅ **Rollback plan ready** - Know how to revert if needed

---

## 🔧 Deployment Types

### Full Deployment

**Use when**:
- Multiple PRs merged
- Major feature release
- Breaking changes
- Database schema changes

**Additional steps**:
- Create git tag
- Update CHANGELOG.md
- Full smoke testing (all features)
- Notify all stakeholders

### Hotfix Deployment

**Use when**:
- Critical bug fix
- Security patch
- Urgent production issue

**Streamlined steps**:
- Skip tag creation
- Skip full smoke testing (focus on fixed bug)
- Quick validation only
- Immediate notification

**Example**:
```bash
# Hotfix workflow
git checkout -b hotfix/critical-bug
# ... fix bug ...
git commit -m "fix(critical): resolve [issue]"
git push origin hotfix/critical-bug
# ... PR approved ...
git checkout main
git merge hotfix/critical-bug
# Deploy to staging (this checklist, hotfix mode)
# Deploy to production (after validation)
```

---

## 📊 Staging Environment Specs

**Configuration**:
- **URL**: https://staging.aprender.example.com
- **Database**: PostgreSQL 15 (separate from production)
- **Cache**: Redis 7
- **Environment**: Docker Compose (similar to production)
- **Data**: Anonymized production snapshot OR test data

**Differences from Production**:
- Smaller instance size (cost optimization)
- Debug mode ON (for detailed error messages)
- GCAL_CLIENT=fake (no real calendar integration)
- Email backend: Console (prints to logs)

---

## 🧪 Testing After Deployment

### Automated Tests

```bash
# Run full test suite in staging
ssh staging "docker compose exec web pytest -v --maxfail=5"

# Run critical tests only (faster)
ssh staging "docker compose exec web pytest -v -m critical"

# Run specific compliance tests
ssh staging "docker compose exec web pytest apps/core/tests/test_approval_policy_PA.py -v"
ssh staging "docker compose exec web pytest apps/core/tests/test_availability_service.py -v"
```

### Manual QA Checklist

**RF01-RF08 Validation**:
- [ ] RF01: Data import (ETL dry-run works)
- [ ] RF02: Create solicitação (wizard completes)
- [ ] RF03: Check conflicts (displays conflicts correctly)
- [ ] RF04: Approve/reject (Superintendência only)
- [ ] RF05: Google Calendar preview (payload generated)
- [ ] RF06: Meet link generation (field populated)
- [ ] RF07: Audit log (actions recorded)
- [ ] RF08: Monthly grid (data displays correctly)

**Cross-browser Testing** (if UI changes):
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile (Chrome Android)

---

## 🔄 Continuous Improvement

**After each deployment, review**:
1. What went well?
2. What could be improved?
3. Were any steps missing from checklist?
4. Update this checklist accordingly

**Metrics to track**:
- Deployment duration (target: <15 min)
- Rollback frequency (target: <5%)
- Tests passing rate (target: 100%)
- Incidents post-deployment (target: 0)

---

## 📚 Reference

- **Deployment Guide**: `v2/docs/RUNBOOK.md`
- **Migration Guide**: `.claude/commands/migrate.md`
- **Testing Guide**: `.claude/commands/test-coverage.md`
- **Project Context**: `.claude/CLAUDE.md`

---

## ✅ Output

**If all checks pass**:
```
✅ DEPLOYMENT SUCCESSFUL

Environment: Staging
Version: v2.1.0
Date: 2025-01-15 10:30 BRT
Duration: 12 minutes

Pre-deployment:
- Tests: 56/56 passing ✓
- Coverage: 95% ✓
- Migrations: 3 applied ✓
- Backup: Created ✓

Post-deployment:
- Health check: OK ✓
- Database: Connected ✓
- Redis: Connected ✓
- Celery: 2 workers active ✓

Smoke tests: ALL PASS
- RF02: Create solicitação ✓
- RF03: Check conflicts ✓
- RF04: Approve/reject ✓

Status: Ready for QA testing

Next steps:
1. Notify QA team
2. Monitor logs for 1 hour
3. Schedule production deployment (after QA approval)
```

**If checks fail**:
```
❌ DEPLOYMENT FAILED

Failed checks:
- Tests: 2/56 failing ✗
- Health check: Timeout ✗

Action taken: Rollback initiated

Rollback status:
- Database restored ✓
- Code reverted ✓
- Services restarted ✓

Incident created: #INC-123
Next steps:
1. Review failed tests
2. Fix issues
3. Retry deployment
```

---

**Focus**: Safe, validated deployment with rollback capability and comprehensive testing.
