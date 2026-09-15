"""
Wave 4 — audit-before-delete atômico em perform_destroy.

`Solicitacao.perform_destroy` e `Deslocamento.perform_destroy` criavam o AuditLog
(DELETE) e SÓ DEPOIS chamavam `instance.delete()`, cada um como escrita autocommit
separada (ATOMIC_REQUESTS=False neste projeto → a request não é atômica por si).
Se o delete falhasse, sobrava um AuditLog "DELETE" FANTASMA para um registro que
continua existindo (trilha de auditoria mente).

Contrato: AuditLog + delete no MESMO `transaction.atomic()` — delete falho desfaz
o AuditLog (nada de trilha fantasma).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false, reportMissingTypeStubs=false

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Deslocamento, Solicitacao
from apps.core.tests.factories import SolicitacaoFactory, UsuarioFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def superuser():
    return UsuarioFactory(username="su_abd", cpf="70700000701", is_superuser=True, is_staff=True)


def _client(user):
    c = APIClient()
    c.raise_request_exception = False  # 500 vira resposta, não propaga a exceção
    c.force_authenticate(user)
    return c


class TestSolicitacaoAuditBeforeDeleteAtomic:
    def test_delete_failure_rolls_back_auditlog(self, superuser):
        """RED: AuditLog(DELETE) é criado antes do delete; delete falho deixa a trilha fantasma."""
        sol = SolicitacaoFactory(usuario=superuser)
        client = _client(superuser)
        antes = AuditLog.objects.filter(action=AuditLog.Action.DELETE, model_name="Solicitacao").count()

        with patch.object(Solicitacao, "delete", side_effect=RuntimeError("boom")):
            resp = client.delete(f"/api/solicitacoes/{sol.id}/")

        assert resp.status_code == 500
        assert Solicitacao.objects.filter(pk=sol.pk).exists(), "delete falho não pode remover a solicitacao"
        depois = AuditLog.objects.filter(action=AuditLog.Action.DELETE, model_name="Solicitacao").count()
        assert depois == antes, "delete falho não pode deixar AuditLog(DELETE) fantasma"


class TestDeslocamentoAuditBeforeDeleteAtomic:
    def test_delete_failure_rolls_back_auditlog(self, superuser):
        """RED: AuditLog(DELETE_DESLOCAMENTO) é criado antes do delete; delete falho deixa a trilha fantasma."""
        desl = Deslocamento.objects.create(
            usuario=superuser,
            origem="Fortaleza",
            destino="Sobral",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        client = _client(superuser)
        antes = AuditLog.objects.filter(action=AuditLog.Action.DELETE_DESLOCAMENTO).count()

        with patch.object(Deslocamento, "delete", side_effect=RuntimeError("boom")):
            resp = client.delete(f"/api/deslocamentos/{desl.id}/")

        assert resp.status_code == 500
        assert Deslocamento.objects.filter(pk=desl.pk).exists(), "delete falho não pode remover o deslocamento"
        depois = AuditLog.objects.filter(action=AuditLog.Action.DELETE_DESLOCAMENTO).count()
        assert depois == antes, "delete falho não pode deixar AuditLog(DELETE_DESLOCAMENTO) fantasma"
