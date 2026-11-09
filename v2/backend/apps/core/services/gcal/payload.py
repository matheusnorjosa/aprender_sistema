"""
AS v2 — GCal Payload Building

Functions for building Google Calendar event payloads.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportOptionalMemberAccess=false, reportCallIssue=false, reportOptionalSubscript=false, reportArgumentType=false, reportMissingTypeStubs=false, reportAttributeAccessIssue=false, reportReturnType=false, reportPrivateUsage=false, reportUnusedVariable=false

from __future__ import annotations

import logging
import unicodedata
from datetime import timezone as dt_timezone

from django.conf import settings
from django.db.models import Q

from apps.core.models import Solicitacao
from apps.core.pii import email_de_reserva
from apps.core.services.solicitacao_projetos import SEPARADOR_DOS_PROJETOS
from apps.core.types import JsonDict, PayloadHash

from .minimize import minimize_free_text
from .utils import _payload_hash
from .validation import GCAL_EVENT_ID_PREFIX, _event_id_for, _request_id_for

logger = logging.getLogger(__name__)


def build_attendees_for_solicitacao(s: Solicitacao) -> list[JsonDict]:
    """
    Extrai attendees (participantes) de uma Solicitacao.

    Inclui FORMADOR, COORD_ACOMPANHA e o COORDENADOR só quando é o responsável
    (`Solicitacao.coordenador`; sem a FK, quem criou). Decisão do dono (05/11/2026): quem só
    cadastrou o evento para outra pessoa não é convidado, nem pela linha COORDENADOR antiga.
    Para cada participação:
    - Se usuario existe, usa usuario.email
    - Se guest_email existe, usa guest_email

    Args:
        s: Solicitacao

    Returns:
        list[dict]: Lista de attendees no formato Google Calendar
                    [{"email": "..."}, ...]
    """
    responsavel_id = s.coordenador_id or s.usuario_id
    participations = s.participations.filter(
        Q(role__in=["FORMADOR", "COORD_ACOMPANHA"]) | Q(role="COORDENADOR", usuario_id=responsavel_id)
    ).select_related("usuario")

    emails = set()
    for p in participations:
        email = None
        if p.usuario and p.usuario.email:
            email = p.usuario.email
        elif p.guest_email:
            email = p.guest_email

        # S5: o e-mail de reserva `<cpf>@placeholder.local` não é caixa de verdade e mostraria o
        # CPF a todos os convidados.
        if email and not email_de_reserva(email):
            emails.add(email.strip().lower())

    # Retornar lista de dicts no formato Google Calendar
    return [{"email": email} for email in sorted(emails)]


def _build_payload(s: Solicitacao, *, enable_meet: bool = False) -> JsonDict:
    """
    Constrói payload do evento para Google Calendar API (Fase 3 - Template Padronizado).

    Template Format:
    - Title: "{MUNICÍPIO} - {UF} {N}º EF - {tipo_evento.nome} [{NOME NA AGENDA} {segmento}]" (igual à planilha)
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
    # TITLE (SUMMARY) - igual ao da planilha (decisão do dono, 03/11/2026; 417 títulos medidos)
    # ================================================================
    # Formação:       "{MUNICÍPIO} - {UF} {N}º EF - {tipo_evento.nome} [{NOME NA AGENDA} {segmento}]"
    # Acompanhamento: "{MUNICÍPIO} - {UF} {N}º Acompanhamento [{NOME NA AGENDA} {segmento}]"
    # Ex.: "CURVELO - MG 4º EF - Presencial [SUPERATIVAR 4º ano MAT]"
    title_parts = []

    # 1. MUNICÍPIO - UF
    if municipio:
        nome_mun = getattr(municipio, "nome", "")
        uf_mun = getattr(municipio, "uf", "")
        if nome_mun:
            mun_part = f"{nome_mun.upper()} - {uf_mun}" if uf_mun else nome_mun.upper()
            title_parts.append(mun_part)

    # 2. Número do encontro: dígitos ganham "º"; "4º" ou outro texto ficam como estão; vazio, sem número.
    numero = (getattr(s, "encontro", "") or "").strip()
    if numero.isdigit():
        numero = f"{numero}º"
    if numero:
        title_parts.append(numero)

    # 3. Tipo de evento: "Acompanhamento" sem "EF"; os outros "EF - {nome}". Sem tipo, a modalidade.
    is_online = getattr(s, "is_online", False)
    modalidade = "Online" if is_online else "Presencial"
    nome_tipo = (getattr(tipo, "nome", "") or "").strip() or modalidade
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", nome_tipo) if not unicodedata.combining(c))
    title_parts.append("Acompanhamento" if sem_acento.casefold() == "acompanhamento" else f"EF - {nome_tipo}")

    # 4. [NOME NA AGENDA segmento]: o da coleção; vazio, a coleção em maiúsculas; sem coleção, o projeto.
    # Combo (#2036, PR 6): os dois nomes na ordem das vagas, "[UNI DUNI TÊ / CATAVENTOS 2 a 5 anos]".
    if projeto:
        nomes = []
        for p in (projeto, getattr(s, "projeto_2", None)):
            if not p:
                continue
            colecao = getattr(p, "projeto_geral", None)
            nome = (getattr(colecao, "nome_na_agenda", "") or "").strip() or (
                getattr(colecao, "nome", "") or ""
            ).upper()
            nome = nome or (getattr(p, "nome", "") or "").upper()
            if nome:
                nomes.append(nome)
        segmento = (getattr(s, "segmento", "") or "").strip()
        rotulo = f"{SEPARADOR_DOS_PROJETOS.join(nomes)} {segmento}".strip()
        if rotulo:
            title_parts.append(f"[{rotulo}]")

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

    # Seção 2: Projeto. Evento de dois projetos (#2036): "Projetos: A / B", na ordem das vagas, como o
    # rótulo da tela (`rotulo_dos_projetos`). Com um projeto, a linha de sempre.
    projetos_display = []
    for p in (p for p in (projeto, getattr(s, "projeto_2", None)) if p):
        projeto_nome = getattr(p, "nome", "")
        projeto_codigo = getattr(p, "codigo", "")
        if projeto_nome:
            projetos_display.append(f"{projeto_nome} ({projeto_codigo})" if projeto_codigo else projeto_nome)
    if len(projetos_display) == 1:
        description_lines.append(f"📂 Projeto: {projetos_display[0]}")
    elif projetos_display:
        description_lines.append(f"📂 Projetos: {SEPARADOR_DOS_PROJETOS.join(projetos_display)}")

    # Seção 3: Tipo de Evento
    if tipo:
        tipo_nome = getattr(tipo, "nome", "")
        if tipo_nome:
            description_lines.append(f"🎯 Tipo: {tipo_nome}")

    # Seção 3b: Nº da formação (campo `encontro`; decisão do dono de 03/11/2026)
    encontro = (getattr(s, "encontro", "") or "").strip()
    if encontro:
        description_lines.append(f"🔢 Nº da formação: {encontro}")

    # Seção 4: Data/Horário (formatado em America/Fortaleza)
    from zoneinfo import ZoneInfo

    fortaleza_tz = ZoneInfo("America/Fortaleza")
    inicio_local = s.inicio.astimezone(fortaleza_tz)
    fim_local = s.fim.astimezone(fortaleza_tz)
    data_format = "%d/%m/%Y %H:%M"
    description_lines.append(f"📅 Data: {inicio_local.strftime(data_format)} a {fim_local.strftime(data_format)}")

    # Seção 5: Modalidade
    description_lines.append(f"🌐 Modalidade: {modalidade}")

    # Seção 6: Equipe (Formadores + Coordenador)
    equipe_parts = []

    # Formadores (via Participation, a mesma fonte dos attendees; a M2M `formadores` ninguém grava, M10-06).
    # Só quem tem conta: o convidado só por e-mail já vai nos attendees e o e-mail não entra no texto.
    # Uma consulta para formadores e coordenadores além do responsável (COORD_ACOMPANHA, 03/11/2026).
    equipe = list(
        s.participations.filter(role__in=("FORMADOR", "COORD_ACOMPANHA"), usuario__isnull=False).select_related(
            "usuario"
        )
    )
    formadores = {p.usuario_id: p.usuario for p in equipe if p.role == "FORMADOR"}
    if formadores:
        formadores_names = sorted(str(f) for f in formadores.values())  # nome ou "Usuario #id", nunca o login (CPF)
        equipe_parts.append(f"Formador(es): {', '.join(formadores_names)}")

    # Coordenador: o responsável e, depois dele, os demais (COORD_ACOMPANHA; decisão do dono, 03/11/2026).
    extras = sorted(
        str(p.usuario)
        for p in equipe
        if p.role == "COORD_ACOMPANHA" and p.usuario_id != getattr(coordenador, "pk", None)
    )
    coordenadores = ([str(coordenador)] if coordenador else []) + extras
    if len(coordenadores) == 1:
        equipe_parts.append(f"Coordenador(a): {coordenadores[0]}")
    elif coordenadores:
        equipe_parts.append(f"Coordenador(es): {', '.join(coordenadores)}")

    if equipe_parts:
        description_lines.append("")
        description_lines.append("👥 Equipe:")
        for equipe_line in equipe_parts:
            description_lines.append(f"  • {equipe_line}")

    # Seção 7: Links e Observações
    # LGPD arts. 6-III/33: `observacoes` é texto livre transferido ao Google — redige
    # PII incidental (CPF/e-mail) antes da transferência, preservando o restante da nota.
    # S6 (auditoria 14/10, C5): redige o texto INTEIRO e só depois a descrição é cortada em 5000; cortar
    # antes partiria um e-mail no limite e o pedaço iria sem redação. A regex é linear (`minimize.py`).
    observacoes = minimize_free_text(getattr(s, "observacoes", ""))
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
        request_id = _request_id_for(s)
        conference_data = {
            "createRequest": {
                "requestId": request_id,
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    # Construir payload
    payload = {
        # O DELETE do Google é soft-delete (o evento fica `cancelled` e o GET pelo id
        # determinístico ainda o acha). Republicar depois de remover adota o evento e faz
        # PATCH, que só troca os campos enviados: sem `status` aqui ele seguia oculto.
        "status": "confirmed",
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
        # Extrai sufixo do event_id (formato: {GCAL_EVENT_ID_PREFIX}{id})
        event_num = event_id[len(GCAL_EVENT_ID_PREFIX) :] if event_id.startswith(GCAL_EVENT_ID_PREFIX) else event_id
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
