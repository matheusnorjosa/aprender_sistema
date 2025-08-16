from dataclasses import dataclass

@dataclass
class CalendarEventResult:
    provider_event_id: str
    html_link: str | None = None
    meet_link: str | None = None

def is_enabled() -> bool:
    from django.conf import settings
    return bool(getattr(settings, "ENABLE_CALENDAR", False))

def create_event(solicitacao) -> CalendarEventResult:
    """
    RF05: stub seguro (para testes). 
    Em produção, aqui entra a chamada real à API.
    """
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")

    # Simular retorno de provedor (para testes com mock ou flag ligada em dev)
    fake_id = f"fake-{solicitacao.id}"
    return CalendarEventResult(provider_event_id=fake_id, html_link=None, meet_link=None)

def update_event(evento_gc, solicitacao) -> None:
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")

def delete_event(evento_gc) -> None:
    if not is_enabled():
        raise RuntimeError("Calendar integration disabled")
