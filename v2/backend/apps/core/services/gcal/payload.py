"""
AS v2 — GCal Payload Building

Functions for building Google Calendar event payloads.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportPrivateUsage=false, reportUnusedVariable=false

from __future__ import annotations

import logging
from datetime import timezone as dt_timezone

from django.conf import settings

from apps.core.models import Solicitacao
from apps.core.types import JsonDict, PayloadHash

from .utils import _payload_hash
from .validation import _event_id_for

logger = logging.getLogger(__name__)


def build_attendees_for_solicitacao(s: Solicitacao) -> list[JsonDict]:
    """
    Extrai attendees (participantes) de uma Solicitacao.

    Inclui apenas roles: COORDENADOR, FORMADOR, COORD_ACOMPANHA.
    Para cada participação:
    - Se usuario existe, usa usuario.email
    - Se guest_email existe, usa guest_email

    Args:
        s: Solicitacao

    Returns:
        list[dict]: Lista de attendees no formato Google Calendar
                    [{"email": "..."}, ...]
    """
    # Roles que devem ser incluídos como attendees
    attendee_roles = ["COORDENADOR", "FORMADOR", "COORD_ACOMPANHA"]

    # Buscar participações com prefetch do usuário
    participations = s.participations.filter(role__in=attendee_roles).select_related("usuario")

    emails = set()
    for p in participations:
        email = None
        if p.usuario and p.usuario.email:
            email = p.usuario.email
        elif p.guest_email:
            email = p.guest_email

        if email:
            emails.add(email.strip().lower())

    # Retornar lista de dicts no formato Google Calendar
    return [{"email": email} for email in sorted(emails)]


def _build_payload(s: Solicitacao, *, enable_meet: bool = False) -> JsonDict:
    """
    Constrói payload do evento para Google Calendar API (Fase 3 - Template Padronizado).

    Template Format:
    - Title: "{municipio.nome} - {municipio.uf} {segmento} {modalidade} [{projeto.codigo}]"
    - Description: Structured multi-line sections (Município, Projeto, Data, Modalidade, Equipe, Links/Observações)

    Args:
        s: Solicitacao aprovada
        enable_meet: Se True, adiciona conferenceData para Google Meet (RF06)

    Returns:
        dict: Payload compatível com Google Calendar API
    """
    # Converter para UTC (Google aceita ISO8601 com Z)
    start_iso = s.inicio.astimezone(dt_timezone.utc).isoformat()
    end_iso = s.fim.astimezone(dt_timezone.utc).isoformat()

    # Extrair atributos (podem ser None)
    municipio = getattr(s, "municipio", None)
    projeto = getattr(s, "projeto", None)
    tipo = getattr(s, "tipo_evento", None)
    _usuario = getattr(s, "usuario", None)  # Reserved for future use
    coordenador = getattr(s, "coordenador", None)

    # ================================================================
    # TITLE (SUMMARY) - Fase 3 Template
    # ================================================================
    # Format: "{municipio.nome} - {municipio.uf} {segmento} {modalidade} [{projeto.codigo ou nome}]"
    # Example: "Salvador - BA Fundamental I Online [ACERTA]"
    title_parts = []

    # 1. Município - UF
    if municipio:
        nome_mun = getattr(municipio, "nome", "")
        uf_mun = getattr(municipio, "uf", "")
        if nome_mun:
            mun_part = f"{nome_mun} - {uf_mun}" if uf_mun else nome_mun
            title_parts.append(mun_part)

    # 2. Segmento (ex: "Fundamental I", "Fundamental II")
    segmento = getattr(s, "segmento", "")
    if segmento:
        title_parts.append(segmento.strip())

    # 3. Modalidade (Online/Presencial)
    is_online = getattr(s, "is_online", False)
    modalidade = "Online" if is_online else "Presencial"
    title_parts.append(modalidade)

    # 4. Projeto [codigo] ou [nome] como fallback
    if projeto:
        projeto_codigo = getattr(projeto, "codigo", "")
        projeto_nome = getattr(projeto, "nome", "")
        projeto_label = projeto_codigo if projeto_codigo else projeto_nome
        if projeto_label:
            title_parts.append(f"[{projeto_label}]")

    summary = " ".join(title_parts) if title_parts else f"Solicitação #{s.id}"

    # ================================================================
    # DEFENSIVE TRUNCATION (Google Calendar limits)
    # ================================================================
    # Summary: ≤1000 chars. Se exceder, move excess para description.
    # Description: ≤5000 chars total.
    summary_excess = ""
    if len(summary) > 1000:
        logger.warning(
            f"GCal payload truncation: Solicitacao #{s.id} summary truncated "
            f"(original: {len(summary)} chars, truncated to 1000 chars)"
        )
        summary_excess = f"\n\n[Título completo]\n{summary}\n"
        summary_trimmed = summary[:997] + "..."
    else:
        summary_trimmed = summary

    # ================================================================
    # DESCRIPTION - Fase 3 Template
    # ================================================================
    # Structured multi-line format with sections
    description_lines = []

    # Header
    description_lines.append(f"📋 Solicitação #{s.id} — AS v2")
    description_lines.append("")

    # Seção 1: Município
    if municipio:
        nome_mun = getattr(municipio, "nome", "")
        uf_mun = getattr(municipio, "uf", "")
        mun_display = f"{nome_mun} - {uf_mun}" if (nome_mun and uf_mun) else nome_mun
        description_lines.append(f"📍 Município: {mun_display}")

    # Seção 2: Projeto
    if projeto:
        projeto_nome = getattr(projeto, "nome", "")
        projeto_codigo = getattr(projeto, "codigo", "")
        if projeto_nome:
            projeto_display = f"{projeto_nome} ({projeto_codigo})" if projeto_codigo else projeto_nome
            description_lines.append(f"📂 Projeto: {projeto_display}")

    # Seção 3: Tipo de Evento
    if tipo:
        tipo_nome = getattr(tipo, "nome", "")
        if tipo_nome:
            description_lines.append(f"🎯 Tipo: {tipo_nome}")

    # Seção 4: Data/Horário (formatado em America/Fortaleza)
    import pytz

    fortaleza_tz = pytz.timezone("America/Fortaleza")
    inicio_local = s.inicio.astimezone(fortaleza_tz)
    fim_local = s.fim.astimezone(fortaleza_tz)
    data_format = "%d/%m/%Y %H:%M"
    description_lines.append(f"📅 Data: {inicio_local.strftime(data_format)} a {fim_local.strftime(data_format)}")

    # Seção 5: Modalidade
    description_lines.append(f"🌐 Modalidade: {modalidade}")

    # Seção 6: Equipe (Formadores + Coordenador)
    equipe_parts = []

    # Formadores (via ManyToMany)
    formadores = s.formadores.all()
    if formadores.exists():
        formadores_names = [f.get_full_name() or f.username for f in formadores]
        equipe_parts.append(f"Formador(es): {', '.join(formadores_names)}")

    # Coordenador
    if coordenador:
        coord_name = coordenador.get_full_name() or coordenador.username
        equipe_parts.append(f"Coordenador(a): {coord_name}")

    if equipe_parts:
        description_lines.append("")
        description_lines.append("👥 Equipe:")
        for equipe_line in equipe_parts:
            description_lines.append(f"  • {equipe_line}")

    # Seção 7: Links e Observações
    observacoes = getattr(s, "observacoes", "")
    if observacoes:
        description_lines.append("")
        description_lines.append("📝 Observações:")
        description_lines.append(observacoes.strip())

    # Adicionar excess do summary (se houver)
    if summary_excess:
        description_lines.append("")
        description_lines.append(summary_excess.strip())

    # Join lines
    description = "\n".join(description_lines).strip()

    # Limitar description a 5000 chars
    if len(description) > 5000:
        logger.warning(
            f"GCal payload truncation: Solicitacao #{s.id} description truncated "
            f"(original: {len(description)} chars, truncated to 5000 chars)"
        )
        description_trimmed = description[:4997] + "..."
    else:
        description_trimmed = description

    # RF06: Google Meet conferenceData
    conference_data = None
    if enable_meet:
        # requestId determinístico para idempotência (fix #573: era uuid4 aleatório)
        # Google usa requestId para deduplicar createRequest — mesmo ID = mesmo Meet link
        request_id = f"meet-asv2-{s.id}"
        conference_data = {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    # Construir payload
    payload = {
        "summary": summary_trimmed,
        "description": description_trimmed,
        "start": {"dateTime": start_iso, "timeZone": "UTC"},
        "end": {"dateTime": end_iso, "timeZone": "UTC"},
        "location": getattr(municipio, "nome", None) if municipio else None,
        # Metadados para auditoria e reconciliação
        "extendedProperties": {
            "private": {
                "solicitation_id": str(s.id),
                "ssot_version": "v2",
                "last_updated": (s.updated_at.isoformat() if hasattr(s, "updated_at") and s.updated_at else ""),
            }
        },
    }

    # Attendees (via Participation: COORDENADOR, FORMADOR, COORD_ACOMPANHA)
    payload["attendees"] = build_attendees_for_solicitacao(s)

    # Color mapping (opcional)
    color_map = getattr(settings, "GCAL_COLOR_MAP", None)
    if color_map and tipo:
        tipo_nome = getattr(tipo, "nome", None)
        if tipo_nome and tipo_nome in color_map:
            payload["colorId"] = str(color_map[tipo_nome])

    # RF06: Adicionar conferenceData apenas se enable_meet=True (modalidade online)
    if conference_data is not None:
        payload["conferenceData"] = conference_data

    return payload


def build_event_payload(s: Solicitacao, *, enable_meet: bool = False) -> JsonDict:
    """
    Wrapper público para _build_payload (PR14, PR19).

    Args:
        s: Solicitacao
        enable_meet: Se True, adiciona conferenceData para Google Meet (RF06)

    Returns:
        dict: Payload para Google Calendar API
    """
    return _build_payload(s, enable_meet=enable_meet)


def build_preview_for_solicitacao(s: Solicitacao) -> JsonDict:
    """
    Constrói preview do payload GCal sem publicar (PR14, PR19/RF06).

    Args:
        s: Solicitacao

    Returns:
        dict: {
            "event_id": str,
            "payload": dict (Google Calendar API format),
            "payload_hash": str (SHA1 hex),
            "meet_link": str (fake link para preview, não persiste no DB)
        }
    """
    # PR19/RF06 + Modalidade: habilita Meet no preview apenas se for online
    enable_meet = bool(getattr(s, "is_online", False))
    payload = _build_payload(s, enable_meet=enable_meet)
    event_id = _event_id_for(s)

    # Gerar meet_link fake para preview (não persiste) apenas quando online
    meet_link_preview = None
    if enable_meet:
        # Extrai número do event_id (formato: asv2-{id})
        event_num = event_id.split("-")[-1] if "-" in event_id else event_id
        meet_link_preview = f"https://meet.google.com/fake-{event_num}"

    return {
        "event_id": event_id,
        "payload": payload,
        "payload_hash": _payload_hash(payload),
        "meet_link": meet_link_preview,  # PR19/RF06: Preview do Meet link (somente online)
    }


def compute_payload_hash(s: Solicitacao) -> PayloadHash:
    """
    Calcula hash do payload de uma solicitação (PR14).

    Args:
        s: Solicitacao

    Returns:
        str: SHA1 hash hex (40 chars)
    """
    payload = build_event_payload(s)
    return _payload_hash(payload)
