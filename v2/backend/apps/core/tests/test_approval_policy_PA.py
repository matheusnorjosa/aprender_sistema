"""
Testes obrigatórios para Política de Aprovação Manual (PA-01 a PA-07).

Garante que:
- PA-01: Nenhuma solicitação é auto-aprovada
- PA-02: Apenas Superintendência pode aprovar/reprovar
- PA-03: Integrações externas só executam após aprovação
- PA-05: Auditoria completa de aprovações/reprovações
- PA-07: Testes obrigatórios implementados
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false

from __future__ import annotations
import pytest
from uuid import uuid4
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from django.test import override_settings

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
def usuario_comum(faker):
    """Usuário comum sem permissões especiais."""
    # Python uuid4() is truly random (faker.uuid4() is seeded and generates duplicates!)
    uid = uuid4().hex  # 32 chars hex, 128-bit entropy
    return Usuario.objects.create_user(
        username=f"comum_{uid}",
        email=f"comum_{uid}@example.com",
        password="testpass",
        cpf=str(uuid4().int % 10**11).zfill(11),  # 11-digit CPF from UUID int
    )


@pytest.fixture
def usuario_superintendencia(faker):
    """Usuário do grupo Superintendência."""
    # Python uuid4() is truly random (faker.uuid4() is seeded and generates duplicates!)
    uid = uuid4().hex  # 32 chars hex, 128-bit entropy
    user = Usuario.objects.create_user(
        username=f"super_{uid}",
        email=f"super_{uid}@example.com",
        password="testpass",
        cpf=str(uuid4().int % 10**11).zfill(11),  # 11-digit CPF from UUID int
    )
    grupo, _ = Group.objects.get_or_create(name="Superintendência")
    user.groups.add(grupo)
    return user


@pytest.fixture
def solicitacao_pendente(usuario_comum):
    """Solicitação pendente para testes (projeto SUPER)."""
    municipio, _ = Municipio.objects.get_or_create(
        nome="Fortaleza", defaults={"uf": "CE", "ativo": True}
    )
    projeto, _ = Projeto.objects.get_or_create(
        nome="Projeto Teste SUPER",
        defaults={"ativo": True, "fluxo": "SUPER"}
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
    PA-01: Solicitacao de projeto SUPER NUNCA muda para "aprovado" automaticamente.

    Verifica que .save() e .clean() não alteram status para projetos SUPER.

    Nota: Projetos NAO_SUPER são auto-aprovados (testado em test_solicitacao_fluxo.py).
    """
    sol = solicitacao_pendente
    assert sol.projeto.fluxo == "SUPER", "Teste deve usar projeto SUPER"
    assert sol.status == "pendente"

    # Save sem mudanças não deve alterar status
    sol.save()
    sol.refresh_from_db()
    assert sol.status == "pendente", "Save() não deve auto-aprovar projeto SUPER"

    # Update de outro campo não deve alterar status
    sol.observacoes = "Atualização de teste"
    sol.save()
    sol.refresh_from_db()
    assert sol.status == "pendente", "Update de campo não deve auto-aprovar projeto SUPER"

    # Clean não deve alterar status
    sol.full_clean()
    assert sol.status == "pendente", "full_clean() não deve auto-aprovar projeto SUPER"


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


@override_settings(GCAL_CLIENT='fake', GCAL_AUTH_MODE='service_account')
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_calendar_integration_not_called_before_approval(
    mock_celery_task,
    solicitacao_pendente,
    usuario_superintendencia,
):
    """
    PA-03: Integrações externas (Google Calendar) só executam após aprovação.

    Verifica que:
    - Publish de solicitação pendente → falha com 400
    - Task Celery NÃO é enfileirada para solicitações não-aprovadas

    Issue #130: Simplificado para ser puramente unitário e rápido (<3s).
    Foca apenas em validar que integração não é chamada antes de aprovação.
    Override settings para evitar I/O pesado (OAuth, cliente real).
    Removido mock de AuditLog pois não é criado no caminho de erro 400.
    """
    client = APIClient()
    client.force_authenticate(user=usuario_superintendencia)

    # Tentar publish em status pendente → deve falhar
    response = client.post(f"/api/solicitacoes/{solicitacao_pendente.id}/publish/")

    # Endpoint deve rejeitar com 400 (apenas aprovadas podem publicar)
    assert response.status_code == 400, (
        f"Publish de solicitação pendente deve retornar 400, "
        f"recebido: {response.status_code}"
    )

    # Task Celery não deve ser enfileirada
    mock_celery_task.assert_not_called()


@override_settings(GCAL_CLIENT='google', GCAL_AUTH_MODE='service_account')
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_calendar_integration_is_called_after_approval(
    mock_celery_task,
    usuario_superintendencia,
):
    """
    PA-03 (parte positiva): Integrações executam APÓS aprovação.

    Verifica que:
    - Publish de solicitação aprovada → sucesso (200/202/204)
    - Task Celery É enfileirada para solicitações aprovadas

    Complementa test_calendar_integration_not_called_before_approval para
    cobertura completa de PA-03 (caminho negativo + positivo).
    """
    from unittest.mock import MagicMock
    from django.utils import timezone
    from datetime import timedelta
    from apps.core.models import Solicitacao, Municipio, Projeto, TipoEvento, Usuario

    # Mock task.delay() para retornar objeto com id serializável (evita JSON error)
    mock_task_result = MagicMock()
    mock_task_result.id = "test-task-id-12345"
    mock_celery_task.return_value = mock_task_result

    # Criar Solicitacao já aprovada (evita caminho lento de aprovação)
    mun, _ = Municipio.objects.get_or_create(
        nome="Fortaleza", defaults={"uf": "CE", "ativo": True}
    )
    proj, _ = Projeto.objects.get_or_create(
        nome="Projeto Teste SUPER", defaults={"ativo": True, "fluxo": "SUPER"}
    )
    tipo, _ = TipoEvento.objects.get_or_create(nome="Formação")
    coord = Usuario.objects.create_user(
        username=f"coord_pa03_{uuid4().hex[:8]}",
        email=f"coord_pa03_{uuid4().hex[:8]}@x.com",
        password="x",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )

    sol = Solicitacao.objects.create(
        usuario=coord,
        municipio=mun,
        projeto=proj,
        tipo_evento=tipo,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
        status="aprovado",  # Já aprovada
    )

    client = APIClient()
    client.force_authenticate(user=usuario_superintendencia)

    # Publish de solicitação aprovada → deve enfileirar task
    response = client.post(f"/api/solicitacoes/{sol.id}/publish/")

    # Endpoint deve aceitar (GCAL_CLIENT='google', não bloqueado)
    assert response.status_code in (200, 202, 204), (
        f"Publish de solicitação aprovada deve retornar 2xx, "
        f"recebido: {response.status_code} - {getattr(response, 'data', None)}"
    )

    # Task Celery DEVE ser enfileirada
    mock_celery_task.assert_called_once()


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
