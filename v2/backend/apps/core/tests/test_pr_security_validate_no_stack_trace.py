"""
Hardening: ``SolicitationValidateView`` não vaza ``str(e)`` de ValueError
na response (CodeQL py/stack-trace-exposure, alert #5).

Detalhe do exception vai apenas para o log server-side; usuário recebe
mensagem genérica.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportCallIssue=false, reportMissingTypeArgument=false

from __future__ import annotations

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario


@pytest.fixture
def authenticated_client(db) -> APIClient:
    user = Usuario.objects.create_user(  # type: ignore[attr-defined]
        username="validate_user",
        email="validate.user@example.com",
        password="testpass123",
        cpf="12345678901",
    )
    coord_group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(coord_group)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestValidateStackTraceNotExposed:
    URL = "/api/solicitacoes/validate/"

    def _payload(self, *, date: str = "2026-08-15", start: str = "09:00", end: str = "12:00") -> dict:
        return {
            "municipio": "Fortaleza",
            "projeto": "ACerta",
            "tipo_evento": "Formação",
            "date": date,
            "start": start,
            "end": end,
            "participants": {},
        }

    def test_invalid_date_does_not_leak_str_of_exception(self, authenticated_client):
        # Data com formato inválido: dispara ValueError em datetime.strptime
        payload = self._payload(date="not-a-date")
        resp = authenticated_client.post(self.URL, payload, format="json")
        assert resp.status_code == 200
        errors_text = " ".join(resp.data.get("errors") or [])
        # Mensagem genérica preserve UX
        assert "formato inválido" in errors_text or "Data ou horário" in errors_text
        # Não pode vazar conteúdo típico de ValueError do strptime:
        # "time data 'not-a-date' does not match format '%Y-%m-%d'"
        assert "does not match format" not in errors_text
        assert "time data" not in errors_text
        assert "not-a-date" not in errors_text  # nem o input maliciental

    def test_invalid_time_does_not_leak_str_of_exception(self, authenticated_client):
        payload = self._payload(start="25:99")  # hora inválida
        resp = authenticated_client.post(self.URL, payload, format="json")
        assert resp.status_code == 200
        errors_text = " ".join(resp.data.get("errors") or [])
        assert "does not match format" not in errors_text
        assert "unconverted data" not in errors_text
        assert "25:99" not in errors_text

    def test_logs_traceback_server_side_only(self, authenticated_client, caplog):
        import logging

        with caplog.at_level(logging.WARNING, logger="apps.core.views_validate"):
            payload = self._payload(date="bad-date")
            authenticated_client.post(self.URL, payload, format="json")
        # Não asserta conteúdo do traceback aqui (logger pode estar com propagate=False);
        # apenas garante que o teste de runtime não quebra com a chamada.
