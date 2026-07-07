"""Guard LGPD do log de INSERT do sync GCal.

O #1506 trocou o dump do payload inteiro por um resumo; a Onda 4 removeu tambem o
summary/titulo e o calendar_id (CodeQL py/clear-text-logging-sensitive-data + defesa a
mais, pois o titulo pode conter nome de pessoa). Restam so escalares nao-sensiveis:
id da Solicitacao, event_id deterministico, contagem de attendees e flag online. Este
teste TRAVA a garantia: o log de INSERT NAO pode conter e-mail de attendee, a descricao
completa NEM o titulo do evento.

Gotcha (por que handler direto e nao caplog): o logger `apps` tem propagate=False
(config/settings.py) e `apps.core.services.gcal.sync` herda dele -> o registro nao sobe
ate a raiz onde o caplog escuta. Anexamos um handler direto no logger do modulo +
setLevel(DEBUG) (mesmo padrao de test_db_retry.py).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false

from __future__ import annotations

import logging

import pytest

from apps.core.services.gcal import sync as sync_module
from apps.core.services.gcal.sync import upsert_one
from apps.core.services.gcal_fake_client import FakeCalendarClient
from apps.core.tests.factories import SolicitacaoFactory


@pytest.mark.django_db
def test_insert_log_nao_vaza_email_nem_descricao_lgpd():
    sol = SolicitacaoFactory(status="aprovado", external_event_id=None)
    email_secreto = "attendee-secreto-lgpd@example.com"
    desc_secreta = "CONFIDENCIAL_LGPD_NAO_DEVE_VAZAR " * 20  # descricao longa
    payload = {
        "summary": "Fortaleza - CE Online [ACERTA]",
        "description": desc_secreta,
        "attendees": [{"email": email_secreto}, {"email": "outro@example.com"}],
        "start": {"dateTime": "2026-08-01T09:00:00-03:00", "timeZone": "America/Fortaleza"},
        "end": {"dateTime": "2026-08-01T12:00:00-03:00", "timeZone": "America/Fortaleza"},
    }

    captured: list[logging.LogRecord] = []

    class _Cap(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Cap(level=logging.DEBUG)
    sync_module.logger.addHandler(handler)
    old_level = sync_module.logger.level
    sync_module.logger.setLevel(logging.DEBUG)  # senao o debug e suprimido (herda INFO de 'apps')
    try:
        outcome = upsert_one(
            client=FakeCalendarClient(), calendar_id="cal", s=sol, dry_run=False, no_delete=False, payload=payload
        )
    finally:
        sync_module.logger.removeHandler(handler)
        sync_module.logger.setLevel(old_level)

    assert outcome.action == "CREATE"
    insert_msgs = [r.getMessage() for r in captured if "GCal INSERT" in r.getMessage()]
    # Nao-vacuidade: sem isto os `not in` passariam a toa se o log deixasse de ser emitido.
    assert insert_msgs, "log de INSERT nao foi emitido"
    txt = "\n".join(insert_msgs)

    assert email_secreto not in txt, "LGPD: e-mail do attendee vazou no log"
    assert "CONFIDENCIAL_LGPD" not in txt, "descricao completa vazou no log"
    # Nem o titulo do evento entra no log (pode conter nome de pessoa; py/clear-text-logging).
    assert "Fortaleza - CE Online [ACERTA]" not in txt, "titulo/summary do evento vazou no log"
    # Correlacao preservada sem dado sensivel: id da Solicitacao + event_id + contagem + flag.
    assert f"#{sol.id}" in txt and "event_id=" in txt
    assert "attendees=2" in txt and "online=False" in txt  # contagem + flag estao
