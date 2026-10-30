"""
AS v2 — GCal Client Adapter

Base interface for Calendar clients.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

from __future__ import annotations

from apps.core.types import CalendarId, EventId, JsonDict


class SyncTokenExpirado(Exception):
    """O Google recusou o syncToken (HTTP 410): quem chama descarta o token e refaz a leitura completa."""


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

    def patch_descricao(self, calendar_id: CalendarId, event_id: EventId, descricao: str) -> JsonDict:
        """
        Troca só a descrição do evento, sem avisar os convidados (cópia Google → Sistema).

        Não manda início nem fim: o horário veio do Google e ele pode ter mudado de novo.
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

    def list_changes(self, calendar_id: CalendarId, sync_token: str | None) -> tuple[list[JsonDict], str]:
        """
        Lê o que mudou no calendário desde `sync_token` (None = leitura completa).

        Returns:
            (itens crus do Google, incluindo cancelados; nextSyncToken da última página)

        Raises:
            SyncTokenExpirado: o Google recusou o token (410)
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
