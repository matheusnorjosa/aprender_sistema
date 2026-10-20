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
from django.core.cache import cache
from rest_framework.test import APIClient
from apps.core.models import Gerencia, Solicitacao
from apps.core.tests.factories import UsuarioFactory, com_papel
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


@pytest.fixture
def tz_fortaleza():
    return ZoneInfo("America/Fortaleza")


@pytest.fixture
def usuario_comum(db):
    return UsuarioFactory()


@pytest.fixture
def gerente_superintendencia(db):
    # PA-02: grupo "Superintendência" é etiqueta e NÃO aprova (migration 0126). Aprovar vem de
    # `solicitation_approval_basis`: aqui, vínculo EquipeGerencia GERENTE vigente na gerência
    # aprovadora (como `APROVADORAS` em test_approval_policy_PA.py).
    g1, _ = Gerencia.objects.get_or_create(
        nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência"}
    )
    usuario = UsuarioFactory(groups__vinculo=False)
    com_papel(usuario, "GERENTE", g1)
    cache.clear()
    return usuario


@pytest.fixture
def solicitacao_pendente(db, usuario_comum, tz_fortaleza):
    from apps.core.models import Projeto, Municipio, TipoEvento

    # O GERENTE da Superintendência só decide projeto SUPER da gerência dele: sem `gerencia=g1`,
    # a aprovação dá 403 `out_of_approval_scope` (`projeto_no_escopo_da_superintendencia`).
    g1, _ = Gerencia.objects.get_or_create(
        nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência"}
    )
    projeto = Projeto.objects.create(nome="Teste", fluxo="SUPER", gerencia=g1)
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE")
    tipo_evento = TipoEvento.objects.create(nome="Formação")
    inicio = datetime(2025, 1, 15, 9, 0, tzinfo=tz_fortaleza)
    # Solicitante ≠ aprovador: decidir a própria solicitação dá 403 (`decisoes_impedidas`).
    return Solicitacao.objects.create(
        usuario=usuario_comum,
        projeto=projeto, municipio=municipio, tipo_evento=tipo_evento,
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
        """PA-02: only users with a `solicitation_approval_basis` can approve."""

        def test_gerente_superintendencia_approves_successfully(
            self, gerente_superintendencia, solicitacao_pendente
        ):
            client = APIClient()
            client.force_authenticate(user=gerente_superintendencia)
            response = client.patch(
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
