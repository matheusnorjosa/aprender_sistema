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

from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import AvailabilityBlock, ImportJob
from apps.core.tests.factories import UsuarioFactory

UPLOAD_URL = "/api/imports/bloqueios/"


@pytest.fixture
def controle_user(db):
    # O seed RBAC (incl. pos-truncate de transaction=True) e garantido globalmente
    # pela fixture autouse `ensure_rbac_seed` (conftest raiz, #1402).
    return UsuarioFactory(
        username="ctrl_intg",
        email="ctrl_intg@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Ctrl",
        last_name="Intg",
        groups=["Controle"],
    )


@pytest.fixture
def target_user(db):
    return UsuarioFactory(
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


@pytest.fixture
def malformed_csv():
    """CSV que parseia mas referencia usuário inexistente → linha pulada."""
    content = "usuario,inicio,fim,tipo,motivo\n" "Fulano Inexistente Zzz,2026-03-01 08:00,2026-03-01 12:00,P,Consulta\n"
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


@pytest.mark.django_db
class TestImportBloqueiosPermissions:
    """Adversarial: autenticação, permissão e validação de entrada no upload."""

    def test_upload_requires_authentication(self, api_client):
        """Sem autenticação → 403 (SessionAuthentication rebaixa 401→403)."""
        resp = api_client.post(UPLOAD_URL, {}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_forbidden_for_non_privileged_user(self, api_client, target_user, sample_csv):
        """Usuário sem a policy import_generic_spreadsheet (não-Controle/DAT) → 403."""
        api_client.force_authenticate(user=target_user)
        with open(sample_csv, "rb") as f:
            resp = api_client.post(UPLOAD_URL, {"file": f}, format="multipart")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_without_file_returns_400(self, api_client, controle_user):
        """POST sem o campo 'file' → 400 (validação antes de despachar a task)."""
        api_client.force_authenticate(user=controle_user)
        resp = api_client.post(UPLOAD_URL, {}, format="multipart")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db(transaction=True)
class TestImportBloqueiosMalformed:
    """Adversarial: CSV válido mas com dados ruins → job SUCCESS com linhas puladas (nunca FAILED)."""

    @pytest.fixture(autouse=True)
    def _celery_eager(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.CELERY_TASK_EAGER_PROPAGATES = True

    def test_malformed_csv_pula_linhas_job_success(self, api_client, controle_user, malformed_csv):
        api_client.force_authenticate(user=controle_user)

        with open(malformed_csv, "rb") as f:
            post = api_client.post(
                UPLOAD_URL + "?dry_run=false",
                {"file": f},
                format="multipart",
            )

        # A entrada é aceita (202) — dados ruins não abortam o upload.
        assert post.status_code == status.HTTP_202_ACCEPTED
        job_id = post.data["id"]

        detail = api_client.get(f"/api/imports/{job_id}/")
        assert detail.status_code == status.HTTP_200_OK

        # Linhas inválidas são puladas com segurança: job termina SUCCESS, não FAILED,
        # e nada é persistido (usuário inexistente → skip, sem levantar).
        assert detail.data["status"] == ImportJob.Status.SUCCESS
        assert detail.data["stats"]["created"] == 0
        assert AvailabilityBlock.objects.count() == 0
