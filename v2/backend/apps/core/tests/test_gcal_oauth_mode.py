"""
Tests: OAuth Mode (Fase 7 - Testes Mínimos)

Testa comportamento do sistema em modo OAuth:
- GCAL_CLIENT='google'
- GCAL_AUTH_MODE='oauth'

Casos:
1. Publish sem credencial → 403 com code='google_not_connected'
2. Publish com credencial → 202 (task enfileirada com operator_user_id)
3. Resync sem credencial → 403 com code='google_not_connected'
4. Resync com credencial → 202 (task enfileirada com operator_user_id)

Refs:
- OAuth Phase 7: Testes mínimos modo OAuth
- fechar_plano_gcal.md
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import override_settings
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

import pytest

from apps.core.models import GoogleOAuthCredential, Municipio, Projeto, Solicitacao, TipoEvento, Usuario
from apps.core.services.google_oauth import _encrypt_token

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def usuario_controle(db):
    """Cria usuário do grupo Controle (xdist-safe: unique IDs)."""
    import uuid

    uid = uuid.uuid4().hex[:8]
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = Usuario.objects.create_user(
        username=f"controle_oauth_{uid}",
        email=f"controle_{uid}@aprendereditora.com.br",
        password="testpass123",
        cpf=f"111{uid.ljust(8, '0')}",
    )
    user.groups.add(controle_group)
    return user


@pytest.fixture
def solicitacao_aprovada(usuario_controle):
    """Cria solicitação aprovada para testes de publish/resync (xdist-safe)."""
    import uuid

    uid = uuid.uuid4().hex[:8]
    municipio = Municipio.objects.create(nome=f"Fortaleza_oauth_{uid}", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome=f"Projeto OAuth {uid}", codigo=f"PO{uid[:3]}", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome=f"Formação OAuth {uid}")

    now = timezone.now()
    return Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        tipo="evento",
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=3),
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.NONE,
    )


@pytest.fixture
def google_oauth_credential(usuario_controle):
    """
    Cria credencial OAuth para testes.

    Usa _encrypt_token() para criptografar tokens de teste.
    """
    access_token = "fake_access_token_oauth_mode"
    refresh_token = "fake_refresh_token_oauth_mode"

    # Criptografar tokens
    access_encrypted = _encrypt_token(access_token)
    refresh_encrypted = _encrypt_token(refresh_token)

    # Garantir tipo bytes
    if not isinstance(access_encrypted, bytes):
        access_encrypted = access_encrypted.encode() if isinstance(access_encrypted, str) else bytes(access_encrypted)
    if not isinstance(refresh_encrypted, bytes):
        refresh_encrypted = (
            refresh_encrypted.encode() if isinstance(refresh_encrypted, str) else bytes(refresh_encrypted)
        )

    cred = GoogleOAuthCredential.objects.create(
        user=usuario_controle,
        google_email="controle@aprendereditora.com.br",
        access_token_encrypted=access_encrypted,
        refresh_token_encrypted=refresh_encrypted,
        token_expiry=timezone.now() + timedelta(hours=1),
        scope="https://www.googleapis.com/auth/calendar",
        default_calendar_id="primary",
    )

    # PostgreSQL BinaryField pode retornar memoryview
    cred.refresh_from_db()
    if hasattr(cred.access_token_encrypted, "tobytes"):
        cred.access_token_encrypted = bytes(cred.access_token_encrypted)
    if hasattr(cred.refresh_token_encrypted, "tobytes"):
        cred.refresh_token_encrypted = bytes(cred.refresh_token_encrypted)

    return cred


# ============================================================================
# TESTES - PUBLISH SEM/COM CREDENCIAL
# ============================================================================


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_publish_oauth_mode_sem_credencial_retorna_403(mock_task, solicitacao_aprovada, usuario_controle):
    """
    OAuth Phase 7: Publish sem credencial → 403 Forbidden com code='google_not_connected'

    Valida:
    - Status 403
    - Payload contém code='google_not_connected'
    - Task NÃO é chamada
    """
    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(
        f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
        {"dry_run": False, "apply_blocked": True},
        format="json",
    )

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN

    # Validar payload
    assert response.data["code"] == "google_not_connected"
    assert "Conecte sua conta Google" in response.data["detail"]

    # Task NÃO deve ter sido chamada
    mock_task.assert_not_called()


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_publish_oauth_mode_com_credencial_retorna_202(
    mock_task, solicitacao_aprovada, usuario_controle, google_oauth_credential
):
    """
    OAuth Phase 7: Publish com credencial → 202 Accepted (task enfileirada)

    Valida:
    - Status 202
    - Task chamada com operator_user_id
    """
    # Mock task result
    mock_task.return_value.id = "fake-task-id-123"

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(
        f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
        {"dry_run": False, "apply_blocked": True},
        format="json",
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar task chamada com operator_user_id
    mock_task.assert_called_once_with(
        solicitacao_aprovada.id, dry_run=False, apply_blocked=True, operator_user_id=usuario_controle.id
    )


# ============================================================================
# TESTES - RESYNC SEM/COM CREDENCIAL
# ============================================================================


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_resync_oauth_mode_sem_credencial_retorna_403(mock_task, solicitacao_aprovada, usuario_controle):
    """
    OAuth Phase 7: Resync sem credencial → 403 Forbidden com code='google_not_connected'

    Valida:
    - Status 403
    - Payload contém code='google_not_connected'
    - Task NÃO é chamada
    """
    # Marcar como PUBLISHED para permitir resync
    solicitacao_aprovada.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    solicitacao_aprovada.external_event_id = "asv2-123"
    solicitacao_aprovada.save()

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/resync-gcal/", format="json")

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN

    # Validar payload
    assert response.data["code"] == "google_not_connected"
    assert "Conecte sua conta Google" in response.data["detail"]

    # Task NÃO deve ter sido chamada
    mock_task.assert_not_called()


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_resync_oauth_mode_com_credencial_retorna_202(
    mock_task, solicitacao_aprovada, usuario_controle, google_oauth_credential
):
    """
    OAuth Phase 7: Resync com credencial → 202 Accepted (task enfileirada)

    Valida:
    - Status 202
    - Task chamada com operator_user_id
    """
    # Marcar como PUBLISHED para permitir resync
    solicitacao_aprovada.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    solicitacao_aprovada.external_event_id = "asv2-123"
    solicitacao_aprovada.save()

    # Mock task result
    mock_task.return_value.id = "fake-task-id-456"

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/resync-gcal/", format="json")

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar task chamada com operator_user_id
    mock_task.assert_called_once_with(
        solicitacao_aprovada.id, dry_run=False, apply_blocked=False, operator_user_id=usuario_controle.id
    )


# ============================================================================
# TESTES - CANCEL SEM/COM CREDENCIAL (fix #572)
# ============================================================================


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_cancel_solicitacao_from_gcal.delay")
def test_cancel_oauth_mode_sem_credencial_retorna_403(mock_task, solicitacao_aprovada, usuario_controle):
    """
    Fix #572: Cancel sem credencial OAuth → 403 Forbidden

    Valida:
    - Status 403
    - Payload contém code='google_not_connected'
    - Task NÃO é chamada
    """
    # Marcar como PUBLISHED para permitir cancel
    solicitacao_aprovada.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    solicitacao_aprovada.external_event_id = "asv2-cancel-test"
    solicitacao_aprovada.save()

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/cancel-gcal/", format="json")

    assert response.status_code == http_status.HTTP_403_FORBIDDEN
    assert response.data["code"] == "google_not_connected"
    mock_task.assert_not_called()


@pytest.mark.django_db
@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="oauth")
@patch("apps.core.tasks.task_cancel_solicitacao_from_gcal.delay")
def test_cancel_oauth_mode_com_credencial_retorna_202(
    mock_task, solicitacao_aprovada, usuario_controle, google_oauth_credential
):
    """
    Fix #572: Cancel com credencial OAuth → 202 Accepted (task com operator_user_id)

    Valida:
    - Status 202
    - Task chamada com operator_user_id
    """
    # Marcar como PUBLISHED para permitir cancel
    solicitacao_aprovada.gcal_status = Solicitacao.GCalStatus.PUBLISHED
    solicitacao_aprovada.external_event_id = "asv2-cancel-test"
    solicitacao_aprovada.save()

    mock_task.return_value.id = "fake-cancel-task-789"

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

    response = client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/cancel-gcal/", format="json")

    assert response.status_code == http_status.HTTP_202_ACCEPTED
    mock_task.assert_called_once_with(
        solicitacao_aprovada.id,
        operator_user_id=usuario_controle.id,
    )
