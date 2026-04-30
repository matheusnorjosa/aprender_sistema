"""
Issue #723 - Cadeia funcional compras -> solicitacao -> publish gcal.

Objetivo:
- Cobrir o fluxo feliz ponta-a-ponta usando endpoints reais do backend.
- Cobrir o fluxo invalido sem compra elegivel (municipio + projeto).
- Manter execucao deterministica no CI (sem dependencia externa real).
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog, Compra, Municipio, Projeto, Solicitacao, TipoEvento, Usuario

pytestmark = pytest.mark.django_db


def _create_user_in_group(*, prefix: str, group_name: str) -> Usuario:
    uid = uuid4().hex[:8]
    user = Usuario.objects.create_user(
        username=f"{prefix}_{uid}",
        email=f"{prefix}_{uid}@example.com",
        password="testpass",
        cpf=str(uuid4().int % 10**11).zfill(11),
    )
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def _upload_compras_csv(client: APIClient, *, codigo: str, produto: str, municipio: str, uf: str) -> dict:
    csv_content = (
        "COD,Produto,Quant.,Municipio,UF,Data,Uso das colecoes\n"
        f"{codigo},{produto},10,{municipio},{uf},2026-01-15,Fluxo cadeia\n"
    )
    upload = SimpleUploadedFile(
        "compras.csv",
        csv_content.encode("utf-8"),
        content_type="text/csv",
    )
    response = client.post(
        "/api/controle/import-compras/?dry_run=false",
        {"file": upload},
        format="multipart",
        secure=True,
    )
    error_payload = getattr(response, "data", getattr(response, "content", b""))
    assert response.status_code == 200, error_payload
    return response.json()


@override_settings(GCAL_CLIENT="google")
def test_happy_path_import_compra_create_solicitacao_approve_and_publish():
    """
    Fluxo feliz esperado:
    import compras -> cria solicitacao valida -> aprova -> publish retorna sucesso.
    """
    client = APIClient()

    # PR-A1 DAT-Imports (2026-04-29): import-compras agora é DAT-only;
    # publish continua sendo operação Controle.
    user_dat = _create_user_in_group(prefix="dat_chain", group_name="DAT")
    user_controle = _create_user_in_group(prefix="controle_chain", group_name="Controle")
    user_coordenador = _create_user_in_group(prefix="coord_chain", group_name="Coordenador")
    # PR 3 hardening RBAC (2026-04-29): aprovar exige composite Setor Sup + Função Gerente.
    user_super = _create_user_in_group(prefix="super_chain", group_name="Superintendência")
    grupo_gerente, _ = Group.objects.get_or_create(name="Gerente")
    user_super.groups.add(grupo_gerente)

    municipio = Municipio.objects.create(nome="Fortaleza", uf="CE", ativo=True)
    projeto = Projeto.objects.create(nome="Novo Lendo", codigo="NL", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Formacao")

    # 1) Import compras via endpoint real (DAT-only após PR-A1 DAT-Imports).
    client.force_authenticate(user=user_dat)
    import_report = _upload_compras_csv(
        client,
        codigo="COMP-CHAIN-001",
        produto="LIVRO NOVO LENDO",
        municipio=municipio.nome,
        uf=municipio.uf,
    )
    assert import_report["stats"]["created"] == 1
    assert Compra.objects.filter(municipio=municipio, projeto=projeto).exists()

    # 2) Criacao da solicitacao (projeto SUPER => pendente).
    client.force_authenticate(user=user_coordenador)
    inicio = timezone.now() + timedelta(days=5)
    fim = inicio + timedelta(hours=2)
    create_response = client.post(
        "/api/solicitacoes/",
        {
            "municipio": municipio.id,
            "projeto": projeto.id,
            "tipo_evento": tipo_evento.id,
            "tipo": "evento",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
        format="json",
        secure=True,
    )
    assert create_response.status_code == 201, create_response.data
    solicitacao_id = int(create_response.data["id"])
    assert create_response.data["status"] == "pendente"

    # 3) Transicao de estado pendente -> aprovado.
    client.force_authenticate(user=user_super)
    approve_response = client.patch(f"/api/solicitacoes/{solicitacao_id}/approve/", format="json", secure=True)
    assert approve_response.status_code == 200, approve_response.data
    assert approve_response.data["solicitacao"]["status"] == "aprovado"

    # 4) Publish com task mockada (deterministico, sem dependencia externa real).
    mock_task_result = MagicMock()
    mock_task_result.id = "task-chain-001"

    with patch("apps.core.tasks.task_publish_solicitacao_to_gcal.delay", return_value=mock_task_result) as mock_delay:
        client.force_authenticate(user=user_controle)
        publish_response = client.post(f"/api/solicitacoes/{solicitacao_id}/publish/", format="json", secure=True)

    assert publish_response.status_code == 202, publish_response.data
    assert publish_response.data["task_id"] == "task-chain-001"
    mock_delay.assert_called_once()

    solicitacao = Solicitacao.objects.get(pk=solicitacao_id)
    assert solicitacao.status == "aprovado"
    assert solicitacao.gcal_status == Solicitacao.GCalStatus.PENDING

    logs = AuditLog.objects.filter(action="PUBLISH_GCAL_REQUESTED", model_name="Solicitacao")
    assert any((log.details or {}).get("solicitacao_id") == solicitacao_id for log in logs)


def test_invalid_path_blocks_solicitacao_when_pair_municipio_projeto_has_no_compra():
    """
    Fluxo invalido esperado:
    municipio/projeto sem compra elegivel deve retornar 400 com erro claro.
    """
    client = APIClient()

    # PR-A1 DAT-Imports (2026-04-29): import-compras agora é DAT-only.
    user_controle = _create_user_in_group(prefix="dat_invalid", group_name="DAT")
    user_coordenador = _create_user_in_group(prefix="coord_invalid", group_name="Coordenador")

    municipio = Municipio.objects.create(nome="Sobral", uf="CE", ativo=True)
    projeto_com_compra = Projeto.objects.create(nome="Novo Lendo", codigo="NL2", fluxo="SUPER", ativo=True)
    projeto_sem_compra = Projeto.objects.create(nome="ACerta", codigo="AC", fluxo="SUPER", ativo=True)
    tipo_evento = TipoEvento.objects.create(nome="Acompanhamento")

    # Import cria compra somente para "Novo Lendo".
    client.force_authenticate(user=user_controle)
    import_report = _upload_compras_csv(
        client,
        codigo="COMP-CHAIN-002",
        produto="LIVRO NOVO LENDO",
        municipio=municipio.nome,
        uf=municipio.uf,
    )
    assert import_report["stats"]["created"] == 1
    assert Compra.objects.filter(municipio=municipio, projeto=projeto_com_compra).exists()
    assert not Compra.objects.filter(municipio=municipio, projeto=projeto_sem_compra).exists()

    # Tenta criar solicitacao para projeto sem compra => bloqueio.
    client.force_authenticate(user=user_coordenador)
    inicio = timezone.now() + timedelta(days=3)
    fim = inicio + timedelta(hours=2)
    create_response = client.post(
        "/api/solicitacoes/",
        {
            "municipio": municipio.id,
            "projeto": projeto_sem_compra.id,
            "tipo_evento": tipo_evento.id,
            "tipo": "evento",
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat(),
        },
        format="json",
        secure=True,
    )

    assert create_response.status_code == 400
    assert "errors" in create_response.data
    assert "municipio" in create_response.data["errors"]
    assert "compra registrada" in str(create_response.data["errors"]["municipio"]).lower()
