"""
Teste de integracao end-to-end do pipeline assincrono (ASQ-005 fase 1 — #778).

Usa CELERY_TASK_ALWAYS_EAGER=True para executar a task no mesmo thread do
request, sem depender de worker Celery real. Verifica que POST -> task roda
inline -> GET retorna SUCCESS com stats reais (service de verdade, nao mock).
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
# pyright: reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false

from __future__ import annotations

import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, ImportJob

User = get_user_model()

UPLOAD_URL = "/api/imports/bloqueios/"


@pytest.fixture
def controle_user(db):
    # O seed RBAC (incl. pos-truncate de transaction=True) e garantido globalmente
    # pela fixture autouse `ensure_rbac_seed` (conftest raiz, #1402).
    user = User.objects.create_user(
        username="ctrl_intg",
        email="ctrl_intg@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Ctrl",
        last_name="Intg",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def target_user(db):
    return User.objects.create_user(
        username="target_intg",
        email="target_intg@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Target",
        last_name="Intg",
    )


@pytest.fixture
def sample_csv(target_user):
    content = (
        "usuario,inicio,fim,tipo,motivo\n"
        f"{target_user.first_name} {target_user.last_name},"
        "2026-03-01 08:00,2026-03-01 12:00,P,Consulta medica\n"
        f"{target_user.first_name} {target_user.last_name},"
        "2026-03-05 00:00,2026-03-05 23:59,T,Ferias\n"
    )
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db(transaction=True)
class TestAsyncPipelineEndToEnd:
    """POST -> task eager -> GET: fluxo completo sem worker."""

    @pytest.fixture(autouse=True)
    def _celery_eager(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.CELERY_TASK_EAGER_PROPAGATES = True

    def test_dry_run_full_pipeline(self, api_client, controle_user, target_user, sample_csv):
        api_client.force_authenticate(user=controle_user)

        with open(sample_csv, "rb") as f:
            post = api_client.post(
                UPLOAD_URL + "?dry_run=true",
                {"file": f},
                format="multipart",
            )

        assert post.status_code == status.HTTP_202_ACCEPTED
        job_id = post.data["id"]

        # Em eager mode, a task ja rodou ao chegar aqui
        detail = api_client.get(f"/api/imports/{job_id}/")
        assert detail.status_code == status.HTTP_200_OK

        payload = detail.data
        assert payload["status"] == ImportJob.Status.SUCCESS
        assert payload["stats"]["created"] == 2
        assert payload["finished_at"] is not None
        assert payload["duration_ms"] is not None

        # dry_run: nenhum bloqueio persistido
        assert AvailabilityBlock.objects.count() == 0

    def test_apply_full_pipeline_persists(self, api_client, controle_user, target_user, sample_csv):
        api_client.force_authenticate(user=controle_user)

        with open(sample_csv, "rb") as f:
            post = api_client.post(
                UPLOAD_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        assert post.status_code == status.HTTP_202_ACCEPTED
        job_id = post.data["id"]

        detail = api_client.get(f"/api/imports/{job_id}/")
        assert detail.status_code == status.HTTP_200_OK
        assert detail.data["status"] == ImportJob.Status.SUCCESS
        assert detail.data["stats"]["created"] == 2

        # Apply mode: bloqueios persistidos de verdade
        assert AvailabilityBlock.objects.filter(usuario=target_user).count() == 2
