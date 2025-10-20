"""
Fake Calendar Client - In-memory implementation for testing

Armazena eventos em memória sem dependências externas.
Usado nos testes para simular Google Calendar API.
"""

from typing import Optional, Dict, Tuple
from .gcal_sync_service import CalendarClientAdapter


class FakeCalendarClient(CalendarClientAdapter):
    """
    Cliente fake de Calendar para testes.

    Armazena eventos em memória por (calendar_id, event_id).
    Não faz nenhuma chamada de rede.
    """

    def __init__(self):
        """Inicializa store vazio"""
        self._store: Dict[Tuple[str, str], dict] = {}

    def _key(self, calendar_id: str, event_id: str) -> Tuple[str, str]:
        """Gera chave única para o store"""
        return (calendar_id, event_id)

    def get(self, calendar_id: str, event_id: str) -> Optional[dict]:
        """
        Busca evento no store.

        Returns:
            dict com evento, ou None se não existe
        """
        return self._store.get(self._key(calendar_id, event_id))

    def insert(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Insere evento no store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Dados do evento

        Returns:
            dict com evento criado (inclui "id")
        """
        event = {"id": event_id, **payload}
        self._store[self._key(calendar_id, event_id)] = event
        return event

    def update(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        """
        Atualiza evento no store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Novos dados do evento

        Returns:
            dict com evento atualizado
        """
        event = {"id": event_id, **payload}
        self._store[self._key(calendar_id, event_id)] = event
        return event

    def delete(self, calendar_id: str, event_id: str) -> None:
        """
        Remove evento do store.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        self._store.pop(self._key(calendar_id, event_id), None)

    def list_events(self, calendar_id: str) -> list:
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

    def clear(self):
        """Limpa todos os eventos (helper para testes)"""
        self._store.clear()
