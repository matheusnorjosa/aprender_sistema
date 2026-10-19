"""
P27 (item 22 da lista de liberação, 19/10/2026): conta criada sem senha não ganha senha inventada.

O importador de usuários gravava uma senha aleatória que ninguém via; a tela de Usuários, sem senha
no formulário, deixava o campo vazio, que o Django trata como senha utilizável. Agora as duas criam
a conta com `set_unusable_password()`: a senha é definida depois, pela tela de Usuários.

Os CPFs aqui são sintéticos.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportAttributeAccessIssue=false, reportIndexIssue=false

from __future__ import annotations

from rest_framework.test import APIClient

import pytest

from apps.core.models import Usuario
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db


def test_importador_cria_conta_sem_senha(tmp_path):
    arquivo = tmp_path / "usuarios.csv"
    arquivo.write_text("cpf,nome,email\n10000000019,Maria Silva,maria.silva@example.invalid\n", encoding="utf-8")

    resultado = import_usuarios_from_file(path=str(arquivo), dry_run=False)

    assert resultado["stats"]["created"] == 1
    assert Usuario.objects.get(cpf="10000000019").has_usable_password() is False


def _client(user) -> APIClient:
    c = APIClient()
    c.force_authenticate(user)
    return c


def test_tela_de_usuarios_sem_senha_cria_conta_sem_senha():
    resp = _client(UsuarioFactory(superuser=True)).post(
        "/api/usuarios-admin/",
        {"username": "10000000795", "cpf": "10000000795", "email": "joao@example.invalid", "first_name": "Joao"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert Usuario.objects.get(pk=resp.data["id"]).has_usable_password() is False


def test_tela_de_usuarios_com_senha_continua_gravando_a_senha():
    resp = _client(UsuarioFactory(superuser=True)).post(
        "/api/usuarios-admin/",
        {
            "username": "10000001163",
            "cpf": "10000001163",
            "email": "ana@example.invalid",
            "first_name": "Ana",
            "password": "Senha-Forte-2026!",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    conta = Usuario.objects.get(pk=resp.data["id"])
    assert conta.has_usable_password() is True
    assert conta.check_password("Senha-Forte-2026!")
