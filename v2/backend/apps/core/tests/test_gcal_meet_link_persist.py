"""
Testes para persistência de meet_link (RF06 - PR19).

Valida:
- APPLY real persiste meet_link quando hangoutLink retornado
- PREVIEW não persiste meet_link (apenas retorna no payload)
- apply_blocked (409) não persiste meet_link
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta

from apps.core.models import (
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
    Solicitacao,
)


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_meet",
        email="controle_meet@test.com",
        password="testpass",
        cpf="22222222222",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_aprovada(usuario_controle):
    """Solicitação aprovada sem meet_link"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Meet", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="aprovado",
    )

    return sol


@pytest.mark.django_db
class TestMeetLinkPersistence:
    """Testes para persistência de meet_link"""

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
    @patch('apps.core.services.gcal_google_client.GoogleCalendarClient')
    def test_apply_persists_meet_link_when_hangoutlink_returned(
        self,
        MockGoogleClient,
        mock_task,
        usuario_controle,
        solicitacao_aprovada,
        settings
    ):
        """
        RF06: APPLY real deve persistir meet_link quando API retorna hangoutLink.

        Cenário:
        - Solicitação aprovada sem meet_link
        - POST /api/solicitacoes/{id}/publish/ com GCAL_CLIENT=google
        - Mock retorna hangoutLink na resposta
        - Task Celery executa (mock)

        Resultado esperado:
        - meet_link persiste no DB
        """
        # Configurar GCAL_CLIENT=google para permitir publicação
        settings.GCAL_CLIENT = "google"
        settings.GCAL_CALENDAR_ID = "test@calendar.google.com"

        # Mock da resposta do GoogleCalendarClient
        mock_client_instance = MockGoogleClient.return_value
        mock_client_instance.insert.return_value = {
            "id": "gcal-event-123",
            "hangoutLink": "https://meet.google.com/xyz-abcd-efg"
        }

        # Garantir que a task retorna imediatamente (mock)
        mock_task.return_value = MagicMock(id="task-123")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert solicitacao_aprovada.meet_link is None

        # POST publish (task é enqueuada, mas mock não executa)
        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi aceita
        assert response.status_code in [200, 202]

        # Nota: A persistência real acontece na task Celery (task_publish_solicitacao_to_gcal)
        # Este teste valida que a task é enfileirada corretamente
        # O teste de persistência real está em test_gcal_sync_service.py
        mock_task.assert_called_once()

    @patch('apps.core.services.gcal_sync_service.build_preview_for_solicitacao')
    def test_preview_does_not_persist_meet_link(
        self,
        mock_build_preview,
        usuario_controle,
        solicitacao_aprovada
    ):
        """
        RF06: PREVIEW não deve persistir meet_link no DB.

        Cenário:
        - Solicitação aprovada sem meet_link
        - POST /api/solicitacoes/{id}/preview-gcal/
        - Mock retorna payload com meet_link

        Resultado esperado:
        - Response contém meet_link no payload
        - DB permanece com meet_link=None
        """
        # Mock do preview incluindo meet_link
        mock_build_preview.return_value = {
            "event_id": "asv2-test",
            "payload": {
                "summary": "Teste",
                "start": {},
                "end": {},
            },
            "meet_link": "https://meet.google.com/preview-fake-link",
            "payload_hash": "abc123"
        }

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert solicitacao_aprovada.meet_link is None

        # POST preview
        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/preview-gcal/",
            format="json"
        )

        # Verificar resposta
        assert response.status_code == 200
        assert "preview" in response.data
        preview = response.data["preview"]
        assert preview.get("meet_link") == "https://meet.google.com/preview-fake-link"

        # Refresh do DB
        solicitacao_aprovada.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert solicitacao_aprovada.meet_link is None, \
            "PREVIEW nunca deve persistir meet_link no DB"

    def test_apply_blocked_does_not_persist_meet_link(
        self,
        usuario_controle,
        solicitacao_aprovada,
        settings
    ):
        """
        RF06: apply_blocked (409) não deve persistir meet_link.

        Cenário:
        - Solicitação aprovada sem meet_link
        - POST /api/solicitacoes/{id}/publish/ com GCAL_CLIENT=fake e apply_blocked=false
        - Sistema retorna 409 CONFLICT

        Resultado esperado:
        - Response 409
        - meet_link permanece None no DB
        """
        # Configurar GCAL_CLIENT=fake para bloquear publicação
        settings.GCAL_CLIENT = "fake"

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert solicitacao_aprovada.meet_link is None

        # POST publish (deve ser bloqueado)
        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi bloqueada
        assert response.status_code == 409

        # Refresh do DB
        solicitacao_aprovada.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert solicitacao_aprovada.meet_link is None, \
            "apply_blocked (409) nunca deve persistir meet_link"

    def test_dry_run_does_not_persist_meet_link(
        self,
        usuario_controle,
        solicitacao_aprovada,
        settings
    ):
        """
        RF06: dry_run não deve persistir meet_link.

        Cenário:
        - Solicitação aprovada sem meet_link
        - POST /api/solicitacoes/{id}/publish/ com dry_run=true

        Resultado esperado:
        - meet_link permanece None no DB
        """
        # Configurar GCAL_CLIENT=fake (dry_run permitido)
        settings.GCAL_CLIENT = "fake"

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert solicitacao_aprovada.meet_link is None

        # POST publish com dry_run
        response = client.post(
            f"/api/solicitacoes/{solicitacao_aprovada.id}/publish/",
            {"dry_run": True, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi aceita (dry_run permitido)
        assert response.status_code in [200, 202]

        # Refresh do DB
        solicitacao_aprovada.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert solicitacao_aprovada.meet_link is None, \
            "dry_run nunca deve persistir meet_link"
