"""
Testes para AuditLog em approve/reject.

Valida que os métodos approve e reject persistem
entries no AuditLog com os campos corretos.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.core.models import (
    AuditLog,
    Solicitacao,
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def super_user():
    """Cria usuário com permissões de Superintendência."""
    user = Usuario.objects.create_user(
        username="sup",
        email="sup@test.com",
        password="testpass",
        cpf="99999999901",
    )
    group, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(group)
    return user


@pytest.fixture
def solicitacao_pendente(super_user):
    """Cria solicitação pendente para testes."""
    municipio, _ = Municipio.objects.get_or_create(
        nome="Test City",
        defaults={"uf": "TS", "ativo": True},
    )
    projeto, _ = Projeto.objects.get_or_create(
        nome="Test Project SUPER",
        defaults={"ativo": True, "fluxo": "SUPER"},
    )
    # Garantir que o projeto é SUPER (caso já exista no banco)
    if projeto.fluxo != "SUPER":
        projeto.fluxo = "SUPER"
        projeto.save()

    tipo_evento, _ = TipoEvento.objects.get_or_create(
        nome="Test Event Type",
    )

    now = timezone.now()
    sol = Solicitacao.objects.create(
        usuario=super_user,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now,
        fim=now + timedelta(hours=2),
        status="pendente",
    )
    return sol


def test_approve_persists_audit(super_user, solicitacao_pendente):
    """
    Testa que approve persiste AuditLog.

    Valida que:
    - AuditLog é criado
    - action = "APPROVE"
    - model_name = "Solicitacao"
    - details contém solicitacao_id, prev_status, new_status
    """
    client = APIClient()
    client.force_authenticate(user=super_user)

    # Limpar AuditLogs anteriores
    AuditLog.objects.all().delete()

    response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    assert response.status_code in (200, 204), f"Unexpected status: {response.status_code}"

    # Verificar AuditLog
    audit_logs = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="APPROVE",
    )
    assert audit_logs.exists(), "AuditLog não foi criado"

    audit_log = audit_logs.first()
    assert audit_log.usuario == super_user
    assert audit_log.details["solicitacao_id"] == solicitacao_pendente.id
    assert audit_log.details["prev_status"] == "pendente"
    assert audit_log.details["new_status"] == "aprovado"
    assert "ip_address" in audit_log.details


def test_reject_persists_audit(super_user, solicitacao_pendente):
    """
    Testa que reject persiste AuditLog.

    Valida que:
    - AuditLog é criado
    - action = "REJECT"
    - model_name = "Solicitacao"
    - details contém solicitacao_id, prev_status, new_status, justificativa
    """
    client = APIClient()
    client.force_authenticate(user=super_user)

    # Limpar AuditLogs anteriores
    AuditLog.objects.all().delete()

    response = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "Teste de rejeição"},
    )
    assert response.status_code in (200, 204), f"Unexpected status: {response.status_code}"

    # Verificar AuditLog
    audit_logs = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="REJECT",
    )
    assert audit_logs.exists(), "AuditLog não foi criado"

    audit_log = audit_logs.first()
    assert audit_log.usuario == super_user
    assert audit_log.details["solicitacao_id"] == solicitacao_pendente.id
    assert audit_log.details["prev_status"] == "pendente"
    assert audit_log.details["new_status"] == "reprovado"
    assert audit_log.details["justificativa"] == "Teste de rejeição"
    assert "ip_address" in audit_log.details
