"""
Tests: Batch Operations (Issue #95 - Ações em Massa)

Valida endpoints de ações em massa:
- POST /api/gcal/dashboard/batch/reapply/
- POST /api/gcal/dashboard/batch/resync/

Casos:
1. Reapply retorna 202 com queued count correto
2. Resync retorna 202 com queued count correto
3. Erros para IDs inexistentes listados em errors[]
4. OAuth mode: 403 sem credencial, 202 com credencial
5. RBAC: 403 para perfis sem Controle/Super
6. Validação de limites (max 500 IDs)
7. Resync reseta hash e marca PENDING

Refs:
- Issue #95
- OAuth Phase 7
- RBAC: IsControleOrSuper
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false

from __future__ import annotations
import pytest
from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from django.contrib.auth.models import Group
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework import status as http_status

from apps.core.models import Usuario, Municipio, Projeto, TipoEvento, Solicitacao, GoogleOAuthCredential
from apps.core.services.google_oauth import _encrypt_token


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def api_client():
    """Cliente API para testes."""
    return APIClient()


@pytest.fixture
def usuario_controle(db):
    """Cria usuário do grupo Controle"""
    controle_group, _ = Group.objects.get_or_create(name="Controle")
    user = Usuario.objects.create_user(
        username="controle_batch_test",
        email="controle@aprendereditora.com.br",
        password="testpass123",
        cpf="11111111111",
    )
    user.groups.add(controle_group)
    return user


@pytest.fixture
def usuario_coordenador(db):
    """Cria usuário do grupo Coordenador (sem permissão para batch)"""
    coord_group, _ = Group.objects.get_or_create(name="Coordenador")
    user = Usuario.objects.create_user(
        username="coord_batch_test",
        email="coord@example.com",
        password="testpass123",
        cpf="22222222222",
    )
    user.groups.add(coord_group)
    return user


@pytest.fixture
def setup_solicitacoes(usuario_controle):
    """Cria 3 solicitações aprovadas para testes de batch"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Batch Test", codigo="PBT", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação Batch Test")

    now = timezone.now()
    solicitacoes = []

    for i in range(3):
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=municipio,
            projeto=projeto,
            tipo_evento=tipo_evento,
            tipo="evento",
            inicio=now + timedelta(days=i+1),
            fim=now + timedelta(days=i+1, hours=3),
            status="aprovado",
            gcal_status=Solicitacao.GCalStatus.NONE,
        )
        solicitacoes.append(sol)

    return solicitacoes


@pytest.fixture
def google_oauth_credential(usuario_controle):
    """
    Cria credencial OAuth para testes.

    Usa _encrypt_token() para criptografar tokens de teste.
    """
    access_token = "fake_access_token_batch"
    refresh_token = "fake_refresh_token_batch"

    # Criptografar tokens
    access_encrypted = _encrypt_token(access_token)
    refresh_encrypted = _encrypt_token(refresh_token)

    # Garantir tipo bytes
    if not isinstance(access_encrypted, bytes):
        access_encrypted = access_encrypted.encode() if isinstance(access_encrypted, str) else bytes(access_encrypted)
    if not isinstance(refresh_encrypted, bytes):
        refresh_encrypted = refresh_encrypted.encode() if isinstance(refresh_encrypted, str) else bytes(refresh_encrypted)

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
    if hasattr(cred.access_token_encrypted, 'tobytes'):
        cred.access_token_encrypted = bytes(cred.access_token_encrypted)
    if hasattr(cred.refresh_token_encrypted, 'tobytes'):
        cred.refresh_token_encrypted = bytes(cred.refresh_token_encrypted)

    return cred


# ============================================================================
# TESTES - BATCH REAPPLY
# ============================================================================

@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_reapply_retorna_202_com_queued_count(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    Issue #95: Batch reapply retorna 202 Accepted com queued count correto.

    Valida:
    - Status 202
    - Campo 'queued' com número correto de solicitações
    - Task chamada para cada ID válido
    - Campos dry_run e apply_blocked refletidos na resposta
    """
    # Mock task result
    mock_task.return_value.id = "fake-task-batch-reapply"

    api_client.force_authenticate(user=usuario_controle)

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar payload
    assert response.data['queued'] == 3
    assert response.data['errors'] == []
    assert response.data['dry_run'] is False
    assert response.data['apply_blocked'] is True

    # Task deve ter sido chamada 3 vezes (uma por ID)
    assert mock_task.call_count == 3


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_reapply_retorna_erros_para_ids_inexistentes(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    Issue #95: Batch reapply retorna erros para IDs inexistentes em errors[].

    Valida:
    - Status 202 (sucesso parcial)
    - IDs inexistentes listados em errors[]
    - IDs válidos contados em queued
    """
    api_client.force_authenticate(user=usuario_controle)

    ids_validos = [sol.id for sol in setup_solicitacoes]
    ids_invalidos = [99999, 99998]
    ids = ids_validos + ids_invalidos

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar contadores
    assert response.data['queued'] == 3  # Apenas IDs válidos
    assert len(response.data['errors']) == 2  # 2 IDs inválidos

    # Validar estrutura de errors
    error_ids = [err['id'] for err in response.data['errors']]
    assert 99999 in error_ids
    assert 99998 in error_ids


# ============================================================================
# TESTES - BATCH RESYNC
# ============================================================================

@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_resync_retorna_202_com_queued_count(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    Issue #95: Batch resync retorna 202 Accepted com queued count correto.

    Valida:
    - Status 202
    - Campo 'queued' com número correto
    - Hash resetado para cada solicitação
    - Status marcado como PENDING
    """
    # Mock task result
    mock_task.return_value.id = "fake-task-batch-resync"

    api_client.force_authenticate(user=usuario_controle)

    # Marcar solicitações como PUBLISHED com hash
    for sol in setup_solicitacoes:
        sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
        sol.gcal_payload_hash = "fake-hash-123"
        sol.save()

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar payload
    assert response.data['queued'] == 3
    assert response.data['errors'] == []

    # Validar que hash foi resetado e status marcado PENDING
    for sol in setup_solicitacoes:
        sol.refresh_from_db()
        assert sol.gcal_payload_hash is None
        assert sol.gcal_status == Solicitacao.GCalStatus.PENDING


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_resync_nao_altera_db_em_dry_run(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    Issue #95: Batch resync em dry_run NÃO altera hash/status no banco.

    Valida:
    - Status 202
    - Hash e status permanecem inalterados
    - Task NÃO é chamada em dry_run
    """
    api_client.force_authenticate(user=usuario_controle)

    # Marcar solicitações como PUBLISHED com hash
    for sol in setup_solicitacoes:
        sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
        sol.gcal_payload_hash = "fake-hash-preserve"
        sol.save()

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": True, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED
    assert response.data['dry_run'] is True

    # Validar que hash e status NÃO foram alterados
    for sol in setup_solicitacoes:
        sol.refresh_from_db()
        assert sol.gcal_payload_hash == "fake-hash-preserve"
        assert sol.gcal_status == Solicitacao.GCalStatus.PUBLISHED

    # Task NÃO deve ter sido chamada
    mock_task.assert_not_called()


# ============================================================================
# TESTES - OAUTH MODE
# ============================================================================

@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='oauth')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_reapply_oauth_mode_sem_credencial_retorna_403(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    OAuth Phase 7: Batch reapply sem credencial → 403 Forbidden.

    Valida:
    - Status 403
    - Payload contém code='google_not_connected'
    - Task NÃO é chamada
    """
    api_client.force_authenticate(user=usuario_controle)

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN

    # Validar payload
    assert response.data['code'] == 'google_not_connected'
    assert 'Conecte sua conta Google' in response.data['detail']

    # Task NÃO deve ter sido chamada
    mock_task.assert_not_called()


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='oauth')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_reapply_oauth_mode_com_credencial_retorna_202(
    mock_task, api_client, usuario_controle, setup_solicitacoes, google_oauth_credential
):
    """
    OAuth Phase 7: Batch reapply com credencial → 202 Accepted.

    Valida:
    - Status 202
    - Task chamada com operator_user_id
    - Queued count correto
    """
    # Mock task result
    mock_task.return_value.id = "fake-task-oauth-batch"

    api_client.force_authenticate(user=usuario_controle)

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar queued count
    assert response.data['queued'] == 3

    # Validar que task foi chamada com operator_user_id
    for call_args in mock_task.call_args_list:
        kwargs = call_args[1]
        assert 'operator_user_id' in kwargs
        assert kwargs['operator_user_id'] == usuario_controle.id


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='oauth')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_resync_oauth_mode_sem_credencial_retorna_403(mock_task, api_client, usuario_controle, setup_solicitacoes):
    """
    OAuth Phase 7: Batch resync sem credencial → 403 Forbidden.

    Valida:
    - Status 403
    - Payload contém code='google_not_connected'
    - Task NÃO é chamada
    """
    api_client.force_authenticate(user=usuario_controle)

    # Marcar como PUBLISHED para permitir resync
    for sol in setup_solicitacoes:
        sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
        sol.save()

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN

    # Validar payload
    assert response.data['code'] == 'google_not_connected'

    # Task NÃO deve ter sido chamada
    mock_task.assert_not_called()


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='oauth')
@patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
def test_batch_resync_oauth_mode_com_credencial_retorna_202(
    mock_task, api_client, usuario_controle, setup_solicitacoes, google_oauth_credential
):
    """
    OAuth Phase 7: Batch resync com credencial → 202 Accepted.

    Valida:
    - Status 202
    - Task chamada com operator_user_id
    - Hash resetado e status PENDING
    """
    # Mock task result
    mock_task.return_value.id = "fake-task-oauth-resync"

    api_client.force_authenticate(user=usuario_controle)

    # Marcar como PUBLISHED com hash
    for sol in setup_solicitacoes:
        sol.gcal_status = Solicitacao.GCalStatus.PUBLISHED
        sol.gcal_payload_hash = "fake-hash-oauth"
        sol.save()

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 202
    assert response.status_code == http_status.HTTP_202_ACCEPTED

    # Validar queued count
    assert response.data['queued'] == 3

    # Validar hash resetado
    for sol in setup_solicitacoes:
        sol.refresh_from_db()
        assert sol.gcal_payload_hash is None
        assert sol.gcal_status == Solicitacao.GCalStatus.PENDING


# ============================================================================
# TESTES - RBAC
# ============================================================================

@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
def test_batch_reapply_rbac_coordenador_retorna_403(api_client, usuario_coordenador, setup_solicitacoes):
    """
    RBAC: Batch reapply por Coordenador (sem permissão) → 403 Forbidden.

    Valida:
    - Status 403
    - Apenas Controle/Super podem usar batch operations
    """
    api_client.force_authenticate(user=usuario_coordenador)

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
def test_batch_resync_rbac_coordenador_retorna_403(api_client, usuario_coordenador, setup_solicitacoes):
    """
    RBAC: Batch resync por Coordenador (sem permissão) → 403 Forbidden.

    Valida:
    - Status 403
    - Apenas Controle/Super podem usar batch operations
    """
    api_client.force_authenticate(user=usuario_coordenador)

    ids = [sol.id for sol in setup_solicitacoes]

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 403
    assert response.status_code == http_status.HTTP_403_FORBIDDEN


# ============================================================================
# TESTES - VALIDAÇÃO DE LIMITES
# ============================================================================

@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
def test_batch_reapply_valida_limite_500_ids(api_client, usuario_controle):
    """
    Issue #95: Batch reapply valida limite de 500 IDs.

    Valida:
    - Status 400 quando ids.length > 500
    - Mensagem de erro clara
    """
    api_client.force_authenticate(user=usuario_controle)

    ids = list(range(1, 502))  # 501 IDs

    response = api_client.post(
        "/api/gcal/dashboard/batch/reapply/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 400
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    assert 'Limite de 500 IDs' in response.data['detail']


@pytest.mark.django_db
@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
def test_batch_resync_valida_limite_500_ids(api_client, usuario_controle):
    """
    Issue #95: Batch resync valida limite de 500 IDs.

    Valida:
    - Status 400 quando ids.length > 500
    - Mensagem de erro clara
    """
    api_client.force_authenticate(user=usuario_controle)

    ids = list(range(1, 502))  # 501 IDs

    response = api_client.post(
        "/api/gcal/dashboard/batch/resync/",
        {"ids": ids, "dry_run": False, "apply_blocked": True},
        format="json"
    )

    # Validar 400
    assert response.status_code == http_status.HTTP_400_BAD_REQUEST
    assert 'Limite de 500 IDs' in response.data['detail']
