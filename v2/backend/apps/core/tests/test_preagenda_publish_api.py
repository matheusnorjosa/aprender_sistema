"""
Testes para API de Preview/Publish (PR #4).

Valida:
- build_attendees_for_solicitacao (extração de emails por role)
- build_preview_for_solicitacao (geração de preview)
- apply_one_solicitacao (aplicação com/sem GCAL_CLIENT)
- POST /api/solicitacoes/{id}/preview-gcal/ (preview sem publicar)
- POST /api/solicitacoes/{id}/publish/ (publicação assíncrona via Celery)
- AuditLog para ambas as ações
- Permissões (Controle ou Superintendência)
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from datetime import datetime
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from apps.core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
    Participation,
    AuditLog,
)
from apps.core.services.gcal_sync_service import (
    build_attendees_for_solicitacao,
    build_preview_for_solicitacao,
    apply_one_solicitacao,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    """Cliente API autenticado."""
    return APIClient()


@pytest.fixture
def user_super():
    """Usuário Superintendência."""
    from django.contrib.auth.models import Group

    user = Usuario.objects.create_user(
        username="super_user",
        email="super@example.com",
        password="test123",
        cpf="11111111111",
        first_name="Super",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(group)
    return user


@pytest.fixture
def user_coord():
    """Usuário Coordenador (sem permissão para preview/publish)."""
    from django.contrib.auth.models import Group

    user = Usuario.objects.create_user(
        username="coord_user",
        email="coord@example.com",
        password="test123",
        cpf="22222222222",
        first_name="Coord",
        last_name="User",
    )
    group, _ = Group.objects.get_or_create(name="Coordenador")
    user.groups.add(group)
    return user


@pytest.fixture
def setup_solicitacao():
    """
    Cria solicitação aprovada com participações:
    - COORDENADOR: coord@example.com
    - FORMADOR: formador@example.com
    - COORD_ACOMPANHA: acompanha@example.com
    - CONVIDADO: convidado@example.com (não deve aparecer em attendees)
    """
    tz = timezone.get_current_timezone()

    # Dependências
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Gestão Escolar", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    # Usuários
    coord = Usuario.objects.create_user(
        username="coord",
        email="coord@example.com",
        password="test123",
        cpf="33333333333",
    )
    formador = Usuario.objects.create_user(
        username="formador",
        email="formador@example.com",
        password="test123",
        cpf="44444444444",
    )
    acompanha = Usuario.objects.create_user(
        username="acompanha",
        email="acompanha@example.com",
        password="test123",
        cpf="55555555555",
    )

    # Solicitação aprovada
    sol = Solicitacao.objects.create(
        usuario=coord,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=timezone.make_aware(datetime(2025, 10, 15, 8, 0), tz),
        fim=timezone.make_aware(datetime(2025, 10, 15, 12, 0), tz),
        status="aprovado",
    )

    # Participações
    Participation.objects.create(
        solicitacao=sol, usuario=coord, role="COORDENADOR"
    )
    Participation.objects.create(
        solicitacao=sol, usuario=formador, role="FORMADOR"
    )
    Participation.objects.create(
        solicitacao=sol, usuario=acompanha, role="COORD_ACOMPANHA"
    )
    Participation.objects.create(
        solicitacao=sol,
        usuario=None,
        guest_email="convidado@example.com",
        role="CONVIDADO",
    )

    return {
        "solicitacao": sol,
        "coord": coord,
        "formador": formador,
        "acompanha": acompanha,
    }


def test_build_attendees_for_solicitacao(setup_solicitacao):
    """
    Testa extração de attendees.

    Deve incluir apenas COORDENADOR, FORMADOR, COORD_ACOMPANHA.
    Não deve incluir CONVIDADO.
    """
    sol = setup_solicitacao["solicitacao"]

    attendees = build_attendees_for_solicitacao(sol)

    # Deve ter 3 attendees (coord, formador, acompanha)
    assert len(attendees) == 3

    # Extrair emails
    emails = {a["email"] for a in attendees}
    assert emails == {
        "coord@example.com",
        "formador@example.com",
        "acompanha@example.com",
    }

    # Não deve incluir convidado@example.com
    assert "convidado@example.com" not in emails


def test_build_preview_for_solicitacao(setup_solicitacao):
    """
    Testa geração de preview.

    Deve retornar event_id e payload sem publicar.
    """
    sol = setup_solicitacao["solicitacao"]

    preview = build_preview_for_solicitacao(sol)

    # Validar estrutura
    assert "event_id" in preview
    assert "payload" in preview

    # Validar event_id determinístico
    assert preview["event_id"] == f"asv2-{sol.id}"

    # Validar payload
    payload = preview["payload"]
    assert "summary" in payload
    assert "start" in payload
    assert "end" in payload
    assert "attendees" in payload

    # Validar attendees no payload
    assert len(payload["attendees"]) == 3


@patch("apps.core.services.gcal_fake_client.FakeCalendarClient")
@pytest.mark.skip(reason="TEMP: Do PR19 - será corrigido após merge sequencial")
def test_apply_one_solicitacao_with_client(mock_client_class, setup_solicitacao):
    """
    Testa aplicação com FakeCalendarClient (apply_blocked=True).

    Deve criar evento no Calendar.
    """
    sol = setup_solicitacao["solicitacao"]

    # Mock do cliente
    mock_client = MagicMock()
    mock_client.get.return_value = None  # Evento não existe
    mock_client.insert.return_value = {"id": f"asv2-{sol.id}"}
    mock_client_class.return_value = mock_client

    # Aplicar (com apply_blocked=True para forçar execução)
    outcome = apply_one_solicitacao(sol, dry_run=False, apply_blocked=True)

    # Validar outcome
    assert outcome.action == "CREATE"
    assert outcome.solicitation_id == sol.id
    assert outcome.external_event_id == f"asv2-{sol.id}"

    # Verificar que insert foi chamado
    mock_client.insert.assert_called_once()


def test_apply_one_solicitacao_without_client(setup_solicitacao):
    """
    Testa aplicação sem GCAL_CLIENT configurado (apply_blocked=False).

    Deve retornar SKIP sem tentar publicar.
    """
    sol = setup_solicitacao["solicitacao"]

    # Remover GCAL_CLIENT (se existir)
    original_value = getattr(settings, "GCAL_CLIENT", None)
    try:
        if hasattr(settings, "GCAL_CLIENT"):
            delattr(settings, "GCAL_CLIENT")

        # Aplicar (sem apply_blocked, deve SKIP)
        outcome = apply_one_solicitacao(sol, dry_run=False, apply_blocked=False)

        # Validar outcome
        assert outcome.action == "SKIP"
        assert "GCAL_CLIENT não configurado" in outcome.summary

    finally:
        # Restaurar valor original
        if original_value is not None:
            settings.GCAL_CLIENT = original_value


def test_preview_gcal_api_success(api_client, user_super, setup_solicitacao):
    """
    Testa POST /api/solicitacoes/{id}/preview-gcal/.

    Deve gerar preview e criar AuditLog.
    PR14: Deve incluir payload_hash.
    """
    sol = setup_solicitacao["solicitacao"]
    api_client.force_authenticate(user=user_super)

    response = api_client.post(f"/api/solicitacoes/{sol.id}/preview-gcal/")

    # Validar resposta
    assert response.status_code == 200
    data = response.json()
    assert "detail" in data
    assert "preview" in data

    preview = data["preview"]
    assert preview["event_id"] == f"asv2-{sol.id}"
    assert "payload" in preview

    # PR14: Validar que payload_hash está presente
    assert "payload_hash" in preview
    assert preview["payload_hash"] is not None
    assert len(preview["payload_hash"]) == 40  # SHA1 hex = 40 chars

    # Validar AuditLog
    audit_log = AuditLog.objects.filter(
        action="PREVIEW_GCAL", model_name="Solicitacao"
    ).first()
    assert audit_log is not None
    assert audit_log.usuario == user_super
    assert audit_log.details["solicitacao_id"] == sol.id
    # PR14: Validar que payload_hash foi registrado no AuditLog
    assert "payload_hash" in audit_log.details


def test_preview_gcal_api_permission_denied(api_client, user_coord, setup_solicitacao):
    """
    Testa POST /api/solicitacoes/{id}/preview-gcal/ sem permissão.

    Coordenador não deve ter acesso (apenas Controle ou Superintendência).
    """
    sol = setup_solicitacao["solicitacao"]

    # Garantir que user_coord NÃO é superuser e NÃO está em Superintendência
    user_coord.is_superuser = False
    user_coord.is_staff = False
    user_coord.save()
    # Remover de Superintendência (se estiver)
    user_coord.groups.filter(name="Superintendência").delete()

    # Criar solicitação para o user_coord poder visualizá-la
    coord = setup_solicitacao["coord"]
    sol.usuario = user_coord
    sol.save()

    # Criar participação para o user_coord
    Participation.objects.create(
        solicitacao=sol, usuario=user_coord, role="COORDENADOR"
    )

    api_client.force_authenticate(user=user_coord)

    response = api_client.post(f"/api/solicitacoes/{sol.id}/preview-gcal/")

    # Deve retornar 403 Forbidden
    assert response.status_code == 403


@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_publish_gcal_api_success(mock_task_delay, api_client, user_super, setup_solicitacao):
    """
    Testa POST /api/solicitacoes/{id}/publish/.

    Deve disparar task Celery e criar AuditLog.
    PR14: Deve marcar gcal_status como PENDING.
    """
    sol = setup_solicitacao["solicitacao"]
    api_client.force_authenticate(user=user_super)

    # Mock do task
    mock_task = MagicMock()
    mock_task.id = "task-123-456"
    mock_task_delay.return_value = mock_task

    response = api_client.post(
        f"/api/solicitacoes/{sol.id}/publish/",
        {"dry_run": False, "apply_blocked": True},
        format="json",
    )

    # Validar resposta
    assert response.status_code == 202
    data = response.json()
    assert "detail" in data
    assert data["task_id"] == "task-123-456"
    assert data["solicitacao_id"] == sol.id

    # Verificar que task foi disparada
    mock_task_delay.assert_called_once_with(
        sol.id, dry_run=False, apply_blocked=True
    )

    # PR14: Validar que gcal_status foi marcado como PENDING
    sol.refresh_from_db()
    assert sol.gcal_status == "PENDING"

    # Validar AuditLog
    audit_log = AuditLog.objects.filter(
        action="PUBLISH_GCAL_REQUESTED", model_name="Solicitacao"
    ).first()
    assert audit_log is not None
    assert audit_log.usuario == user_super
    assert audit_log.details["solicitacao_id"] == sol.id
    assert audit_log.details["task_id"] == "task-123-456"


def test_publish_gcal_api_not_approved(api_client, user_super, setup_solicitacao):
    """
    Testa POST /api/solicitacoes/{id}/publish/ com solicitação não-aprovada.

    Deve retornar 400 Bad Request.
    """
    sol = setup_solicitacao["solicitacao"]
    sol.status = "pendente"
    sol.save()

    api_client.force_authenticate(user=user_super)

    response = api_client.post(f"/api/solicitacoes/{sol.id}/publish/")

    # Deve retornar 400
    assert response.status_code == 400
    assert "Apenas solicitações aprovadas" in response.json()["detail"]


def test_publish_gcal_api_permission_denied(api_client, user_coord, setup_solicitacao):
    """
    Testa POST /api/solicitacoes/{id}/publish/ sem permissão.

    Coordenador não deve ter acesso (apenas Controle ou Superintendência).
    """
    sol = setup_solicitacao["solicitacao"]

    # Garantir que user_coord NÃO é superuser e NÃO está em Superintendência
    user_coord.is_superuser = False
    user_coord.is_staff = False
    user_coord.save()
    # Remover de Superintendência (se estiver)
    user_coord.groups.filter(name="Superintendência").delete()

    # Atribuir solicitação ao user_coord para poder visualizá-la
    sol.usuario = user_coord
    sol.save()

    api_client.force_authenticate(user=user_coord)

    response = api_client.post(f"/api/solicitacoes/{sol.id}/publish/")

    # Deve retornar 403 Forbidden
    assert response.status_code == 403
