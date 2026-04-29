"""
Testes para endpoints de importação (upload/permissions).

Valida:
- RBAC: HasPerm("import_spreadsheet") para imports de COMPRAS e AÇÕES
- RBAC: HasPerm("manage_admin_registries") para imports de CADASTROS
- Upload de arquivo com multipart/form-data
- Trailing slashes nas rotas
- Resposta 200 OK com dry_run=true
- Resposta 403 Forbidden para usuários sem permissão
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOperatorIssue=false, reportOptionalSubscript=false, reportUnknownLambdaType=false

from __future__ import annotations

import io
from unittest.mock import patch

from django.contrib.auth.models import Group
from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario

pytestmark = pytest.mark.django_db


def _file(bytes_: bytes, name="sample.csv"):
    """Helper para criar arquivo em memória."""
    f = io.BytesIO(bytes_)
    f.name = name
    return f


def _user_in_group(group_name: str):
    """Helper para criar usuário em grupo específico."""
    u = Usuario.objects.create_user(
        username=f"u{group_name}",
        email=f"{group_name}@x.com",
        password="x",
        cpf="1" * 11,
    )
    g, _ = Group.objects.get_or_create(name=group_name)
    u.groups.add(g)
    return u


def test_import_compras_requires_dat():
    """PR-A1 DAT-Imports: import de COMPRAS requer grupo DAT."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    csv_data = b"codigo,produto,quant,municipio,uf,data,uso\nC1,X,10,Acarape,CE,2025-01-01,Formacao\n"

    r = client.post(
        "/api/controle/import-compras/?dry_run=true",
        {"file": _file(csv_data)},
        format="multipart",
    )

    assert r.status_code == 200
    assert r.json()["dry_run"] is True


def test_import_acoes_requires_dat():
    """PR-A1 DAT-Imports: import de AÇÕES requer grupo DAT."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    csv_data = b"Municipio,Projeto,Coordenador,Data da Entrega,Data Reuniao Alinhamento,Observacao\nAcarape,Gestao Escolar,coord@test.com,2025-01-10,2025-01-20,ok\n"

    with patch("apps.core.views_imports.import_acoes_controle") as mock_import:
        mock_import.return_value = {"stats": {}, "pendencias": {}, "dry_run": True, "file": "mock.csv"}

        r = client.post(
            "/api/controle/import-acoes/?dry_run=true",
            {"file": _file(csv_data)},
            format="multipart",
        )

    assert r.status_code == 200
    assert r.json()["dry_run"] is True
    assert mock_import.call_count == 1
    assert "file_path" in mock_import.call_args.kwargs
    assert "path" not in mock_import.call_args.kwargs
    assert mock_import.call_args.kwargs["dry_run"] is True


def test_import_cadastros_requires_dat():
    """Import de CADASTROS requer grupo DAT."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    csv_data = b"Municipio,Projeto,Tipo de acao,Responsavel,Observacao,Data\nAcarape,Gestao Escolar,Criar curso,dat@test.com,ok,2025-04-01\n"

    with patch("apps.core.views_imports.import_dat_cadastros") as mock_import:
        mock_import.return_value = {"stats": {}, "pendencias": {}, "dry_run": True, "file": "mock.csv"}

        r = client.post(
            "/api/dat/import-cadastros/?dry_run=true",
            {"file": _file(csv_data)},
            format="multipart",
        )

    assert r.status_code == 200
    assert r.json()["dry_run"] is True
    assert mock_import.call_count == 1
    assert "file_path" in mock_import.call_args.kwargs
    assert "path" not in mock_import.call_args.kwargs
    assert mock_import.call_args.kwargs["dry_run"] is True


def test_import_unauthorized_returns_403():
    """Usuário sem permissão recebe 403 Forbidden."""
    user = Usuario.objects.create_user(
        username="plain",
        email="plain@test.com",
        password="x",
        cpf="2" * 11,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    r = client.post(
        "/api/controle/import-acoes/?dry_run=true",
        {"file": _file(b"x")},
        format="multipart",
    )

    assert r.status_code == 403


def test_import_acoes_without_file_returns_400():
    """Import sem arquivo retorna 400 Bad Request."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    r = client.post("/api/controle/import-acoes/?dry_run=true", {})

    assert r.status_code == 400
    assert "file" in r.json()["detail"].lower()


def test_import_cadastros_without_file_returns_400():
    """Import sem arquivo retorna 400 Bad Request."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    r = client.post("/api/dat/import-cadastros/?dry_run=true", {})

    assert r.status_code == 400
    assert "file" in r.json()["detail"].lower()


def test_trailing_slash_in_import_endpoints():
    """Endpoints de import devem ter trailing slash."""
    user = _user_in_group("DAT")
    client = APIClient()
    client.force_authenticate(user=user)

    csv_data = b"x"

    # Com trailing slash (correto)
    r1 = client.post(
        "/api/controle/import-compras/?dry_run=true",
        {"file": _file(csv_data)},
        format="multipart",
    )

    # 200 ou 500 (erro de parse), mas não 404
    assert r1.status_code != 404

    # Sem trailing slash (deve redirecionar ou funcionar via APPEND_SLASH)
    r2 = client.post(
        "/api/controle/import-compras?dry_run=true",
        {"file": _file(csv_data)},
        format="multipart",
    )

    # 200, 500 ou 301 (redirect), mas não 404
    assert r2.status_code != 404
