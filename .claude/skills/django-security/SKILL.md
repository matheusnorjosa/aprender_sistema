---
name: django-security
description: Review and harden security in the AS v2 Django/DRF backend. Use when auditing RBAC access control, reviewing auth/OAuth/import code for vulnerabilities, or hardening an endpoint before deploy. Covers OWASP Top 10, IDOR, CSV injection, row-level scoping, and secrets — mapped to AS v2's session auth, capability RBAC, and Google OAuth.
---

# Django Security — AS v2

## Audit Procedure (RBAC access control)

Run in order; the audit is DONE only when every step passes.

1. **Lint passes** — run `python scripts/rbac_lint.py apps/` (cwd `v2/backend`).
   It bans `user.groups.filter(name=...)` and `Is<Role>` classes outside the
   whitelist. Same job as CI `[required] backend rbac-lint`.
2. **Every ViewSet has explicit `permission_classes`** — enumerate the ViewSets
   touched; each must declare `HasPerm("codename")` (or a composition), never
   rely on the DRF default alone. If `get_permissions()` is overridden, confirm
   it does not silently drop an `@action(permission_classes=...)` decorator.
3. **`get_queryset()` enforces data-scope** — non-privileged users see only their
   own rows (`filter(usuario=request.user)`); the full queryset is gated behind a
   capability check via `user_has_any_perm(...)`. No `objects.all()` leak.
4. **Secrets/config** — no hardcoded keys; production flags set (see A05);
   `.gitignore` blocks the secret files (see Secrets Management).

DONE = steps 1–4 all pass for the code under review.

## OWASP Top 10 — AS v2 Specific

### A01: Broken Access Control

RBAC model, capability codenames, and the canonical ViewSet pattern that gates by
capability then scopes the queryset: **see [reference/rbac-idor.md](reference/rbac-idor.md)**.
That file is the single source for the IDOR / row-level pattern — link to it, do not
re-derive it.

**Audit-specific checks** (beyond the [Audit Procedure](#audit-procedure-rbac-access-control)):
- [ ] Bulk approve/reject actions verify the capability per item, not once for the batch
- [ ] `select_for_update()` on approval flows to prevent race conditions
- [ ] No IDOR: a user cannot read `/solicitacoes/{id}/` outside their scope
- [ ] Frontend permission checks mirror backend (never trust client-side only)

### A02: Cryptographic Failures

**Our crypto surface:**
- `GCAL_ENCRYPTION_KEY` — Fernet encryption for OAuth tokens
- `SECRET_KEY` — Django session signing
- `REDIS_PASSWORD` — Redis auth in production

**Checklist:**
- [ ] OAuth tokens encrypted at rest with Fernet (`GoogleOAuthCredential.access_token_encrypted` / `refresh_token_encrypted`)
- [ ] Key rotation tested via the `rotate_gcal_encryption_key` management command
- [ ] `SECRET_KEY` from environment variable, never hardcoded
- [ ] Sessions use HttpOnly + Secure + SameSite=Lax cookies
- [ ] No sensitive data in URL query parameters (use POST body)

### A03: Injection

**SQL injection vectors in Django:**
```python
# DANGEROUS — never do this
Solicitacao.objects.raw(f"SELECT * FROM core_solicitacao WHERE id = {user_input}")
Solicitacao.objects.extra(where=[f"status = '{request.GET['status']}'"])

# SAFE — parameterized queries
Solicitacao.objects.filter(id=user_input)
Solicitacao.objects.raw("SELECT * FROM core_solicitacao WHERE id = %s", [user_input])
```

**CSV injection in exports** — use the SSOT helper, do not reimplement:
```python
# DANGEROUS — user-controlled data in CSV (a value like =CMD() executes in Excel)
writer.writerow([solicitacao.observacoes])

# SAFE — SEC-007 helper prefixes formula chars (= + - @ TAB CR LF) with a single quote
from apps.core.utils.csv_sanitize import sanitize_csv_value
writer.writerow([sanitize_csv_value(v) for v in row])
```

### A04: Insecure Design

**Our design patterns:**
- Approval flow (PA-01~07) enforced at service layer, not view layer
- Availability rules (RD-01~08) in `availability_service.py`, validated server-side
- Status transitions via state machine, not arbitrary updates
- AuditLog for all approval/rejection operations

### A05: Security Misconfiguration

**Production checklist:**
- [ ] `DEBUG = False`
- [ ] `ALLOWED_HOSTS` explicitly set (not `['*']`)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_HTTPONLY = True`
- [ ] `X_FRAME_OPTIONS = 'DENY'` (anti-clickjacking)
- [ ] `SECURE_HSTS_SECONDS = 31536000`
- [ ] `INCLUDE_DEV_TOOLS = False` (CP-08)
- [ ] Container runs as non-root (SEC-006)
- [ ] `read_only: true` on container filesystem
- [ ] Debug toolbar, silk, nplusone behind try/except ImportError

### A07: Authentication Failures

**Our auth model:**
- Session-based (Redis backend), NOT JWT for web
- CSRF token via HttpOnly cookie + `/api/csrf/` endpoint
- Account lockout: 10 attempts → 15 min block
- Rate limiting: login 10/min, gcal_write 10/min

**Checklist:**
- [ ] Login endpoint rate-limited (DRF throttle + Nginx)
- [ ] Failed login attempts logged with IP + user-agent
- [ ] Session cookie: `asv2sid`, age 7200s, SameSite=Lax
- [ ] CSRF token refreshed after login
- [ ] Logout clears session + CSRF cache

### A08: Software and Data Integrity

**Our supply chain:**
- Docker images signed with Cosign (keyless OIDC)
- SLSA provenance attestations
- Trivy container scanning in CI
- Gitleaks + TruffleHog secret detection
- pip-audit for Python dependencies
- npm audit for frontend dependencies

### A09: Logging and Monitoring

**Our logging:**
- Structured JSON logging with request ID correlation
- AuditLog model for approval/rejection operations
- Login/logout audit with IP + user-agent
- Django-prometheus metrics at `/metrics/`

**Security events to always log:**
- Authentication failures (with IP)
- Authorization failures (403s with user + resource)
- CSRF failures
- Rate limit triggers
- OAuth token operations (create, refresh, revoke)

## Secrets Management

**Never commit:**
- `.env` files with real credentials
- `service_account.json` (Google)
- `GCAL_ENCRYPTION_KEY` values
- `SECRET_KEY` values
- Database passwords

**`.gitignore` already blocks** (`.env*` local variants and Google creds):
```
.env
.env.local
.env.*.local
!.env.*.example
service_account.json
*service_account.json
backend/service_account.json   # v2/.gitignore
```

Verify any new secret file is covered before committing — the ignore list is
explicit, not a blanket `.env.*`.
