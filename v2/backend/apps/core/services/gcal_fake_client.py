"""
Fake Calendar Client - In-memory implementation for testing

Armazena eventos em memória sem dependências externas.
Usado nos testes para simular Google Calendar API.
"""

from __future__ import annotations

from apps.core.services.gcal_sync_service import CalendarClientAdapter
from apps.core.types import CalendarId, EventId, JsonDict


class FakeCalendarClient(CalendarClientAdapter):
    """
    Cliente fake de Calendar para testes.

    Armazena eventos em memória por (calendar_id, event_id).
    Não faz nenhuma chamada de rede.
    """

    def __init__(self) -> None:
        """Inicializa store vazio"""
        self._store: dict[tuple[CalendarId, EventId], JsonDict] = {}

    def _key(self, calendar_id: CalendarId, event_id: EventId) -> tuple[CalendarId, EventId]:
        """Gera chave única para o store"""
        return (calendar_id, event_id)

    def get(self, calendar_id: CalendarId, event_id: EventId) -> JsonDict | None:
        """
        Busca evento no store.

        Returns:
            dict com evento, ou None se não existe
        """
        return self._store.get(self._key(calendar_id, event_id))

    def insert(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Insere evento no store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Dados do evento

        Returns:
            dict com evento criado (inclui "id" e "hangoutLink" se conferenceData presente)
        """
        event: JsonDict = {"id": event_id, **payload}

        # RF06/PR19: Gerar hangoutLink fake se conferenceData presente
        if payload.get("conferenceData"):
            # Extrair event_id numérico do formato asv2-{id}
            event_num: str = event_id.split("-")[-1] if "-" in event_id else event_id
            event["hangoutLink"] = f"https://meet.google.com/fake-{event_num}"

        self._store[self._key(calendar_id, event_id)] = event
        return event

    def update(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Atualiza evento no store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Novos dados do evento

        Returns:
            dict com evento atualizado (inclui "hangoutLink" se conferenceData presente)
        """
        event: JsonDict = {"id": event_id, **payload}

        # RF06/PR19: Gerar hangoutLink fake se conferenceData presente
        if payload.get("conferenceData"):
            # Extrair event_id numérico do formato asv2-{id}
            event_num: str = event_id.split("-")[-1] if "-" in event_id else event_id
            event["hangoutLink"] = f"https://meet.google.com/fake-{event_num}"

        self._store[self._key(calendar_id, event_id)] = event
        return event

    def delete(self, calendar_id: CalendarId, event_id: EventId) -> None:
        """
        Remove evento do store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        self._store.pop(self._key(calendar_id, event_id), None)

    def list_events(self, calendar_id: CalendarId) -> list[JsonDict]:
        """
        Lista todos os eventos de um calendário (helper para testes).

        Args:
            calendar_id: ID do calendário

        Returns:
            Lista de eventos
        """
        return [
            event
            for (cal, _), event in self._store.items()
            if cal == calendar_id
        ]

    def clear(self) -> None:
        """Limpa todos os eventos (helper para testes)"""
        self._store.clear()

    def list_calendars(self) -> list[JsonDict]:
        """
        Lista calendários disponíveis (mock).

        Returns:
            Lista fake de calendários para testes
        """
        return [
            {
                "id": "primary",
                "summary": "Calendário Principal (Fake)",
                "primary": True,
            },
            {
                "id": "test-calendar-1",
                "summary": "Calendário de Testes 1",
                "primary": False,
            },
            {
                "id": "test-calendar-2",
                "summary": "Calendário de Testes 2",
                "primary": False,
            },
        ]

    def health_check(self) -> JsonDict:
        """
        Health check (fake sempre retorna healthy).

        Returns:
            dict com status healthy
        """
        return {
            "status": "healthy",
            "client_type": "fake",
            "details": "Fake client is always healthy",
        }
