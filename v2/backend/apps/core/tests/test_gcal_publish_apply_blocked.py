"""
Testes para comportamento de apply_blocked + dry_run em endpoints GCal (RF05/PA-03 - PR19).

Valida:
- dry_run deve funcionar mesmo com GCAL_CLIENT != "google" (apply_blocked)
- Publicação real (dry_run=False) deve ser bloqueada com 409 quando apply_blocked
- Publicação real deve funcionar normalmente quando GCAL_CLIENT == "google"
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import (
    Municipio,
    Projeto,
    Solicitacao,
    TipoEvento,
    Usuario,
)


def mock_task_result():
    """Helper para criar mock de AsyncResult com id serializável"""
    mock_result = Mock()
    mock_result.id = "test-task-id-12345"
    return mock_result


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_test",
        email="controle@test.com",
        password="testpass",
        cpf="33333333333",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_aprovada(usuario_controle):
    """Solicitação aprovada para testes de publicação"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Teste", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    now = timezone.now()
    return Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
    )


@pytest.mark.django_db
class TestPublishApplyBlocked:
    """Testes para endpoint /api/solicitacoes/{id}/publish/ com apply_blocked"""

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_dry_run_allowed_with_apply_blocked(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05/PA-03: dry_run deve funcionar mesmo com GCAL_CLIENT != "google".

        Cenário:
        - GCAL_CLIENT = "fake" (não é "google")
        - apply_blocked = False (não forçar)
        - dry_run = True

        Resultado esperado: 200/202 OK (não bloqueia)
        """
        mock_task.return_value = mock_task_result()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": True, "apply_blocked": False},
            format="json",
        )

        # Dry-run deve sempre funcionar
        assert response.status_code in (
            200,
            202,
        ), f"Dry-run deve ser permitido. Got {response.status_code}: {response.data}"

        # Task deve ter sido disparada
        assert mock_task.called, "Task Celery deve ter sido chamada"

        # Validar argumentos da task
        call_args = mock_task.call_args
        assert call_args[0][0] == solicitacao_aprovada.id
        assert call_args[1]["dry_run"] is True

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_real_publish_blocked_with_apply_blocked_false(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05/PA-03: Publicação real deve ser bloqueada com 409 quando apply_blocked=False.

        Cenário:
        - GCAL_CLIENT = "fake" (não é "google")
        - apply_blocked = False
        - dry_run = False

        Resultado esperado: 409 CONFLICT
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json",
        )

        # Publicação real deve ser bloqueada
        assert (
            response.status_code == 409
        ), f"Publicação real deve ser bloqueada. Got {response.status_code}: {response.data}"

        assert "bloqueada" in response.data.get("detail", "").lower()
        # §1 Epic #459: standardized error format puts details in 'errors' key
        assert response.data.get("errors", {}).get("features_apply_blocked") is True
        assert response.data.get("errors", {}).get("dry_run_allowed") is True

        # Task NÃO deve ter sido disparada
        assert not mock_task.called, "Task não deve ser chamada quando bloqueado"

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_real_publish_allowed_with_apply_blocked_true(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05/PA-03: Publicação real com apply_blocked=True deve funcionar.

        Cenário:
        - GCAL_CLIENT = "fake"
        - apply_blocked = True (forçar)
        - dry_run = False

        Resultado esperado: 200/202 OK
        """
        mock_task.return_value = mock_task_result()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": True},
            format="json",
        )

        # Deve permitir quando apply_blocked=True
        assert response.status_code in (
            200,
            202,
        ), f"Publicação com apply_blocked=True deve ser permitida. Got {response.status_code}: {response.data}"

        # Task deve ter sido disparada
        assert mock_task.called

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "google")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_real_publish_allowed_with_google_client(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05: Publicação real deve funcionar normalmente com GCAL_CLIENT="google".

        Cenário:
        - GCAL_CLIENT = "google"
        - apply_blocked = False
        - dry_run = False

        Resultado esperado: 200/202 OK (não bloqueia)
        """
        mock_task.return_value = mock_task_result()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json",
        )

        # Não deve bloquear quando GCAL_CLIENT == "google"
        assert response.status_code in (
            200,
            202,
        ), f"Publicação com GCAL_CLIENT=google deve ser permitida. Got {response.status_code}: {response.data}"

        # Task deve ter sido disparada
        assert mock_task.called

        # Validar argumentos
        call_args = mock_task.call_args
        assert call_args[1]["dry_run"] is False
        assert call_args[1]["apply_blocked"] is False

    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_solicitacao_nao_aprovada_blocked(
        self, mock_throttle1, mock_throttle2, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05: Solicitações não aprovadas devem retornar 400.

        Cenário:
        - status = "pendente"
        - dry_run = True

        Resultado esperado: 400 BAD REQUEST
        """
        # Mudar status para pendente
        solicitacao_aprovada.status = "pendente"
        solicitacao_aprovada.save()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/", {"dry_run": True}, format="json"
        )

        assert response.status_code == 400
        assert "aprovada" in response.data.get("detail", "").lower()

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_gcal_status_not_changed_on_dry_run(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05: dry_run não deve alterar gcal_status.

        Cenário:
        - dry_run = True
        - gcal_status inicial = NONE

        Resultado esperado: gcal_status permanece NONE
        """
        mock_task.return_value = mock_task_result()

        # Garantir status inicial
        solicitacao_aprovada.gcal_status = "NONE"
        solicitacao_aprovada.save()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/", {"dry_run": True}, format="json"
        )

        assert response.status_code in (200, 202)

        # Verificar que status não mudou
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == "NONE", "dry_run não deve alterar gcal_status"

    @patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_gcal_status_changed_on_real_publish(
        self, mock_throttle1, mock_throttle2, mock_task, solicitacao_aprovada, usuario_controle
    ):
        """
        RF05: Publicação real deve marcar gcal_status como PENDING.

        Cenário:
        - dry_run = False
        - apply_blocked = True
        - gcal_status inicial = NONE

        Resultado esperado: gcal_status = PENDING
        """
        mock_task.return_value = mock_task_result()

        # Garantir status inicial
        solicitacao_aprovada.gcal_status = "NONE"
        solicitacao_aprovada.save()

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": True},
            format="json",
        )

        assert response.status_code in (200, 202)

        # Verificar que status mudou
        solicitacao_aprovada.refresh_from_db()
        assert solicitacao_aprovada.gcal_status == "PENDING", "Publicação real deve marcar como PENDING"

    @patch("django.conf.settings.GCAL_CLIENT", "fake")
    @patch("rest_framework.throttling.AnonRateThrottle.allow_request", return_value=True)
    @patch("rest_framework.throttling.UserRateThrottle.allow_request", return_value=True)
    def test_preview_always_allowed(self, mock_throttle1, mock_throttle2, solicitacao_aprovada, usuario_controle):
        """
        RF05: Preview deve sempre funcionar, independente de apply_blocked.

        Cenário:
        - GCAL_CLIENT = "fake"
        - Endpoint: /preview-gcal/

        Resultado esperado: 200 OK
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.post(f"/api/solicitacoes/{solicitacao_aprovada.id}/preview-gcal/", format="json")

        assert (
            response.status_code == 200
        ), f"Preview deve sempre funcionar. Got {response.status_code}: {response.data}"

        assert "preview" in response.data
        assert "event_id" in response.data["preview"]
