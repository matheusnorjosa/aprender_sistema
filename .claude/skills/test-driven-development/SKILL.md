---
name: test-driven-development
description: Write the failing test before the implementation in AS v2 (pytest + Django/DRF). Use when implementing a feature or fixing a bug, before any production code is written.
---

# Test-Driven Development (TDD)

## Overview

Write the test first. Watch it fail. Write minimal code to pass.

**Core principle:** If you didn't watch the test fail, you don't know if it tests the right thing.

**Violating the letter of the rules is violating the spirit of the rules.**

## When to Use

**Always:**
- New features
- Bug fixes
- Refactoring
- Behavior changes

**Exceptions (ask your human partner):**
- Throwaway prototypes
- Generated code
- Configuration files

Thinking "skip TDD just this once"? Stop. That's rationalization.

## The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Write code before the test? Delete it. Start over.

**No exceptions:**
- Don't keep it as "reference"
- Don't "adapt" it while writing tests
- Don't look at it
- Delete means delete

Implement fresh from tests. Period.

## Red-Green-Refactor

### RED - Write Failing Test

Write one minimal test showing what should happen. Use `APITestCase` for
endpoints, `TestCase` for models/services, and the factories in
`apps/core/tests/factories.py` (`force_authenticate` to seed the actor).

**Good:**
```python
def test_non_dat_user_is_forbidden(self):
    user = UsuarioFactory()  # no DAT group
    self.client.force_authenticate(user=user)
    resp = self.client.get(reverse("core:dat-registro-list"))
    self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
```
Clear name, tests real behavior through the URL, one thing. Asserts the `403`
status (the contract) — not the response body shape.

**Bad:**
```python
def test_access(self):
    user = UsuarioFactory()
    view = DATRegistroViewSet()
    view.request = Mock(user=user)
    self.assertFalse(view.get_permissions()[0].has_permission(view.request, view))
```
Vague name, pokes a mocked view internal instead of the real request/RBAC path.

**Requirements:**
- One behavior
- Clear name
- Real code through the URL/ORM (no mocks unless unavoidable)

### Verify RED - Watch It Fail

**MANDATORY. Never skip.** Tests run inside the dev container (CP-01):

```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/test_dat_registros.py -v
```

Confirm:
- Test fails (not errors)
- Failure message is expected
- Fails because feature missing (not typos)

**Test passes?** You're testing existing behavior. Fix test.
**Test errors?** Fix error, re-run until it fails correctly.

### GREEN - Minimal Code

Write simplest code to pass the test.

**Good:**
```python
class DATRegistroViewSet(viewsets.ModelViewSet):
    permission_classes = [HasPerm("manage_admin_registries")]
    # ...
```
Just enough for the `403` test to pass — RBAC via the canonical `HasPerm`.

**Bad:**
```python
class DATRegistroViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == "list" and self.request.query_params.get("export"):
            return [HasPerm("export_datregistro")]
        # ... branches the test never asked for — YAGNI
```

Don't add features, refactor other code, or "improve" beyond the test.

### Verify GREEN - Watch It Pass

**MANDATORY.**

```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/test_dat_registros.py -v
```

Confirm:
- Test passes
- Other tests still pass
- Output pristine (no errors, warnings)
- Coverage holds the 85% gate (`fail_under = 85` in `v2/backend/pytest.ini`)

**Test fails?** Fix code, not test.
**Other tests fail?** Fix now.

### REFACTOR - Clean Up

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green. Don't add behavior.

### Repeat

Next failing test for next feature.

## Rationalizations and Red Flags — STOP

Any row below means: stop, delete the untested code, start over with TDD.

| Excuse / Red flag | Reality | Action |
|-------------------|---------|--------|
| "Too simple to test" | Simple code breaks. Test takes 30 seconds. | Write the test. |
| "I'll test after" / "tests added later" | A test passing immediately proves nothing. | Write the test first. |
| "Tests after achieve the same goal" | Tests-after = "what does this do?" Tests-first = "what should this do?" | Write the test first. |
| "Already manually tested it" | Ad-hoc ≠ systematic. No record, can't re-run. | Write the test. |
| "Deleting X hours is wasteful" | Sunk cost fallacy. Unverified code is technical debt. | Delete it. Start over. |
| "Keep as reference / adapt existing code" | You'll adapt it — that's testing after. Delete means delete. | Delete it. Start fresh from tests. |
| "Need to explore first" | Fine. Throw away the exploration. | Restart with TDD. |
| "Test is hard = design unclear" | Listen to the test. Hard to test = hard to use. | Simplify the interface, then test. |
| "TDD will slow me down" | TDD is faster than debugging. Pragmatic = test-first. | Write the test first. |
| Code written before any test | No failing test gated it. | Delete the code. Start over. |
| Test passes on first run | It tests existing behavior, not the new one. | Fix the test so it fails first. |
| Can't explain why the test failed | You didn't watch it fail for the right reason. | Re-run; confirm the failure is the missing feature. |
| Rationalizing "just this once" | That's the rationalization the Iron Law forbids. | Stop. Follow the law. |

## Verification Checklist

Before marking work complete:

- [ ] Every new function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason (feature missing, not typo)
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output pristine (no errors, warnings)
- [ ] Tests use real code (mocks only if unavoidable)
- [ ] Edge cases and errors covered

Can't check all boxes? You skipped TDD. Start over.

## Worked examples

Full RED→GREEN→REFACTOR walkthroughs (a model `__str__` and a DRF endpoint with
RBAC), with the real `docker exec ... pytest` commands and the 85% gate, live in
[`reference/worked-examples.md`](reference/worked-examples.md).

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API. Write assertion first. Ask your human partner. |
| Test too complicated | Design too complicated. Simplify interface. |
| Must mock everything | Code too coupled. Use dependency injection. |
| Test setup huge | Extract helpers. Still complex? Simplify design. |

## Final Rule

```
Production code → test exists and failed first
Otherwise → not TDD
```

No exceptions without your human partner's permission.
