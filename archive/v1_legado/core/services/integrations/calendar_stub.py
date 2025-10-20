from typing import Optional

from django.conf import settings

from core.services.integrations.calendar_types import GoogleEvent


class GoogleCalendarServiceStub:
    """
    Stub do RF05. Quando FEATURE_GOOGLE_SYNC=0, só registra intenção.
    Quando ligarmos a integração real, substituiremos esse stub.
    """

    def __init__(self, calendar_id: Optional[str] = None):
        self.calendar_id = calendar_id or settings.GOOGLE_CALENDAR_CALENDAR_ID

    def create_event(self, gevent: GoogleEvent) -> dict:
        """
        Retorna um objeto fake parecido com o Google:
        {
          "id": "...",
          "htmlLink": "https://calendar.google.com/...event?eid=...",
          "hangoutLink": "https://meet.google.com/abc-defg-hij" (se conference=True)
        }
        """
        if not settings.FEATURE_GOOGLE_SYNC:
            # short-circuit: em flag OFF, não cria nada
            return {"status": "skipped", "reason": "FEATURE_GOOGLE_SYNC=0"}

        # Quando for real, aqui chamaremos a API do Google e retornaremos o payload verdadeiro.
        # Por ora, retorna um sucesso simulado estável para os testes:
        fake_id = "evt_fake_" + gevent.start_iso.replace(":", "").replace("-", "")
        payload = {
            "id": fake_id,
            "htmlLink": f"https://calendar.google.com/calendar/u/0/r/eventedit/{fake_id}",
        }
        if gevent.conference:
            payload["hangoutLink"] = "https://meet.google.com/fake-code-xyz"
        return payload
