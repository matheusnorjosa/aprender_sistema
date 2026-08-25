---
description: Automated security scanning for AS v2. Use before commits or when reviewing changes for vulnerabilities. Runs dependency audit (pip-audit, npm audit), secret detection (grep patterns), and code pattern scanning (SQL injection, XSS, eval, pickle, hardcoded secrets). Integrates with project hooks system.
disable-model-invocation: true
---

# Security Scan — AS v2

## Scan Phases

### Phase 1: Secret Detection

Scan for accidentally committed secrets:

```bash
# Patterns to detect
grep -rn --include="*.py" --include="*.ts" --include="*.tsx" --include="*.js" \
  -E "(password|secret|token|api_key|apikey|private_key)\s*=\s*['\"][^'\"]{8,}" \
  v2/backend/ v2/frontend/src/ \
  | grep -v "test_\|tests/\|\.example\|placeholder\|CHANGEME\|your-\|xxx\|fake"

# Check for hardcoded IPs/hosts
grep -rn --include="*.py" --include="*.yml" \
  -E "\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b" \
  v2/backend/config/ .github/workflows/ \
  | grep -v "127\.0\.0\.1\|0\.0\.0\.0\|localhost\|host\.docker"

# Check .env files are not tracked
git ls-files | grep -E "\.env$|\.env\." | grep -v "example"
```

**Expected result**: Zero findings. Any match requires immediate investigation.

### Phase 2: Dependency Audit

```bash
# Python dependencies
cd v2/backend
pip-audit -r requirements.txt --format json 2>/dev/null | python -c "
import sys, json
data = json.load(sys.stdin)
vulns = [d for d in data.get('dependencies', []) if d.get('vulns')]
if vulns:
    for v in vulns:
        for vuln in v['vulns']:
            print(f\"  {v['name']}=={v['version']}: {vuln['id']} (fix: {vuln.get('fix_versions', 'none')})\")
    print(f'FAIL: {len(vulns)} vulnerable packages')
    sys.exit(1)
print('PASS: 0 vulnerable packages')
"

# Frontend dependencies (production only)
cd v2/frontend
npm audit --omit=dev --audit-level=high 2>/dev/null
```

**Expected result**: Zero HIGH/CRITICAL vulnerabilities. Moderate are tracked but don't block.

### Phase 3: Code Pattern Scanning

Scan for dangerous code patterns specific to our Django+React stack:

```bash
# SQL injection vectors
grep -rn --include="*.py" \
  -E "\.raw\(|\.extra\(|execute\(" \
  v2/backend/apps/ \
  | grep -v "test_\|tests/\|# nosec\|healthcheck"

# XSS vectors in React
grep -rn --include="*.tsx" --include="*.ts" \
  "dangerouslySetInnerHTML" \
  v2/frontend/src/

# Eval/exec (code execution)
grep -rn --include="*.py" \
  -E "^\s*(eval|exec|compile)\(" \
  v2/backend/apps/

# Pickle deserialization (RCE)
grep -rn --include="*.py" \
  -E "pickle\.(load|loads)\(" \
  v2/backend/

# Unsafe YAML loading
grep -rn --include="*.py" \
  "yaml\.load\(" \
  v2/backend/ \
  | grep -v "Loader=\|SafeLoader"

# Hardcoded Django SECRET_KEY
grep -rn --include="*.py" \
  "SECRET_KEY\s*=\s*['\"]" \
  v2/backend/config/ \
  | grep -v "environ\|env(\|decouple\|os\.getenv"

# Open redirects
grep -rn --include="*.py" \
  "redirect(request\.\|HttpResponseRedirect(request\." \
  v2/backend/apps/

# Mass assignment (serializer without explicit fields)
grep -rn --include="*.py" \
  "fields\s*=\s*['\"]__all__['\"]" \
  v2/backend/apps/
```

**Expected result**: Zero findings or all findings have `# nosec` justification.

### Phase 4: Configuration Audit

```bash
# Check Django security settings (v2 is Docker-only, CP-01)
docker exec aprender_dev-web-1 python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from django.conf import settings

checks = {
    'DEBUG': (settings.DEBUG, False),
    'SECURE_SSL_REDIRECT': (getattr(settings, 'SECURE_SSL_REDIRECT', False), True),
    'SESSION_COOKIE_SECURE': (getattr(settings, 'SESSION_COOKIE_SECURE', False), True),
    'CSRF_COOKIE_SECURE': (getattr(settings, 'CSRF_COOKIE_SECURE', False), True),
    'CSRF_COOKIE_HTTPONLY': (getattr(settings, 'CSRF_COOKIE_HTTPONLY', False), True),
    'SECURE_HSTS_SECONDS': (getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0, True),
    'X_FRAME_OPTIONS': (getattr(settings, 'X_FRAME_OPTIONS', ''), 'SAMEORIGIN'),
}

for name, (actual, expected) in checks.items():
    status = 'PASS' if actual == expected else 'WARN'
    print(f'  {status}: {name} = {actual} (expected {expected})')
" 2>/dev/null || echo "Cannot check settings — ensure the dev container is up (cd v2 && make up; CP-01)"
```

## Integration with CI

These checks already run in CI via:
- `security-scan.yml` → pip-audit, Trivy, npm audit, Gitleaks, TruffleHog
- `ci.yaml` → Bandit (SAST)
- `dependency-review-scorecard.yml` → OpenSSF Scorecard

This skill is for **local pre-commit** and **code review** augmentation.

## Quick Commands

```bash
# Full scan (all 4 phases)
/security-scan

# Just secrets
/security-scan secrets

# Just dependencies
/security-scan deps

# Just code patterns
/security-scan patterns
```

## Severity Classification

| Severity | Action | Examples |
|---|---|---|
| **CRITICAL** | Block commit, fix immediately | Hardcoded secrets, SQL injection, known CVE with exploit |
| **HIGH** | Fix before merge | IDOR, missing permission class, XSS, unsafe deserialization |
| **MEDIUM** | Fix in same sprint | Missing rate limit, verbose error messages, weak CSRF |
| **LOW** | Track in backlog | Informational headers, minor config improvements |
