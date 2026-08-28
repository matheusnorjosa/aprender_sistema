"""
#1894 — Usuario.desativado_localmente: representação persistente da desativação LOCAL.

A planilha (fonte) não é corrigida e marca pessoas como ativas (caso Elienai). Regra do dono:
o import não reativa quem foi desativado NO SISTEMA. `desativado_localmente` distingue a
desativação local (admin) da que veio da planilha:
- admin desativa (is_active True->False) => desativado_localmente=True;
- admin reativa (False->True) => limpa a flag;
- o import bloqueia reativação (False->True) SÓ quando desativado_localmente=True — refinando o
  #1891/#1902 (que bloqueava TODA reativação). A planilha pode reativar quem ela mesma desativou.
"""

# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportOptionalMemberAccess=false, reportAttributeAccessIssue=false, reportArgumentType=false, reportMissingTypeArgument=false, reportCallIssue=false, reportIndexIssue=false, reportOptionalSubscript=false

from __future__ import annotations

from rest_framework.test import APIRequestFactory

import pytest

from apps.core.models import Usuario
from apps.core.serializers import UsuarioAdminSerializer
from apps.core.services.usuarios_import import import_usuarios_from_file
from apps.core.tests.factories import UsuarioFactory

pytestmark = pytest.mark.django_db

User = Usuario


def _write_csv(tmp_path, content: str) -> str:
    p = tmp_path / "usuarios.csv"
    p.write_text(content, encoding="utf-8")
    return str(p)


def _admin_save(instance, data, actor):
    """Persiste via UsuarioAdminSerializer com um ator (caminho admin real)."""
    req = APIRequestFactory().patch(f"/api/usuarios/{instance.pk}/", data)
    req.user = actor
    ser = UsuarioAdminSerializer(instance=instance, data=data, partial=True, context={"request": req})
    ser.is_valid(raise_exception=True)
    return ser.save()


class TestFieldDefault:
    def test_desativado_localmente_defaults_false(self):
        assert UsuarioFactory().desativado_localmente is False


class TestAdminDeactivationMarksLocal:
    def test_admin_deactivate_sets_flag(self):
        admin = UsuarioFactory(superuser=True, cpf="10000000009")
        target = UsuarioFactory(is_active=True, cpf="10000005673")

        _admin_save(target, {"is_active": False}, admin)

        target.refresh_from_db()
        assert target.is_active is False
        assert target.desativado_localmente is True, "desativação pelo admin marca decisão LOCAL"

    def test_admin_reactivate_clears_flag(self):
        admin = UsuarioFactory(superuser=True, cpf="10000000009")
        target = UsuarioFactory(is_active=False, desativado_localmente=True, cpf="10000005673")

        _admin_save(target, {"is_active": True}, admin)

        target.refresh_from_db()
        assert target.is_active is True
        assert target.desativado_localmente is False, "reativar (ação humana) limpa a flag"


class TestImportRespectsLocalFlag:
    def test_import_does_not_reactivate_locally_deactivated(self, tmp_path):
        UsuarioFactory(cpf="10000005673", is_active=False, desativado_localmente=True)
        path = _write_csv(tmp_path, "cpf,nome,ativo\n10000005673,Fulano De Tal,sim\n")

        import_usuarios_from_file(path=path, dry_run=False)

        assert User.objects.get(cpf="10000005673").is_active is False, "import NÃO reativa desligado LOCAL"

    def test_import_can_reactivate_sheet_deactivated(self, tmp_path):
        # Refinamento vs #1902: quem NÃO foi desativado localmente PODE ser reativado pela planilha.
        UsuarioFactory(cpf="10000005673", is_active=False, desativado_localmente=False)
        path = _write_csv(tmp_path, "cpf,nome,ativo\n10000005673,Fulano De Tal,sim\n")

        import_usuarios_from_file(path=path, dry_run=False)

        assert User.objects.get(cpf="10000005673").is_active is True, "planilha reativa quem ela mesma desativou"
