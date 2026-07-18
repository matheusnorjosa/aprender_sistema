"""Testes do admin action `export_usuarios_sem_cpf` — sanitização CSV (SEC-007).

Garante que o export de "usuários sem CPF" neutraliza formula injection nos
campos controlados pelo usuário (nome, cargo) antes de escrever o CSV — tanto na
resposta HTTP quanto no arquivo de auditoria.

Não pertence a `test_admin_user_security.py` (esse cobre o serializer DRF).
"""

from __future__ import annotations

from pathlib import Path

from django.test import RequestFactory

import pytest

from apps.core.admin import UsuarioAdmin
from apps.core.admin_site import admin_site
from apps.core.models import Usuario
from apps.core.tests.factories import UsuarioFactory


@pytest.mark.django_db
def test_export_usuarios_sem_cpf_neutraliza_formula(tmp_path: Path, settings) -> None:  # noqa: ANN001
    # Redireciona a escrita do arquivo de auditoria para um dir temporário.
    settings.IMPORT_OUTPUT_DIR = str(tmp_path)

    # Vetor fiel: a fórmula viaja em first_name (compõe nome_completo) e em cargo.
    # (ORM bypassa o UnicodeUsernameValidator; o vetor realista é nome/cargo, não
    # username.) cpf="" garante que o usuário entra no recorte "sem CPF".
    UsuarioFactory(
        username="user_formula",
        first_name="=cmd",
        last_name="",
        cargo="=HYPERLINK(1)",
        cpf="",
    )

    admin_obj = UsuarioAdmin(Usuario, admin_site)
    request = RequestFactory().get("/admin/")
    queryset = Usuario.objects.all()

    response = admin_obj.export_usuarios_sem_cpf(request, queryset)

    # Nome e cargo saem neutralizados com prefixo ' na resposta HTTP.
    assert b"'=cmd" in response.content
    assert b"'=HYPERLINK(1)" in response.content

    # A fórmula crua (célula começando com '=') não deve aparecer sem prefixo.
    assert b",=cmd" not in response.content
    assert b",=HYPERLINK(1)" not in response.content

    # O arquivo de auditoria também deve estar sanitizado.
    audit_file = tmp_path / "usuarios_sem_cpf.csv"
    assert audit_file.exists()
    audit_content = audit_file.read_bytes()
    assert b"'=cmd" in audit_content
    assert b"'=HYPERLINK(1)" in audit_content
