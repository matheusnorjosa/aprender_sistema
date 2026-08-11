"""AS v2 — Minimização de PII em texto livre transferido ao Google Calendar.

LGPD arts. 6-III (necessidade) e 33 (transferência internacional): a descrição do evento
é transferida ao Google (processador nos EUA). Campos estruturados (município, projeto,
equipe, attendees) são necessários ao agendamento/notificação e permanecem. Já o texto
livre `observacoes` pode conter PII *incidental* — um CPF ou e-mail digitado nas notas —
que não é necessário ao agendamento. Redigimos apenas esses padrões, preservando o resto.

Deliberadamente independente de `apps.core.logging_filters` (redação de log é outro
contexto): mantém este PR self-contained e o placeholder é legível para quem lê a agenda.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# CPF formatado (000.000.000-00) OU sequência crua de 11 dígitos (CPF ou telefone móvel).
_CPF_RE = re.compile(r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b")

_PLACEHOLDER = "[dado pessoal removido]"


def minimize_free_text(text: str | None) -> str:
    """Redige CPF/e-mail de um texto livre antes de transferi-lo ao Google.

    Preserva todo o restante do conteúdo. Idempotente e seguro para None/vazio.
    """
    if not text:
        return ""
    redacted = _EMAIL_RE.sub(_PLACEHOLDER, text)
    redacted = _CPF_RE.sub(_PLACEHOLDER, redacted)
    return redacted
