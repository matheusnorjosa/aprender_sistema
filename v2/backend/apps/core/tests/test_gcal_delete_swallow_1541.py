"""#1541 (lote C) — robustez do GCal: delete-swallow e auto-retry do breaker.

Dois defeitos silenciosos achados pela auditoria adversarial:

1. `upsert_one` (DELETE): uma falha não-404 ao deletar o evento no Google era
   ENGOLIDA — o código zerava `external_event_id` e retornava `action="DELETE"`
   como sucesso. O evento continuava vivo no Google (participantes ainda o viam) e
   o único ponteiro para ele era descartado: órfão permanente, reportado como OK.

2. `queue_gcal_sync_retry` existia (Gap 6) mas NUNCA era enfileirada. Uma sync
   derrubada pelo circuit breaker aberto ficava perdida até re-disparo manual.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportArgumentType=false

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.core.services.gcal.sync import upsert_one
from apps.core.tests.factories import SolicitacaoFactory

pytestmark = pytest.mark.django_db

# Bypassa o backoff/circuit-breaker real no teste: chama a fn uma vez e propaga.
_PASSTHROUGH = "apps.core.services.gcal.sync._retry_with_circuit_breaker"


def _passthrough(fn, **kwargs):
    return fn()


class _FakeClient:
    """Cliente de Calendar mínimo cujo delete pode ser configurado para falhar."""

    def __init__(self, delete_exc: Exception | None = None) -> None:
        self._delete_exc = delete_exc

    def get(self, calendar_id, event_id):  # noqa: ARG002
        return {"id": event_id}

    def insert(self, calendar_id, event_id, payload):  # noqa: ARG002
        return {"id": event_id}

    def update(self, calendar_id, event_id, payload):  # noqa: ARG002
        return {"id": event_id}

    def delete(self, calendar_id, event_id):  # noqa: ARG002
        if self._delete_exc is not None:
            raise self._delete_exc


class TestUpsertDeleteSwallow:
    def test_delete_failure_reraises_and_keeps_pointer(self):
        """Falha não-404 ao deletar → RE-LEVANTA e NÃO zera external_event_id.

        Antes do fix retornava action="DELETE" com o ponteiro descartado (órfão).
        """
        s = SolicitacaoFactory(status="reprovado", external_event_id="asv2-orphan-1")
        client = _FakeClient(delete_exc=RuntimeError("500 Internal Server Error"))

        with patch(_PASSTHROUGH, side_effect=_passthrough):
            with pytest.raises(RuntimeError):
                upsert_one(client=client, calendar_id="primary", s=s)

        s.refresh_from_db()
        assert s.external_event_id == "asv2-orphan-1", "ponteiro deve ser preservado na falha"

    def test_delete_404_is_success_and_clears_pointer(self):
        """404 = evento já removido no Google → sucesso idempotente, zera o ponteiro."""
        s = SolicitacaoFactory(status="reprovado", external_event_id="asv2-gone-1")
        client = _FakeClient(delete_exc=Exception("404 Not Found"))

        with patch(_PASSTHROUGH, side_effect=_passthrough):
            outcome = upsert_one(client=client, calendar_id="primary", s=s)

        assert outcome.action == "DELETE"
        s.refresh_from_db()
        assert s.external_event_id is None

    def test_delete_success_clears_pointer(self):
        """DELETE bem-sucedido zera o ponteiro e reporta action=DELETE."""
        s = SolicitacaoFactory(status="reprovado", external_event_id="asv2-ok-1")
        client = _FakeClient(delete_exc=None)

        with patch(_PASSTHROUGH, side_effect=_passthrough):
            outcome = upsert_one(client=client, calendar_id="primary", s=s)

        assert outcome.action == "DELETE"
        s.refresh_from_db()
        assert s.external_event_id is None


class TestBreakerAutoRetryWired:
    def test_publish_enqueues_retry_on_circuit_breaker_open(self):
        """CircuitBreakerError no publish → enfileira queue_gcal_sync_retry.

        Sem o wiring, a task de recuperação existia mas nunca era acionada: a sync
        ficava perdida até re-disparo manual, em silêncio.
        """
        from apps.core.services.gcal.circuit_breaker import CircuitBreakerError, gcal_breaker
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        s = SolicitacaoFactory(status="aprovado")

        with (
            patch(
                "apps.core.services.gcal_sync_service.apply_one_solicitacao",
                side_effect=CircuitBreakerError(gcal_breaker),
            ),
            patch("apps.core.tasks.queue_gcal_sync_retry.apply_async") as mock_enqueue,
        ):
            result = task_publish_solicitacao_to_gcal(s.id, dry_run=False, apply_blocked=True)

        assert result["action"] == "ERROR"
        assert mock_enqueue.called, "deve enfileirar o auto-retry quando o breaker abre"
        args, _kwargs = mock_enqueue.call_args
        assert args[0] == (s.id,)

    def test_publish_does_not_enqueue_retry_for_other_errors(self):
        """Erro comum (não breaker) NÃO enfileira retry — evita retry-storm à toa."""
        from apps.core.tasks import task_publish_solicitacao_to_gcal

        s = SolicitacaoFactory(status="aprovado")

        with (
            patch(
                "apps.core.services.gcal_sync_service.apply_one_solicitacao",
                side_effect=RuntimeError("erro qualquer"),
            ),
            patch("apps.core.tasks.queue_gcal_sync_retry.apply_async") as mock_enqueue,
        ):
            result = task_publish_solicitacao_to_gcal(s.id, dry_run=False, apply_blocked=True)

        assert result["action"] == "ERROR"
        assert not mock_enqueue.called
