# Test template — pytest + Django/DRF, PA layout

Conventions:
- **Nested classes** map to requirement groups (`TestSolicitacaoApproval` → `TestManualApproval`
  for PA-01, `TestPermissions` for PA-02). Docstrings name the rule being tested.
- **Test behavior, not implementation** — assert observable outcome (status code, persisted
  state, audit log), never that a method was called.
- **Determinism**: build unique CPF/email with an atomic counter, never `abs(hash(str)) % N`
  (PYTHONHASHSEED makes it non-deterministic). Never hardcode a date whose assertion depends
  on "deadline not yet reached".
- **Pyright header**: new test files need the same `# pyright: ...=false` header the
  neighboring test files carry, or CI breaks.

```python
import pytest
from django.contrib.auth.models import Group
from apps.core.models import Usuario, Solicitacao
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@pytest.fixture
def tz_fortaleza():
    return ZoneInfo("America/Fortaleza")


@pytest.fixture
def grupo_superintendencia(db):
    return Group.objects.get_or_create(name="Superintendência")[0]


@pytest.fixture
def usuario_superintendencia(db, grupo_superintendencia):
    usuario = Usuario.objects.create_user(
        username="super1", email="super@example.com", password="pass123",
    )
    usuario.groups.add(grupo_superintendencia)
    return usuario


@pytest.fixture
def solicitacao_pendente(db, usuario_superintendencia, tz_fortaleza):
    from apps.core.models import Projeto, Municipio

    projeto = Projeto.objects.create(nome="Teste", fluxo="SUPER")
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
    inicio = datetime(2025, 1, 15, 9, 0, tzinfo=tz_fortaleza)
    return Solicitacao.objects.create(
        solicitante=usuario_superintendencia,
        projeto=projeto, municipio=municipio,
        inicio=inicio, fim=inicio + timedelta(hours=3),
        status="pendente",
    )


class TestSolicitacaoApproval:
    """Approval flow tests (PA-01 to PA-07)."""

    class TestManualApproval:
        """PA-01: no auto-approval for SUPER projects."""

        def test_super_project_stays_pending(self, solicitacao_pendente):
            assert solicitacao_pendente.status == "pendente"

    class TestPermissions:
        """PA-02: only Superintendência can approve."""

        def test_superintendencia_approves_successfully(
            self, client, usuario_superintendencia, solicitacao_pendente
        ):
            client.force_login(usuario_superintendencia)
            response = client.post(
                f"/api/solicitacoes/{solicitacao_pendente.id}/approve/",
                {"justificativa": "Aprovado para teste"},
            )
            assert response.status_code == 200
            solicitacao_pendente.refresh_from_db()
            assert solicitacao_pendente.status == "aprovado"
```

## Behavior vs implementation

```python
# BAD — asserts an implementation detail
def test_approve_calls_save():
    solicitacao.save = Mock()
    approve(solicitacao)
    assert solicitacao.save.called

# GOOD — asserts the observable effect
def test_approve_creates_audit_log():
    approve(solicitacao)
    assert AuditLog.objects.filter(
        action="APPROVE", details__solicitacao_id=solicitacao.id,
    ).exists()
```

## RBAC-oriented asserts

Assert the **403 status**, not the org chart. `"Setor" in response.data` ties the test to
the legacy organigram; the real assertion is the HTTP status code.

Real examples (`apps/core/tests/`): `test_solicitacao_fluxo.py`,
`test_solicitacao_approval_concurrency.py`, `test_views_solicitacao_coverage.py`.
Use a fixture URL via `/api/...` hardcoded (Django URL-reverse pitfall in tests).
