---
description: Comprehensive code review for AS v2 - 10 categories (clarity, security, a11y, performance, compliance). Adapted from premium Claude Code package with focus on Python/Django.
argument-hint: [file or directory to review]
allowed-tools: Bash(git:*)
---

# Enhanced Code Review — AS v2

Review code: $ARGUMENTS

**Review Framework**: 10-category comprehensive analysis (adapted from premium package)
- **Primary Focus**: Clarity (naming, anti-patterns, specificity)
- **Context**: Python/Django/DRF + AS v2 business rules (CP, RD, PA)

## Review Process

### 1. **Clarity Review** ⭐ PRIMARY FOCUS

**Goal**: Code that reads like a journal - clear, specific, maintainable.

**Why clarity first**: Unclear code causes 60%+ of bugs and maintenance issues.

#### Naming Standards
- [ ] **Descriptive names** that say what they mean
  - Good: `retry_after_seconds`, `email_validator`, `solicitacao_pendente`
  - Bad: `data`, `info`, `stuff`, `tmp`, `mgr`, `helper`
- [ ] **Specificity over generality**
  - Good: `check_availability_conflicts`, `publish_to_gcal`
  - Bad: `process`, `handle`, `manager`, `utility`
- [ ] **Brevity without redundancy**
  - Good: `Users` (not `UserList`), `retry_ms` (not `retry_milliseconds`)
- [ ] **Consistency across codebase**
  - Python: `snake_case` functions, `UpperCamelCase` classes, `SNAKE_CAPS` constants
  - Django: `snake_case` models fields, `related_name` descriptive

#### Anti-Patterns to Flag
- [ ] Ambiguous terms: `data`, `info`, `manager`, `helper`, `handler`, `processor`
- [ ] Hungarian notation: `strUsername`, `intCount`
- [ ] Redundant naming: `UserModel`, `UserClass`, `get_user_info()`
- [ ] Magic numbers/strings without constants

---

### 2. **Python/Django Standards**

#### Type Safety (Pyright Strict Mode)
- [ ] **Type hints on all functions/methods**
  ```python
  # Good
  def check_conflicts(usuario: Usuario, inicio: datetime, fim: datetime) -> AvailabilityResult:

  # Bad
  def check_conflicts(usuario, inicio, fim):
  ```
- [ ] **PEP 695 type aliases** (Python 3.12+)
  ```python
  type UserId = int
  type Status = Literal["pendente", "aprovado", "reprovado"]
  ```
- [ ] **Django QuerySet typed**
  ```python
  def pendentes(cls) -> models.QuerySet[Self]:
  ```
- [ ] **No `Any` usage** (minimal exceptions documented)
- [ ] **Serializers with type hints**
  ```python
  class SolicitacaoSerializer(serializers.ModelSerializer[Solicitacao]):
  ```

#### Control Flow
- [ ] **Early returns** over nested if-else
  ```python
  # Good
  if not user.is_authenticated:
      return Response(status=401)
  if not user.is_superintendencia:
      return Response(status=403)
  # ... happy path

  # Bad
  if user.is_authenticated:
      if user.is_superintendencia:
          # ... deep nesting
  ```
- [ ] **Max 2-3 levels** of indentation
- [ ] **Prefer dict dispatch** over long if-elif chains
  ```python
  # Good
  HANDLERS = {
      'APPROVE': handle_approve,
      'REJECT': handle_reject,
      'PUBLISH': handle_publish,
  }
  handler = HANDLERS.get(action, handle_default)

  # Bad
  if action == 'APPROVE':
      ...
  elif action == 'REJECT':
      ...
  elif action == 'PUBLISH':
      ...
  ```

#### Async/Await (Django 5.x)
- [ ] **Prefer async views** when I/O-bound
  ```python
  async def check_conflicts(request):
      sol = await Solicitacao.objects.aget(id=request.data['id'])
      conflicts = await availability_service.acheck_conflicts(...)
  ```
- [ ] **sync_to_async** for sync code in async context
- [ ] **No blocking calls** in async functions (e.g., `time.sleep()` → `asyncio.sleep()`)

#### Variables and Imports
- [ ] **Unused variables** prefixed with `_`
  ```python
  for _idx, item in enumerate(items):  # _idx not used
  ```
- [ ] **Named imports** (no `from x import *`)
- [ ] **Grouped imports**: stdlib → third-party → local
- [ ] **Absolute imports** preferred over relative

---

### 3. **Django/DRF Patterns**

#### Models (SSOT - Single Source of Truth)
- [ ] **Constraints at DB level**
  ```python
  class Meta:
      constraints = [
          models.CheckConstraint(check=Q(inicio__lt=F('fim')), name='inicio_before_fim'),
          models.UniqueConstraint(fields=['usuario', 'inicio'], name='unique_usuario_periodo'),
      ]
  ```
- [ ] **Indexes on filter/order fields**
  ```python
  class Meta:
      indexes = [
          models.Index(fields=['status', 'projeto']),
          models.Index(fields=['-created_at']),
      ]
  ```
- [ ] **Descriptive `related_name`**
  ```python
  usuario = models.ForeignKey(Usuario, related_name='solicitacoes_criadas')  # Good
  usuario = models.ForeignKey(Usuario, related_name='usuario_set')  # Bad
  ```
- [ ] **Timezone-aware** (`America/Fortaleza`, store UTC)

#### Serializers
- [ ] **Read vs Write separation**
  ```python
  class SolicitacaoReadSerializer(serializers.ModelSerializer):
      usuario = UsuarioSerializer(read_only=True)

  class SolicitacaoWriteSerializer(serializers.ModelSerializer):
      usuario = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.all())
  ```
- [ ] **Explicit validation** in `validate_*()`
- [ ] **Custom fields for complex logic**
- [ ] **Meta.fields explicit** (no `'__all__'` in production)

#### Views/ViewSets (Thin Controllers)
- [ ] **Business logic in services** (not in views)
- [ ] **Permission classes** correct
  ```python
  permission_classes = [IsAuthenticated, IsSuperintendencia]
  ```
- [ ] **Throttling** on sensitive endpoints
  ```python
  throttle_classes = [UserRateThrottle]
  throttle_scope = 'approval_actions'
  ```
- [ ] **select_related/prefetch_related** to avoid N+1
  ```python
  Solicitacao.objects.select_related('usuario', 'projeto', 'municipio').all()
  ```

#### Services Layer
- [ ] **Business logic isolated**
- [ ] **Type hints mandatory**
- [ ] **Pure functions when possible** (no hidden side effects)
- [ ] **Testable** (dependency injection)

---

### 4. **Observability**

#### Logging
- [ ] **Structured logging** with context
  ```python
  logger.info("Solicitacao approved", extra={
      "solicitacao_id": sol.id,
      "usuario_id": user.id,
      "action": "APPROVE",
  })
  ```
- [ ] **Log levels appropriate**
  - DEBUG: Development debugging
  - INFO: Normal flow (approval, rejection, publish)
  - WARNING: Recoverable issues (retries, fallbacks)
  - ERROR: Unrecoverable errors
  - CRITICAL: System failures
- [ ] **No secrets in logs** (passwords, tokens, API keys)

#### Error Handling
- [ ] **Specific exceptions** caught
  ```python
  try:
      publish_to_gcal(sol)
  except GoogleAPIError as e:
      logger.error(f"GCal publish failed: {e}", extra={"solicitacao_id": sol.id})
      raise PublishFailedError() from e
  ```
- [ ] **User-friendly error messages**
- [ ] **AuditLog** for critical operations (APPROVE, REJECT, PUBLISH)

#### Monitoring
- [ ] **Celery tasks have timeout**
  ```python
  @shared_task(time_limit=300)  # 5 minutes
  def task_publish_solicitacao_to_gcal(solicitacao_id):
  ```
- [ ] **Performance metrics** for slow operations (>1s)
- [ ] **Retry policies documented**

---

### 5. **Security (OWASP Top 10)**

#### Input Validation
- [ ] **DRF serializers validate** all inputs
- [ ] **Model `clean()` methods** for complex validation
- [ ] **No eval()** or `exec()` usage
- [ ] **File uploads sanitized** (type, size, name)

#### SQL Injection Prevention
- [ ] **ORM used exclusively** (no raw SQL)
- [ ] **If raw SQL**: Parameterized queries
  ```python
  # Good
  cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])

  # Bad (NEVER)
  cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
  ```

#### Authentication/Authorization
- [ ] **RBAC enforced** at view level (permissions.py)
- [ ] **Tokens/sessions secure** (httpOnly, secure, sameSite)
- [ ] **Password hashing** (Django default PBKDF2)
- [ ] **No hardcoded credentials**

#### Secret Management
- [ ] **Secrets via environment variables** (`.env`)
- [ ] **`.env` in `.gitignore`**
- [ ] **No secrets in logs/error messages**

#### CSRF/XSS
- [ ] **CSRF middleware enabled** (Django default)
- [ ] **Templates auto-escape** (Django default)
- [ ] **User input sanitized** before rendering

---

### 6. **Accessibility (WCAG 2.0)**

#### HTML Semantic
- [ ] **Proper elements** (`<button>` not `<div onclick>`)
- [ ] **Forms with labels**
  ```html
  <label for="usuario">Usuário:</label>
  <input id="usuario" name="usuario" />
  ```
- [ ] **Headings hierarchy** (h1 → h2 → h3, no skipping)
- [ ] **Alt text** for images

#### ARIA
- [ ] **ARIA labels** for complex UI
  ```html
  <button aria-label="Aprovar solicitação #123">Aprovar</button>
  ```
- [ ] **ARIA roles** when semantic HTML insufficient
- [ ] **ARIA states** (`aria-expanded`, `aria-selected`)

#### Keyboard Navigation
- [ ] **All interactive elements** keyboard accessible
- [ ] **Tab order logical**
- [ ] **Focus indicators** visible
- [ ] **Skip links** for long navigation

#### Color/Contrast
- [ ] **Contrast ratios** sufficient (4.5:1 for text, 3:1 for large text)
- [ ] **Color not sole indicator** (use icons + text)

---

### 7. **Performance**

#### Database
- [ ] **select_related** for FKs (1:1, N:1)
  ```python
  Solicitacao.objects.select_related('usuario', 'municipio', 'projeto')
  ```
- [ ] **prefetch_related** for M2M
  ```python
  Solicitacao.objects.prefetch_related('formadores', 'anexos')
  ```
- [ ] **Indexes** on frequently filtered/ordered fields
- [ ] **Avoid N+1 queries** (Django Debug Toolbar in dev)

#### Caching
- [ ] **Cache expensive queries** (Redis, 5-15 min)
  ```python
  @cache_page(60 * 5)  # 5 minutes
  def monthly_availability(request):
  ```
- [ ] **Cache keys descriptive**
  ```python
  cache_key = f"availability:monthly:{year}:{month}:{usuario_id}"
  ```
- [ ] **Cache invalidation** on data updates

#### Algorithm Efficiency
- [ ] **Avoid O(n²)** when possible (use sets, dicts)
- [ ] **Pagination** for large datasets
- [ ] **Lazy evaluation** (generators for large iterables)

#### Frontend Performance
- [ ] **Bundle size minimal** (tree-shaking, code splitting)
- [ ] **Images optimized** (WebP, lazy loading)
- [ ] **CSS in production minified**

#### Premature Optimization
- [ ] **Flag over-optimization** (profile before optimizing)
- [ ] **Readability > micro-optimization**

---

### 8. **Testing Quality**

#### Test Behavior, Not Implementation
- [ ] **Test what code does**, not how
  ```python
  # Good
  def test_approve_changes_status_to_aprovado():
      sol = create_solicitacao(status='pendente')
      approve(sol)
      assert sol.status == 'aprovado'

  # Bad
  def test_approve_calls_save():
      sol = Mock()
      approve(sol)
      sol.save.assert_called_once()  # Testing implementation detail
  ```

#### Test Structure
- [ ] **Describe clause organization**
  ```python
  class TestAvailabilityService:
      class TestCheckConflicts:
          def test_detects_total_overlap(self):
          def test_detects_partial_overlap(self):
          def test_allows_adjacent_events(self):
  ```

#### Assertions
- [ ] **3rd person verbs**, not "should"
  ```python
  # Good
  def test_approval_creates_audit_log():
  def test_user_cannot_approve_own_solicitacao():

  # Bad
  def test_should_create_audit_log():
  def test_user_shouldnt_approve_own():
  ```

#### Coverage
- [ ] **Bug tests** (test for each fixed bug)
- [ ] **Critical paths 100%**
- [ ] **Business logic 90%+**
- [ ] **Happy path + edge cases + error cases**

#### Fixtures
- [ ] **Reusable fixtures** (pytest/Django fixtures)
- [ ] **Factory pattern** for complex objects
- [ ] **Fixtures descriptive names**

---

### 9. **Code Quality**

#### Comments
- [ ] **98% should be functions/variables**, not comments
  ```python
  # Bad
  # Check if user has Superintendência permission
  if user.groups.filter(name='Superintendência').exists():

  # Good
  def has_superintendencia_permission(user):
      return user.groups.filter(name='Superintendência').exists()

  if has_superintendencia_permission(user):
  ```
- [ ] **WHY, not WHAT**
  ```python
  # Good
  # PA-05: Persistent audit required for compliance
  AuditLog.objects.create(...)

  # Bad
  # Create audit log
  AuditLog.objects.create(...)
  ```
- [ ] **Docstrings on public functions**

#### Functions
- [ ] **Single Responsibility Principle**
- [ ] **Max 20-30 lines** (complex functions → split)
- [ ] **Pure when possible** (same input = same output)

#### Duplication
- [ ] **DRY principle** (used 3+ times → extract)
- [ ] **Shared utilities** in `lib/` or `utils/`

#### Complexity
- [ ] **Cyclomatic complexity <10** (flag if >15)
- [ ] **Cognitive complexity** low (easy to understand)

---

### 10. **Compliance Checks (AS v2 Specific)**

#### Cláusulas Pétreas (CP-01 to CP-06)
- [ ] **CP-01**: Docker-only (check `/.dockerenv`)
- [ ] **CP-02**: Manual approval (PA-01 to PA-07) if approval flow
- [ ] **CP-03**: Availability rules (RD-01 to RD-08) if conflicts
- [ ] **CP-04**: Workflow followed (Understand → Plan → Implement → Test)
- [ ] **CP-05**: v1 untouched
- [ ] **CP-06**: Conventional commits (`feat:`, `fix:`, etc.)

#### Regras de Disponibilidade (RD-01 to RD-08)
If code handles availability/conflicts:
- [ ] **RD-01**: Non-overlapping (fim==início OK)
- [ ] **RD-02**: Total block (T) prevents any event
- [ ] **RD-03**: Partial block (P) prevents subinterval
- [ ] **RD-04**: Travel buffer (D) between cities
- [ ] **RD-05**: Daily capacity (M)
- [ ] **RD-06**: Timezone-aware (America/Fortaleza)
- [ ] **RD-07**: Priority: Blocks → Conflicts → Buffer → Capacity
- [ ] **RD-08**: Structured messages (code, title, detail, ref_id)

#### Política de Aprovação (PA-01 to PA-07)
If code handles approvals:
- [ ] **PA-01**: No auto-approval for SUPER projects
- [ ] **PA-02**: Only Superintendência can approve/reject
- [ ] **PA-03**: External integrations AFTER approval
- [ ] **PA-04**: Initial status = 'pendente' (SUPER)
- [ ] **PA-05**: AuditLog persistent (usuario, action, details, ip)
- [ ] **PA-06**: UI buttons hidden for non-authorized
- [ ] **PA-07**: 5 mandatory tests passing

---

## Output Format

### For Each Issue:

**File:line**: Exact location
**Issue**: Clear description
**Rule**: Reference (CLAUDE-principles.md:L89, PA-02, RD-06, or category name)
**Severity**: CRITICAL | HIGH | MEDIUM | LOW
**Suggestion**: Code fix or refactoring (concrete, actionable)

**Example**:
```
apps/core/views.py:145
Issue: Missing AuditLog for approval action
Rule: PA-05 (Política de Aprovação Manual)
Severity: HIGH (compliance violation)
Suggestion:
  AuditLog.objects.create(
      usuario=request.user,
      action='APPROVE',
      model_name='Solicitacao',
      details={"solicitacao_id": sol.id, "prev_status": "pendente", "new_status": "aprovado"}
  )
```

---

## Final Summary

### Counts
- **CRITICAL**: [count] (security, data loss)
- **HIGH**: [count] (compliance, major bugs)
- **MEDIUM**: [count] (quality, maintainability)
- **LOW**: [count] (style, minor improvements)

### Scores (0-100)
- **Type Safety**: [score] (type hints, Pyright compliance)
- **Security**: [score] (OWASP compliance)
- **Accessibility**: [score] (WCAG 2.0 compliance)
- **Performance**: [score] (DB queries, caching, algorithms)
- **Testing**: [score] (coverage, quality, behavior-driven)
- **Compliance**: [score] (CP, RD, PA rules)

### Top 3 Priorities
1. [Most critical fix with severity and file reference]
2. [Second most critical fix]
3. [Third most critical fix]

### Approval Status
- ✅ **Approved** (no critical/high issues)
- ⚠️ **Approved with minor changes** (only low issues)
- ❌ **Requires changes** (critical or high issues present)

---

## References
- **Code Quality**: `.claude/CLAUDE-principles.md`
- **Business Rules**: `.claude/skills/aprender-domain/SKILL.md`
- **Django Patterns**: `.claude/skills/django-patterns/SKILL.md`
- **Main Context**: `.claude/CLAUDE.md`

---

**Framework Origin**: Adapted from Premium Claude Code Package (TypeScript/React)
**Customized For**: AS v2 (Python/Django/DRF)
**Adaptations Applied**:
- Removed React/TypeScript specific checks
- Added Python/Django/DRF standards
- Added AS v2 compliance checks (CP, RD, PA)
- Focus on PEP 257, Pyright strict, Django ORM

**Last Updated**: 2025-11-24
