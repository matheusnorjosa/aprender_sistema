"""
Fake Calendar Client - In-memory implementation for testing

Armazena eventos em memória sem dependências externas.
Usado nos testes para simular Google Calendar API.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportGeneralTypeIssues=false

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apps.core.services.gcal.client import SyncTokenExpirado
from apps.core.services.gcal.validation import GCAL_EVENT_ID_PREFIX
from apps.core.services.gcal_sync_service import CalendarClientAdapter
from apps.core.types import CalendarId, EventId, JsonDict

# O Google devolve as horas no fuso do calendário (Fortaleza, sem horário de verão).
_FORTALEZA = timezone(timedelta(hours=-3))
# Campos que o `list_changes` do cliente real pede (`CAMPOS_LIST_CHANGES`).
_CAMPOS_LIST_CHANGES = ("id", "status", "start", "end", "updated", "recurringEventId", "recurrence")
_PREFIXO_TOKEN = "fake-sync-"


def _como_google(event: JsonDict) -> JsonDict:
    """Cópia do evento com `status` e com `start`/`end` no offset -03:00, como o Google devolve."""
    copia = {"status": "confirmed", **event}
    for campo in ("start", "end"):
        horario = event.get(campo)
        if isinstance(horario, dict) and horario.get("dateTime"):
            instante = datetime.fromisoformat(horario["dateTime"])
            copia[campo] = {**horario, "dateTime": instante.astimezone(_FORTALEZA).isoformat()}
    return copia


class FakeCalendarClient(CalendarClientAdapter):
    """
    Cliente fake de Calendar para testes.

    Armazena eventos em memória por (calendar_id, event_id).
    Não faz nenhuma chamada de rede.

    Fiel ao Google onde a cópia Google → Sistema depende: o DELETE é soft (o evento fica
    `cancelled` e o GET ainda o acha), as horas voltam com offset -03:00 e o `list_changes`
    lê um log de mudanças com token falso. `sync_token_expirado = True` simula o 410.
    """

    def __init__(self) -> None:
        """Inicializa store vazio"""
        self._store: dict[tuple[CalendarId, EventId], JsonDict] = {}
        self._mudancas: list[tuple[CalendarId, EventId]] = []
        self._atualizado_em: dict[tuple[CalendarId, EventId], str] = {}
        self.sync_token_expirado = False

    def _registrar_mudanca(self, calendar_id: CalendarId, event_id: EventId) -> None:
        self._mudancas.append(self._key(calendar_id, event_id))
        self._atualizado_em[self._key(calendar_id, event_id)] = datetime.now(timezone.utc).isoformat()

    def _key(self, calendar_id: CalendarId, event_id: EventId) -> tuple[CalendarId, EventId]:
        """Gera chave única para o store"""
        return (calendar_id, event_id)

    def get(self, calendar_id: CalendarId, event_id: EventId) -> JsonDict | None:
        """
        Busca evento no store.

        Returns:
            dict com evento (cancelado inclusive, como no Google), ou None se não existe
        """
        event = self._store.get(self._key(calendar_id, event_id))
        return None if event is None else _como_google(event)

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
            # Extrair sufixo do event_id no formato asv2{id}
            event_num: str = (
                event_id[len(GCAL_EVENT_ID_PREFIX) :] if event_id.startswith(GCAL_EVENT_ID_PREFIX) else event_id
            )
            event["hangoutLink"] = f"https://meet.google.com/fake-{event_num}"

        self._store[self._key(calendar_id, event_id)] = event
        self._registrar_mudanca(calendar_id, event_id)
        return event

    def update(self, calendar_id: CalendarId, event_id: EventId, payload: JsonDict) -> JsonDict:
        """
        Atualiza evento no store com a semântica do PATCH do Google: o que não vem no payload fica.

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
            payload: Campos a trocar

        Returns:
            dict com evento atualizado (inclui "hangoutLink" se conferenceData presente)
        """
        event: JsonDict = {**self._store.get(self._key(calendar_id, event_id), {}), **payload, "id": event_id}

        # RF06/PR19: Gerar hangoutLink fake se conferenceData presente
        if payload.get("conferenceData"):
            # Extrair sufixo do event_id no formato asv2{id}
            event_num: str = (
                event_id[len(GCAL_EVENT_ID_PREFIX) :] if event_id.startswith(GCAL_EVENT_ID_PREFIX) else event_id
            )
            event["hangoutLink"] = f"https://meet.google.com/fake-{event_num}"

        self._store[self._key(calendar_id, event_id)] = event
        self._registrar_mudanca(calendar_id, event_id)
        return event

    def patch_descricao(self, calendar_id: CalendarId, event_id: EventId, descricao: str) -> JsonDict:
        """PATCH só da descrição (mesma semântica do `update`)."""
        return self.update(calendar_id, event_id, {"description": descricao})

    def delete(self, calendar_id: CalendarId, event_id: EventId) -> None:
        """
        Cancela o evento (soft delete, como o Google: ele continua no store com `status=cancelled`).

        Args:
            calendar_id: ID do calendário
            event_id: ID do evento
        """
        event = self._store.get(self._key(calendar_id, event_id))
        if event is None or event.get("status") == "cancelled":
            return
        self._store[self._key(calendar_id, event_id)] = {**event, "status": "cancelled"}
        self._registrar_mudanca(calendar_id, event_id)

    def list_events(self, calendar_id: CalendarId) -> list[JsonDict]:
        """
        Lista os eventos de um calendário (helper para testes).

        Como a listagem padrão do Google (sem `showDeleted`), não traz os cancelados.

        Args:
            calendar_id: ID do calendário

        Returns:
            Lista de eventos
        """
        return [
            _como_google(event)
            for (cal, _), event in self._store.items()
            if cal == calendar_id and event.get("status") != "cancelled"
        ]

    def list_changes(self, calendar_id: CalendarId, sync_token: str | None) -> tuple[list[JsonDict], str]:
        """
        O que mudou desde `sync_token` (None = tudo, cancelados inclusive), só com os campos da máscara.

        O token é a posição no log de mudanças. Com `sync_token_expirado`, um token dado vira 410.
        """
        if sync_token is not None:
            if self.sync_token_expirado or not sync_token.startswith(_PREFIXO_TOKEN):
                raise SyncTokenExpirado("syncToken recusado (fake)")
            chaves = dict.fromkeys(self._mudancas[int(sync_token[len(_PREFIXO_TOKEN) :]) :])
        else:
            chaves = dict.fromkeys(self._store)
        itens: list[JsonDict] = []
        for chave in chaves:
            if chave[0] != calendar_id or chave not in self._store:
                continue
            event = _como_google({**self._store[chave], "updated": self._atualizado_em.get(chave)})
            if event["status"] == "cancelled":
                # Lápide: o Google só garante o id e o status do evento cancelado.
                itens.append({"id": event["id"], "status": "cancelled"})
                continue
            itens.append({campo: event[campo] for campo in _CAMPOS_LIST_CHANGES if event.get(campo) is not None})
        return itens, f"{_PREFIXO_TOKEN}{len(self._mudancas)}"

    def clear(self) -> None:
        """Limpa todos os eventos (helper para testes)"""
        self._store.clear()
        self._mudancas.clear()
        self._atualizado_em.clear()

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
