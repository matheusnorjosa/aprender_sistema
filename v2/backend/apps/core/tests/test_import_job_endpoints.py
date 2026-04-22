"""
Testes dos endpoints async de import (ASQ-005 fase 1 — #778).

Endpoints testados:
    POST   /api/imports/bloqueios/
    GET    /api/imports/
    GET    /api/imports/<id>/

Cobertura:
- POST cria ImportJob + despacha task (202 Accepted)
- Permissoes: Formador 403, anonimo 401/403
- Validacoes: file ausente 400, MIME invalido 400
- GET detail owner retorna payload completo sem error_traceback
- GET detail non-owner sem super -> 404 (IDOR guard)
- GET detail super em job de outro usuario -> 200
- GET list filtra por owner (nao super) e suporta ?import_type=, ?status=
"""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportAttributeAccessIssue=false
# pyright: reportUnknownParameterType=false, reportMissingParameterType=false
# pyright: reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportArgumentType=false, reportOptionalMemberAccess=false

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.models import ImportJob

UPLOAD_URL = "/api/imports/bloqueios/"
LIST_URL = "/api/imports/"


User = get_user_model()


@pytest.fixture
def controle_user(db):
    user = User.objects.create_user(
        username="ctrl_imp",
        email="ctrl_imp@test.com",
        password="testpass123",
        cpf="11111111111",
        first_name="Ctrl",
        last_name="Imp",
    )
    group, _ = Group.objects.get_or_create(name="Controle")
    user.groups.add(group)
    return user


@pytest.fixture
def formador_user(db):
    user = User.objects.create_user(
        username="frm_imp",
        email="frm_imp@test.com",
        password="testpass123",
        cpf="22222222222",
        first_name="Frm",
        last_name="Imp",
    )
    group, _ = Group.objects.get_or_create(name="Formador")
    user.groups.add(group)
    return user


@pytest.fixture
def super_user(db):
    return User.objects.create_superuser(
        username="super_imp",
        email="super_imp@test.com",
        password="testpass123",
        cpf="33333333333",
        first_name="Super",
        last_name="Imp",
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_csv():
    content = "usuario,inicio,fim,tipo,motivo\nAlice,2026-03-01 08:00,2026-03-01 12:00,P,X\n"
    temp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    temp.write(content)
    temp.close()
    yield temp.name
    Path(temp.name).unlink(missing_ok=True)


# =============================================================================
# POST /api/imports/bloqueios/
# =============================================================================


@pytest.mark.django_db
class TestUploadEndpoint:
    def test_controle_upload_creates_job_and_dispatches_task(self, api_client, controle_user, sample_csv):
        api_client.force_authenticate(user=controle_user)

        mocked_async = MagicMock(id="celery-id-abc")
        with patch("apps.core.tasks.task_run_import_job.delay", return_value=mocked_async) as mocked_delay:
            with open(sample_csv, "rb") as f:
                response = api_client.post(
                    UPLOAD_URL + "?dry_run=true",
                    {"file": f},
                    format="multipart",
                )

        assert response.status_code == status.HTTP_202_ACCEPTED
        payload = response.data
        assert payload["status"] == ImportJob.Status.QUEUED
        assert payload["import_type"] == ImportJob.ImportType.BLOQUEIOS
        assert payload["dry_run"] is True
        assert payload["celery_task_id"] == "celery-id-abc"
        # error_traceback NUNCA deve vazar na resposta
        assert "error_traceback" not in payload

        # ImportJob foi persistido
        job = ImportJob.objects.get(id=payload["id"])
        assert job.user_id == controle_user.id
        assert job.file.name.endswith(".csv")

        # Task foi despachada com o id correto
        mocked_delay.assert_called_once_with(job.id)

    def test_formador_forbidden(self, api_client, formador_user, sample_csv):
        api_client.force_authenticate(user=formador_user)
        with open(sample_csv, "rb") as f:
            response = api_client.post(UPLOAD_URL, {"file": f}, format="multipart")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauth_rejected(self, api_client, sample_csv):
        with open(sample_csv, "rb") as f:
            response = api_client.post(UPLOAD_URL, {"file": f}, format="multipart")
        assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}

    def test_missing_file_returns_400(self, api_client, controle_user):
        api_client.force_authenticate(user=controle_user)
        response = api_client.post(UPLOAD_URL, {}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "file" in response.data["detail"].lower()

    def test_invalid_mime_returns_400(self, api_client, controle_user):
        api_client.force_authenticate(user=controle_user)
        fake = SimpleUploadedFile("malware.exe", b"MZ\x90\x00", content_type="application/x-msdownload")
        response = api_client.post(UPLOAD_URL, {"file": fake}, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_dry_run_default_is_true(self, api_client, controle_user, sample_csv):
        api_client.force_authenticate(user=controle_user)
        mocked_async = MagicMock(id="abc")
        with patch("apps.core.tasks.task_run_import_job.delay", return_value=mocked_async):
            with open(sample_csv, "rb") as f:
                response = api_client.post(UPLOAD_URL, {"file": f}, format="multipart")  # sem ?dry_run
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["dry_run"] is True

    def test_dry_run_false_param(self, api_client, controle_user, sample_csv):
        api_client.force_authenticate(user=controle_user)
        mocked_async = MagicMock(id="abc")
        with patch("apps.core.tasks.task_run_import_job.delay", return_value=mocked_async):
            with open(sample_csv, "rb") as f:
                response = api_client.post(UPLOAD_URL + "?dry_run=false", {"file": f}, format="multipart")
        assert response.data["dry_run"] is False


# =============================================================================
# GET /api/imports/<id>/
# =============================================================================


def _create_job(user, *, dry_run: bool = True, import_type: str | None = None) -> ImportJob:
    return ImportJob.objects.create(
        user=user,
        import_type=import_type or ImportJob.ImportType.BLOQUEIOS,
        dry_run=dry_run,
        file=SimpleUploadedFile("x.csv", b"a\n", content_type="text/csv"),
    )


@pytest.mark.django_db
class TestDetailEndpoint:
    def test_owner_sees_own_job(self, api_client, controle_user):
        job = _create_job(controle_user)
        api_client.force_authenticate(user=controle_user)

        response = api_client.get(f"/api/imports/{job.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == job.id
        # Campos sensiveis NAO sao expostos
        assert "error_traceback" not in response.data
        assert "file" not in response.data  # FileField nao expoe path

    def test_non_owner_gets_404_not_403(self, api_client, controle_user, formador_user):
        """IDOR guard: 404 em vez de 403 para nao vazar existencia."""
        job = _create_job(controle_user)
        api_client.force_authenticate(user=formador_user)

        response = api_client.get(f"/api/imports/{job.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_superuser_sees_any_job(self, api_client, controle_user, super_user):
        job = _create_job(controle_user)
        api_client.force_authenticate(user=super_user)

        response = api_client.get(f"/api/imports/{job.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == job.id
        assert response.data["user"]["id"] == controle_user.id

    def test_unauth_rejected(self, api_client, controle_user):
        job = _create_job(controle_user)
        response = api_client.get(f"/api/imports/{job.id}/")
        assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


# =============================================================================
# GET /api/imports/
# =============================================================================


@pytest.mark.django_db
class TestListEndpoint:
    def test_list_scoped_to_owner(self, api_client, controle_user, formador_user):
        mine = _create_job(controle_user)
        _other = _create_job(formador_user)  # noqa: F841

        api_client.force_authenticate(user=controle_user)
        response = api_client.get(LIST_URL)
        assert response.status_code == status.HTTP_200_OK

        ids = [row["id"] for row in response.data["results"]]
        assert mine.id in ids
        assert _other.id not in ids

    def test_list_super_sees_all(self, api_client, controle_user, formador_user, super_user):
        j1 = _create_job(controle_user)
        j2 = _create_job(formador_user)

        api_client.force_authenticate(user=super_user)
        response = api_client.get(LIST_URL)
        ids = [row["id"] for row in response.data["results"]]
        assert j1.id in ids
        assert j2.id in ids

    def test_filter_by_status(self, api_client, controle_user):
        queued = _create_job(controle_user)
        success = _create_job(controle_user)
        success.mark_running(celery_task_id="t")
        success.mark_success(stats={"created": 1}, pendencias={})

        api_client.force_authenticate(user=controle_user)
        response = api_client.get(LIST_URL + "?status=SUCCESS")
        ids = [row["id"] for row in response.data["results"]]
        assert success.id in ids
        assert queued.id not in ids

    def test_filter_by_import_type(self, api_client, controle_user):
        j = _create_job(controle_user, import_type=ImportJob.ImportType.BLOQUEIOS)

        api_client.force_authenticate(user=controle_user)
        response = api_client.get(LIST_URL + "?import_type=bloqueios")
        ids = [row["id"] for row in response.data["results"]]
        assert j.id in ids
