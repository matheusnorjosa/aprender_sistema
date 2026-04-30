"""
Testes para AuditLog em approve/reject.

Valida que os métodos approve e reject persistem
entries no AuditLog com os campos corretos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def super_user():
    """Gerente da Superintendência (PR 3 hardening RBAC, 2026-04-29):
    composite Setor `Superintendência` + Função `Gerente`."""
    import uuid

    uid = uuid.uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"sup_audit_{uid}",
        email=f"sup_audit_{uid}@test.com",
        password="testpass",
        cpf=f"999{uid.ljust(8, '0')}",
    )
    grupo_setor, _ = Group.objects.get_or_create(name="Superintendência")
    grupo_funcao, _ = Group.objects.get_or_create(name="Gerente")
    user.groups.add(grupo_setor, grupo_funcao)
    return user


@pytest.fixture
def solicitacao_pendente(super_user):
    """
    Cria solicitação pendente para testes de AuditLog.

    IMPORTANTE: Usa fluxo='SUPER' para evitar auto-aprovação.
    Força status='pendente' via .update() para bypass de save() logic.
    """
    municipio, _ = Municipio.objects.get_or_create(
        nome="Test City",
        defaults={"uf": "TS", "ativo": True},
    )

    # Projeto com fluxo SUPER (não auto-aprova)
    projeto = Projeto.objects.create(
        nome="Test Project SUPER",
        codigo="",
        ativo=True,
        fluxo="SUPER",
    )

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

    # Garantir que status é 'pendente' (bypass auto-aprovação se houver)
    Solicitacao.objects.filter(pk=sol.pk).update(status="pendente")
    sol.refresh_from_db()

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

    # Snapshot count antes (xdist-safe: não deletar logs de outros testes)
    count_before = AuditLog.objects.filter(action="APPROVE", model_name="Solicitacao").count()

    response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    assert response.status_code in (200, 204), f"Unexpected status: {response.status_code}"

    # Verificar AuditLog criado para ESTA solicitação
    audit_log = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="APPROVE",
        details__solicitacao_id=solicitacao_pendente.id,
    ).first()
    assert audit_log is not None, "AuditLog não foi criado"
    assert audit_log.usuario == super_user
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

    response = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "Teste de rejeição"},
    )
    assert response.status_code in (200, 204), f"Unexpected status: {response.status_code}"

    # Verificar AuditLog criado para ESTA solicitação (xdist-safe)
    audit_log = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="REJECT",
        details__solicitacao_id=solicitacao_pendente.id,
    ).first()
    assert audit_log is not None, "AuditLog não foi criado"
    assert audit_log.usuario == super_user
    assert audit_log.details["prev_status"] == "pendente"
    assert audit_log.details["new_status"] == "reprovado"
    assert audit_log.details["justificativa"] == "Teste de rejeição"
    assert "ip_address" in audit_log.details
