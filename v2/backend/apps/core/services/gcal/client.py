"""
AS v2 — GCal Client Adapter

Base interface for Calendar clients.
"""
# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from apps.core.types import CalendarId, EventId, JsonDict


class CalendarClientAdapter:
    """
    Interface para clientes de Calendar.

    Implementações:
    - FakeCalendarClient: in-memory para testes
    - GoogleCalendarClient: real Google API (futuro)
    """

    def get(self, calendar_id: CalendarId, event_id: EventId) -> JsonDict | None:
        """
        Busca evento por ID.

        Returns:
            dict com dados do evento, ou None se não existe
        """
        raise NotImplementedError

    def insert(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Cria novo evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID determinístico do evento
            payload: Dados do evento (summary, start, end, etc)

        Returns:
            dict com evento criado (incluindo "id")
        """
        raise NotImplementedError

    def update(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Atualiza evento existente.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Novos dados do evento

        Returns:
            dict com evento atualizado
        """
        raise NotImplementedError

    def delete(self, calendar_id: CalendarId, event_id: EventId) -> None:
        """
        Deleta evento.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        raise NotImplementedError

    def list_calendars(self) -> list[JsonDict]:
        """
        Lista calendários disponíveis.

        Returns:
            Lista de dicts com informações dos calendários:
            [{"id": str, "summary": str, "primary": bool}, ...]
        """
        raise NotImplementedError

    def health_check(self) -> JsonDict:
        """
        Verifica saúde da integração com Calendar API.

        Returns:
            dict com status: {"status": "healthy"|"unhealthy", "details": str}
        """
        raise NotImplementedError
