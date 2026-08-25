# TDD worked examples — AS v2 (pytest + Django/DRF)

Run tests inside the dev container (CP-01: v2 roda APENAS em Docker):

```bash
docker exec aprender_dev-web-1 pytest apps/core/tests/test_dat_registros.py -v
```

The 85% coverage gate is enforced by `fail_under = 85` in `v2/backend/pytest.ini`
(policy: `v2/docs/analysis/COVERAGE_POLICY.md`). A green run that drops below 85%
still fails — new code needs new tests.

## Example: model behavior (RED → GREEN → REFACTOR)

**Behavior:** `ProjetoGeral.__str__` must show whether the project uses Avaliar.

**RED** — write the failing test first (`apps/core/tests/test_dat_registros.py`):

```python
from django.test import TestCase
from apps.core.models import ProjetoGeral

class ProjetoGeralStrTests(TestCase):
    def test_str_marks_avaliar_status(self):
        com = ProjetoGeral.objects.create(nome="Com", usa_avaliar=True)
        sem = ProjetoGeral.objects.create(nome="Sem", usa_avaliar=False)
        self.assertIn("✅", str(com))
        self.assertIn("⭕", str(sem))
```

**Verify RED**

```bash
$ docker exec aprender_dev-web-1 pytest apps/core/tests/test_dat_registros.py::ProjetoGeralStrTests -v
FAILED — AssertionError: '✅' not found in 'Com'
```

It fails because `__str__` does not yet render the marker — not because of a typo.

**GREEN** — minimal code on the model:

```python
def __str__(self) -> str:
    marca = "✅" if self.usa_avaliar else "⭕"
    return f"{marca} {self.nome}"
```

**Verify GREEN**

```bash
$ docker exec aprender_dev-web-1 pytest apps/core/tests/test_dat_registros.py::ProjetoGeralStrTests -v
2 passed
```

**REFACTOR** — only after green: extract the marker if a second model needs it. Keep tests green; add no behavior.

## Example: DRF endpoint with RBAC

Use `rest_framework.test.APITestCase`, the factories in
`apps/core/tests/factories.py`, and `force_authenticate` to seed the actor.

**Behavior:** a user without DAT access gets `403` on the registros list.

**RED**

```python
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from apps.core.tests.factories import UsuarioFactory

class DATRegistroAccessTests(APITestCase):
    def test_non_dat_user_is_forbidden(self):
        user = UsuarioFactory()  # no DAT group
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse("core:dat-registro-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
```

Assert on the `403` status, not on the response body shape — the status is the
contract (see memory `identity-oriented-test-asserts`).

**Verify RED → GREEN** as above: watch it fail (endpoint open / wrong permission),
add the `HasPerm` permission class, watch it pass, confirm sibling tests stay green.

Factories use `factory.Sequence` for unique fields (deterministic — never `hash()`),
so parallel xdist workers don't collide.
