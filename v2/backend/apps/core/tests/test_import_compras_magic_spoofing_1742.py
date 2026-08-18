"""
S6 (#1742): anti-spoofing (magic bytes) no import de Compras.

Fix sob teste (apps/core/views_controle_imports.py — ImportComprasView.post):
o handler agora chama `validate_upload(upload)` (tamanho + Content-Type + MAGIC
BYTES) antes de processar, em vez de checar apenas size + content_type.

Prova do RED (por que falharia SEM o fix):
    O código antigo confiava só no header Content-Type (spoofável pelo cliente).
    Um upload com Content-Type "text/csv" mas conteúdo binário PNG passaria e o
    import seguiria — a resposta NÃO seria um 400 de validação com a mensagem
    "não corresponde ao tipo declarado". Com o fix, `validate_upload` inspeciona
    os magic bytes (image/png ≠ CSV/XLS/XLSX) e devolve 400. Mesmo sem libmagic,
    `UPLOAD_MAGIC_FAIL_OPEN=False` força fail-closed → 400.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

import pytest

from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

IMPORT_COMPRAS_URL = "/api/controle/import-compras/?dry_run=true"

# Assinatura PNG (8 bytes) + preenchimento — magic bytes de imagem, jamais de CSV/XLS.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64

# CSV válido, mesmo shape do teste de sucesso existente (test_import_endpoints.py).
VALID_CSV = b"codigo,produto,quant,municipio,uf,data,uso\nC1,X,10,Acarape,CE,2025-01-01,Formacao\n"


def _dat_client(cpf: str) -> APIClient:
    """APIClient autenticado como usuário do grupo DAT (detentor de
    import_spreadsheet via seed RBAC)."""
    user = UsuarioFactory(username=f"dat_s6_{cpf}", cpf=cpf, groups=["DAT"])
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@override_settings(UPLOAD_MAGIC_FAIL_OPEN=False)
def test_import_compras_rejects_png_spoofed_as_csv():
    """Conteúdo PNG com Content-Type text/csv é rejeitado com 400 (anti-spoofing)."""
    client = _dat_client("90000000201")
    spoofed = SimpleUploadedFile("compras.csv", PNG_MAGIC, content_type="text/csv")

    r = client.post(IMPORT_COMPRAS_URL, {"file": spoofed}, format="multipart")

    assert r.status_code == status.HTTP_400_BAD_REQUEST, r.content
    assert "não corresponde" in r.json()["detail"].lower()


def test_import_compras_valid_csv_dry_run_ok():
    """Não-regressão: um CSV válido em dry_run continua retornando 200."""
    client = _dat_client("90000000202")
    valid = SimpleUploadedFile("compras.csv", VALID_CSV, content_type="text/csv")

    r = client.post(IMPORT_COMPRAS_URL, {"file": valid}, format="multipart")

    assert r.status_code == status.HTTP_200_OK, r.content
    assert r.json()["dry_run"] is True
