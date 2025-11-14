---
description: Run tests with coverage report and enforce 90%+ threshold
argument-hint: [optional: specific test path or app]
---

# Test Coverage — Quality Gate

Run tests with coverage: ${ARGUMENTS:-all tests}

## Approach:

### 1. Coverage Target

**AS v2 Standards**:
- **Overall**: 90%+ coverage required
- **Critical modules**: 100% coverage required
  - `apps/core/services/availability_service.py` (RD-01 to RD-08)
  - `apps/core/services/approval_service.py` (PA-01 to PA-07)
  - `apps/core/models.py` (Solicitacao.save logic)

### 2. Run Coverage

```bash
# All tests with coverage
docker compose exec web pytest --cov=apps --cov-report=term-missing --cov-report=html

# Specific app
docker compose exec web pytest apps/core/tests/ --cov=apps.core --cov-report=term-missing

# Specific module
docker compose exec web pytest apps/core/tests/test_availability_service.py \
  --cov=apps.core.services.availability_service \
  --cov-report=term-missing

# With minimum threshold (fail if below 90%)
docker compose exec web pytest --cov=apps --cov-fail-under=90

# Generate XML report (for CI)
docker compose exec web pytest --cov=apps --cov-report=xml --cov-report=term
```

### 3. Interpret Coverage Report

**Terminal output**:
```
Name                                        Stmts   Miss  Cover   Missing
---------------------------------------------------------------------------
apps/core/models.py                           250      5    98%   145-149
apps/core/services/availability_service.py     180      0   100%
apps/core/services/approval_service.py         120      0   100%
apps/core/views.py                             300     30    90%
apps/core/serializers.py                       150     15    90%
---------------------------------------------------------------------------
TOTAL                                         1000     50    95%
```

**What to look for**:
- **Stmts**: Total statements (lines of code)
- **Miss**: Statements not covered by tests
- **Cover**: Coverage percentage
- **Missing**: Line numbers not covered

### 4. HTML Report (Detailed)

```bash
# Generate HTML report
docker compose exec web pytest --cov=apps --cov-report=html

# View report (opens in browser)
# File: htmlcov/index.html
```

**HTML Report Features**:
- Line-by-line coverage visualization
- Click files to see covered/uncovered lines
- Green = covered, Red = uncovered
- Branch coverage (if/else paths)

### 5. Coverage Analysis

#### High Priority (Must Fix)

**Uncovered lines in critical modules**:
```
apps/core/services/availability_service.py   98%   145-149
```

**Action**: Add tests for lines 145-149

**Example**:
```python
# Uncovered code (lines 145-149)
def check_conflicts(...):
    # ... covered code ...

    if daily_capacity_exceeded:  # Line 145 not tested
        conflicts.append(...)     # Line 146 not tested
        return result             # Line 147 not tested
```

**Missing test**:
```python
def test_daily_capacity_exceeded():
    """Test daily capacity limit (RD-05)."""
    # Create multiple events exceeding daily limit
    # Assert conflict code 'M' returned
```

#### Medium Priority (Should Fix)

**Low coverage in non-critical modules**:
```
apps/core/views.py   85%
```

**Action**: Identify untested edge cases, add tests

#### Low Priority (Optional)

**Defensive code / error handling**:
```python
try:
    result = compute_something()
except Exception as e:  # Rarely triggered in tests
    logger.error(f"Unexpected error: {e}")
    raise
```

**Action**: May skip if truly exceptional (but document why)

### 6. Increase Coverage (Strategies)

#### Strategy 1: Test Edge Cases

**Example**: RD-01 (Non-overlapping)
```python
# Already tested: Total overlap, partial overlap, no overlap
# Missing: Edge case - fim == inicio (adjacent)

def test_no_conflict_adjacent_end_equals_start():
    """Adjacent events (fim == inicio) do not conflict (RD-01)."""
    # Event 1: 09:00-12:00
    # Event 2: 12:00-15:00 (starts exactly when Event 1 ends)
    # Expected: No conflict
```

#### Strategy 2: Test Error Paths

**Example**: Validation errors
```python
def test_create_solicitacao_with_invalid_time_range():
    """Creating solicitacao with fim <= inicio raises ValidationError."""
    with pytest.raises(ValidationError):
        Solicitacao.objects.create(
            inicio=datetime(..., 12, 0),
            fim=datetime(..., 9, 0),  # Before inicio
            ...
        )
```

#### Strategy 3: Test Branches (if/else)

**Example**: Conditional logic
```python
# Code under test
def approve(solicitacao):
    if solicitacao.status != 'pendente':
        raise ValueError("Already processed")  # Branch 1

    solicitacao.status = 'aprovado'  # Branch 2
    solicitacao.save()

# Test Branch 1
def test_approve_already_processed_raises_error():
    solicitacao.status = 'aprovado'
    with pytest.raises(ValueError):
        approve(solicitacao)

# Test Branch 2
def test_approve_pending_solicitacao_succeeds():
    solicitacao.status = 'pendente'
    approve(solicitacao)
    assert solicitacao.status == 'aprovado'
```

#### Strategy 4: Test Loops

**Example**: Batch processing
```python
# Code under test
def process_batch(items):
    results = []
    for item in items:
        result = process_item(item)
        results.append(result)
    return results

# Tests needed
def test_process_batch_empty_list():
    """Empty list returns empty results."""
    assert process_batch([]) == []

def test_process_batch_single_item():
    """Single item processed correctly."""
    assert len(process_batch([item1])) == 1

def test_process_batch_multiple_items():
    """Multiple items processed correctly."""
    assert len(process_batch([item1, item2, item3])) == 3
```

### 7. Critical Module Checklist

#### availability_service.py (RD-01 to RD-08)

**Required tests** (17 total):
- [ ] `test_conflict_overlap_total` (RD-01)
- [ ] `test_conflict_overlap_partial` (RD-01)
- [ ] `test_no_conflict_adjacent_end_equals_start` (RD-01)
- [ ] `test_block_total_T_prevents_any_event` (RD-02)
- [ ] `test_block_partial_P_prevents_inside_allows_outside` (RD-03)
- [ ] `test_travel_buffer_between_cities_required` (RD-04)
- [ ] `test_same_city_allows_zero_buffer` (RD-04)
- [ ] `test_daily_capacity_M_exceeded` (RD-05)
- [ ] `test_multi_formador_any_conflict_blocks` (RD-01)
- [ ] `test_timezone_aware_fortaleza_localtime` (RD-06)
- [ ] `test_conflict_messages_include_codes_and_intervals` (RD-08)
- [ ] `test_check_conflicts_requires_authentication` (API)
- [ ] `test_check_conflicts_missing_params_returns_400` (API)
- [ ] `test_check_conflicts_returns_conflicts` (API)
- [ ] `test_check_many_batch_processing` (API)
- [ ] `test_check_conflicts_rbac_self_or_privileged` (API)
- [ ] `test_check_conflicts_structured_messages` (API)

**Target**: 100% coverage

**Validation**:
```bash
docker compose exec web pytest apps/core/tests/test_availability_service.py \
  --cov=apps.core.services.availability_service \
  --cov-report=term-missing \
  --cov-fail-under=100
```

#### approval_service.py (PA-01 to PA-07)

**Required tests** (5 mandatory):
- [ ] `test_never_auto_approves_on_clean_or_save` (PA-01)
- [ ] `test_only_superintendencia_can_approve_or_reject` (PA-02)
- [ ] `test_non_privileged_user_gets_403_on_approval_endpoint` (PA-02)
- [ ] `test_calendar_integration_not_called_before_approval` (PA-03)
- [ ] `test_approval_flow_records_audit_log` (PA-05)

**Target**: 100% coverage

**Validation**:
```bash
docker compose exec web pytest apps/core/tests/test_approval_policy_PA.py \
  --cov=apps.core.models \
  --cov=apps.core.views \
  --cov-report=term-missing \
  --cov-fail-under=100
```

### 8. Exclude Unnecessary Code

**Coverage configuration** (`.coveragerc` or `pyproject.toml`):

```ini
# .coveragerc
[run]
source = apps
omit =
    */migrations/*
    */tests/*
    */test_*.py
    */__pycache__/*
    */venv/*
    */settings.py
    */manage.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    def __str__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

**Example usage in code**:
```python
def debug_only_function():  # pragma: no cover
    """Only used for debugging, not in production."""
    print("Debug info...")
```

### 9. CI Integration

**GitHub Actions** (`.github/workflows/test-coverage.yml`):
```yaml
name: Test Coverage

on: [push, pull_request]

jobs:
  test-coverage:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest-cov

      - name: Run tests with coverage
        run: |
          pytest --cov=apps --cov-report=xml --cov-report=term --cov-fail-under=90

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### 10. Coverage by Component

**Run coverage for specific components**:

```bash
# Models
docker compose exec web pytest apps/core/tests/test_models.py \
  --cov=apps.core.models --cov-report=term-missing

# Serializers
docker compose exec web pytest apps/core/tests/test_serializers.py \
  --cov=apps.core.serializers --cov-report=term-missing

# Views
docker compose exec web pytest apps/core/tests/test_views.py \
  --cov=apps.core.views --cov-report=term-missing

# Services
docker compose exec web pytest apps/core/tests/test_availability_service.py \
  --cov=apps.core.services --cov-report=term-missing
```

### 11. Coverage Report Summary

**Generate summary report**:
```bash
# Terminal summary
docker compose exec web pytest --cov=apps --cov-report=term

# Generate badge (for README)
docker compose exec web pytest --cov=apps --cov-report=term | grep TOTAL
```

**Example output**:
```
TOTAL    1000     50    95%
```

**Badge format** (for README.md):
```markdown
![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)
```

### 12. Fix Uncovered Code

**Workflow**:
1. Run coverage report
2. Identify uncovered lines
3. Analyze why uncovered (edge case? error path? dead code?)
4. Write test for uncovered code
5. Re-run coverage
6. Repeat until 90%+ achieved

**Example**:
```bash
# Step 1: Run coverage
docker compose exec web pytest --cov=apps.core.services.availability_service \
  --cov-report=term-missing

# Output shows:
# availability_service.py   145-149  (5 lines uncovered)

# Step 2: View code at lines 145-149
# (Use Read tool or editor)

# Step 3: Write test
# (Create test_daily_capacity_exceeded)

# Step 4: Re-run coverage
docker compose exec web pytest --cov=apps.core.services.availability_service \
  --cov-report=term-missing

# Output shows:
# availability_service.py   100%  (success!)
```

### 13. Output

**If coverage >= 90%**:
```
✅ COVERAGE THRESHOLD MET

Coverage Report:
- Total statements: 1000
- Covered: 950
- Coverage: 95%
- Threshold: 90%

Status: PASS

Critical Modules:
- availability_service.py: 100% ✓
- approval_service.py: 100% ✓
- models.py: 98% ✓

HTML Report: htmlcov/index.html
```

**If coverage < 90%**:
```
❌ COVERAGE THRESHOLD NOT MET

Coverage Report:
- Total statements: 1000
- Covered: 850
- Coverage: 85%
- Threshold: 90%

Status: FAIL

Uncovered modules:
- views.py: 80% (60 lines uncovered)
- serializers.py: 85% (23 lines uncovered)

Action Required:
1. Review uncovered lines in HTML report (htmlcov/index.html)
2. Write tests for uncovered code
3. Re-run coverage until 90%+ achieved

Critical: Do not merge PR until coverage threshold met.
```

### 14. Best Practices

#### DO
- ✅ Run coverage before every PR
- ✅ Aim for 90%+ overall, 100% critical
- ✅ Test behavior, not implementation
- ✅ Use HTML report for detailed analysis
- ✅ Exclude migrations, test files, vendored code
- ✅ Test edge cases and error paths
- ✅ Document intentional coverage exclusions

#### DON'T
- ❌ Write tests just to hit coverage (test behavior!)
- ❌ Exclude critical code with `pragma: no cover`
- ❌ Ignore uncovered error handling
- ❌ Test private methods directly (test via public API)
- ❌ Merge PRs below threshold
- ❌ Focus on 100% coverage over code quality

### 15. Quick Reference

| Command | Purpose |
|---------|---------|
| `pytest --cov` | Run tests with coverage |
| `--cov-report=term-missing` | Show uncovered lines |
| `--cov-report=html` | Generate HTML report |
| `--cov-fail-under=90` | Fail if below 90% |
| `--cov=apps.core` | Coverage for specific app |
| `--cov-report=xml` | Generate XML (for CI) |

## Reference

- **Testing Philosophy**: `.claude/CLAUDE-principles.md` (Testing section)
- **Pytest Docs**: https://docs.pytest.org/en/stable/
- **Coverage.py**: https://coverage.readthedocs.io/

---

**Focus**: Enforce quality gate (90%+), test behavior, cover critical paths.
