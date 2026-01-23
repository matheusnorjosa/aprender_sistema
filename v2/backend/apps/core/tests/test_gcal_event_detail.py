"""
Testes Issue #98 - Event Detail with AuditLog Timeline

Cobertura:
- GET /api/gcal/dashboard/events/{id}/detail/ - 200 (dados corretos)
- GET /api/gcal/dashboard/events/{id}/detail/ - 404 (ID não existe)
- GET /api/gcal/dashboard/events/{id}/detail/ - 403 (sem permissão)
- Timeline ordering (created_at desc, últimos 20)

100% fake/mocked, sem rede real.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Municipio, Projeto, Solicitacao, TipoEvento, Usuario


@pytest.fixture
def usuario_controle():
    """Usuário do grupo Controle"""
    user = Usuario.objects.create_user(
        username="controle_test_detail",
        email="controle_detail@test.com",
        password="testpass",
        cpf="22222222222",
    )
    grupo, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(grupo)
    return user


@pytest.fixture
def usuario_formador():
    """Usuário sem permissão (grupo Formador)"""
    user = Usuario.objects.create_user(
        username="formador_test_detail",
        email="formador_detail@test.com",
        password="testpass",
        cpf="33333333333",
    )
    grupo, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(grupo)
    return user


@pytest.fixture
def municipio():
    """Município de teste"""
    return Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)


@pytest.fixture
def projeto():
    """Projeto de teste"""
    return Projeto.objects.create(nome="Projeto Detail Test", codigo="PDT", fluxo="SUPER", ativo=True)


@pytest.fixture
def tipo_evento():
    """Tipo de evento de teste"""
    return TipoEvento.objects.create(nome="Formação Detail Test")


@pytest.fixture
def solicitacao_aprovada(usuario_controle, municipio, projeto, tipo_evento):
    """Solicitação aprovada para testes"""
    now = timezone.now()
    inicio = now + timedelta(days=5)
    fim = inicio + timedelta(hours=4)

    return Solicitacao.objects.create(
        usuario=usuario_controle,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        tipo="evento",
        inicio=inicio,
        fim=fim,
        status="aprovado",
        gcal_status=Solicitacao.GCalStatus.PUBLISHED,
        external_event_id="asv2-test-123",
        meet_link="https://meet.google.com/test-meet",
        gcal_payload_hash="abc123hash",
    )


@pytest.mark.django_db
class TestEventDetail:
    """Testes para GET /api/gcal/dashboard/events/{id}/detail/"""

    def test_event_detail_200_ok(self, usuario_controle, solicitacao_aprovada):
        """
        Caso 1: GET /api/gcal/dashboard/events/{id}/detail/ deve retornar 200
        com todos os campos esperados.
        """
        # Criar alguns logs de auditoria para timeline
        # Ordem: primeiro PUBLISH_GCAL_REQUESTED (mais antigo), depois PUBLISH_GCAL (mais recente)
        AuditLog.objects.create(
            usuario=None,  # Sistema
            action="PUBLISH_GCAL_REQUESTED",
            model_name="Solicitacao",
            details={"solicitacao_id": solicitacao_aprovada.id},
        )
        AuditLog.objects.create(
            usuario=usuario_controle,
            action="PUBLISH_GCAL",
            model_name="Solicitacao",
            details={"solicitacao_id": solicitacao_aprovada.id, "dry_run": False, "status": "success"},
        )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get(f"/api/gcal/dashboard/events/{solicitacao_aprovada.id}/detail/")

        # Assertions
        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        # Campos do evento
        assert data["id"] == solicitacao_aprovada.id
        assert data["municipio_nome"] == "Fortaleza"
        assert data["projeto_nome"] == "Projeto Detail Test"
        assert data["tipo_evento_nome"] == "Formação Detail Test"
        assert data["usuario_username"] == "controle_test_detail"
        assert data["coordenador_username"] == "controle_test_detail"  # Fallback para usuario
        assert data["fluxo"] == "SUPER"

        # Campos GCal
        assert data["gcal_status"] == "PUBLISHED"
        assert data["external_event_id"] == "asv2-test-123"
        assert data["meet_link"] == "https://meet.google.com/test-meet"
        # Note: gcal_payload_hash removed from serializer (internal implementation detail)
        assert data["gcal_last_error"] is None  # Campo é nullable, retorna None quando vazio

        # Participations (vazio neste caso)
        assert isinstance(data["participations"], list)

        # Timeline (deve conter 2 logs)
        assert isinstance(data["timeline"], list)
        assert len(data["timeline"]) == 2

        # Primeiro item na timeline deve ser PUBLISH_GCAL (mais recente)
        assert data["timeline"][0]["action"] == "PUBLISH_GCAL"
        assert data["timeline"][0]["usuario_nome"] == "controle_test_detail"

        # Segundo item deve ser PUBLISH_GCAL_REQUESTED
        assert data["timeline"][1]["action"] == "PUBLISH_GCAL_REQUESTED"
        assert data["timeline"][1]["usuario_nome"] == "Sistema"

    def test_event_detail_404_not_found(self, usuario_controle):
        """
        Caso 2: GET /api/gcal/dashboard/events/99999/detail/ deve retornar 404
        quando ID não existe.
        """
        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get("/api/gcal/dashboard/events/99999/detail/")

        assert response.status_code == http_status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"] == "Solicitação não encontrada"

    def test_event_detail_403_forbidden(self, usuario_formador, solicitacao_aprovada):
        """
        Caso 3: GET /api/gcal/dashboard/events/{id}/detail/ deve retornar 403
        para usuários sem permissão IsControleOrSuper.
        """
        client = APIClient()
        client.force_authenticate(user=usuario_formador)

        response = client.get(f"/api/gcal/dashboard/events/{solicitacao_aprovada.id}/detail/")

        assert response.status_code == http_status.HTTP_403_FORBIDDEN

    def test_timeline_ordering_desc(self, usuario_controle, solicitacao_aprovada):
        """
        Caso 4: Timeline deve retornar logs ordenados por created_at DESC
        (mais recentes primeiro), limitado a 20 registros.
        """
        # Criar 25 logs de auditoria (para testar limite de 20)
        now = timezone.now()

        for i in range(25):
            AuditLog.objects.create(
                usuario=usuario_controle if i % 2 == 0 else None,
                action="PUBLISH_GCAL" if i % 3 == 0 else "RESYNC_GCAL_REQUESTED",
                model_name="Solicitacao",
                details={"solicitacao_id": solicitacao_aprovada.id, "index": i},
                created_at=now - timedelta(minutes=25 - i),  # Mais antigo primeiro, depois mais recente
            )

        client = APIClient()
        client.force_authenticate(user=usuario_controle)

        response = client.get(f"/api/gcal/dashboard/events/{solicitacao_aprovada.id}/detail/")

        assert response.status_code == http_status.HTTP_200_OK
        data = response.json()

        # Timeline deve ter exatamente 20 itens (limite)
        assert len(data["timeline"]) == 20

        # Verificar ordenação DESC (mais recentes primeiro)
        # O index 24 é o mais recente (25 - 24 = 1 minuto atrás)
        # O index 5 é o mais antigo no top 20 (25 - 5 = 20 minutos atrás)
        assert data["timeline"][0]["details"]["index"] == 24  # Mais recente
        assert data["timeline"][19]["details"]["index"] == 5  # 20º mais recente

        # Verificar que todos os logs têm created_at em ordem DESC
        timestamps = [item["created_at"] for item in data["timeline"]]
        assert timestamps == sorted(timestamps, reverse=True)
