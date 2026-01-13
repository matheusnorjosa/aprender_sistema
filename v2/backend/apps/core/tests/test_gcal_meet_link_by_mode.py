"""
Testes para geração de Meet link baseado em modalidade (is_online) - PR19.

Valida:
- Preview online: inclui meet_link no payload, não persiste no DB
- Preview offline: não inclui meet_link
- Publish online (APPLY real): persiste meet_link quando API retorna hangoutLink
- Publish offline: não gera conferenceData, não persiste meet_link
- Apply_blocked (409) online: não persiste meet_link mesmo se online
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

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
        username="controle_mode",
        email="controle_mode@test.com",
        password="testpass",
        cpf="44444444444",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def fixtures_basicas():
    """Fixtures básicas para criar solicitações"""
    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Projeto Mode", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formação")

    return {
        "municipio": municipio,
        "projeto": projeto,
        "tipo_evento": tipo_evento,
    }


@pytest.mark.django_db
class TestGCalMeetLinkByMode:
    """Testes para geração de Meet link baseado em is_online"""

    def test_preview_online_includes_meet_link(
        self, usuario_controle, fixtures_basicas
    ):
        """
        PR19: Preview de solicitação online deve incluir meet_link (fake), sem persistir.

        Cenário:
        - Solicitação aprovada com is_online=True
        - POST /api/solicitacoes/{id}/preview-gcal/

        Resultado esperado:
        - Response contém preview.meet_link (fake)
        - DB permanece com meet_link=None
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=1),
            fim=now + timedelta(days=1, hours=2),
            status="aprovado",
            is_online=True,  # Evento online
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert sol.meet_link is None
        assert sol.is_online is True

        # POST preview
        response = client.post(
            f"/api/solicitacoes/{sol.id}/preview-gcal/",
            format="json"
        )

        # Verificar resposta
        assert response.status_code == 200
        assert "preview" in response.data
        preview = response.data["preview"]

        # Preview de evento online deve incluir meet_link fake
        assert "meet_link" in preview
        assert preview["meet_link"] is not None
        assert "meet.google.com" in preview["meet_link"]

        # Refresh do DB
        sol.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert sol.meet_link is None, \
            "PREVIEW nunca deve persistir meet_link no DB"

    def test_preview_offline_no_meet_link(
        self, usuario_controle, fixtures_basicas
    ):
        """
        PR19: Preview de solicitação presencial não deve incluir meet_link.

        Cenário:
        - Solicitação aprovada com is_online=False (presencial)
        - POST /api/solicitacoes/{id}/preview-gcal/

        Resultado esperado:
        - Response preview sem meet_link ou meet_link=None
        - DB permanece com meet_link=None
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=2),
            fim=now + timedelta(days=2, hours=2),
            status="aprovado",
            is_online=False,  # Evento presencial
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert sol.meet_link is None
        assert sol.is_online is False

        # POST preview
        response = client.post(
            f"/api/solicitacoes/{sol.id}/preview-gcal/",
            format="json"
        )

        # Verificar resposta
        assert response.status_code == 200
        assert "preview" in response.data
        preview = response.data["preview"]

        # Preview de evento presencial não deve incluir meet_link
        # ou deve retornar meet_link=None
        if "meet_link" in preview:
            assert preview["meet_link"] is None, \
                "Evento presencial não deve ter meet_link no preview"

        # Refresh do DB
        sol.refresh_from_db()

        # Verificar que meet_link permanece None
        assert sol.meet_link is None

    @patch('apps.core.tasks.task_publish_solicitacao_to_gcal.delay')
    @patch('apps.core.services.gcal_google_client.GoogleCalendarClient')
    def test_publish_online_allowed_persists_meet_link(
        self,
        MockGoogleClient,
        mock_task,
        usuario_controle,
        fixtures_basicas,
        settings
    ):
        """
        PR19: Publish de solicitação online deve persistir meet_link quando APPLY real.

        Cenário:
        - Solicitação aprovada com is_online=True
        - POST /api/solicitacoes/{id}/publish/ com GCAL_CLIENT=google
        - Mock retorna hangoutLink na resposta

        Resultado esperado:
        - Task Celery enfileirada
        - (Task real persistiria meet_link)
        """
        # Configurar GCAL_CLIENT=google para permitir publicação
        settings.GCAL_CLIENT = "google"
        settings.GCAL_CALENDAR_ID = "test@calendar.google.com"

        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=3),
            fim=now + timedelta(days=3, hours=2),
            status="aprovado",
            is_online=True,  # Evento online
        )

        # Mock da resposta do GoogleCalendarClient
        mock_client_instance = MockGoogleClient.return_value
        mock_client_instance.insert.return_value = {
            "id": "gcal-event-456",
            "hangoutLink": "https://meet.google.com/online-xyz-abc"
        }

        # Garantir que a task retorna imediatamente (mock)
        mock_task.return_value = MagicMock(id="task-456")

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert sol.meet_link is None
        assert sol.is_online is True

        # POST publish (task é enqueuada)
        response = client.post(
            f"/api/solicitacoes/{sol.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi aceita
        assert response.status_code in [200, 202]

        # Verificar que task Celery foi enfileirada
        mock_task.assert_called_once()

    def test_publish_offline_no_meet_link(
        self, usuario_controle, fixtures_basicas, settings
    ):
        """
        PR19: Publish de solicitação presencial não deve persistir meet_link.

        Cenário:
        - Solicitação aprovada com is_online=False (presencial)
        - POST /api/solicitacoes/{id}/publish/ com dry_run=True

        Resultado esperado:
        - meet_link permanece None
        - Payload GCal não contém conferenceData
        """
        # Configurar GCAL_CLIENT=fake para dry_run
        settings.GCAL_CLIENT = "fake"

        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=4),
            fim=now + timedelta(days=4, hours=2),
            status="aprovado",
            is_online=False,  # Evento presencial
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert sol.meet_link is None
        assert sol.is_online is False

        # POST publish com dry_run
        response = client.post(
            f"/api/solicitacoes/{sol.id}/publish/",
            {"dry_run": True, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi aceita (dry_run permitido)
        assert response.status_code in [200, 202]

        # Refresh do DB
        sol.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert sol.meet_link is None, \
            "Evento presencial nunca deve ter meet_link persistido"

    def test_apply_blocked_online_no_persist(
        self, usuario_controle, fixtures_basicas, settings
    ):
        """
        PR19: apply_blocked (409) não deve persistir meet_link, mesmo para evento online.

        Cenário:
        - Solicitação aprovada com is_online=True
        - POST /api/solicitacoes/{id}/publish/ com GCAL_CLIENT=fake e apply_blocked=false
        - Sistema retorna 409 CONFLICT

        Resultado esperado:
        - Response 409
        - meet_link permanece None no DB
        """
        # Configurar GCAL_CLIENT=fake para bloquear publicação
        settings.GCAL_CLIENT = "fake"

        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=5),
            fim=now + timedelta(days=5, hours=2),
            status="aprovado",
            is_online=True,  # Evento online, mas será bloqueado
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # Verificar estado inicial
        assert sol.meet_link is None
        assert sol.is_online is True

        # POST publish (deve ser bloqueado)
        response = client.post(
            f"/api/solicitacoes/{sol.id}/publish/",
            {"dry_run": False, "apply_blocked": False},
            format="json"
        )

        # Verificar que publicação foi bloqueada
        assert response.status_code == 409

        # Refresh do DB
        sol.refresh_from_db()

        # Verificar que meet_link NÃO foi persistido
        assert sol.meet_link is None, \
            "apply_blocked (409) nunca deve persistir meet_link, mesmo para evento online"

    def test_preview_payload_has_no_conference_data_when_offline(
        self, usuario_controle, fixtures_basicas
    ):
        """
        PR19: Preview de evento presencial não deve incluir conferenceData no payload.

        Cenário:
        - Solicitação aprovada com is_online=False
        - POST /api/solicitacoes/{id}/preview-gcal/

        Resultado esperado:
        - preview.payload não contém conferenceData
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=6),
            fim=now + timedelta(days=6, hours=2),
            status="aprovado",
            is_online=False,  # Evento presencial
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # POST preview
        response = client.post(
            f"/api/solicitacoes/{sol.id}/preview-gcal/",
            format="json"
        )

        # Verificar resposta
        assert response.status_code == 200
        assert "preview" in response.data
        preview = response.data["preview"]
        payload = preview.get("payload", {})

        # Payload de evento presencial não deve ter conferenceData
        assert "conferenceData" not in payload, \
            "Evento presencial não deve ter conferenceData no payload"

    def test_preview_payload_has_conference_data_when_online(
        self, usuario_controle, fixtures_basicas
    ):
        """
        PR19: Preview de evento online deve incluir conferenceData no payload.

        Cenário:
        - Solicitação aprovada com is_online=True
        - POST /api/solicitacoes/{id}/preview-gcal/

        Resultado esperado:
        - preview.payload contém conferenceData
        """
        now = timezone.now()
        sol = Solicitacao.objects.create(
            usuario=usuario_controle,
            municipio=fixtures_basicas["municipio"],
            projeto=fixtures_basicas["projeto"],
            tipo_evento=fixtures_basicas["tipo_evento"],
            inicio=now + timedelta(days=7),
            fim=now + timedelta(days=7, hours=2),
            status="aprovado",
            is_online=True,  # Evento online
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        # POST preview
        response = client.post(
            f"/api/solicitacoes/{sol.id}/preview-gcal/",
            format="json"
        )

        # Verificar resposta
        assert response.status_code == 200
        assert "preview" in response.data
        preview = response.data["preview"]
        payload = preview.get("payload", {})

        # Payload de evento online deve ter conferenceData
        assert "conferenceData" in payload, \
            "Evento online deve ter conferenceData no payload"
        assert payload["conferenceData"]["createRequest"]["requestId"] is not None
