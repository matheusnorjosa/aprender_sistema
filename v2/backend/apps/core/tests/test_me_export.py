"""LGPD art. 18-V (portabilidade) — export self-service em GET /api/me/export/.

O titular baixa o próprio dossiê; o escopo é sempre `request.user` (não há como
exportar dados de outro). A exportação é auditada (EXPORT, o FATO). O serviço
`build_lgpd_export_data` é o SSOT compartilhado com o command `lgpd_export`.
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportIndexIssue=false

from __future__ import annotations

import json

from rest_framework.test import APIClient

import pytest

from apps.core.models import AuditLog
from apps.core.services.lgpd_export_service import build_lgpd_export_data
from apps.core.tests.factories import UsuarioFactory

ME_EXPORT_URL = "/api/me/export/"


# ------------------------- serviço (SSOT) -------------------------


@pytest.mark.django_db
def test_build_lgpd_export_data_traz_dados_do_titular():
    user = UsuarioFactory(cpf="11144477735", telefone="(85) 90000-0000", cargo="Coordenadora")
    data = build_lgpd_export_data(user)

    assert data["personal_data"]["cpf"] == "11144477735"
    assert data["personal_data"]["telefone"] == "(85) 90000-0000"
    assert data["export_info"]["purpose"].startswith("LGPD Data Portability")
    # Seções esperadas presentes (listas mesmo que vazias).
    for key in ("solicitations_created", "events_as_formador", "availability_blocks", "approvals_made"):
        assert isinstance(data[key], list)


# ------------------------- endpoint self-service -------------------------


@pytest.mark.django_db
def test_get_export_baixa_json_do_proprio_titular_e_audita():
    user = UsuarioFactory(cpf="11144477735")
    client = APIClient()
    client.force_authenticate(user=user)

    resp = client.get(ME_EXPORT_URL)

    assert resp.status_code == 200
    assert resp["Content-Disposition"] == 'attachment; filename="meus-dados-aprender.json"'
    body = json.loads(resp.content)
    assert body["personal_data"]["cpf"] == "11144477735"
    # Trilha do FATO (art. 37): EXPORT self-service, sem valores de PII no details.
    log = AuditLog.objects.filter(usuario=user, action=AuditLog.Action.EXPORT).first()
    assert log is not None
    assert log.details["channel"] == "self-service"
    assert log.details["target_user_id"] == user.pk
    assert "cpf" not in json.dumps(log.details)


@pytest.mark.django_db
def test_export_e_escopado_ao_proprio_usuario():
    eu = UsuarioFactory(cpf="11144477735")
    outro = UsuarioFactory(cpf="22255588846")
    client = APIClient()
    client.force_authenticate(user=eu)

    body = json.loads(client.get(ME_EXPORT_URL).content)

    assert body["personal_data"]["cpf"] == "11144477735"
    assert outro.cpf not in json.dumps(body)


@pytest.mark.django_db
def test_export_exige_autenticacao():
    resp = APIClient().get(ME_EXPORT_URL)
    assert resp.status_code in (401, 403)
