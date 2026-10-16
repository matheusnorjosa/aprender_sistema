"""
Testes obrigatórios para Política de Aprovação Manual (PA-01 a PA-07).

Garante que:
- PA-01: Nenhuma solicitação é auto-aprovada
- PA-02: Apenas as bases de `solicitation_approval_basis` aprovam/reprovam (Superintendência por
  vínculo, par legado e, desde o PR 10, o DAT pela capacidade `approve_solicitation` do pacote), e
  ninguém decide a solicitação de quem teve a conta alterada por ele nos últimos 30 dias
- PA-03: Integrações externas só executam após aprovação
- PA-05: Auditoria completa de aprovações/reprovações
- PA-07: Testes obrigatórios implementados
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Gerencia, Usuario
from apps.core.tests.factories import (
    GroupFactory,
    MunicipioFactory,
    ProjetoFactory,
    SolicitacaoFactory,
    TipoEventoFactory,
    UsuarioFactory,
    com_papel,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario_comum(faker):
    """Usuário comum sem permissões especiais."""
    # Python uuid4() is truly random (faker.uuid4() is seeded and generates duplicates!)
    uid = uuid4().hex  # 32 chars hex, 128-bit entropy
    return UsuarioFactory(
        username=f"comum_{uid}",
        email=f"comum_{uid}@example.com",
        password="testpass",
        cpf=str(uuid4().int % 10**11).zfill(11),  # 11-digit CPF from UUID int
    )


@pytest.fixture
def usuario_superintendencia(faker):
    """Gerente da Superintendência (PR 3 hardening RBAC, 2026-04-29):
    composite Setor `Superintendência` + Função `Gerente`. A regra antiga
    (Setor sozinho aprovava via PA-02) foi descontinuada."""
    uid = uuid4().hex  # 32 chars hex, 128-bit entropy
    user = UsuarioFactory(
        username=f"super_{uid}",
        email=f"super_{uid}@example.com",
        password="testpass",
        cpf=str(uuid4().int % 10**11).zfill(11),  # 11-digit CPF from UUID int
    )
    grupo_setor = GroupFactory(name="Superintendência")
    grupo_funcao = GroupFactory(name="Gerente")
    user.groups.add(grupo_setor, grupo_funcao)
    return user


@pytest.fixture
def usuario_controle():
    """Quem publica no Google (`use_gcal` pelo `operate_preagenda` do Controle). Desde o PR 10 o grupo
    Superintendência não tem capacidade (migration 0126): o par legado aprova, mas não publica."""
    return UsuarioFactory(groups=["Controle"])


@pytest.fixture
def solicitacao_pendente(usuario_comum):
    """Solicitação pendente para testes (projeto SUPER)."""
    municipio = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    g1, _ = Gerencia.objects.get_or_create(nome="SUPERINTENDENCIA", defaults={"nome_setor": "Superintendência"})
    projeto = ProjetoFactory(nome="Projeto Teste SUPER", ativo=True, fluxo="SUPER", gerencia=g1)
    tipo_evento = TipoEventoFactory(nome="Formação")

    now = timezone.now()
    return SolicitacaoFactory(
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
# PA-02: Apenas as bases de aprovação aprovam/reprovam
# ===================================================================


def _gerencia(nome: str, perfil: str = "PADRAO") -> Gerencia:
    gerencia, _ = Gerencia.objects.get_or_create(nome=nome, defaults={"nome_setor": nome.title()})
    gerencia.perfil = perfil
    gerencia.save()
    return gerencia


def _com_vinculo(papel: str, gerencia: Gerencia, grupos: tuple[str, ...] = ()) -> Usuario:
    user = UsuarioFactory(groups=list(grupos) or None, groups__vinculo=False)
    com_papel(user, papel, gerencia)
    cache.clear()
    return user


# Bases 2, 4 e 5 de `solicitation_approval_basis` (a 1 é o superusuário; a 3, o par Controle).
APROVADORAS = {
    "gerente_g1_por_vinculo": lambda: _com_vinculo("GERENTE", _gerencia("SUPERINTENDENCIA")),
    "par_legado": lambda: UsuarioFactory(groups=["Superintendência", "Gerente"], groups__vinculo=False),
    "dat_pelo_pacote": lambda: _com_vinculo("EQUIPE", _gerencia("GERENCIA DAT", "ADMIN_OPERACIONAL"), ("DAT",)),
}

# Quem não aprova: Controle puro, COORDENADOR e FORMADOR na gerência DAT, grupo DAT sem vínculo,
# Gerente pedagógico.
SEM_PODER = {
    "controle_puro": lambda: UsuarioFactory(groups=["Controle"]),
    "coordenador_na_gerencia_dat": lambda: _com_vinculo("COORDENADOR", _gerencia("GERENCIA DAT", "ADMIN_OPERACIONAL")),
    "formador_na_gerencia_dat": lambda: _com_vinculo("FORMADOR", _gerencia("GERENCIA DAT", "ADMIN_OPERACIONAL")),
    "grupo_dat_sem_vinculo": lambda: UsuarioFactory(groups=["DAT"]),
    "gerente_pedagogico": lambda: _com_vinculo("GERENTE", _gerencia("GERENCIA VIDAS PA07")),
}


@pytest.mark.parametrize("base", sorted(APROVADORAS))
def test_only_superintendencia_can_approve_or_reject(
    solicitacao_pendente,
    usuario_comum,
    base,
):
    """
    PA-02: Só quem tem base de aprovação aprova/reprova.

    Verifica que:
    - Usuário comum → 403
    - Base 2 (GERENTE por vínculo na Superintendência), 4 (par legado) e 5 (DAT pelo pacote) → 200/204
    """
    usuario_superintendencia = APROVADORAS[base]()
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


@pytest.mark.parametrize("perfil", ["usuario_comum", *sorted(SEM_PODER)])
def test_non_privileged_user_gets_403_on_approval_endpoint(
    solicitacao_pendente,
    usuario_comum,
    perfil,
):
    """
    PA-07: Usuário não-privilegiado recebe 403 ao tentar aprovar.

    Complementar a test_only_superintendencia_can_approve_or_reject.
    """
    usuario = usuario_comum if perfil == "usuario_comum" else SEM_PODER[perfil]()
    client = APIClient()
    client.force_authenticate(user=usuario)

    response_approve = client.patch(f"/api/solicitacoes/{solicitacao_pendente.id}/approve/")
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


@override_settings(GCAL_CLIENT="fake", GCAL_AUTH_MODE="service_account")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_calendar_integration_not_called_before_approval(
    mock_celery_task,
    solicitacao_pendente,
    usuario_controle,
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
    client.force_authenticate(user=usuario_controle)

    # Tentar publish em status pendente → deve falhar
    response = client.post(f"/api/solicitacoes/{solicitacao_pendente.id}/publish/")

    # Endpoint deve rejeitar com 400 (apenas aprovadas podem publicar)
    assert response.status_code == 400, (
        f"Publish de solicitação pendente deve retornar 400, " f"recebido: {response.status_code}"
    )

    # Task Celery não deve ser enfileirada
    mock_celery_task.assert_not_called()


@override_settings(GCAL_CLIENT="google", GCAL_AUTH_MODE="service_account")
@patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay")
def test_calendar_integration_is_called_after_approval(
    mock_celery_task,
    usuario_controle,
):
    """
    PA-03 (parte positiva): Integrações executam APÓS aprovação.

    Verifica que:
    - Publish de solicitação aprovada → sucesso (200/202/204)
    - Task Celery É enfileirada para solicitações aprovadas

    Complementa test_calendar_integration_not_called_before_approval para
    cobertura completa de PA-03 (caminho negativo + positivo).
    """
    from datetime import timedelta
    from unittest.mock import MagicMock

    from django.utils import timezone

    # Mock task.delay() para retornar objeto com id serializável (evita JSON error)
    mock_task_result = MagicMock()
    mock_task_result.id = "test-task-id-12345"
    mock_celery_task.return_value = mock_task_result

    # Criar Solicitacao já aprovada (evita caminho lento de aprovação)
    mun = MunicipioFactory(nome="Fortaleza", uf="CE", ativo=True)
    proj = ProjetoFactory(nome="Projeto Teste SUPER", ativo=True, fluxo="SUPER")
    tipo = TipoEventoFactory(nome="Formação")
    coord = UsuarioFactory(
        username=f"coord_pa03_{uuid4().hex[:8]}",
        email=f"coord_pa03_{uuid4().hex[:8]}@x.com",
        password="x",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )

    sol = SolicitacaoFactory(
        usuario=coord,
        municipio=mun,
        projeto=proj,
        tipo_evento=tipo,
        inicio=timezone.now() + timedelta(days=1),
        fim=timezone.now() + timedelta(days=1, hours=2),
        status="aprovado",  # Já aprovada
    )

    client = APIClient()
    client.force_authenticate(user=usuario_controle)

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
