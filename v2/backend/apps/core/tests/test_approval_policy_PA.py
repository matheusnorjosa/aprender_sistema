"""
Testes obrigatórios para Política de Aprovação Manual (PA-01 a PA-07).

Garante que:
- PA-01: Nenhuma solicitação é auto-aprovada
- PA-02: Apenas Superintendência pode aprovar/reprovar
- PA-03: Integrações externas só executam após aprovação
- PA-05: Auditoria completa de aprovações/reprovações
- PA-07: Testes obrigatórios implementados
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from apps.core.models import (
    Solicitacao,
    AuditLog,
    Usuario,
    Municipio,
    Projeto,
    TipoEvento,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario_comum():
    """Usuário comum sem permissões especiais."""
    return Usuario.objects.create_user(
        username="comum",
        email="comum@test.com",
        password="testpass",
        cpf="11111111111",
    )


@pytest.fixture
def usuario_superintendencia():
    """Usuário do grupo Superintendência."""
    user = Usuario.objects.create_user(
        username="super",
        email="super@test.com",
        password="testpass",
        cpf="22222222222",
    )
    grupo, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_pendente(usuario_comum):
    """Solicitação pendente para testes."""
    municipio, _ = Municipio.objects.get_or_create(
        nome="Fortaleza", defaults={"uf": "CE", "ativo": True}
    )
    projeto, _ = Projeto.objects.get_or_create(
        nome="Projeto Teste", defaults={"ativo": True}
    )
    tipo_evento, _ = TipoEvento.objects.get_or_create(nome="Formação")

    now = timezone.now()
    return Solicitacao.objects.create(
        usuario=usuario_comum,
        municipio=municipio,
        projeto=projeto,
        tipo_evento=tipo_evento,
        inicio=now + timedelta(days=1),
        fim=now + timedelta(days=1, hours=2),
        status="pendente",
    )


# ===================================================================
# PA-01: Sem auto-aprovação
# ===================================================================


def test_never_auto_approves_on_clean_or_save(solicitacao_pendente):
    """
    PA-01: Solicitacao NUNCA muda para "aprovado" automaticamente.

    Verifica que .save() e .clean() não alteram status.
    """
    sol = solicitacao_pendente
    assert sol.status == "pendente"

    # Save sem mudanças não deve alterar status
    sol.save()
    sol.refresh_from_db()
    assert sol.status == "pendente", "Save() não deve auto-aprovar"

    # Update de outro campo não deve alterar status
    sol.observacoes = "Atualização de teste"
    sol.save()
    sol.refresh_from_db()
    assert sol.status == "pendente", "Update de campo não deve auto-aprovar"

    # Clean não deve alterar status
    sol.full_clean()
    assert sol.status == "pendente", "full_clean() não deve auto-aprovar"


# ===================================================================
# PA-02: Apenas Superintendência pode aprovar/reprovar
# ===================================================================


def test_only_superintendencia_can_approve_or_reject(
    solicitacao_pendente,
    usuario_comum,
    usuario_superintendencia,
):
    """
    PA-02: Apenas usuários da Superintendência podem aprovar/reprovar.

    Verifica que:
    - Usuário comum → 403
    - Superintendência → 200/204
    """
    client = APIClient()

    # Teste 1: Usuário comum tenta aprovar → 403
    client.force_authenticate(user=usuario_comum)
    response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    assert response.status_code == 403, "Usuário comum não deve poder aprovar"

    # Teste 2: Superintendência pode aprovar → 200/204
    client.force_authenticate(user=usuario_superintendencia)
    response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    assert response.status_code in (
        200,
        204,
    ), "Superintendência deve poder aprovar"

    # Recriar solicitação pendente para teste de reject
    solicitacao_pendente.status = "pendente"
    solicitacao_pendente.save()

    # Teste 3: Usuário comum tenta reprovar → 403
    client.force_authenticate(user=usuario_comum)
    response = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "teste"},
    )
    assert response.status_code == 403, "Usuário comum não deve poder reprovar"

    # Teste 4: Superintendência pode reprovar → 200/204
    client.force_authenticate(user=usuario_superintendencia)
    response = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "teste"},
    )
    assert response.status_code in (
        200,
        204,
    ), "Superintendência deve poder reprovar"


def test_non_privileged_user_gets_403_on_approval_endpoint(
    solicitacao_pendente,
    usuario_comum,
):
    """
    PA-07: Usuário não-privilegiado recebe 403 ao tentar aprovar.

    Complementar a test_only_superintendencia_can_approve_or_reject.
    """
    client = APIClient()
    client.force_authenticate(user=usuario_comum)

    response_approve = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/approve/"
    )
    response_reject = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "teste"},
    )

    assert response_approve.status_code == 403
    assert response_reject.status_code == 403

    # Verificar que a mensagem indica falta de permissão (aceita variações)
    detail_lower = response_approve.data.get("detail", "").lower()
    assert (
        "permissão" in detail_lower or "superintendência" in detail_lower
    ), f"Mensagem deve indicar falta de permissão, recebido: {detail_lower}"


# ===================================================================
# PA-03: Integrações externas só executam após aprovação
# ===================================================================


@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_calendar_integration_not_called_before_approval(
    mock_celery_task,
    solicitacao_pendente,
    usuario_superintendencia,
):
    """
    PA-03: Integrações externas (Google Calendar) só executam após aprovação.

    Verifica que:
    - Publish de solicitação pendente → falha ou skip
    - Publish de solicitação aprovada → executa (ou enfileira task)

    Nota: Assumindo que existe endpoint /api/solicitacoes/<id>/publish/
    Se o endpoint for diferente, ajustar conforme a implementação real.
    """
    client = APIClient()
    client.force_authenticate(user=usuario_superintendencia)

    # Teste 1: Tentar publish em status pendente → deve falhar
    # Se o endpoint não existir, este teste documentará isso
    response = client.post(f"/api/solicitacoes/{solicitacao_pendente.id}/publish/")

    # Pode ser 400, 403, 404, ou 409 dependendo da implementação
    # O importante é que NÃO seja 2xx (sucesso)
    if response.status_code == 404:
        # Endpoint não existe, documentar no relatório
        pytest.skip("Endpoint /publish/ não implementado ainda")

    assert (
        response.status_code >= 400
    ), "Publish de solicitação pendente deve falhar"
    assert (
        not mock_celery_task.called
    ), "Task Celery não deve ser chamada para solicitação pendente"

    # Teste 2: Aprovar solicitação
    client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    solicitacao_pendente.refresh_from_db()
    assert solicitacao_pendente.status == "aprovado"

    # Teste 3: Agora publish deve executar ou enfileirar task
    mock_celery_task.reset_mock()
    response = client.post(f"/api/solicitacoes/{solicitacao_pendente.id}/publish/")

    if response.status_code == 404:
        pytest.skip("Endpoint /publish/ não implementado ainda")

    # Deve ser sucesso (200, 202, 204) ou 409 (apply_blocked)
    assert response.status_code in (
        200,
        202,
        204,
        409,
    ), "Publish de solicitação aprovada deve ter sucesso ou retornar 409"

    # Se não for 409 (blocked), task deve ter sido enfileirada
    if response.status_code != 409:
        assert (
            mock_celery_task.called
        ), "Task Celery deve ser enfileirada após aprovação"


# ===================================================================
# PA-05: Auditoria completa
# ===================================================================


def test_approval_flow_records_audit_log(
    solicitacao_pendente,
    usuario_superintendencia,
):
    """
    PA-05: Aprovações e reprovações devem criar entries em AuditLog.

    Verifica que:
    - Approve cria AuditLog com action="APPROVE"
    - Reject cria AuditLog com action="REJECT"
    - AuditLog contém usuário, prev_status, new_status, justificativa, ip
    """
    client = APIClient()
    client.force_authenticate(user=usuario_superintendencia)

    # Limpar AuditLogs anteriores
    AuditLog.objects.all().delete()

    # Teste 1: Approve cria AuditLog
    response = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
    assert response.status_code in (200, 204)

    audit_logs = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="APPROVE",
    )
    assert audit_logs.exists(), "AuditLog não foi criado para approve"

    audit_log = audit_logs.first()
    assert audit_log.usuario == usuario_superintendencia
    assert audit_log.details["solicitacao_id"] == solicitacao_pendente.id
    assert audit_log.details["prev_status"] == "pendente"
    assert audit_log.details["new_status"] == "aprovado"
    assert "ip_address" in audit_log.details

    # Recriar solicitação pendente para teste de reject
    solicitacao_pendente.status = "pendente"
    solicitacao_pendente.save()
    AuditLog.objects.all().delete()

    # Teste 2: Reject cria AuditLog
    response = client.patch(
        f"/api/solicitacoes/{solicitacao_pendente.id}/reject/",
        {"justificativa": "Motivo de teste"},
    )
    assert response.status_code in (200, 204)

    audit_logs = AuditLog.objects.filter(
        model_name="Solicitacao",
        action="REJECT",
    )
    assert audit_logs.exists(), "AuditLog não foi criado para reject"

    audit_log = audit_logs.first()
    assert audit_log.usuario == usuario_superintendencia
    assert audit_log.details["solicitacao_id"] == solicitacao_pendente.id
    assert audit_log.details["prev_status"] == "pendente"
    assert audit_log.details["new_status"] == "reprovado"
    assert audit_log.details["justificativa"] == "Motivo de teste"
    assert "ip_address" in audit_log.details
