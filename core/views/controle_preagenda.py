# core/views/controle_preagenda.py
"""
View de Pré-Agenda (fila operacional) - Hotfix Dia 3 COMPLETO
Lista solicitações em estado CRIADO/APROVADO aguardando agendamento no Google Calendar.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from core.models import Solicitacao, EventoGoogleCalendar
from core.services.google_calendar_automation import manual_create_calendar_event
import hashlib
import json
import uuid


@login_required
@permission_required("core.sync_calendar", raise_exception=True)
def preagenda_list(request):
    """
    Lista solicitações em fila de pré-agenda (status CRIADO ou APROVADO).
    Aguardam criação manual no Google Calendar.
    """
    qs = (
        Solicitacao.objects.select_related(
            "projeto", "municipio", "tipo_evento", "usuario_solicitante"
        )
        .prefetch_related("formadores")
        .filter(status__in=["CRIADO", "APROVADO"])
        .order_by("data_inicio")
    )
    return render(request, "core/controle/preagenda_list.html", {"itens": qs})


@login_required
@permission_required("core.sync_calendar", raise_exception=True)
def preagenda_calendar_action(request, solicitacao_id):
    """
    Ação: Criar/Atualizar evento no Google Calendar (idempotente).

    - Gera request_id/hash_payload para idempotência
    - Chama service de Calendar
    - Sucesso: status=AGENDADO + atualiza EventoGoogleCalendar
    - Falha: mantém CRIADO/APROVADO + incrementa tentativas + registra erro
    """
    s = get_object_or_404(Solicitacao, pk=solicitacao_id)

    # Gerar payload idempotente
    payload = {
        "id": str(s.id),
        "titulo": s.titulo_evento,
        "data_inicio": str(s.data_inicio),
        "data_fim": str(s.data_fim),
        "municipio": str(s.municipio.id) if s.municipio else None,
        "projeto": str(s.projeto.id) if s.projeto else None,
    }
    request_id = uuid.uuid4().hex
    hash_payload = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()

    # Get or create registro de sincronização
    egc, _ = EventoGoogleCalendar.objects.get_or_create(
        solicitacao=s,
        defaults={
            "request_id": request_id,
            "hash_payload": hash_payload,
            "tentativas": 0,
        },
    )

    try:
        # Chamar service de Calendar (requires user param)
        resultado = manual_create_calendar_event(s, request.user)

        if resultado.get("success"):
            # Sucesso: atualizar status e registro
            s.status = "AGENDADO"
            s.save(update_fields=["status"])

            egc.google_event_id = resultado.get("event_id")
            egc.hash_payload = hash_payload
            egc.ultimo_erro = ""
            egc.save()
        else:
            # Falha lógica: incrementar tentativas
            egc.tentativas = (egc.tentativas or 0) + 1
            egc.ultimo_erro = resultado.get("error", "Erro desconhecido")
            egc.save()

    except Exception as e:
        # Falha de exceção: incrementar tentativas
        egc.tentativas = (egc.tentativas or 0) + 1
        egc.ultimo_erro = str(e)
        egc.save()

    return HttpResponseRedirect(reverse("core:controle-preagenda"))
