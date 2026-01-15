---
description: Comprehensive code review for AS v2 - 11 categories (clarity, security, a11y, performance, React perf, compliance). Adapted from premium Claude Code package + Vercel React Best Practices.
argument-hint: [file or directory to review]
allowed-tools: Bash(git:*)
---

# Enhanced Code Review — AS v2

Review code: $ARGUMENTS

**Review Framework**: 11-category comprehensive analysis
- **Primary Focus**: Clarity (naming, anti-patterns, specificity)
- **Context**: Python/Django/DRF + React 18/Vite/Ant Design + AS v2 business rules (CP, RD, PA)
- **NEW**: React Performance (Vercel Engineering's 45 rules)

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

### 8. **React Performance** (Vercel Best Practices)

> 45 regras da Vercel Engineering adaptadas para React 18 + Vite + Ant Design

#### 🔴 CRÍTICO — Eliminating Waterfalls

**Why**: Waterfall requests are the #1 cause of slow page loads.

- [ ] **Parallel async operations** with `Promise.all()`
  ```tsx
  // Bad - Sequential (waterfall)
  const users = await fetchUsers();
  const projects = await fetchProjects();

  // Good - Parallel
  const [users, projects] = await Promise.all([
    fetchUsers(),
    fetchProjects()
  ]);
  ```
- [ ] **Defer await until needed** - Move `await` to where data is actually used
  ```tsx
  // Bad - Blocks even if not used
  async function handler(needsData: boolean) {
    const data = await fetchData();
    if (!needsData) return null;
    return <Component data={data} />;
  }

  // Good - Only fetches when needed
  async function handler(needsData: boolean) {
    if (!needsData) return null;
    const data = await fetchData();
    return <Component data={data} />;
  }
  ```
- [ ] **Strategic Suspense boundaries** - Don't block entire UI
  ```tsx
  // Good - Independent loading states
  <Suspense fallback={<HeaderSkeleton />}>
    <Header />
  </Suspense>
  <Suspense fallback={<ContentSkeleton />}>
    <Content />
  </Suspense>
  ```

#### 🔴 CRÍTICO — Bundle Size Optimization

**Why**: Large bundles directly impact TTI (Time to Interactive) and LCP.

- [ ] **Dynamic imports for heavy components** (React.lazy)
  ```tsx
  // Bad - Loaded in main bundle
  import MonacoEditor from '@monaco-editor/react';

  // Good - Lazy loaded when needed
  const MonacoEditor = React.lazy(() => import('@monaco-editor/react'));

  // With Suspense
  <Suspense fallback={<EditorSkeleton />}>
    <MonacoEditor />
  </Suspense>
  ```
- [ ] **Avoid barrel file imports** from large libraries
  ```tsx
  // Bad - Imports entire library (~200-800ms)
  import { Button, Table, Modal, Form } from 'antd';

  // Good - Direct imports (tree-shakeable)
  import Button from 'antd/es/button';
  import Table from 'antd/es/table';
  // Or with proper Vite config for antd
  ```
- [ ] **Defer non-critical third-party** (analytics, error tracking)
  ```tsx
  // Bad - Blocks initial render
  import * as Sentry from '@sentry/react';
  Sentry.init({ dsn: '...' });

  // Good - Load after hydration
  useEffect(() => {
    import('@sentry/react').then(Sentry => {
      Sentry.init({ dsn: '...' });
    });
  }, []);
  ```
- [ ] **Preload on user intent** (hover, focus)
  ```tsx
  // Preload heavy modal on button hover
  const preloadModal = () => import('./HeavyModal');

  <button
    onMouseEnter={preloadModal}
    onFocus={preloadModal}
    onClick={() => setShowModal(true)}
  >
    Open Modal
  </button>
  ```

#### 🟡 MÉDIO — Re-render Optimization

**Why**: Unnecessary re-renders cause UI jank and wasted CPU cycles.

- [ ] **useMemo for expensive computations**
  ```tsx
  // Bad - Recalculates on every render
  const sortedItems = items.sort((a, b) => a.date - b.date);

  // Good - Only recalculates when items change
  const sortedItems = useMemo(
    () => items.sort((a, b) => a.date - b.date),
    [items]
  );
  ```
- [ ] **useCallback for callbacks passed to children**
  ```tsx
  // Bad - New function on every render
  <ChildComponent onClick={() => handleClick(id)} />

  // Good - Stable reference
  const handleItemClick = useCallback(() => handleClick(id), [id]);
  <ChildComponent onClick={handleItemClick} />
  ```
- [ ] **Derived state instead of state + useEffect**
  ```tsx
  // Bad - Extra state + effect
  const [items, setItems] = useState([]);
  const [filteredItems, setFilteredItems] = useState([]);
  useEffect(() => {
    setFilteredItems(items.filter(i => i.active));
  }, [items]);

  // Good - Derived during render
  const [items, setItems] = useState([]);
  const filteredItems = useMemo(
    () => items.filter(i => i.active),
    [items]
  );
  ```
- [ ] **Lazy state initialization** for expensive defaults
  ```tsx
  // Bad - Runs on every render
  const [state, setState] = useState(expensiveComputation());

  // Good - Runs only once
  const [state, setState] = useState(() => expensiveComputation());
  ```
- [ ] **useTransition for non-urgent updates**
  ```tsx
  const [isPending, startTransition] = useTransition();

  const handleSearch = (query: string) => {
    // Urgent: update input immediately
    setQuery(query);

    // Non-urgent: can be interrupted
    startTransition(() => {
      setFilteredResults(filterResults(query));
    });
  };
  ```
- [ ] **Extract to memoized components** for early returns
  ```tsx
  // Bad - Expensive work even when loading
  function UserCard({ userId, loading }) {
    const avatar = useMemo(() => computeAvatar(userId), [userId]);
    if (loading) return <Skeleton />;
    return <Card avatar={avatar} />;
  }

  // Good - Skip computation when loading
  function UserCard({ userId, loading }) {
    if (loading) return <Skeleton />;
    return <UserCardContent userId={userId} />;
  }

  const UserCardContent = React.memo(({ userId }) => {
    const avatar = computeAvatar(userId);
    return <Card avatar={avatar} />;
  });
  ```

#### 🟡 MÉDIO — Rendering Performance

**Why**: Inefficient rendering causes layout thrashing and slow paints.

- [ ] **Hoist static JSX outside components**
  ```tsx
  // Bad - Recreated on every render
  function Component() {
    const icon = <Icon name="check" />;
    return <div>{icon}</div>;
  }

  // Good - Created once
  const CheckIcon = <Icon name="check" />;
  function Component() {
    return <div>{CheckIcon}</div>;
  }
  ```
- [ ] **Explicit conditional rendering** (ternary, not &&)
  ```tsx
  // Bad - Can render "0" or "NaN"
  {count && <Badge count={count} />}

  // Good - Explicit boolean check
  {count > 0 ? <Badge count={count} /> : null}
  ```
- [ ] **CSS content-visibility for long lists**
  ```css
  /* Skip rendering off-screen items */
  .list-item {
    content-visibility: auto;
    contain-intrinsic-size: 0 50px;
  }
  ```
- [ ] **Prevent hydration mismatch** (client-only storage)
  ```tsx
  // Bad - Mismatch between server and client
  const [theme] = useState(localStorage.getItem('theme'));

  // Good - Sync after mount
  const [theme, setTheme] = useState('light');
  useEffect(() => {
    setTheme(localStorage.getItem('theme') ?? 'light');
  }, []);
  ```

#### 🟢 BAIXO — JavaScript Performance

**Why**: Micro-optimizations that matter in hot paths.

- [ ] **Set/Map for O(1) lookups** instead of Array.find()
  ```tsx
  // Bad - O(n) on every check
  const isSelected = selectedIds.find(id => id === item.id);

  // Good - O(1) lookup
  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const isSelected = selectedSet.has(item.id);
  ```
- [ ] **Combine array iterations** (.filter + .map → single loop)
  ```tsx
  // Bad - Two iterations
  const result = items.filter(x => x.active).map(x => x.name);

  // Good - Single iteration
  const result = items.reduce((acc, x) => {
    if (x.active) acc.push(x.name);
    return acc;
  }, []);
  ```
- [ ] **Cache expensive function results**
  ```tsx
  const cache = useMemo(() => new Map(), []);

  const getProcessedItem = useCallback((id: string) => {
    if (cache.has(id)) return cache.get(id);
    const result = expensiveProcess(id);
    cache.set(id, result);
    return result;
  }, [cache]);
  ```
- [ ] **Hoist RegExp creation** outside render
  ```tsx
  // Bad - New RegExp on every render
  function Component({ pattern }) {
    const regex = new RegExp(pattern);
    // ...
  }

  // Good - Memoized
  function Component({ pattern }) {
    const regex = useMemo(() => new RegExp(pattern), [pattern]);
    // ...
  }
  ```
- [ ] **toSorted() for immutable sorting** (ES2023)
  ```tsx
  // Bad - Mutates original array
  const sorted = items.sort((a, b) => a.name.localeCompare(b.name));

  // Good - Returns new array
  const sorted = items.toSorted((a, b) => a.name.localeCompare(b.name));
  ```

#### React Performance — Exemplos AS v2

| Padrão | Onde Aplicar no AS v2 |
|--------|----------------------|
| Dynamic imports | `MonthlyCalendar`, `GCalDashboard`, `AdminModule` |
| Ant Design imports | Todos os arquivos que usam `import { } from 'antd'` |
| useMemo | `SolicitacoesList` (filtros), `DisponibilidadeGrid` |
| Set lookups | `AvailabilityCheck` (selectedFormadores) |
| Suspense boundaries | Wizard steps, Modal contents |
| useTransition | Search inputs, filter changes |

---

### 9. **Testing Quality** (renumbered from 8)

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

### 10. **Code Quality**

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

### 11. **Compliance Checks (AS v2 Specific)**

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
